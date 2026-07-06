"""
collect_festival_news.py (속초 버전)
─────────────────────────────────────────────────────────────
속초 축제·행사 소식 수집기.

속초문화관광재단(sokchocf.or.kr) 공식 "공연·행사·공모" 캘린더 게시판을
긁어와서 festival_news.json 을 만든다. 프론트엔드(index.html)가 이 파일을
읽어서 지도 하단에 최신 소식 몇 개를 보여준다.

⚠️ 정직하게 알아둘 점 (강릉 버전보다 더 까다로운 사이트라 꼭 읽어주세요)
  - 이 사이트는 표(table) 형태가 아니라 달력형 게시판이고, 개별 글마다
    실제 상세페이지 링크가 없다(자바스크립트로 팝업을 띄우는 방식).
    그래서 이 스크립트가 만드는 각 소식은 "속초문화관광재단 행사 목록
    페이지" 자체로 링크된다 (개별 글로 바로 가지는 못함).
  - 클래스명에 의존하지 않고, "제목 안에 2026.01.16 ~ 2026.02.11 같은
    날짜 범위 문구가 있다"는 패턴으로 항목을 찾는다. 이러면 사이트
    디자인이 조금 바뀌어도 어느 정도 버틴다.
  - 그래도 사이트가 통째로 개편되면 이 스크립트도 깨질 수 있다.
    그 경우 fetch_items() 안의 파싱 로직만 다시 맞추면 된다.

실행:  python collect_festival_news.py
결과:  같은 폴더에 festival_news.json 생성 (GitHub Actions가 주기 실행)
"""

import json
import re
import datetime as dt
from pathlib import Path

SOURCE_URL = "http://sokchocf.or.kr/sokchocf/event/information"
OUT_PATH = Path(__file__).parent / "festival_news.json"
MAX_ITEMS = 8

CATEGORIES = ["공연·전시", "축제", "교육", "공모", "행사·소식"]
DATE_RANGE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(\d{4})\.(\d{2})\.(\d{2})")


def fetch_items():
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (compatible; SokchoFoodMapBot/1.0)"}
    res = requests.get(SOURCE_URL, headers=headers, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding or "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    items = []
    seen = set()

    # "YYYY.MM.DD ~ YYYY.MM.DD" 날짜 범위 문구가 들어있는 텍스트 노드를 전부 찾는다
    for text_node in soup.find_all(string=DATE_RANGE_RE):
        m = DATE_RANGE_RE.search(str(text_node))
        if not m:
            continue
        start_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # 날짜 문구를 감싸고 있는 항목 하나(제목+카테고리 포함)를 찾을 때까지
        # "자세히보기"라는 확실한 마커가 나올 때까지 부모 태그를 올라간다
        # (텍스트 길이만으로 판단하면 날짜 문구 자체가 이미 길어서 헷갈릴 수 있음)
        container = text_node.parent
        full_text = ""
        for _ in range(6):
            if container is None:
                break
            candidate = container.get_text(" ", strip=True)
            if "자세히보기" in candidate or "더보기" in candidate:
                full_text = candidate
                break
            container = container.parent
        if not full_text:
            full_text = text_node.parent.get_text(" ", strip=True)

        cat_found = None
        for c in CATEGORIES:
            if full_text.startswith(c):
                cat_found = c
                break

        title = full_text[len(cat_found):] if cat_found else full_text
        title = DATE_RANGE_RE.sub("", title)
        title = title.replace("자세히보기", "").replace("더보기", "").strip(" -·*")
        if not title or title in seen:
            continue
        seen.add(title)

        items.append({
            "title": (f"[{cat_found}] " if cat_found else "") + title,
            "date": start_date,
            "url": SOURCE_URL,
        })
        if len(items) >= MAX_ITEMS:
            break

    return items


def build():
    print("속초 축제·행사 소식 수집 시작…")
    try:
        items = fetch_items()
        print(f"  · {len(items)}건 수집")
    except Exception as e:
        print(f"  ! 수집 실패 ({type(e).__name__}): {e}")
        # 실패해도 기존 파일이 있으면 그대로 두고, 없으면 빈 목록으로 생성
        if OUT_PATH.exists():
            print("  · 기존 festival_news.json 유지")
            return
        items = []

    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": SOURCE_URL,
        "items": items,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료 → {OUT_PATH}")


if __name__ == "__main__":
    build()
