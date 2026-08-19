import json
from src.db import init_db, upsert, set_status
from src.notify import notify_draft
from pathlib import Path
from src.llm import ask

SELECT_SYSTEM = """너는 채용 공고와 지원자의 경험을 매칭하는 분석기다.
주어진 JD와 경험 목록을 보고, 이 공고에 가장 설득력 있는 경험을 3~5개 고른다.

아래 JSON만 출력한다:
{
  "selected": [
    {
      "id": "경험 id",
      "match_reason": "이 공고의 어떤 요구사항과 연결되는지 한 문장",
      "emphasis": "이 경험에서 특히 강조해야 할 측면 한 문장"
    }
  ],
  "gaps": ["JD가 요구하지만 지원자 경험으로 채워지지 않는 항목"]
}

규칙:
- 경험 목록에 없는 id는 절대 만들지 않는다.
- 억지로 연결하지 않는다. 관련 없으면 고르지 않는다.
- gaps는 솔직하게 적는다. 비워두지 않는다.
- 위 스키마에 정의된 키만 사용한다. 임의의 키를 추가하지 않는다.
- 설명이나 코드펜스 없이 JSON만 출력한다."""

WRITE_SYSTEM = """너는 자기소개서 초안을 작성한다.

절대 규칙:
- 제공된 경험의 facts 배열에 있는 내용만 사용한다.
- facts에 없는 수치, 기술, 성과를 절대 추가하지 않는다.
- 추측하거나 미화하지 않는다. 과장된 형용사를 쓰지 않는다.
- 확인되지 않은 내용을 쓰고 싶으면 [확인필요] 로 표시한다.

작성 방식:
- 문항별로 소제목 + 본문 구성
- 각 문항 500~700자
- 구체적 수치를 반드시 포함
- 결론부터 쓰고 근거를 뒤에 배치
- 회사의 culture_keywords를 억지로 나열하지 말고 경험 서술에 자연스럽게 녹인다
- 지원 중인 회사에 노출되면 부적절한 프로젝트(구직 활동 자체를 자동화하는 도구 등)는
  프로젝트명을 그대로 쓰지 말고 기술적 성취만 서술하며 용도는 일반적으로 표현한다
- "최근", "현재" 같은 상대적 시점 표현 대신 연도를 명시한다
- 같은 경험을 여러 문항에서 반복 사용하지 않는다. 문항마다 다른 경험을 배치한다"""


def load(path: str) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select(jd: dict, experiences: list) -> dict:
    """JD에 맞는 경험 원자를 선별한다."""
    summary = [
        {"id": e["id"], "title": e["title"], "skills": e["skills"], "tags": e["tags"]}
        for e in experiences
    ]
    prompt = (
        f"[채용공고]\n{json.dumps(jd, ensure_ascii=False, indent=2)}\n\n"
        f"[지원자 경험 목록]\n{json.dumps(summary, ensure_ascii=False, indent=2)}"
    )
    raw = ask(prompt, system=SELECT_SYSTEM, max_tokens=4000)
    data = json.loads(raw.strip().strip("`").replace("json\n", "", 1))

    # 스키마에 없는 키 제거
    allowed = {"id", "match_reason", "emphasis"}
    data["selected"] = [
        {k: v for k, v in item.items() if k in allowed}
        for item in data["selected"]
    ]
    return data


def write(jd: dict, experiences: list, selection: dict) -> str:
    """선별된 경험만 재료로 자소서 초안을 작성한다."""
    by_id = {e["id"]: e for e in experiences}
    chosen = []
    for s in selection["selected"]:
        exp = by_id.get(s["id"])
        if exp is None:
            print(f"⚠️  존재하지 않는 id 무시: {s['id']}")
            continue
        chosen.append({**exp, "emphasis": s["emphasis"]})

    prompt = (
        f"[채용공고]\n{json.dumps(jd, ensure_ascii=False, indent=2)}\n\n"
        f"[사용 가능한 경험 — 이 안의 facts만 사용할 것]\n"
        f"{json.dumps(chosen, ensure_ascii=False, indent=2)}\n\n"
        f"[문항]\n1. 지원 동기 및 직무 역량\n"
        f"2. 성격의 장점 및 직무 강점\n"
        f"3. 협업 경험 및 입사 후 포부\n"
        f"4. 맺음말 및 다짐 (200~300자, 앞 문항의 핵심을 압축하고 지원 회사명을 명시할 것)"
    )
    return ask(prompt, system=WRITE_SYSTEM, max_tokens=8000)


def run(jd_path: str):
    jd = load(jd_path)
    experiences = load("data/experiences.json")

    selection = select(jd, experiences)
    print("=== 선별된 경험 ===")
    for s in selection["selected"]:
        print(f"  [{s['id']}] {s['match_reason']}")
    print("\n=== 채워지지 않는 요구사항 ===")
    for g in selection.get("gaps", []):
        print(f"  - {g}")

    print("\n자소서 초안 생성 중... (30초~1분 소요)")
    draft = write(jd, experiences, selection)

    out = Path("data/drafts")
    out.mkdir(exist_ok=True)
    company = jd.get("company") or "unknown"
    position = jd.get("position") or "unknown"
    name = f"{company}_{position}".replace("/", "_").replace(" ", "_")
    path = out / f"{name}.md"
    path.write_text(draft, encoding="utf-8")
    print(f"\n초안 저장 → {path}")
    meta_path = out / f"{name}_meta.json"
    meta_path.write_text(
        json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"선별 근거 저장 → {meta_path}")
    
    # DB 갱신
    init_db()
    app_id = upsert(company, position, draft_path=str(path))
    set_status(app_id, "drafted", "자소서 초안 생성 완료")
    print(f"DB 갱신 → id={app_id} | 상태: 초안 생성")

    # 검토 요청 메일 발송
    try:
        notify_draft(company, position, str(path), selection.get("gaps", []))
    except Exception as e:
        print(f"메일 발송 실패(무시하고 계속): {e}")


if __name__ == "__main__":
    import sys
    run(sys.argv[1])