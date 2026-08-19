# Job Jarvis 사용 매뉴얼

공고 하나를 처리하는 전체 절차. 익숙해지면 5~10분이면 끝난다.

---

## 0. 터미널 준비

VS Code를 열고 터미널에서 **항상 이 두 줄 먼저**.

```powershell
cd C:\Users\user\Desktop\job-jarvis
venv\Scripts\activate
```

프롬프트가 이렇게 보이면 준비 완료.

```
(venv) PS C:\Users\user\Desktop\job-jarvis>
```

> `(venv)`가 없으면 패키지를 못 찾고, 폴더가 다르면 파일을 못 찾는다. 에러의 절반이 여기서 나온다.

---

## 1. 공고 수집 (자동)

워크넷 공채속보 API로 키워드에 맞는 공고를 자동으로 찾는다.

```powershell
python -m src.collector AI 자동화 데이터 품질 DX
```

키워드는 몇 개든 띄어쓰기로 나열하면 된다. 공고 제목이나 회사명에
하나라도 포함되면 수집한다.

### 정상 출력

```
조회: 100건 (전체 245건 중 1페이지)
  + [중견기업] 회사명 — 공고 제목
    마감 2026-08-23 | https://...
신규 등록: 5건
```

수집된 공고는 **상태 `discovered`(공고 발견)** 로 DB에 들어간다.
이미 있는 공고는 건너뛰므로 매일 돌려도 중복이 안 생긴다.

### 수집되는 범위

대기업·공기업·공공기관·중견기업·외국계기업의 **공채 정보**다.
개인 계정은 워크넷의 일반 채용정보 API를 쓸 수 없어 공채속보만 가능하다.

중소기업·스타트업 공고는 사람인 등에서 직접 찾아 2단계로 넘어간다.

### 키워드 조합 예시

| 목적 | 키워드 |
|---|---|
| AI·자동화 직무 | `AI 자동화 데이터 DX AX` |
| 품질 직무 | `품질 QC QA 검사 신뢰성` |
| 제조 DX | `스마트팩토리 제조 생산기술 MES` |
| 특정 회사 | `삼성 SK 현대` |

---

## 2. 공고 텍스트 확보

수집기는 **목록만** 가져온다. 자격요건·우대사항은 직접 확보해야 한다.

### 2-1. 목록에서 URL 확인

```powershell
python -m src.cli
```

각 공고 아래에 `→ https://...` 로 링크가 표시된다.

### 2-2. 브라우저에서 복사

공고 페이지에서 **F12** → **Console** 탭 → 아래 입력 후 엔터.

```javascript
copy(document.body.innerText)
```

> "Allow pasting" 경고가 뜨면 `allow pasting` 을 타이핑하고 엔터 친 뒤 다시 시도. 한 번만 하면 된다.

### 2-3. 표가 있으면 추가로

자격요건·우대사항이 표 안에 있으면 위 명령으로는 누락된다. 추가 실행.

```javascript
copy([...document.querySelectorAll('td,th')].map(c=>c.innerText.trim()).join('\n---\n'))
```

### 2-4. iframe 안에 있으면

사람인 등은 본문이 iframe에 있는 경우가 많다.

```javascript
copy([document.body.innerText, ...[...document.querySelectorAll('iframe')].map(f => { try { return f.contentDocument.body.innerText } catch(e) { return '' } })].join('\n\n=== FRAME ===\n\n'))
```

### 2-5. 다 안 되면

**그냥 화면 보고 타이핑한다.** 자격요건·우대사항은 보통 각 5줄 안팎이라 5분이면 된다.
여기서 시간 쓰지 말 것.

---

## 3. txt 파일 만들기

### 3-1. 파일 생성

파일명 규칙: `회사명_직무.txt` — **소문자·영문·언더스코어만.**

```powershell
New-Item data\jobs\회사명_직무.txt
code data\jobs\회사명_직무.txt
```

### 3-2. 내용 붙여넣고 이 형식으로 정리

```
[회사] (주)회사명
[공고명] 직무명
[마감일] 2026-09-30

## 담당업무
- 
- 

## 자격요건
- 
- 

## 우대사항
- 
- 
```

### 3-3. 체크리스트

- [ ] `[회사]`, `[공고명]` 이 있는가 → **없으면 에러로 중단됨**
- [ ] `[마감일]` 을 `YYYY-MM-DD` 로 적었는가 → `D-14` 같은 표기는 파서가 못 읽음
- [ ] 담당업무·자격요건·우대사항 내용이 실제로 있는가
- [ ] 사이드바의 다른 회사 공고, 광고를 지웠는가

저장은 **Ctrl + S**.

> 회사명은 **DB에 등록된 것과 똑같이** 적는다. 다르면 같은 공고가 두 건으로 들어간다.

---

## 4. 공고 파싱

```powershell
python -m src.jd_parser data/jobs/회사명_직무.txt
```

### 정상 출력

```
저장 완료 → data\jobs\회사명_직무.json
DB 등록 → id=2 | (주)회사명 / 직무명
{ ... JSON 내용 ... }
```

### 확인할 것

- `required_skills`, `preferred_skills`, `responsibilities` 가 채워졌는가
- `deadline` 이 `null` 이 아닌가

### `⚠️ 비어있는 필드` 경고가 뜨면

txt에 해당 내용이 없다는 뜻. **2단계로 돌아가서 표 내용을 보충**하고 다시 실행한다.
경고를 무시하고 넘어가면 자소서가 부실해진다.

---

## 5. 자소서 초안 생성

```powershell
python -m src.draft data/jobs/회사명_직무.json
```

> **주의**: `.txt` 가 아니라 **`.json`** 을 넣는다. 4단계가 만든 결과물이다.

30초~1분 걸린다. 그동안 출력이 없어도 정상.

### 정상 출력

```
=== 선별된 경험 ===
  [proj_erp_dashboard] ...
=== 채워지지 않는 요구사항 ===
  - ...
자소서 초안 생성 중... (30초~1분 소요)
초안 저장 → data\drafts\(주)회사명_직무명.md
선별 근거 저장 → data\drafts\(주)회사명_직무명_meta.json
DB 갱신 → id=2 | 상태: 초안 생성
메일 발송 완료 → ...
```

메일함에도 초안 미리보기와 gaps가 도착한다.

---

## 6. 초안 검토 — 여기가 제일 중요

**AI 초안은 60% 완성품이다. 나머지 40%는 직접 한다.**

```powershell
code data\drafts\
```

### 반드시 확인할 것

1. **소리 내어 읽기** — 눈으로는 안 걸리는 어색함이 입으로 읽으면 걸린다
2. **면접 시뮬레이션** — 각 문단마다 "이거 물어보면 뭐라고 답하지?" 답이 막히면 그 문장은 빼거나 고친다
3. **숫자 검증** — 설명 못 하는 수치는 독이다
4. **안 해본 기술이 등장하지 않는지** — 공고 키워드를 AI가 끌어다 쓸 수 있다
5. **회사명 확인** — 다른 회사 이름이 남아있지 않은지
6. **글자 수** — 사람인 등은 문항별 제한이 있다

### 자주 나오는 수정 지점

- 시점 표현("최근", "2026년 8월부터") → 애매하게 하거나 삭제
- 같은 경험이 여러 문항에 중복 → 하나만 남기기
- 안 써본 기술 언급 → 삭제하거나 일반화
- 맺음말이 평범함 → 본인 문장으로 다시 쓰기

---

## 7. 지원하고 상태 기록

지원을 마쳤으면 DB에 반영한다. 세 가지 방법 중 아무거나.

### 방법 A — 메일 버튼 (가장 편함)

5단계에서 온 메일의 **"지원 완료로 표시"** 버튼 클릭.
단, 승인 서버가 켜져 있어야 한다.

```powershell
uvicorn src.server:app
```

### 방법 B — 대시보드

```powershell
streamlit run app.py
```

항목 펼치기 → 상태 선택 → 변경 버튼.

### 방법 C — 터미널

```powershell
python -m src.cli set 2 applied "사람인을 통해 지원"
```

### 상태 값

| 코드 | 의미 |
|---|---|
| `discovered` | 공고 발견 |
| `parsed` | 분석 완료 |
| `drafted` | 초안 생성 |
| `applied` | 지원 완료 |
| `passed` | 서류 합격 |
| `failed` | 서류 불합격 |
| `interview` | 면접 예정 |
| `closed` | 종료 |

마감이 지났거나 지원을 포기한 건은 `closed` 로 정리하면 목록이 깔끔해진다.

---

## 8. 현황 확인

### 터미널

```powershell
python -m src.cli                # 전체 목록 (공고 URL 포함)
python -m src.cli stats          # 통계 (통과율)
python -m src.cli list applied   # 특정 상태만
```

### 대시보드

```powershell
streamlit run app.py
```

브라우저에서 `http://localhost:8501`

### 메일로 받기

```powershell
python -m src.notify weekly        # 주간 현황 요약
python -m src.notify deadline 7    # D-7 이내 마감 알림
```

---

## 전체 흐름 요약

```
1. python -m src.collector AI 자동화 품질     ← 공고 수집 (자동)
2. python -m src.cli                          ← 목록·URL 확인
3. 브라우저 F12 → copy(document.body.innerText)
4. data/jobs/회사명_직무.txt 에 붙여넣고 정리
5. python -m src.jd_parser data/jobs/회사명_직무.txt
6. python -m src.draft data/jobs/회사명_직무.json
7. data/drafts/ 초안 직접 검토·수정           ← 가장 중요
8. 지원 후 상태를 applied 로 변경
```

---

## 터미널 몇 개를 켜둬야 하나

| 터미널 | 언제 필요한가 |
|---|---|
| 일반 (명령 실행) | **거의 항상** |
| `uvicorn` (승인 서버) | 메일 버튼을 쓸 때만 |
| `streamlit` (대시보드) | 현황을 볼 때만 |

**대부분은 일반 터미널 하나면 충분하다.** 상태 변경은 `cli` 로도 되고,
대시보드는 하루 한 번 열어보면 된다.

---

## 자주 만나는 에러

| 에러 | 원인 | 해결 |
|---|---|---|
| `No module named src.xxx` | 폴더가 다르거나 파일 없음 | `cd` 로 프로젝트 폴더 이동 |
| `회사명 또는 직무명을 추출하지 못했습니다` | txt에 `[회사]`, `[공고명]` 없음 | txt 상단에 추가 |
| `⚠️ 비어있는 필드` | 표 내용이 복사 안 됨 | txt에 자격요건·우대사항 보충 |
| `개인회원은 사용할 수 없는 OPEN-API입니다` | 권한 밖 API 호출 | 공채속보 API만 사용 가능 |
| `.env에 WORKNET_API_KEY를 설정하세요` | 키 미등록 | `.env` 에 인증키 추가 |
| `JSONDecodeError` | JSON 문법 오류 (쉼표 등) | 알려주는 줄 번호로 이동해 확인 |
| `SMTPAuthenticationError` | 앱 비밀번호 문제 | `.env` 의 16자리 확인 (공백 제거) |
| 아무 반응 없음 | 정상 종료했거나 조건 미충족 | 로그·출력 메시지 확인 |

**에러가 나면 메시지를 끝까지 읽는다.** 파이썬 트레이스백은 아래에서 위로 읽으면 대부분 답이 있다.

---

## 기록해두면 좋은 것

### `data/notes.md`

공고를 돌릴 때마다 한 덩어리씩 추가한다.

```markdown
## 2026-08-20 | 회사명
- 소요시간: N분
- 파싱: 정상 / 문제
- 선별: N개, 타당 여부
- gaps: 
- 문제:
- 조치:
```

### 왜 기록하나

- **소요시간** → "지원 1건당 N분 → M분" 이라는 성과 지표가 된다
- **반복되는 gaps** → 다음에 채워야 할 역량이 보인다
- **문제와 조치** → "프롬프트를 어떻게 개선했는가" 를 설명할 근거가 된다

이 기록 자체가 포트폴리오다.

---

## 유지보수

### 경험이 추가되면

`data/experiences.json` 에 원자를 추가한다. 형식은 `experiences.example.json` 참고.
**`facts` 에는 사실만.** 여기 없는 내용은 자소서에 등장할 수 없다.

수정 후 문법 검사:

```powershell
python -c "import json;d=json.load(open('data/experiences.json',encoding='utf-8-sig'));print('원자',len(d),'개')"
```

### 자소서 품질이 마음에 안 들면

`src/draft.py` 의 `WRITE_SYSTEM` 에 규칙을 한 줄 추가하고 다시 돌린다.
바꾼 내용은 `data/notes.md` 에 기록.

### 파싱이 부정확하면

`src/jd_parser.py` 의 `SYSTEM` 에 규칙을 추가한다.

### 수집 결과가 너무 많거나 적으면

키워드를 조정한다. 좁히려면 구체적인 단어를, 넓히려면 일반적인 단어를 쓴다.
페이지 수를 늘리려면 `collector.py` 의 `collect(keywords, pages=3)` 값을 바꾼다.

---

## 코드를 수정했으면

```powershell
git add .
git commit -m "무엇을 바꿨는지"
git push
```

커밋 메시지는 나중에 본인이 볼 기록이다. "수정" 보다
"공고 파싱 시 빈 필드 경고 추가" 가 낫다.

---

## 백업

GitHub에 코드가 올라가 있지만, **개인 데이터는 제외되어 있다.**
아래 파일은 별도로 백업한다.

- `data/experiences.json` — 가장 중요. 다시 만들기 어렵다
- `data/jarvis.db` — 지원 이력
- `data/notes.md` — 실험 기록
- `.env` — 백업하되 **절대 공유하지 않는다**
