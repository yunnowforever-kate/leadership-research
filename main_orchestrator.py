"""
리더십 모델링 & 리더 성장 로드맵 리서치 자동화
메인 오케스트레이터: 5개 에이전트를 순차/병렬로 실행하여 최종 DOCX 생성
"""
import concurrent.futures
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

from agents import paper_agent, hbr_agent, mooc_agent, synthesis_agent, docx_writer


def load_cached(name: str):
    path = os.path.join(BASE_DIR, "data", f"{name}.json")
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        age_hours = (time.time() - mtime) / 3600
        if age_hours < 24:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            print(f"  [{name}] 캐시 사용 ({age_hours:.1f}시간 전 수집, {len(data)}건)")
            return data
    return None


def phase1_search(use_cache: bool = True):
    print("\n" + "=" * 60)
    print("Phase 2: 병렬 검색 실행")
    print("=" * 60)

    # 캐시 확인
    if use_cache:
        cached_papers = load_cached("papers")
        cached_hbr = load_cached("hbr_articles")
        cached_courses = load_cached("courses")
        if cached_papers and cached_hbr and cached_courses:
            print("모든 데이터 캐시 사용. 검색 생략.")
            return cached_papers, cached_hbr, cached_courses

    # 병렬 검색
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f_papers = executor.submit(paper_agent.run)
        f_hbr = executor.submit(hbr_agent.run)
        f_courses = executor.submit(mooc_agent.run)

        papers = f_papers.result()
        hbr = f_hbr.result()
        courses = f_courses.result()

    return papers, hbr, courses


def phase2_synthesize(papers: list, hbr: list, courses: list, use_cache: bool = True):
    print("\n" + "=" * 60)
    print("Phase 3: 통합 분석 (Claude API)")
    print("=" * 60)

    if use_cache:
        syn_path = os.path.join(BASE_DIR, "data", "synthesis.json")
        if os.path.exists(syn_path):
            age_hours = (time.time() - os.path.getmtime(syn_path)) / 3600
            if age_hours < 24:
                with open(syn_path, encoding="utf-8") as f:
                    synthesis = json.load(f)
                print(f"  [synthesis] 캐시 사용 ({age_hours:.1f}시간 전 생성)")
                return synthesis

    return synthesis_agent.run(papers, hbr, courses)


def phase3_docx(synthesis: dict) -> str:
    print("\n" + "=" * 60)
    print("Phase 4: DOCX 생성")
    print("=" * 60)
    return docx_writer.run(synthesis)


def validate(out_path: str, synthesis: dict):
    print("\n" + "=" * 60)
    print("Phase 5: 검증")
    print("=" * 60)

    ok = True

    if not os.path.exists(out_path):
        print(f"  [실패] 파일 없음: {out_path}")
        ok = False
    else:
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  [OK] 파일 존재: {out_path} ({size_kb:.1f} KB)")

    sections = synthesis.get("sections", {})
    expected = {"의미", "방법", "사례", "학습자료"}
    missing = expected - set(sections.keys())
    if missing:
        print(f"  [경고] 누락 섹션: {missing}")
        ok = False
    else:
        print(f"  [OK] 4개 섹션 모두 포함")

    sources = synthesis.get("sources", {})
    n_papers = len(sources.get("papers", []))
    n_hbr = len(sources.get("hbr_articles", []))
    n_courses = len(sources.get("courses", []))
    print(f"  [OK] 수집 현황: 논문 {n_papers}편 | HBR {n_hbr}개 | 강의 {n_courses}개")

    if n_papers < 4:
        print(f"  [경고] 논문 {n_papers}편 (목표: 4편)")
    if n_hbr < 10:
        print(f"  [경고] HBR 아티클 {n_hbr}개 (목표: 10개+)")

    return ok


def main(use_cache: bool = True):
    start = time.time()

    print("=" * 60)
    print("리더십 모델링 & 리더 성장 로드맵 리서치 자동화")
    print("=" * 60)

    # ANTHROPIC_API_KEY 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n[오류] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print("  set ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    try:
        # Phase 2: 검색
        papers, hbr, courses = phase1_search(use_cache=use_cache)

        # Phase 3: 통합 분석
        synthesis = phase2_synthesize(papers, hbr, courses, use_cache=use_cache)

        # Phase 4: DOCX
        out_path = phase3_docx(synthesis)

        # Phase 5: 검증
        validate(out_path, synthesis)

        elapsed = time.time() - start
        print(f"\n{'=' * 60}")
        print(f"완료! 총 소요 시간: {elapsed:.0f}초")
        print(f"최종 파일: {out_path}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n사용자 중단.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[오류] {e}")
        raise


if __name__ == "__main__":
    # --no-cache 옵션으로 캐시 무시 가능
    use_cache = "--no-cache" not in sys.argv
    main(use_cache=use_cache)
