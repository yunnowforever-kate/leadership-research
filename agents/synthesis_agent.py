"""통합 분석 에이전트: Claude API로 4개 섹션 한국어 콘텐츠 생성 (주제 기반)"""
import json
import os
import anthropic

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.environ.get("RESEARCH_DATA_DIR", os.path.join(BASE_DIR, "data"))


def _make_section_guides(topic: str) -> dict:
    return {
        "의미": {
            "title": f"{topic}의 의미와 중요성",
            "instruction": (
                f"'{topic}'의 정의, 핵심 개념, 중요성, 시대적 배경을 설명하라. "
                "A4 1~1.5페이지 분량. 하위 항목: 1.1 정의 및 핵심 개념, 1.2 왜 중요한가, 1.3 시대적 배경."
            ),
        },
        "방법": {
            "title": f"{topic} 실행 방법",
            "instruction": (
                f"'{topic}'을 설계하고 실행하는 원칙, 단계별 프로세스, 핵심 체크포인트를 설명하라. "
                "A4 2~3페이지 분량. 하위 항목: 2.1 설계 원칙, 2.2 단계별 프로세스, 2.3 핵심 체크포인트."
            ),
        },
        "사례": {
            "title": f"AI 시대 {topic} 대표 사례",
            "instruction": (
                f"AI 시대에 적합한 '{topic}' 실제 사례 3~5개를 제시하라. "
                "A4 2~3페이지 분량. 하위 항목: 3.1 국내외 대표 사례, 3.2 AI 활용 혁신 사례. "
                "각 사례에 출처 명기."
            ),
        },
        "학습자료": {
            "title": f"{topic} 학습 자료 큐레이션",
            "instruction": (
                f"수집된 논문, HBR 아티클, 온라인 강의를 '{topic}' 관점에서 큐레이션하고 활용 가이드를 제공하라. "
                "A4 1~2페이지 분량. 하위 항목: 4.1 핵심 논문, 4.2 HBR 아티클 큐레이션, 4.3 추천 온라인 강의."
            ),
        },
    }


def _build_prompt(topic: str, section_key: str, guide: dict, data: dict) -> str:
    papers_text  = json.dumps(data["papers"],        ensure_ascii=False, indent=2)
    hbr_text     = json.dumps(data["hbr_articles"][:10], ensure_ascii=False, indent=2)
    courses_text = json.dumps(data["courses"],       ensure_ascii=False, indent=2)

    return f"""당신은 '{topic}' 분야 전문 리서처입니다. 아래 수집된 자료를 바탕으로 보고서 섹션을 한국어로 작성하세요.

## 작성할 섹션
제목: {guide['title']}
지침: {guide['instruction']}

## 작성 규칙
- 한국어로 작성 (자료 제목·저자·기관명은 원어 병기)
- 구체적인 사례, 데이터, 프레임워크 포함
- 각 내용마다 출처 표기: (저자, 연도) 또는 (출처: URL)
- 소제목은 ## 마크다운 사용
- 생략 없이 풍부하게 작성

## 수집 자료

### 학술 논문
{papers_text}

### HBR 아티클
{hbr_text}

### 온라인 강의
{courses_text}

위 자료를 종합하여 '{guide['title']}' 섹션을 작성하세요."""


def run(topic: str, papers: list, hbr_articles: list, courses: list) -> dict:
    print(f"[통합 분석 에이전트] '{topic}' Claude API 섹션 생성 시작...")
    os.makedirs(DATA_DIR, exist_ok=True)

    client = anthropic.Anthropic()
    section_guides = _make_section_guides(topic)
    all_data = {"papers": papers, "hbr_articles": hbr_articles, "courses": courses}

    sections = {}
    for key, guide in section_guides.items():
        print(f"  섹션 생성 중: {guide['title']}")
        prompt = _build_prompt(topic, key, guide, all_data)

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=3000,
            system=[{
                "type": "text",
                "text": f"당신은 '{topic}' 주제로 한국어 연구 보고서를 작성하는 전문가입니다. 수집된 자료를 기반으로 체계적이고 심층적인 내용을 작성합니다.",
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        sections[key] = {
            "title": guide["title"],
            "content": response.content[0].text,
        }
        print(f"  완료: {guide['title']} ({len(response.content[0].text)}자)")

    synthesis = {
        "topic": topic,
        "sections": sections,
        "sources": {
            "papers": papers,
            "hbr_articles": hbr_articles,
            "courses": courses,
        },
    }

    out_path = os.path.join(DATA_DIR, "synthesis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(synthesis, f, ensure_ascii=False, indent=2)

    print(f"[통합 분석 에이전트] 완료 → {out_path}")
    return synthesis


if __name__ == "__main__":
    import sys

    def _load(name):
        p = os.path.join(DATA_DIR, f"{name}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return []

    topic = sys.argv[1] if len(sys.argv) > 1 else "리더십 모델링"
    run(topic, _load("papers"), _load("hbr_articles"), _load("courses"))
