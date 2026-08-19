"""메일 링크로 지원 상태를 변경하는 승인 서버."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.db import STATUS_LABELS, find_by_token, init_db, set_status

load_dotenv(override=True)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

app = FastAPI(title="Job Jarvis")

PAGE = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Jarvis</title>
<style>
  body {{ font-family: -apple-system, 'Malgun Gothic', sans-serif;
         display: flex; align-items: center; justify-content: center;
         min-height: 90vh; margin: 0; background: #f5f5f5; }}
  .box {{ background: #fff; padding: 32px 40px; border-radius: 12px;
         box-shadow: 0 2px 12px rgba(0,0,0,.08); text-align: center;
         max-width: 420px; }}
  h1 {{ font-size: 20px; margin: 0 0 12px; }}
  p {{ color: #666; font-size: 14px; line-height: 1.6; }}
  .ok {{ color: #2e7d32; }}
  .err {{ color: #c62828; }}
</style></head>
<body><div class="box">
  <h1 class="{cls}">{title}</h1>
  <p>{message}</p>
</div></body></html>
"""


def page(title: str, message: str, ok: bool = True) -> HTMLResponse:
    return HTMLResponse(
        PAGE.format(title=title, message=message, cls="ok" if ok else "err")
    )


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def home():
    return page("Job Jarvis", "승인 서버가 실행 중입니다.")


@app.get("/action", response_class=HTMLResponse)
def action(id: int, token: str, to: str):
    """메일 버튼이 호출하는 엔드포인트."""
    row = find_by_token(id, token)
    if row is None:
        return page("접근 불가", "잘못된 링크이거나 만료되었습니다.", ok=False)

    if to not in STATUS_LABELS:
        return page("알 수 없는 상태", f"'{to}'는 처리할 수 없습니다.", ok=False)

    set_status(id, to, "메일 링크로 처리", force=True)

    return page(
        "처리 완료",
        f"<b>{row['company']}</b> / {row['position']}<br><br>"
        f"상태가 <b>{STATUS_LABELS[to]}</b>(으)로 변경되었습니다.",
    )