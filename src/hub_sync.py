"""
지원 단계별 개수를 Project Hub 용 Upstash Redis 키(hub:pipeline)에 저장한다.
회사명·공고명·id 는 보내지 않고, 개수와 갱신 시각만 보낸다.

단계 기준
- saved     저장: 아직 지원 안 했고 종료도 안 된 공고 (weekly_summary 의 in_progress)
- applied   지원: applied_at 이 있는 공고 (weekly_summary 의 applied)
- screening 서류: status_log 에 passed 또는 interview 기록이 있는 공고 (weekly_summary 의 passed)
- interview 면접: status_log 에 interview 기록이 있는 공고
- result    결과: 지원한 공고 중 failed 기록이 있거나 종료(closed)된 공고
            (최종 합격 상태는 따로 없어서, 지원 후 종료를 결과 확정으로 본다)

사용: python -m src.hub_sync [--db 데이터베이스경로]
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

import src.db as db
from src.db import get_conn, list_all
from src.notify import weekly_summary

load_dotenv(override=True)

KEY = "hub:pipeline"
# 한국은 서머타임이 없어 +9 고정 (윈도우에 시간대 데이터가 없어도 동작)
KST = timezone(timedelta(hours=9), "KST")


def pipeline_counts() -> dict:
    """단계별 개수만 계산한다 (회사명·공고명·id 는 담지 않음)."""
    rows = list_all()
    summary = weekly_summary(rows)  # 지원·서류는 주간 리포트와 같은 기준
    ids = {r["id"] for r in rows}

    conn = get_conn()
    logged = lambda status: {
        row["application_id"]
        for row in conn.execute(
            "SELECT DISTINCT application_id FROM status_log WHERE to_status = ?", (status,)
        )
    }
    interview_ids = logged("interview") & ids
    failed_ids = logged("failed") & ids
    conn.close()

    result = sum(
        1 for r in rows
        if r["applied_at"] and (r["id"] in failed_ids or r["status"] == "closed")
    )
    return {
        "saved": summary["in_progress"],
        "applied": summary["applied"],
        "screening": summary["passed"],
        "interview": len(interview_ids),
        "result": result,
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
    }


def sync_pipeline(db_path=None, log=print):
    """
    개수를 계산해 Upstash 에 저장한다. 성공하면 저장한 내용(dict), 아니면 None.
    어떤 경우에도 예외를 밖으로 내보내지 않는다.
    로그·에러에는 주소와 토큰을 남기지 않는다 (requests 예외 메시지에는 주소가 들어 있어 쓰지 않음).
    """
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if not url or not token:
        log("허브 동기화 건너뜀(설정 없음)")
        return None

    original_db = db.DB_PATH
    try:
        if db_path:
            db.DB_PATH = Path(db_path)  # 테스트용: 다른 DB(복사본)에서 계산
        payload = pipeline_counts()

        res = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=["SET", KEY, json.dumps(payload, ensure_ascii=False)],
            timeout=10,
        )
        if res.status_code != 200 or res.json().get("result") != "OK":
            log(f"허브 동기화 실패 (HTTP {res.status_code})")
            return None
        log(f"허브 동기화 완료 {payload}")
        return payload
    except Exception as e:
        log(f"허브 동기화 실패 ({type(e).__name__})")
        return None
    finally:
        db.DB_PATH = original_db


if __name__ == "__main__":
    db_arg = None
    if "--db" in sys.argv:
        db_arg = sys.argv[sys.argv.index("--db") + 1]
    sync_pipeline(db_arg)
