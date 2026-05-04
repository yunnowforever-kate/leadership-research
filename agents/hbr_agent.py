"""HBR 에이전트: DuckDuckGo 검색으로 HBR 아티클 수집 (주제 기반)"""
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.environ.get("RESEARCH_DATA_DIR", os.path.join(BASE_DIR, "data"))


def _build_queries(topic: str) -> list:
    return [
        f"site:hbr.org {topic} 2023 2024",
        f"site:hbr.org {topic} strategy",
        f"site:hbr.org {topic} AI",
        f"site:hbr.org {topic} leadership",
        f"site:hbr.org {topic} organization",
        f"site:hbr.org {topic} management",
        f"site:hbr.org {topic} future",
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


def run(topic: str) -> list:
    print(f"[HBR 에이전트] '{topic}' 검색 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    queries = _build_queries(topic)
    articles = []
    seen_urls: set = set()

    for query in queries:
        print(f"  검색: {query[:55]}...")
        results = _ddg_search(query, max_results=3)
        for r in results:
            url = r.get("href", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            snippet = r.get("body", "")
            title = r.get("title", "")
            date = next((y for y in ["2025", "2024", "2023", "2022"] if y in title + snippet), "")

            articles.append({
                "title": title,
                "author": "",
                "date": date,
                "url": url,
                "key_message": snippet[:150],
                "main_points": [snippet] if snippet else [],
                "relevant_section": _classify(title + " " + snippet),
            })
        time.sleep(1.5)

    out_path = os.path.join(DATA_DIR, "hbr_articles.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"[HBR 에이전트] {len(articles)}개 아티클 수집 완료")
    for a in articles[:5]:
        print(f"  · {a['title'][:65]}")
    return articles


def _classify(text: str) -> list:
    t = text.lower()
    sections = []
    if any(w in t for w in ["what is", "definition", "importance", "why", "mean"]):
        sections.append("의미")
    if any(w in t for w in ["how to", "build", "create", "design", "process", "step", "framework"]):
        sections.append("방법")
    if any(w in t for w in ["example", "case", "company", "ai", "digital"]):
        sections.append("사례")
    if any(w in t for w in ["book", "course", "learn", "resource", "program", "tool"]):
        sections.append("학습자료")
    return sections or ["의미", "방법", "사례", "학습자료"]


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "leadership development"
    run(t)
