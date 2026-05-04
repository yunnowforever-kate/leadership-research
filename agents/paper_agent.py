"""논문 에이전트: Semantic Scholar API로 학술 논문 수집 (주제 기반)"""
import requests
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.environ.get("RESEARCH_DATA_DIR", os.path.join(BASE_DIR, "data"))

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,authors,year,citationCount,externalIds,abstract,venue"


def _build_queries(topic: str) -> list:
    return [
        f"{topic} model framework development",
        f"{topic} research methodology",
        f"{topic} strategy organization",
    ]


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
            print(f"  [논문] 검색 오류 ({query[:40]}): {e}")
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


def run(topic: str) -> list:
    print(f"[논문 에이전트] '{topic}' 검색 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    queries = _build_queries(topic)
    seen, all_raw = set(), []

    for q in queries:
        results = _search(q, limit=10)
        for p in results:
            pid = p.get("paperId", "")
            if pid and pid not in seen:
                seen.add(pid)
                all_raw.append(p)
        time.sleep(2)

    # 최신 3편 (2020년 이후, 인용 순)
    recent = [p for p in all_raw if (p.get("year") or 0) >= 2020]
    recent = sorted(recent, key=lambda x: x.get("citationCount", 0), reverse=True)[:3]

    # 클래식 1편 (인용 수 최고)
    classic = sorted(all_raw, key=lambda x: x.get("citationCount", 0), reverse=True)
    classic = [p for p in classic if p not in recent][:1]

    papers = [_format(p) for p in recent + classic]

    out_path = os.path.join(DATA_DIR, "papers.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    print(f"[논문 에이전트] {len(papers)}편 수집 완료")
    for p in papers:
        print(f"  · {p['year']} | {p['citations']}인용 | {p['title'][:55]}")
    return papers


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "leadership development"
    run(t)
