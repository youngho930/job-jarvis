"""워크넷 공채속보 API로 공고를 수집한다."""

import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from dotenv import load_dotenv

from src.db import init_db, list_all, upsert

load_dotenv(override=True)

API_KEY = os.getenv("WORKNET_API_KEY")
LIST_URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L21.do"


def text_of(node, tag: str, default: str = "") -> str:
    """XML 자식 태그의 텍스트를 안전하게 꺼낸다. 없거나 비면 default."""
    child = node.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def to_date(yyyymmdd: str) -> str | None:
    """20260823 → 2026-08-23"""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return None
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def fetch(page: int = 1, display: int = 100) -> list[dict]:
    """공채속보 목록을 가져와 dict 리스트로 반환한다."""
    if not API_KEY:
        raise ValueError(".env에 WORKNET_API_KEY를 설정하세요.")

    params = {
        "authKey": API_KEY,
        "callTp": "L",
        "returnType": "XML",
        "startPage": page,
        "display": display,
    }

    res = requests.get(LIST_URL, params=params, timeout=20)
    res.raise_for_status()

    root = ET.fromstring(res.text)

    # 에러 응답 처리
    error = root.find("error")
    if error is not None:
        raise ValueError(f"API 오류: {error.text}")

    items = []
    for node in root.findall("dhsOpenEmpInfo"):
        items.append({
            "seq": text_of(node, "empSeqno"),
            "company": text_of(node, "empBusiNm"),
            "title": text_of(node, "empWantedTitle"),
            "co_type": text_of(node, "coClcdNm", "미분류"),
            "start": to_date(text_of(node, "empWantedStdt")),
            "deadline": to_date(text_of(node, "empWantedEndt")),
            "url": text_of(node, "empWantedHomepgDetail"),
        })

    total = text_of(root, "total", "0")
    print(f"조회: {len(items)}건 (전체 {total}건 중 {page}페이지)")
    return items


def match(item: dict, keywords: list[str]) -> bool:
    """공고 제목이나 회사명에 키워드가 있는지 확인한다."""
    haystack = f"{item['title']} {item['company']}"
    return any(kw in haystack for kw in keywords)


def collect(keywords: list[str], pages: int = 3) -> None:
    """키워드에 맞는 공고를 수집해 DB에 등록한다."""
    init_db()

    existing = {(r["company"], r["position"]) for r in list_all()}
    added = 0

    for page in range(1, pages + 1):
        for item in fetch(page):
            if not match(item, keywords):
                continue

            key = (item["company"], item["title"])
            if key in existing:
                continue

            app_id = upsert(
                item["company"],
                item["title"],
                deadline=item["deadline"],
                memo=f"[워크넷 공채속보] {item['co_type']} | {item['url']}",
            )
            existing.add(key)
            added += 1
            print(f"  + [{item['co_type']}] {item['company']} — {item['title']}")
            print(f"    마감 {item['deadline']} | {item['url']}")

    print(f"\n신규 등록: {added}건")
    if added:
        print("공고 원문은 위 URL에서 확인해 data/jobs/ 에 저장하세요.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m src.collector <키워드1> [키워드2] ...")
        print("예시:   python -m src.collector AI 자동화 데이터 DX")
        sys.exit(1)

    collect(sys.argv[1:])