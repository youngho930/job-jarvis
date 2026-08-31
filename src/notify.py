"""DB 상태를 읽어 알림 메일을 구성하고 발송한다."""

import os
import sys
from datetime import datetime
from pathlib import Path

from src.db import STATUS_LABELS, get_token, init_db, list_all
from src.mailer import send

# 메일 공통 스타일
STYLE = """
<style>
  body { font-family: -apple-system, 'Malgun Gothic', sans-serif;
         color: #222; line-height: 1.6; }
  .card { border: 1px solid #e0e0e0; border-radius: 8px;
          padding: 16px; margin-bottom: 12px; }
  .urgent { border-left: 4px solid #e53935; }
  .label { color: #777; font-size: 13px; }
  table { border-collapse: collapse; width: 100%; }
  th, td { padding: 8px 10px; border-bottom: 1px solid #eee;
           text-align: left; font-size: 14px; }
  th { background: #fafafa; }
  .gap { background: #fff8e1; padding: 10px; border-radius: 6px;
         font-size: 13px; }
</style>
"""


def days_left(deadline):
    """마감까지 남은 일수. 계산할 수 없으면 None."""
    if not deadline:
        return None
    try:
        d = datetime.strptime(deadline, "%Y-%m-%d").date()
        return (d - datetime.now().date()).days
    except ValueError:
        return None


def extract_url(memo) -> str:
    """memo 필드에서 공고 URL을 꺼낸다. 없으면 빈 문자열."""
    text = str(memo or "")
    if "http" not in text:
        return ""
    return text.split("| ")[-1].strip()


def link_button(url: str, label: str = "공고 보기") -> str:
    """파란 버튼 HTML. url이 없으면 빈 문자열."""
    if not url:
        return ""
    return (
        '<div style="margin-top:10px;">'
        f'<a href="{url}" style="background:#1976d2; color:#fff; '
        'padding:8px 16px; border-radius:5px; text-decoration:none; '
        f'font-size:13px; display:inline-block;">{label}</a>'
        "</div>"
    )


def notify_draft(company: str, position: str, draft_path: str, gaps: list, app_id=None) -> None:
    """자소서 초안이 생성됐을 때 검토 요청 메일을 보낸다."""
    preview = ""
    p = Path(draft_path)
    if p.exists():
        text = p.read_text(encoding="utf-8-sig")
        preview = text[:600].replace("\n", "<br>")

    gap_html = ""
    if gaps:
        items = "".join(f"<li>{g}</li>" for g in gaps)
        gap_html = (
            '<div class="gap"><b>채워지지 않은 요구사항</b>'
            f'<ul style="margin:6px 0 0 0; padding-left:18px;">{items}</ul>'
            '<div style="margin-top:8px; color:#888;">'
            "면접에서 질문될 가능성이 높은 항목입니다.</div></div>"
        )

    buttons = ""
    if app_id:
        base = os.getenv("BASE_URL", "http://127.0.0.1:8000")
        token = get_token(app_id)
        link = f"{base}/action?id={app_id}&token={token}&to="
        buttons = (
            '<div style="margin:20px 0;">'
            f'<a href="{link}applied" style="background:#1976d2; color:#fff; '
            "padding:12px 24px; border-radius:6px; text-decoration:none; "
            'display:inline-block; margin-right:8px;">지원 완료로 표시</a>'
            f'<a href="{link}closed" style="background:#757575; color:#fff; '
            "padding:12px 24px; border-radius:6px; text-decoration:none; "
            'display:inline-block;">보류/포기</a>'
            "</div>"
        )

    body = f"""{STYLE}
    <h2>자소서 초안이 준비되었습니다</h2>
    <div class="card">
      <div class="label">회사</div><b>{company}</b>
      <div class="label" style="margin-top:8px;">직무</div>{position}
      <div class="label" style="margin-top:8px;">파일 위치</div>
      <code>{draft_path}</code>
    </div>
    {gap_html}
    {buttons}
    <div class="card">
      <div class="label">미리보기</div>
      <div style="margin-top:8px; font-size:14px;">{preview}...</div>
    </div>
    <p style="color:#888; font-size:13px;">
      제출 전 반드시 직접 검토하고 본인 문장으로 다듬으세요.
    </p>
    """
    send(f"[Job Jarvis] 초안 준비 - {company}", body, html=True)


def notify_deadlines(within: int = 3) -> None:
    """마감이 임박한 미지원 공고를 알린다."""
    init_db()
    pending = [r for r in list_all() if r["status"] in ("discovered", "parsed", "drafted")]

    urgent = []
    for r in pending:
        left = days_left(r["deadline"])
        if left is not None and 0 <= left <= within:
            urgent.append((left, r))

    if not urgent:
        print(f"D-{within} 이내 마감 예정인 미지원 공고가 없습니다.")
        return

    urgent.sort(key=lambda x: x[0])

    cards = ""
    for left, r in urgent:
        cards += (
            '<div class="card urgent">'
            f"<b>D-{left}</b> &middot; {r['deadline']}<br>"
            f'<span style="font-size:16px;">{r["company"]}</span><br>'
            f'<span class="label">{r["position"]} &middot; '
            f'현재 {STATUS_LABELS[r["status"]]}</span>'
            f"{link_button(extract_url(r['memo']))}"
            "</div>"
        )

    body = f"""{STYLE}
    <h2>마감 임박 공고 {len(urgent)}건</h2>
    {cards}
    """
    send(f"[Job Jarvis] 마감 임박 {len(urgent)}건", body, html=True)
    print(f"마감 임박 {len(urgent)}건 알림 발송")


def notify_weekly() -> None:
    """전체 지원 현황을 요약해서 보낸다."""
    init_db()
    rows = list_all()
    if not rows:
        print("등록된 지원 건이 없습니다.")
        return

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    applied = sum(
        counts.get(s, 0)
        for s in ("applied", "passed", "failed", "interview", "closed")
    )
    passed = counts.get("passed", 0) + counts.get("interview", 0)
    rate = f"{passed / applied * 100:.0f}%" if applied else "-"

    trs = ""
    for r in rows:
        left = days_left(r["deadline"])
        dday = f"D-{left}" if left is not None and left >= 0 else "-"

        company = r["company"]
        url = extract_url(r["memo"])
        if url:
            company = f'<a href="{url}" style="color:#1976d2;">{company}</a>'

        trs += (
            f"<tr><td>{company}</td><td>{r['position']}</td>"
            f"<td>{STATUS_LABELS[r['status']]}</td>"
            f"<td>{r['deadline'] or '-'}</td><td>{dday}</td></tr>"
        )

    body = f"""{STYLE}
    <h2>주간 지원 현황</h2>
    <div class="card">
      전체 <b>{len(rows)}</b>건 &middot; 지원 완료 <b>{applied}</b>건 &middot;
      서류 통과 <b>{passed}</b>건 (통과율 {rate})
    </div>
    <table>
      <tr><th>회사</th><th>직무</th><th>상태</th><th>마감</th><th>D-day</th></tr>
      {trs}
    </table>
    """
    send(f"[Job Jarvis] 주간 현황 - 총 {len(rows)}건", body, html=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "weekly"

    if cmd == "deadline":
        within = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        notify_deadlines(within)
    elif cmd == "weekly":
        notify_weekly()
    else:
        print("사용법:")
        print("  python -m src.notify weekly       주간 현황 요약")
        print("  python -m src.notify deadline 3   D-3 이내 마감 알림")