import json
import re
from src.db import init_db, upsert, set_status
from pathlib import Path
from src.llm import ask

SYSTEM = """너는 채용 공고를 구조화하는 분석기다.
주어진 공고 원문을 읽고 아래 스키마의 JSON만 출력한다.

{
  "company": "회사명",
  "position": "직무명",
  "role_type": "ML Engineer | Data Engineer | SW Engineer | Research | 기타 중 하나",
  "domain": "사업 도메인 (예: 반도체/HBM)",
  "required_skills": ["필수 자격요건에서 추출한 기술/역량"],
  "preferred_skills": ["우대사항에서 추출한 기술/역량"],
  "responsibilities": ["담당 업무 요약"],
  "keywords": ["공고에서 반복되거나 강조된 핵심 단어"],
  "culture_keywords": ["인재상/조직문화 관련 표현"],
  "deadline": "YYYY-MM-DD 또는 null"
}

규칙:
- 공고에 없는 내용은 절대 지어내지 않는다. 없으면 빈 배열 또는 null.
- skills는 "Python", "PyTorch"처럼 짧은 명사구로 정규화한다.
- 입력에 사이드바 배너, 다른 회사의 추천 공고, 광고가 섞여 있을 수 있다.
  이는 모두 무시하고 제목에 명시된 단일 공고의 내용만 추출한다.
- 마감일이 "D-14"처럼 상대 표기이거나 불명확하면 null로 둔다.
- 설명, 인사말, 마크다운 코드펜스 없이 JSON만 출력한다."""


def parse_jd(raw_text: str) -> dict:
    """공고 원문을 구조화된 dict로 변환한다."""
    result = ask(raw_text, system=SYSTEM, max_tokens=3000)

    # 혹시 ```json 펜스가 붙어 나오면 제거
    cleaned = re.sub(r"^```(?:json)?|```$", "", result.strip(), flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("JSON 파싱 실패. 원본 응답:\n", result)
        raise e


def parse_file(txt_path: str) -> dict:
    """txt 공고 파일을 읽어 파싱하고, 같은 이름의 .json으로 저장한다."""
    path = Path(txt_path)
    if not path.exists():
        raise FileNotFoundError(
            f"공고 파일이 없습니다: {path.resolve()}\n"
            f"현재 data/jobs 안의 파일: {[p.name for p in Path('data/jobs').glob('*.txt')]}"
        )
    raw = path.read_text(encoding="utf-8")

    data = parse_jd(raw)

    out_path = path.with_suffix(".json")
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료 → {out_path}")
    # DB에 등록
    init_db()
    company = data.get("company") or "unknown"
    position = data.get("position") or "unknown"
    app_id = upsert(
        company,
        position,
        deadline=data.get("deadline"),
        jd_path=str(out_path),
    )
    set_status(app_id, "parsed", "공고 파싱 완료")
    print(f"DB 등록 → id={app_id} | {company} / {position}")
    empty = [k for k in ("required_skills", "preferred_skills", "responsibilities")
             if not data.get(k)]
    if empty:
        print(f"⚠️  비어있는 필드: {empty} — 원문에 해당 내용이 있는지 확인하세요.")
    return data


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python -m src.jd_parser <공고파일경로>")
        print("예시:   python -m src.jd_parser data/jobs/wizkorea_ai_agent.txt")
        sys.exit(1)

    result = parse_file(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))