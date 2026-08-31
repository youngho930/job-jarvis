"""지원 현황을 조회하고 상태를 변경하는 커맨드라인 도구."""

import sys
from datetime import datetime

from src.db import STATUS_LABELS, init_db, list_all, set_status


def show(status_filter: str = None) -> None:
    rows = list_all(status_filter)

    # 필터를 지정하지 않으면 종료된 건은 숨긴다
    hidden = 0
    if status_filter is None:
        before = len(rows)
        rows = [r for r in rows if r["status"] != "closed"]
        hidden = before - len(rows)

    if not rows:
        print("표시할 지원 건이 없습니다.")
        return

    today = datetime.now().date()
    print(f"\n{'ID':<4} {'회사':<20} {'직무':<24} {'상태':<10} {'마감':<12} D-day")
    print("-" * 84)

    for r in rows:
        dday = ""
        if r["deadline"]:
            try:
                left = (datetime.strptime(r["deadline"], "%Y-%m-%d").date() - today).days
                dday = f"D-{left}" if left >= 0 else "마감"
            except ValueError:
                dday = "?"

        print(
            f"{r['id']:<4} {r['company'][:19]:<20} {r['position'][:23]:<24} "
            f"{STATUS_LABELS.get(r['status'], r['status']):<10} "
            f"{r['deadline'] or '-':<12} {dday}"
        )

        if r["memo"] and "http" in str(r["memo"]):
            url = str(r["memo"]).split("| ")[-1]
            print(f"     → {url}")

    msg = f"\n총 {len(rows)}건"
    if hidden:
        msg += f"  (종료 {hidden}건 숨김 — 보려면: python -m src.cli list closed)"
    print(msg)


def stats() -> None:
    rows = list_all()
    if not rows:
        print("데이터가 없습니다.")
        return

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    print("\n[상태별 현황]")
    for code, label in STATUS_LABELS.items():
        if code in counts:
            print(f"  {label:<10} {counts[code]}건")

    applied = sum(counts.get(s, 0) for s in ("applied", "passed", "failed", "interview", "closed"))
    passed = counts.get("passed", 0) + counts.get("interview", 0)
    if applied:
        print(f"\n지원 {applied}건 / 서류 통과 {passed}건 ({passed / applied * 100:.0f}%)")


def main() -> None:
    init_db()

    if len(sys.argv) < 2:
        show()
        return

    cmd = sys.argv[1]

    if cmd == "list":
        show(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "stats":
        stats()
    elif cmd == "set":
        if len(sys.argv) < 4:
            print("사용법: python -m src.cli set <id> <상태> [메모]")
            print(f"상태 값: {', '.join(STATUS_LABELS)}")
            return
        app_id = int(sys.argv[2])
        new_status = sys.argv[3]
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        set_status(app_id, new_status, note, force=True)
        print(f"id={app_id} → {STATUS_LABELS[new_status]}")
        show()
    else:
        print("사용법:")
        print("  python -m src.cli              전체 목록")
        print("  python -m src.cli list applied 특정 상태만")
        print("  python -m src.cli stats        통계")
        print("  python -m src.cli set 1 passed 상태 변경")


if __name__ == "__main__":
    main()