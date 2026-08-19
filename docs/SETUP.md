# 다른 PC로 옮기기 (SETUP)

프로젝트를 새 컴퓨터에서 다시 세팅하는 절차. 15~20분 걸린다.

---

## 핵심 원칙

**`venv` 폴더는 복사하지 않는다.**

가상환경 안에는 원래 컴퓨터의 절대경로(`C:\Users\user\Desktop\job-jarvis\venv\...`)가
파일 곳곳에 기록되어 있다. 다른 PC에 그대로 옮기면 파이썬이 자기 위치를 못 찾아 깨진다.

새 PC에서 **새로 만들면 된다.** 어차피 1분이면 끝난다.

---

## 1단계 — 원래 PC에서 복사할 것

### 반드시 가져갈 것

```
job-jarvis/
├── src/              ← 코드 전부
│   ├── __init__.py
│   ├── llm.py
│   ├── reader.py
│   ├── jd_parser.py
│   ├── draft.py
│   ├── db.py
│   ├── cli.py
│   ├── mailer.py
│   ├── notify.py
│   ├── server.py
│   └── daily.py
├── data/
│   ├── experiences.json    ← 가장 중요. 다시 만들기 어렵다
│   ├── jarvis.db           ← 지원 이력
│   ├── notes.md            ← 실험 기록
│   ├── jobs/               ← 공고 원문·JSON
│   └── drafts/             ← 생성된 자소서
├── app.py
├── .env                    ← API 키. 별도로 안전하게 옮길 것
├── .gitignore
├── run_daily.bat
├── run_weekly.bat
└── USAGE.md
```

### 가져가지 말 것

```
venv/            ← 새로 만든다
__pycache__/     ← 자동 생성되는 캐시
*.pyc
```

### 옮기는 방법

**USB / 외장하드 / 클라우드 드라이브** 아무거나.

폴더를 통째로 복사하되, 복사 후 새 PC에서 `venv` 와 `__pycache__` 폴더를 삭제한다.

```powershell
Remove-Item -Recurse -Force venv
Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
```

> **`.env` 주의**: API 키와 앱 비밀번호가 들어있다.
> 카카오톡·이메일로 보내지 말고 USB로 직접 옮기거나, 새 PC에서 손으로 다시 입력한다.

---

## 2단계 — 새 PC에 필요한 프로그램

### Python 설치

python.org/downloads 에서 **3.10 이상** 설치.

설치 화면에서 **"Add Python to PATH" 반드시 체크.** 이거 놓치면 나중에
`python` 명령을 못 찾는다.

확인:

```powershell
python --version
```

`Python 3.12.x` 같은 게 나오면 성공.

### VS Code 설치

code.visualstudio.com 에서 설치. 무료.

---

## 3단계 — 프로젝트 세팅

### 3-1. 폴더 위치 정하기

어디든 상관없지만 **경로에 한글이나 공백이 없는 곳**을 권한다.

```
C:\Users\사용자명\Desktop\job-jarvis
```

### 3-2. PowerShell 실행 정책 (처음 한 번만)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

확인 메시지에 `Y` 입력.

> 이걸 안 하면 가상환경 활성화가 막힌다.

### 3-3. 가상환경 새로 만들기

프로젝트 폴더에서:

```powershell
cd C:\Users\사용자명\Desktop\job-jarvis
python -m venv venv
venv\Scripts\activate
```

프롬프트 앞에 `(venv)` 가 붙으면 성공.

### 3-4. 패키지 설치

```powershell
pip install anthropic python-dotenv pypdf fastapi uvicorn streamlit
```

2~3분 걸린다.

---

## 4단계 — `.env` 확인

```powershell
code .env
```

내용이 이렇게 있어야 한다.

```
ANTHROPIC_API_KEY=sk-ant-api03-...
GMAIL_ADDRESS=본인계정@gmail.com
GMAIL_APP_PASSWORD=16자리앱비밀번호
NOTIFY_TO=받을주소@naver.com
BASE_URL=http://127.0.0.1:8000
```

**체크리스트**

- [ ] `sk-ant-` 가 한 번만 들어있는가
- [ ] 앱 비밀번호에 공백이 없는가 (16자)
- [ ] 따옴표가 없는가
- [ ] 각 줄이 한 줄로 되어 있는가

파일이 없으면 새로 만든다.

```powershell
New-Item .env
code .env
```

---

## 5단계 — 동작 확인

순서대로 실행하며 각 단계가 통과하는지 본다.

### 5-1. Claude API

```powershell
python -m src.llm
```

인사말이 나오면 통과.

**실패하면**: `.env` 의 API 키 확인. 키가 만료됐으면 console.anthropic.com 에서 재발급.

### 5-2. DB

```powershell
python -m src.cli
```

기존 지원 목록이 나오면 통과.

**목록이 비어 있으면**: `data/jarvis.db` 를 복사해오지 않은 것. 원래 PC에서 다시 가져온다.

### 5-3. 경험 원자

```powershell
python -c "import json;d=json.load(open('data/experiences.json',encoding='utf-8-sig'));print('원자',len(d),'개')"
```

원자 개수가 나오면 통과.

### 5-4. 메일

```powershell
python -m src.mailer
```

테스트 메일이 도착하면 통과.

**실패하면**: 앱 비밀번호 확인. Gmail 2단계 인증이 켜져 있어야 한다.

### 5-5. 승인 서버

```powershell
uvicorn src.server:app
```

`http://127.0.0.1:8000` 접속해서 페이지가 뜨면 통과. Ctrl+C 로 종료.

### 5-6. 대시보드

```powershell
streamlit run app.py
```

브라우저가 열리고 지원 목록이 보이면 통과.

---

## 6단계 — 스케줄러 재등록

작업 스케줄러는 **OS에 등록된 것이라 파일 복사로 옮겨지지 않는다.** 새로 등록해야 한다.

### 6-1. 배치 파일 경로 수정

```powershell
code run_daily.bat
```

경로를 새 PC에 맞게 고친다.

```bat
@echo off
cd /d C:\Users\새사용자명\Desktop\job-jarvis
call venv\Scripts\activate.bat
python -m src.daily daily
```

`run_weekly.bat` 도 동일하게.

**테스트**: 탐색기에서 더블클릭 → 로그가 추가되면 성공.

```powershell
Get-Content data\scheduler.log -Tail 5 -Encoding UTF8
```

### 6-2. 작업 스케줄러 등록

1. **Win + R** → `taskschd.msc`
2. **기본 작업 만들기**
3. 이름: `Job Jarvis 일일 알림`
4. 트리거: **매일** / 오전 9:00
5. 동작: **프로그램 시작**
6. 프로그램: `C:\Users\새사용자명\Desktop\job-jarvis\run_daily.bat`
7. 시작 위치: `C:\Users\새사용자명\Desktop\job-jarvis`

등록 후 더블클릭 → **조건** 탭:
- "AC 전원이 켜져 있는 경우에만 시작" → **체크 해제**

**설정** 탭:
- "예약 시간이 지난 후 가능한 한 빨리 작업 시작" → **체크**

주간 작업도 같은 방식으로 (트리거: 매주 월요일).

---

## 자주 나오는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `python`을 찾을 수 없음 | PATH 미등록 | Python 재설치 시 "Add to PATH" 체크 |
| `venv\Scripts\activate` 실행 불가 | 실행 정책 | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `No module named anthropic` | 패키지 미설치 또는 venv 비활성 | `(venv)` 확인 후 `pip install` 다시 |
| `No module named src.xxx` | 프로젝트 폴더가 아님 | `cd` 로 이동 |
| DB가 비어 있음 | `jarvis.db` 미복사 | 원래 PC에서 가져오기 |
| 한글 깨짐 | 인코딩 | 읽을 때 `utf-8-sig` 사용 (코드에 이미 적용됨) |

---

## 더 나은 방법 — GitHub 사용

USB로 옮기는 것보다 GitHub이 훨씬 편하다. 특히 두 대를 오가며 쓸 경우.

### 최초 설정 (원래 PC에서)

```powershell
git init
git add .
git commit -m "initial commit"
```

GitHub에서 새 저장소를 만들고:

```powershell
git remote add origin https://github.com/본인계정/job-jarvis.git
git branch -M main
git push -u origin main
```

> `.gitignore` 에 `.env`, `venv/`, `*.db` 가 들어있으므로
> **API 키와 개인 지원 이력은 올라가지 않는다.** 안전하다.

### 새 PC에서

```powershell
git clone https://github.com/본인계정/job-jarvis.git
cd job-jarvis
python -m venv venv
venv\Scripts\activate
pip install anthropic python-dotenv pypdf fastapi uvicorn streamlit
```

그다음 `.env` 와 `data/experiences.json`, `data/jarvis.db` 만 손으로 옮기면 끝.

### 이후 동기화

원래 PC에서:
```powershell
git add .
git commit -m "수정 내용"
git push
```

새 PC에서:
```powershell
git pull
```

**부수 효과**: 저장소를 공개로 두면 면접에서 링크 하나로 프로젝트를 보여줄 수 있다.

---

## requirements.txt 만들어두기

패키지 목록을 파일로 남겨두면 다음 세팅이 한 줄로 끝난다.

**원래 PC에서:**

```powershell
pip freeze > requirements.txt
```

**새 PC에서:**

```powershell
pip install -r requirements.txt
```

패키지를 하나씩 기억할 필요가 없어진다. 지금 만들어두는 것을 권한다.
