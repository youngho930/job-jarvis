"""매일 실행할 작업을 모아둔다. 스케줄러가 이 파일을 호출한다."""

import sys
import traceback
from datetime import datetime

from src.db import init_db, list_all
from src.notify import days_left, notify_deadlines, notify_weekly


def log(msg: str) -> None:
    """실행 기록을 화면과 파일에 남긴다."""
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open("data/scheduler.log", "a", encoding="utf-8-sig") as f:
        f.write(line + "\n")


def run_daily() -> None:
    """매일 아침 실행: 마감 임박 공고 확인."""
    log("일일 작업 시작")
    init_db()

    try:
        notify_deadlines(within=3)
        log("마감 알림 처리 완료")
    except Exception:
        log(f"마감 알림 실패:\n{traceback.format_exc()}")

    # 마감 지난 미지원 건 정리 안내
    try:
        expired = [
            r for r in list_all()
            if r["status"] in ("discovered", "parsed", "drafted")
            and (d := days_left(r["deadline"])) is not None and d < 0
        ]
        if expired:
            names = ", ".join(r["company"] for r in expired)
            log(f"마감이 지난 미지원 공고 {len(expired)}건: {names}")
    except Exception:
        log(f"만료 확인 실패:\n{traceback.format_exc()}")

    log("일일 작업 종료")


def run_weekly() -> None:
    """주 1회 실행: 전체 현황 요약."""
    log("주간 작업 시작")
    init_db()

    try:
        notify_weekly()
        log("주간 요약 발송 완료")
    except Exception:
        log(f"주간 요약 실패:\n{traceback.format_exc()}")

    log("주간 작업 종료")


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "daily"

    if task == "daily":
        run_daily()
    elif task == "weekly":
        run_weekly()
    else:
        print("사용법: python -m src.daily [daily|weekly]")