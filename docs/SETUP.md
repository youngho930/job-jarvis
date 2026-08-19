# 다른 PC로 옮기기 (SETUP)

프로젝트를 새 컴퓨터에서 세팅하는 절차. 15~20분 걸린다.

---

## 핵심 원칙

**`venv` 폴더는 복사하지 않는다.**

가상환경 안에는 원래 컴퓨터의 절대경로(`C:\Users\user\Desktop\job-jarvis\venv\...`)가
파일 곳곳에 기록되어 있다. 다른 PC에 그대로 옮기면 파이썬이 자기 위치를 못 찾아 깨진다.

새 PC에서 **새로 만들면 된다.** 어차피 1분이면 끝난다.

---

## 준비물

### Python 설치

python.org/downloads 에서 **3.10 이상** 설치.

설치 화면에서 **"Add Python to PATH" 반드시 체크.** 이거 놓치면 나중에
`python` 명령을 못 찾는다.

```powershell
python --version
```

`Python 3.12.x` 같은 게 나오면 성공.

### Git 설치

git-scm.com/downloads 에서 설치. 설치 옵션은 전부 기본값으로 넘긴다.

```powershell
git --version
```

### VS Code 설치

code.visualstudio.com 에서 설치. 무료.

---

## 방법 A — GitHub에서 받기 (권장)

코드는 GitHub에 있으므로 clone만 하면 된다.

### A-1. 코드 받기

```powershell
cd C:\Users\사용자명\Desktop
git clone https://github.com/본인계정/job-jarvis.git
cd job-jarvis
```

### A-2. PowerShell 실행 정책 (처음 한 번만)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

확인 메시지에 `Y` 입력. 이걸 안 하면 가상환경 활성화가 막힌다.

### A-3. 가상환경 + 패키지

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` 가 없으면:

```powershell
pip install anthropic python-dotenv requests pypdf fastapi uvicorn streamlit
```

### A-4. 개인 데이터 옮기기

GitHub에는 **코드만** 있다. 아래 파일은 직접 옮긴다.

| 파일 | 없으면 |
|---|---|
| `.env` | API 키·메일 설정. 새로 작성해도 됨 |
| `data/experiences.json` | 경험 원자. 다시 만들기 어려우니 꼭 옮길 것 |
| `data/jarvis.db` | 지원 이력. 없으면 빈 상태로 시작 |
| `data/notes.md` | 실험 기록 |

USB로 옮기거나, 새 PC에서 손으로 다시 작성한다.

> **`.env` 주의**: API 키와 앱 비밀번호가 들어있다.
> 카카오톡·이메일로 보내지 말 것.

---

## 방법 B — 폴더 통째로 복사

GitHub을 쓰지 않는 경우.

### 가져갈 것

```
job-jarvis/
├── src/          ← 코드 전부
├── docs/         ← 문서
├── data/         ← 개인 데이터
├── app.py
├── .env
├── .gitignore
├── README.md
├── run_daily.bat
└── run_weekly.bat
```

### 가져가지 말 것

```
venv/            ← 새로 만든다
__pycache__/     ← 자동 생성 캐시
.git/            ← 굳이 옮길 필요 없음
```

복사 후 새 PC에서 정리:

```powershell
Remove-Item -Recurse -Force venv
Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
python -m venv venv
venv\Scripts\activate
pip install anthropic python-dotenv requests pypdf fastapi uvicorn streamlit
```

---

## `.env` 작성

```powershell
code .env
```

내용:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
WORKNET_API_KEY=워크넷-인증키
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

### 키를 새로 발급받아야 하면

| 키 | 발급처 |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `WORKNET_API_KEY` | work24.go.kr → OPEN-API → 인증키 신청 (개인, 즉시 승인) |
| `GMAIL_APP_PASSWORD` | Google 계정 → 보안 → 앱 비밀번호 (2단계 인증 필요) |

---

## 동작 확인

순서대로 실행하며 각 단계가 통과하는지 본다.

### 1. Claude API

```powershell
python -m src.llm
```

인사말이 나오면 통과. 실패하면 `.env` 의 API 키 확인.

### 2. DB

```powershell
python -m src.cli
```

지원 목록이 나오면 통과. 비어 있으면 `data/jarvis.db` 를 안 옮긴 것.

### 3. 경험 원자

```powershell
python -c "import json;d=json.load(open('data/experiences.json',encoding='utf-8-sig'));print('원자',len(d),'개')"
```

### 4. 워크넷 수집기

```powershell
python -m src.collector AI 자동화
```

`조회: N건` 이 나오면 통과.

### 5. 메일

```powershell
python -m src.mailer
```

테스트 메일이 도착하면 통과. 실패하면 앱 비밀번호 확인.

### 6. 승인 서버

```powershell
uvicorn src.server:app
```

`http://127.0.0.1:8000` 접속해 페이지가 뜨면 통과. Ctrl+C 로 종료.

### 7. 대시보드

```powershell
streamlit run app.py
```

브라우저가 열리고 지원 목록이 보이면 통과.

---

## 스케줄러 재등록

작업 스케줄러는 **OS에 등록된 것이라 파일 복사로 옮겨지지 않는다.**

### 배치 파일 경로 수정

```powershell
code run_daily.bat
```

```bat
@echo off
cd /d C:\Users\새사용자명\Desktop\job-jarvis
call venv\Scripts\activate.bat
python -m src.daily daily
```

`run_weekly.bat` 도 동일하게 수정.

**테스트**: 탐색기에서 더블클릭 → 로그가 추가되면 성공.

```powershell
Get-Content data\scheduler.log -Tail 5 -Encoding UTF8
```

### 작업 스케줄러 등록

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

주간 작업도 같은 방식으로 (트리거: 매주 월요일, `run_weekly.bat`).

---

## 두 PC를 오가며 쓸 때

### 작업한 PC에서

```powershell
git add .
git commit -m "수정 내용"
git push
```

### 다른 PC에서

```powershell
git pull
```

**주의**: `data/` 안의 개인 데이터는 Git으로 동기화되지 않는다.
`jarvis.db` 는 양쪽에서 따로 쌓이므로, 한쪽을 주로 쓰거나
USB로 주기적으로 맞춰야 한다.

---

## requirements.txt 만들어두기

패키지 목록을 파일로 남겨두면 다음 세팅이 한 줄로 끝난다.

```powershell
pip freeze > requirements.txt
git add requirements.txt
git commit -m "requirements.txt 추가"
git push
```

이후 새 PC에서:

```powershell
pip install -r requirements.txt
```

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
| `git push` 시 인증 요구 | 최초 1회 | "Sign in with your browser" 선택 |
