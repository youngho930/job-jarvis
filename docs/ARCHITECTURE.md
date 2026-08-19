# Job Jarvis 구조 레퍼런스

취업 지원 자동화 AI 에이전트. 채용공고를 수집·분석해 자소서 초안을 만들고,
지원 이력을 관리하며, 마감이 다가오면 메일로 알려준다.

이 문서는 **전체 구조와 각 부분이 왜 그렇게 만들어졌는지**를 설명한다.
사용법은 `USAGE.md`, 다른 PC 세팅은 `SETUP.md` 참고.

---

## 1. 한눈에 보는 전체 흐름

```
   [수집]              [처리]                    [저장]          [알림]

워크넷 공채속보 API
     │
     ├─→ collector.py ── 키워드 필터 ────────────→ db.py ──→ SQLite
     │                                              │
채용공고 텍스트                                      │
     │                                              │
     ├─→ reader.py ──── 파일 형식별 추출 (txt/pdf)  │
     │        │                                     │
     │        ↓                                     │
     ├─→ jd_parser.py ── LLM으로 구조화 → JSON ────→┤
     │        │                                     │
     │        ↓                                     │
     ├─→ draft.py ───── ① 경험 선별                 │
     │        │         ② 자소서 작성 ──→ .md 파일  │
     │        │                                     │
     │        └─────────────────────────────────────┴──→ notify.py
     │                                                       │
     │                                                       ↓
     │                                                  mailer.py
     │                                                       │
     │                                                       ↓
     │                                                 [메일 도착]
     │                                                  ↓        ↓
     │                                           승인 버튼    gaps 확인
     │                                                  ↓
     └─→ server.py ── 버튼 클릭 처리 ──→ db.py ──→ 상태 변경

  [조회]                              [자동 실행]
  cli.py     터미널에서 목록·통계      daily.py ← Windows 작업 스케줄러
  app.py     웹 대시보드                        (매일 9시)
```

---

## 2. 파일별 역할

### 코어 모듈

| 파일 | 한 줄 설명 | 의존하는 것 |
|---|---|---|
| `src/llm.py` | Claude API 호출 창구. 모든 AI 요청이 여기를 지난다 | - |
| `src/collector.py` | 워크넷 공채속보 API로 공고 수집 | `db` |
| `src/reader.py` | 파일에서 텍스트 추출. txt/pdf 형식별 분기 | - |
| `src/jd_parser.py` | 공고 원문 → 구조화 JSON | `llm`, `reader`, `db` |
| `src/draft.py` | 경험 매칭 + 자소서 초안 생성 | `llm`, `db`, `notify` |
| `src/db.py` | SQLite 저장·조회. 상태 관리의 중심 | - |

### 부가 모듈

| 파일 | 한 줄 설명 | 의존하는 것 |
|---|---|---|
| `src/mailer.py` | Gmail SMTP로 메일 발송 | - |
| `src/notify.py` | 메일 내용(HTML) 구성 | `db`, `mailer` |
| `src/server.py` | 승인 버튼 처리 웹서버 (FastAPI) | `db` |
| `src/cli.py` | 터미널에서 목록·통계·상태변경 | `db` |
| `src/daily.py` | 스케줄러가 호출하는 작업 묶음 | `db`, `notify` |
| `app.py` | 웹 대시보드 (Streamlit) | `db` |

### 데이터 파일

| 경로 | 내용 | 중요도 | Git |
|---|---|---|---|
| `data/experiences.json` | **내 경험 원자 DB.** 자소서의 유일한 재료 | ★★★ | 제외 |
| `data/experiences.example.json` | 구조 설명용 예시 | ★ | 포함 |
| `data/jarvis.db` | 지원 이력 (SQLite) | ★★★ | 제외 |
| `data/jobs/*.txt` | 공고 원문 | ★ | 제외 |
| `data/jobs/*.json` | 파싱된 공고 | ★ | 제외 |
| `data/drafts/*.md` | 생성된 자소서 초안 | ★★ | 제외 |
| `data/drafts/*_meta.json` | 선별 근거 + gaps | ★★ | 제외 |
| `data/notes.md` | 실험 기록 | ★★ | 제외 |
| `data/scheduler.log` | 자동 실행 로그 | ★ | 제외 |
| `.env` | API 키, 메일 비밀번호 | ★★★ | **절대 제외** |

개인정보·자격증명은 전부 `.gitignore`로 제외했다. 저장소에는 코드와 문서만 올라간다.

**의존 방향이 한쪽으로만 흐른다.** `db.py`는 아무것도 의존하지 않고,
`draft.py`는 `db.py`를 쓴다. 반대는 없다. 이렇게 해두면 한 모듈을 고쳐도
영향 범위가 예측 가능하다.

---

## 3. 데이터 구조

### 3-1. 경험 원자 (`experiences.json`)

이 프로젝트의 심장. 이력서를 하나의 통 문서로 두지 않고
**재사용 가능한 조각**으로 쪼갠 것.

```json
{
  "id": "proj_erp_dashboard",
  "type": "project",
  "title": "이카운트 ERP 연동 사내 재고·BOM 대시보드",
  "period": "2025.11 - 2026.02",
  "role": "단독 기획·개발·운영",
  "skills": ["Python", "REST API 연동", "ngrok"],
  "facts": [
    "도입 전 재고 확인은 전화 문의로 건당 1~2분, 하루 7~10건 발생",
    "도입 후 건당 약 30초로 단축 (약 66% 감소)",
    "사내 7명이 실제 업무에 사용"
  ],
  "learned": "완벽한 인프라보다 빠른 PoC로 실사용 검증이 효과적이다",
  "tags": ["업무자동화", "API연동", "PoC"]
}
```

**필드의 역할이 다르다.**

- `skills`, `tags` → **검색 키.** 공고와 매칭할 때 쓴다
- `facts` → **재료.** AI는 이 안의 내용만으로 문장을 만든다
- `learned` → 문항 마무리에 쓰이는 통찰
- `title`, `period`, `role` → 맥락

### 3-2. 워크넷 API 응답 (XML)

공채속보 목록 API가 돌려주는 구조.

```xml
<dhsOpenEmpInfoList>
  <total>245</total>
  <dhsOpenEmpInfo>
    <empSeqno>174728</empSeqno>              <!-- 공고 고유번호 -->
    <empWantedTitle>공고 제목</empWantedTitle>
    <empBusiNm>회사명</empBusiNm>
    <coClcdNm>중견기업</coClcdNm>              <!-- 비어있을 수 있음 -->
    <empWantedStdt>20260819</empWantedStdt>   <!-- 시작일 -->
    <empWantedEndt>20260823</empWantedEndt>   <!-- 마감일 -->
    <empWantedHomepgDetail>공고 URL</empWantedHomepgDetail>
  </dhsOpenEmpInfo>
</dhsOpenEmpInfoList>
```

**주의 지점 두 가지.**

날짜가 `20260823` 형식이라 `2026-08-23`으로 변환해야 한다(`to_date`).
그리고 `<coClcdNm/>`처럼 **빈 태그가 실제로 존재**하므로 `.text`를 바로 읽으면
`AttributeError`가 난다. 이를 막기 위해 `text_of()` 헬퍼를 따로 뒀다.

### 3-3. 파싱된 공고 (`jobs/*.json`)

```json
{
  "company": "(주)회사명",
  "position": "직무명",
  "role_type": "ML Engineer | Data Engineer | SW Engineer | Research | 기타",
  "domain": "사업 도메인",
  "required_skills": [],
  "preferred_skills": [],
  "responsibilities": [],
  "keywords": [],
  "culture_keywords": [],
  "deadline": "2026-09-30"
}
```

### 3-4. 선별 결과 (`drafts/*_meta.json`)

```json
{
  "selected": [
    { "id": "경험 id", "match_reason": "왜 골랐는지", "emphasis": "무엇을 강조할지" }
  ],
  "gaps": ["공고가 요구하지만 내 경험으로 못 채우는 것"]
}
```

### 3-5. DB 스키마

**applications** — 지원 건 하나당 한 줄

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | INTEGER | 자동 증가 기본키 |
| `company` | TEXT | 회사명 |
| `position` | TEXT | 직무명 |
| `status` | TEXT | 현재 상태 코드 |
| `deadline` | TEXT | 마감일 (YYYY-MM-DD) |
| `jd_path` | TEXT | 파싱된 공고 JSON 경로 |
| `draft_path` | TEXT | 자소서 초안 경로 |
| `applied_at` | TEXT | 지원 시각 |
| `memo` | TEXT | 출처·기업구분·공고 URL |
| `token` | TEXT | 메일 승인 링크용 비밀 토큰 |
| `created_at` / `updated_at` | TEXT | 생성·수정 시각 |

`UNIQUE(company, position)` 제약 — 같은 공고를 두 번 돌려도 중복이 안 생긴다.
수집기가 매일 돌아도 기존 건은 갱신만 되고 새 행이 생기지 않는다.

**status_log** — 상태가 바뀔 때마다 한 줄씩 쌓임

| 컬럼 | 설명 |
|---|---|
| `application_id` | 어느 지원 건인지 |
| `from_status` → `to_status` | 무엇에서 무엇으로 |
| `note` | 변경 사유 |
| `changed_at` | 변경 시각 |

지금은 안 쓰지만, 쌓이면 "지원부터 결과까지 평균 며칠",
"어느 단계에서 가장 많이 떨어지는가"를 알 수 있다.

---

## 4. 상태 머신

지원 건은 이 단계를 거친다.

```
discovered (0)  공고 발견      ← collector 수집 시 자동
     ↓
parsed (1)      분석 완료      ← jd_parser 실행 시 자동
     ↓
drafted (2)     초안 생성      ← draft 실행 시 자동
     ↓
applied (3)     지원 완료      ← 사람이 직접 표시
     ↓
  ┌──┴──┐
passed(4) failed(4)   서류 합격 / 불합격
  ↓
interview (5)   면접 예정
  ↓
closed (6)      종료
```

괄호 안 숫자가 `STATUS_ORDER`. **뒤 단계에서 앞 단계로 되돌아가지 않는다.**
이미 지원한 건을 다시 파싱해도 상태가 "분석 완료"로 후퇴하지 않게 막았다.

되돌리려면 `force=True`를 명시해야 한다 — 실수는 막고 의도는 허용.

---

## 5. 설계 판단 — 왜 이렇게 만들었나

면접에서 "AI로 만들었다"보다 훨씬 잘 통하는 부분. 각 판단에는 이유가 있다.

### 5-1. 왜 완전 자동 제출이 아닌가

**채용 플랫폼 대부분이 약관으로 자동 제출을 금지**하고, 봇 탐지도 있다.
계정이 막히면 지원 자체를 못 한다.

더 중요한 건 신뢰성이다. AI가 만든 문서를 검토 없이 제출하면
사실과 다른 내용이 나가도 알 수 없다. 그래서 **제출 직전에 사람이 승인하는
human-in-the-loop 구조**로 설계했다.

자동화의 목적은 사람을 빼는 게 아니라, 사람이 판단할 것에만 집중하게 하는 것.

### 5-2. 왜 크롤링이 아니라 공식 API인가

채용 사이트 크롤링은 약관 위반 소지가 있고, 봇 탐지·캡차로 쉽게 막힌다.
그래서 **워크넷 OpenAPI라는 공식 경로**를 택했다.

다만 제약이 있었다. 개인 계정은 **채용정보 목록/상세 API를 쓸 수 없고**,
공채속보·공채기업정보·채용행사 API만 열려 있다.

이 제약을 우회하는 대신 **범위를 재정의**했다. 공채속보는
대기업·공기업·공공기관·중견기업의 공채 정보라, 오히려 목표 타겟에 더 가까웠다.

제약이 있으면 그 안에서 다른 길을 찾는 편이, 규칙을 우회하는 것보다 낫다.

### 5-3. 왜 이력서를 원자 단위로 쪼갰나

이력서를 통째로 넣고 "이 공고에 맞게 고쳐줘"라고 하면
**LLM이 없는 경험을 지어낸다.** 그럴듯하니까.

경험을 `facts` 배열로 쪼개고 "이 안의 내용만 사용하라"고 제약하면,
할루시네이션이 **구조적으로** 차단된다. 프롬프트로 부탁하는 게 아니라
재료 자체를 제한하는 방식.

### 5-4. 왜 파싱과 작성을 나눴나

공고 원문을 그대로 넣고 자소서를 요청하면 매번 결과가 달라지고,
왜 그렇게 나왔는지 알 수 없다.

중간에 **구조화 JSON** 단계를 두면:
- 뒷단계 입력이 일정해져 결과가 안정된다
- "파싱이 틀렸나, 작성이 틀렸나"를 구분할 수 있다 (디버깅 가능)
- 공고 데이터가 쌓여 통계를 낼 수 있다

같은 이유로 `draft.py` 안에서도 **선별(select)과 작성(write)을 분리**했다.

### 5-5. 왜 gaps를 일부러 출력하나

부족한 점을 숨기는 게 아니라 드러낸다.

- **면접 예상 질문**이 여기서 나온다
- 여러 공고에서 **반복되는 gap** = 다음에 채워야 할 역량
- AI가 억지로 끼워 맞추지 않았다는 신호

### 5-6. 왜 제약을 프롬프트가 아니라 코드로 거나

`SELECT_SYSTEM`에 "스키마에 없는 키를 만들지 마라"고 써도
LLM이 가끔 어긴다. 그래서 받은 뒤 코드로 걸러낸다.

```python
allowed = {"id", "match_reason", "emphasis"}
data["selected"] = [
    {k: v for k, v in item.items() if k in allowed}
    for item in data["selected"]
]
```

**프롬프트는 부탁이고 코드는 보장이다.**
DB의 `UNIQUE(company, position)` 제약도 같은 원리 — 중요한 규칙은
지켜주기를 바라지 말고 강제한다.

### 5-7. 왜 수집 계층과 처리 계층을 분리했나

`collector.py`는 API에서 목록을 가져오고, `reader.py`는 파일 형식을 판단하며,
`jd_parser.py`는 **텍스트만 받는다.**

```python
def read_source(path_str: str) -> str:
    if ext == ".pdf":  return read_pdf(path)
    if ext in (".txt", ".md"):  return path.read_text(...)
```

덕분에 수집 경로가 늘어나도 파서는 그대로다. 실제로 워크넷 API를
나중에 붙였을 때 `jd_parser.py`는 한 줄도 고치지 않았다.

### 5-8. 왜 XML 필드를 헬퍼로 감쌌나

워크넷 응답에는 `<coClcdNm/>` 같은 **빈 태그가 실제로 존재한다.**

```python
def text_of(node, tag, default=""):
    child = node.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()
```

`node.find(tag).text`를 바로 쓰면 그 순간 터진다.
**외부에서 오는 데이터는 필드가 없을 수 있다고 가정하고 짠다.**

### 5-9. 왜 메일 발송은 try/except로 감쌌나

```python
try:
    notify_draft(...)
except Exception as e:
    print(f"메일 발송 실패(무시하고 계속): {e}")
```

메일이 실패해도 **초안은 이미 만들어졌다.** 여기서 예외를 터뜨리면
사용자가 다시 실행해서 API 비용을 또 쓴다.

**본 작업과 부가 작업을 구분한 것.** 반대로 DB 저장은 감싸지 않았다.
그건 실패하면 데이터가 유실되니까.

### 5-10. 왜 APScheduler 대신 Windows 작업 스케줄러인가

APScheduler는 **파이썬 프로그램이 계속 떠 있어야** 한다.
개인 노트북에서 매일 아침 알림을 받는 용도로는 OS 스케줄러가 안정적이다.

24시간 뜬 서버가 있다면 APScheduler가 자연스럽다.
**도구 선택은 상황에 따라 달라진다.**

### 5-11. 왜 대시보드는 Streamlit인가

같은 기능을 FastAPI + HTML로 만들면 400줄 이상,
Streamlit으로는 100줄이면 된다.

대신 복잡한 인터랙션에는 안 맞는다. 버튼 하나 누를 때마다
스크립트 전체가 재실행되는 구조라서.

**개인용 조회 도구**라는 용도에 맞는 선택.

### 5-12. 왜 승인 링크에 토큰을 쓰나

`/action?id=1&to=applied` 같은 주소면 숫자만 바꿔서
남의 지원 상태를 조작할 수 있다.

```python
token = secrets.token_urlsafe(16)
```

`random`이 아니라 `secrets`를 쓴 것도 의도적. 보안 용도로 설계된 모듈이다.

---

## 6. 데이터 흐름 상세

### 6-1. 공고 수집 (자동)

```
python -m src.collector AI 자동화 데이터 품질
      ↓
collector.fetch()         → 워크넷 API 호출 (XML)
ET.fromstring()           → XML 파싱
[검증] <error> 태그 있으면 예외
text_of() / to_date()     → 필드 추출 + 날짜 변환
      ↓
collector.match()         → 제목·회사명에 키워드 포함 여부
[중복 확인] 기존 (company, position) 집합과 대조
      ↓
db.upsert(status='discovered', memo='[워크넷] 기업구분 | URL')
```

### 6-2. 공고 1건 처리 (반자동)

```
1. cli 목록에서 관심 공고의 URL 확인
      ↓
2. 브라우저에서 본문 복사 → data/jobs/xxx.txt
      ↓
3. python -m src.jd_parser data/jobs/xxx.txt
      ↓
   reader.read_source()      → 텍스트 추출
   llm.ask(SYSTEM=파싱규칙)   → Claude 호출
   json.loads()              → 파싱
   [검증] company/position 없으면 에러로 중단
   [검증] 필수 배열 비면 경고 출력
      ↓
   data/jobs/xxx.json 저장
   db.upsert() + db.set_status('parsed')
      ↓
4. python -m src.draft data/jobs/xxx.json
      ↓
   select()  → llm.ask(SELECT_SYSTEM) → 경험 3~5개 + gaps
   [필터] 스키마 외 키 제거
      ↓
   write()   → llm.ask(WRITE_SYSTEM) → 자소서 본문
              (선별된 경험의 facts만 재료로 사용)
      ↓
   data/drafts/회사_직무.md 저장
   data/drafts/회사_직무_meta.json 저장
   db.upsert() + db.set_status('drafted')
      ↓
   notify.notify_draft() → mailer.send() → 메일 발송
      ↓
5. [사람] 초안 검토·수정 후 실제 지원
      ↓
6. 메일 버튼 클릭 → server.action() → db.set_status('applied')
   또는 python -m src.cli set 1 applied
      ↓
7. 매일 9시: 작업 스케줄러 → run_daily.bat → daily.run_daily()
             → notify_deadlines() → 마감 임박 시 메일
```

**수집은 자동, 본문 확보는 수동, 생성은 자동, 제출은 사람.**
자동화의 경계를 의도적으로 나눴다.

---

## 7. 확장하려면 어디를 건드리나

| 하고 싶은 것 | 건드릴 파일 |
|---|---|
| 자소서 문체·문항 바꾸기 | `draft.py` 의 `WRITE_SYSTEM` |
| 공고 파싱 정확도 개선 | `jd_parser.py` 의 `SYSTEM` |
| 수집 키워드·필터 변경 | `collector.py` 의 `match()`, 실행 인자 |
| 다른 채용 API 추가 | `collector.py` 에 fetch 함수 추가 |
| 새 파일 형식 지원 (docx 등) | `reader.py` 에 분기 추가 |
| 메일 디자인 변경 | `notify.py` 의 `STYLE`, 각 함수 |
| 알림 주기 변경 | Windows 작업 스케줄러 |
| 새 상태 추가 | `db.py` 의 `STATUS_LABELS` + `STATUS_ORDER` |
| 대시보드 화면 | `app.py` |

**핵심 원칙**: 새 입력 경로가 생겨도 `jd_parser` 이후는 그대로 재사용된다.

---

## 8. 아직 안 만든 것

| 기능 | 왜 미뤘나 |
|---|---|
| 공고 본문 자동 수집 | 사이트마다 구조가 달라 범용 파서가 어렵다. 수동 복사가 아직 빠르다 |
| Google Calendar 연동 | OAuth 절차가 번거롭다. 면접 일정이 생기면 붙일 예정 |
| ngrok 외부 접근 | 승인 버튼을 휴대폰에서 쓰려면 필요. 10분이면 붙는다 |
| OCR (이미지 공고) | 별도 프로그램 설치 필요. 타이핑이 더 빠르다 |
| 채용정보 목록 API | 개인 계정 권한 밖. 공채속보로 대체 |
| 자동 제출 | 의도적으로 만들지 않음 (5-1 참고) |

**안 만든 것에도 이유가 있다**는 게 중요하다.
"할 줄 몰라서"와 "지금 필요 없어서"는 다르다.

---

## 9. 성과 측정

이 프로젝트의 가치는 코드가 아니라 **결과 데이터**에 있다.

```powershell
python -m src.cli stats
```

기록해야 할 것:

- **지원 1건당 소요시간** — 도구 사용 전 대비
- **공고 발견에 쓰던 시간** — 수집기 도입 전후
- **적용 회사 수**
- **서류 통과율** — DB에서 자동 계산됨
- **반복되는 gaps** — 채워야 할 역량

`data/notes.md`에 공고별로 남기면 된다.
이 숫자들이 다음 자소서의 재료가 된다.
