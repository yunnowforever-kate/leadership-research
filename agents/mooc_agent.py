"""MOOC 에이전트: 유수 대학 리더십 온라인 강의 수집"""
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 검증된 무료 강의 기반 데이터 (항상 포함)
KNOWN_COURSES = [
    {
        "title": "Inspiring and Motivating Individuals",
        "university": "University of Michigan",
        "platform": "Coursera",
        "instructor": "Scott DeRue, Maxim Sytch",
        "url": "https://www.coursera.org/learn/motivate-people-teams",
        "duration": "약 14시간 (4주)",
        "free": True,
        "syllabus_summary": (
            "리더십 비전 수립, 동기부여 이론 (자기결정이론·목표설정이론), "
            "팀 몰입 증진 전략, 변화 관리 리더십"
        ),
        "key_frameworks": ["Self-Determination Theory", "Goal-Setting Theory", "Visionary Leadership"],
    },
    {
        "title": "Leadership in 21st Century Organizations",
        "university": "Copenhagen Business School",
        "platform": "Coursera",
        "instructor": "Erik Lund, Steen Vallentin",
        "url": "https://www.coursera.org/learn/leadership-21st-century",
        "duration": "약 10시간 (5주)",
        "free": True,
        "syllabus_summary": (
            "21세기 리더십 패러다임 전환, 복잡계 리더십, "
            "지속가능한 조직 리더십, AI 시대 리더 역할"
        ),
        "key_frameworks": ["Complexity Leadership", "Adaptive Leadership", "Sustainable Leadership"],
    },
    {
        "title": "MIT OpenCourseWare: Leadership and Personal Effectiveness",
        "university": "MIT",
        "platform": "MIT OpenCourseWare",
        "instructor": "MIT Sloan Faculty",
        "url": "https://ocw.mit.edu/courses/15-311-organizational-processes-fall-2003/",
        "duration": "자기 페이스 (전체 강의 무료)",
        "free": True,
        "syllabus_summary": (
            "조직 프로세스와 리더십, 의사결정 프레임워크, "
            "변화 관리 및 조직 학습, 리더 개인 효과성 향상"
        ),
        "key_frameworks": ["Organizational Learning", "Decision Framing", "Change Management"],
    },
    {
        "title": "High Performance Collaboration: Leadership, Teamwork, and Negotiation",
        "university": "Northwestern University",
        "platform": "Coursera",
        "instructor": "Leigh Thompson",
        "url": "https://www.coursera.org/learn/leadership-collaboration",
        "duration": "약 11시간 (4주)",
        "free": True,
        "syllabus_summary": (
            "고성과 리더십 행동 패턴, 팀워크 최적화, "
            "협상 전략, 리더십 스타일 진단 및 개발"
        ),
        "key_frameworks": ["High Performance Leadership", "Collaborative Negotiation", "Team Dynamics"],
    },
]

SEARCH_QUERIES = [
    "leadership development course Coursera free university 2024",
    "leader growth roadmap online course edX Harvard Stanford free",
    "AI leadership skills online course free certificate",
]


def _ddg_search_courses(query: str, max_results: int = 3) -> list:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                href = r.get("href", "")
                if any(p in href for p in ["coursera.org", "edx.org", "ocw.mit.edu", "oyc.yale.edu"]):
                    results.append(r)
        return results
    except Exception as e:
        print(f"  [MOOC] 검색 오류: {e}")
        return []


def run() -> list:
    print("[MOOC 에이전트] 강의 수집 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    courses = list(KNOWN_COURSES)
    seen_urls = {c["url"] for c in courses}

    # 추가 검색
    for query in SEARCH_QUERIES:
        print(f"  검색: {query[:50]}...")
        results = _ddg_search_courses(query, max_results=3)
        for r in results:
            url = r.get("href", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            platform = "Coursera" if "coursera" in url else "edX" if "edx" in url else "MIT OCW"
            courses.append({
                "title": r.get("title", ""),
                "university": "",
                "platform": platform,
                "instructor": "",
                "url": url,
                "duration": "미확인",
                "free": True,
                "syllabus_summary": r.get("body", "")[:200],
                "key_frameworks": [],
            })
        time.sleep(1.5)

    # 상위 5개만 유지
    courses = courses[:5]

    out_path = os.path.join(DATA_DIR, "courses.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)

    print(f"[MOOC 에이전트] {len(courses)}개 강의 수집 완료 → {out_path}")
    for c in courses:
        print(f"  · [{c['platform']}] {c['title'][:60]}")
    return courses


if __name__ == "__main__":
    run()
