"""Job Jarvis 대시보드."""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.db import STATUS_LABELS, init_db, list_all, set_status

st.set_page_config(page_title="Job Jarvis", page_icon="🎯", layout="wide")

init_db()


def days_left(deadline):
    if not deadline:
        return None
    try:
        d = datetime.strptime(deadline, "%Y-%m-%d").date()
        return (d - datetime.now().date()).days
    except ValueError:
        return None


st.title("Job Jarvis")
st.caption("취업 지원 현황 대시보드")

rows = list_all()

if not rows:
    st.info("등록된 지원 건이 없습니다. 공고를 파싱하면 여기에 표시됩니다.")
    st.stop()

# ── 요약 지표 ────────────────────────────────
counts = {}
for r in rows:
    counts[r["status"]] = counts.get(r["status"], 0) + 1

applied = sum(
    counts.get(s, 0) for s in ("applied", "passed", "failed", "interview", "closed")
)
passed = counts.get("passed", 0) + counts.get("interview", 0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 공고", f"{len(rows)}건")
c2.metric("지원 완료", f"{applied}건")
c3.metric("서류 통과", f"{passed}건")
c4.metric("통과율", f"{passed / applied * 100:.0f}%" if applied else "-")

st.divider()

# ── 마감 임박 ────────────────────────────────
urgent = []
for r in rows:
    if r["status"] in ("discovered", "parsed", "drafted"):
        left = days_left(r["deadline"])
        if left is not None and 0 <= left <= 7:
            urgent.append((left, r))

if urgent:
    urgent.sort(key=lambda x: x[0])
    st.subheader("마감 임박")
    for left, r in urgent:
        col_a, col_b = st.columns([6, 1])
        with col_a:
            st.warning(
                f"**D-{left}** · {r['company']} / {r['position']} "
                f"— 현재 {STATUS_LABELS[r['status']]}"
            )
        with col_b:
            memo = str(r["memo"] or "")
            if "http" in memo:
                url = memo.split("| ")[-1].strip()
                st.link_button("공고 보기", url, use_container_width=True)
    st.divider()

# ── 지원 목록 ────────────────────────────────
st.subheader("지원 목록")

status_filter = st.selectbox(
    "상태 필터",
    ["전체"] + [STATUS_LABELS[k] for k in STATUS_LABELS if k in counts],
)

label_to_code = {v: k for k, v in STATUS_LABELS.items()}

for r in rows:
    if status_filter != "전체" and r["status"] != label_to_code[status_filter]:
        continue

    left = days_left(r["deadline"])
    dday = f"D-{left}" if left is not None and left >= 0 else ""

    with st.expander(
        f"[{STATUS_LABELS[r['status']]}] {r['company']} — {r['position']}  {dday}"
    ):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**마감일** {r['deadline'] or '-'}")
            st.write(f"**등록일** {r['created_at'][:10]}")
            if r["applied_at"]:
                st.write(f"**지원일** {r['applied_at'][:10]}")
                            # 공고 원문 링크
            memo = str(r["memo"] or "")
            if "http" in memo:
                url = memo.split("| ")[-1].strip()
                st.link_button("공고 보기", url)

            # gaps 표시
            if r["draft_path"]:
                meta = Path(str(r["draft_path"]).replace(".md", "_meta.json"))
                if meta.exists():
                    data = json.loads(meta.read_text(encoding="utf-8-sig"))
                    gaps = data.get("gaps", [])
                    if gaps:
                        st.write("**채워지지 않은 요구사항**")
                        for g in gaps:
                            st.write(f"- {g}")

        with col2:
            new = st.selectbox(
                "상태 변경",
                list(STATUS_LABELS.values()),
                index=list(STATUS_LABELS).index(r["status"]),
                key=f"sel_{r['id']}",
            )
            if st.button("변경", key=f"btn_{r['id']}"):
                set_status(r["id"], label_to_code[new], "대시보드에서 변경", force=True)
                st.rerun()

        # 자소서 초안 보기
        if r["draft_path"] and Path(str(r["draft_path"])).exists():
            with st.container():
                if st.checkbox("자소서 초안 보기", key=f"chk_{r['id']}"):
                    text = Path(str(r["draft_path"])).read_text(encoding="utf-8-sig")
                    st.markdown(text)