"""
지원 이력을 SQLite에 저장하고 관리한다.
DB 파일: data/jarvis.db
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/jarvis.db")

# 상태 코드 → 화면에 표시할 한글 이름
STATUS_LABELS = {
    "discovered": "공고 발견",
    "parsed": "분석 완료",
    "drafted": "초안 생성",
    "applied": "지원 완료",
    "passed": "서류 합격",
    "failed": "서류 불합격",
    "interview": "면접 예정",
    "closed": "종료",
}
# 상태의 진행 순서. 숫자가 클수록 뒤 단계다.
STATUS_ORDER = {
    "discovered": 0,
    "parsed": 1,
    "drafted": 2,
    "applied": 3,
    "passed": 4,
    "failed": 4,
    "interview": 5,
    "closed": 6,
}


def now() -> str:
    """현재 시각을 문자열로. SQLite에는 날짜 타입이 없어 문자열로 저장한다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    """DB 연결을 만든다."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # 결과를 딕셔너리처럼 row["company"] 형태로 꺼낼 수 있게 해준다
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """테이블을 만든다. 이미 있으면 아무것도 하지 않는다."""
    conn = get_conn()

    # 지원 건 하나당 한 줄
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company     TEXT NOT NULL,
            position    TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'discovered',
            deadline    TEXT,
            jd_path     TEXT,
            draft_path  TEXT,
            applied_at  TEXT,
            memo        TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE(company, position)
        )
    """)

    # 상태가 바뀔 때마다 한 줄씩 쌓인다
    conn.execute("""
        CREATE TABLE IF NOT EXISTS status_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            from_status    TEXT,
            to_status      TEXT NOT NULL,
            note           TEXT,
            changed_at     TEXT NOT NULL,
            FOREIGN KEY (application_id) REFERENCES applications(id)
        )
    """)

    # 승인 링크용 토큰 컬럼 (이미 있으면 무시)
    try:
        conn.execute("ALTER TABLE applications ADD COLUMN token TEXT")
    except sqlite3.OperationalError:
        pass  # 이미 존재
    
        # 자격요건 컬럼 (이미 있으면 무시)
    for col in ("min_experience INTEGER", "education TEXT", "language_required INTEGER"):
        try:
            conn.execute(f"ALTER TABLE applications ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def upsert(company: str, position: str, **fields) -> int:
    """
    회사+직무 조합으로 찾아서 있으면 갱신, 없으면 새로 만든다.
    같은 공고를 두 번 돌려도 중복 행이 생기지 않는다.
    반환값: 해당 지원 건의 id
    """
    conn = get_conn()
    cur = conn.execute(
        "SELECT id FROM applications WHERE company = ? AND position = ?",
        (company, position),
    )
    row = cur.fetchone()

    if row is None:
        # 신규 등록
        cur = conn.execute(
            """INSERT INTO applications (company, position, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (company, position, now(), now()),
        )
        app_id = cur.lastrowid
        conn.execute(
            """INSERT INTO status_log (application_id, from_status, to_status, changed_at)
               VALUES (?, NULL, 'discovered', ?)""",
            (app_id, now()),
        )
    else:
        app_id = row["id"]

    # 넘겨받은 필드만 갱신한다
    allowed = {"status", "deadline", "jd_path", "draft_path", "applied_at", "memo",
               "min_experience", "education", "language_required"}
    for key, value in fields.items():
        if key in allowed and value is not None:
            conn.execute(
                f"UPDATE applications SET {key} = ?, updated_at = ? WHERE id = ?",
                (value, now(), app_id),
            )

    conn.commit()
    conn.close()
    return app_id


def set_status(app_id: int, new_status: str, note: str = "", force: bool = False) -> None:
    """상태를 바꾸고 변경 이력을 남긴다."""
    if new_status not in STATUS_LABELS:
        raise ValueError(
            f"알 수 없는 상태입니다: {new_status}\n"
            f"가능한 값: {', '.join(STATUS_LABELS)}"
        )

    conn = get_conn()
    cur = conn.execute("SELECT status FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"id {app_id} 인 지원 건이 없습니다.")

    old_status = row["status"]
    
    if not force and STATUS_ORDER[new_status] < STATUS_ORDER[old_status]:
        conn.close()
        print(f"  (상태 유지: 이미 '{STATUS_LABELS[old_status]}' 단계입니다)")
        return

    conn.execute(
        "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, now(), app_id),
    )
    conn.execute(
        """INSERT INTO status_log (application_id, from_status, to_status, note, changed_at)
           VALUES (?, ?, ?, ?, ?)""",
        (app_id, old_status, new_status, note, now()),
    )

    # 지원 완료로 바뀌면 지원 시각도 기록
    if new_status == "applied":
        conn.execute(
            "UPDATE applications SET applied_at = ? WHERE id = ?", (now(), app_id)
        )

    conn.commit()
    conn.close()


def list_all(status: str = None) -> list[sqlite3.Row]:
    """전체 목록. status를 주면 그 상태만 걸러서 반환한다."""
    conn = get_conn()
    if status:
        cur = conn.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY deadline", (status,)
        )
    else:
        cur = conn.execute("SELECT * FROM applications ORDER BY deadline")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_token(app_id: int) -> str:
    """승인 링크용 토큰을 가져온다. 없으면 새로 만든다."""
    import secrets

    conn = get_conn()
    cur = conn.execute("SELECT token FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()

    if row and row["token"]:
        token = row["token"]
    else:
        token = secrets.token_urlsafe(16)
        conn.execute("UPDATE applications SET token = ? WHERE id = ?", (token, app_id))
        conn.commit()

    conn.close()
    return token


def find_by_token(app_id: int, token: str):
    """토큰이 맞는 지원 건을 찾는다. 틀리면 None."""
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM applications WHERE id = ? AND token = ?", (app_id, token)
    )
    row = cur.fetchone()
    conn.close()
    return row

# 내 자격 조건 — 본인 상황에 맞게 수정
MY_EXPERIENCE = 1        # 경력 연수 (1년 7개월 → 1)
MY_EDUCATION = "초대졸"   # 고졸 / 초대졸 / 학사 / 석사
MY_LANGUAGE = False      # 공인어학성적 보유 여부

EDU_ORDER = {"무관": 0, "고졸": 1, "초대졸": 2, "학사": 3, "석사": 4}


def check_eligible(row) -> tuple:
    """
    지원 가능 여부를 판정한다.
    반환: (가능 여부, 막히는 이유 목록)
    """
    blockers = []

    exp = row["min_experience"]
    if exp is not None and exp > MY_EXPERIENCE:
        blockers.append(f"경력 {exp}년 요구")

    edu = row["education"]
    if edu and edu in EDU_ORDER:
        if EDU_ORDER[edu] > EDU_ORDER.get(MY_EDUCATION, 0):
            blockers.append(f"{edu} 이상 요구")

    if row["language_required"] and not MY_LANGUAGE:
        blockers.append("공인어학성적 필요")

    return (len(blockers) == 0, blockers)

if __name__ == "__main__":
    init_db()
    print(f"DB 준비 완료 → {DB_PATH.resolve()}")