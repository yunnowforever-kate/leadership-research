"""HBR 에이전트: DuckDuckGo 검색으로 HBR 아티클 수집"""
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

QUERIES = [
    "site:hbr.org leadership development model 2023 2024",
    "site:hbr.org leader growth roadmap",
    "site:hbr.org AI leadership skills 2024",
    "site:hbr.org leadership competency framework",
    "site:hbr.org executive leadership program",
    "site:hbr.org developing leaders organization",
    "site:hbr.org leadership pipeline succession",
]


def _ddg_search(query: str, max_results: int = 3) -> list:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                href = r.get("href", "")
                if "hbr.org" in href:
                    results.append(r)
        return results
    except Exception as e:
        print(f"  [HBR] 검색 오류: {e}")
        return []


def run() -> list:
    print("[HBR 에이전트] 검색 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    articles = []
    seen_urls: set = set()

    for query in QUERIES:
        print(f"  검색: {query[:50]}...")
        results = _ddg_search(query, max_results=3)
        for r in results:
            url = r.get("href", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            snippet = r.get("body", "")
            title = r.get("title", "")

            # 날짜 추출 시도 (제목에 포함된 경우)
            date = ""
            for y in ["2025", "2024", "2023", "2022"]:
                if y in title or y in snippet:
                    date = y
                    break

            articles.append({
                "title": title,
                "author": "",
                "date": date,
                "url": url,
                "key_message": snippet[:150],
                "main_points": [snippet] if snippet else [],
                "relevant_section": _classify_section(title + " " + snippet),
            })
        time.sleep(1.5)  # rate limiting

    out_path = os.path.join(DATA_DIR, "hbr_articles.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"[HBR 에이전트] {len(articles)}개 아티클 수집 완료 → {out_path}")
    for a in articles[:5]:
        print(f"  · {a['title'][:70]}")
    return articles


def _classify_section(text: str) -> list:
    text_lower = text.lower()
    sections = []
    if any(w in text_lower for w in ["what is", "definition", "importance", "why"]):
        sections.append("의미")
    if any(w in text_lower for w in ["how to", "build", "create", "design", "process", "step"]):
        sections.append("방법")
    if any(w in text_lower for w in ["example", "case", "company", "organization", "ai"]):
        sections.append("사례")
    if any(w in text_lower for w in ["book", "course", "learn", "resource", "program"]):
        sections.append("학습자료")
    return sections or ["의미", "방법", "사례", "학습자료"]


if __name__ == "__main__":
    run()
