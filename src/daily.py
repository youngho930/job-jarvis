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
    """매일 아침 실행: 공고 수집 → 만료 정리 → 마감 임박 알림."""
    log("일일 작업 시작")
    init_db()

    # 1. 새 공고 수집
    try:
        from src.collector import collect
        collect(["AI", "자동화", "데이터", "품질", "DX"])
        log("공고 수집 완료")
    except Exception:
        log(f"공고 수집 실패:\n{traceback.format_exc()}")

    # 2. 마감 지난 미지원 건 자동 정리
    try:
        from src.db import set_status
        expired = [
            r for r in list_all()
            if r["status"] in ("discovered", "parsed", "drafted")
            and (d := days_left(r["deadline"])) is not None and d < 0
        ]
        for r in expired:
            set_status(r["id"], "closed", "마감 경과 자동 정리", force=True)
        if expired:
            log(f"마감 경과 {len(expired)}건 자동 종료")
    except Exception:
        log(f"만료 정리 실패:\n{traceback.format_exc()}")

    # 3. 마감 임박 알림
    try:
        notify_deadlines(within=7)
        log("마감 알림 처리 완료")
    except Exception:
        log(f"마감 알림 실패:\n{traceback.format_exc()}")

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