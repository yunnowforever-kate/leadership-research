"""MOOC 에이전트: 온라인 강의 수집 (주제 기반 동적 검색)"""
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.environ.get("RESEARCH_DATA_DIR", os.path.join(BASE_DIR, "data"))


def _build_queries(topic: str) -> list:
    return [
        f"{topic} course Coursera free university 2024",
        f"{topic} online course edX Harvard Stanford free",
        f"{topic} MIT OpenCourseWare free",
        f"{topic} online learning certificate free",
    ]


def _ddg_search(query: str, max_results: int = 4) -> list:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                href = r.get("href", "")
                if any(p in href for p in ["coursera.org", "edx.org", "ocw.mit.edu",
                                           "oyc.yale.edu", "futurelearn.com", "udemy.com"]):
                    results.append(r)
        return results
    except Exception as e:
        print(f"  [MOOC] 검색 오류: {e}")
        return []


def _detect_platform(url: str) -> str:
    if "coursera" in url:   return "Coursera"
    if "edx.org" in url:    return "edX"
    if "ocw.mit" in url:    return "MIT OpenCourseWare"
    if "oyc.yale" in url:   return "Yale Open Courses"
    if "futurelearn" in url: return "FutureLearn"
    if "udemy" in url:      return "Udemy"
    return "기타"


def run(topic: str) -> list:
    print(f"[MOOC 에이전트] '{topic}' 강의 검색 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    courses = []
    seen_urls: set = set()

    for query in _build_queries(topic):
        print(f"  검색: {query[:55]}...")
        results = _ddg_search(query, max_results=4)
        for r in results:
            url = r.get("href", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            platform = _detect_platform(url)
            title = r.get("title", "")
            snippet = r.get("body", "")

            courses.append({
                "title": title,
                "university": "",
                "platform": platform,
                "instructor": "",
                "url": url,
                "duration": "미확인",
                "free": True,
                "syllabus_summary": snippet[:200],
                "key_frameworks": [],
            })
        time.sleep(1.5)

    courses = courses[:5]

    out_path = os.path.join(DATA_DIR, "courses.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)

    print(f"[MOOC 에이전트] {len(courses)}개 강의 수집 완료")
    for c in courses:
        print(f"  · [{c['platform']}] {c['title'][:55]}")
    return courses


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "leadership development"
    run(t)
