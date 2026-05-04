"""논문 에이전트: Semantic Scholar API로 학술 논문 수집"""
import requests
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,authors,year,citationCount,externalIds,abstract,venue"


def _search(query: str, limit: int = 10, retries: int = 3) -> list:
    params = {"query": query, "fields": FIELDS, "limit": limit}
    for attempt in range(retries):
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  [논문] API 한도 초과, {wait}초 대기 후 재시도...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            print(f"  [논문] 검색 오류 ({query[:30]}...): {e}")
            time.sleep(5)
    return []


def _format(raw: dict) -> dict:
    doi = raw.get("externalIds", {}).get("DOI", "")
    authors = [a.get("name", "") for a in raw.get("authors", [])[:5]]
    abstract = (raw.get("abstract") or "")[:200]
    return {
        "title": raw.get("title", ""),
        "authors": authors,
        "year": raw.get("year", ""),
        "journal": raw.get("venue", ""),
        "citations": raw.get("citationCount", 0),
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "abstract_summary": abstract,
        "key_insights": [],
    }


def run() -> list:
    print("[논문 에이전트] 검색 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    # 최신 논문 (2020년 이후, 인용 순)
    recent_raw = _search("leadership development model roadmap competency", limit=20)
    recent = [p for p in recent_raw if (p.get("year") or 0) >= 2020]
    recent = sorted(recent, key=lambda x: x.get("citationCount", 0), reverse=True)[:3]

    # 클래식 논문 (인용 수 최고)
    classic_raw = _search("leader development transformational leadership theory", limit=10)
    classic = sorted(classic_raw, key=lambda x: x.get("citationCount", 0), reverse=True)[:1]

    papers = [_format(p) for p in recent + classic]

    out_path = os.path.join(DATA_DIR, "papers.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    print(f"[논문 에이전트] {len(papers)}편 수집 완료 → {out_path}")
    for p in papers:
        print(f"  · {p['year']} | {p['citations']}인용 | {p['title'][:60]}")
    return papers


if __name__ == "__main__":
    run()
