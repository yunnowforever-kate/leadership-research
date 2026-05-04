"""Flask 웹 애플리케이션 - 리서치 자동화 (SSE 스트리밍, Vercel 호환)"""
import base64
import io
import json
import os
import sys

from flask import Flask, Response, jsonify, render_template, request

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

# Vercel 환경 감지 → /tmp 사용
IS_VERCEL = bool(os.environ.get("VERCEL"))
DATA_DIR   = "/tmp/research_data"   if IS_VERCEL else os.path.join(BASE_DIR, "data")
OUTPUT_DIR = "/tmp/research_output" if IS_VERCEL else os.path.join(BASE_DIR, "outputs")

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 에이전트에 경로 주입
os.environ["RESEARCH_DATA_DIR"]   = DATA_DIR
os.environ["RESEARCH_OUTPUT_DIR"] = OUTPUT_DIR

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

app = Flask(__name__)


# ── 헬퍼 ──────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class _Capture(io.TextIOBase):
    """print() → 버퍼 캡처"""
    def __init__(self):
        self.buf: list[str] = []

    def write(self, text):
        if text.strip():
            self.buf.append(text.strip())
        return len(text)

    def flush(self):
        pass

    def drain(self) -> list[str]:
        items, self.buf = self.buf[:], []
        return items


def _flush(cap: _Capture):
    """캡처된 로그를 SSE 이벤트 문자열로 변환"""
    return [_sse({"type": "log", "m": m}) for m in cap.drain()]


# ── 라우트 ────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json() or {}

    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "리서치 주제를 입력해주세요"}), 400

    api_key = data.get("api_key", "").strip()
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"error": "ANTHROPIC_API_KEY가 필요합니다"}), 400

    def generate():
        from agents import paper_agent, hbr_agent, mooc_agent, synthesis_agent, docx_writer, pptx_agent
        import concurrent.futures

        cap = _Capture()
        old_out = sys.stdout
        sys.stdout = cap

        try:
            yield _sse({"type": "start", "topic": topic})
            yield _sse({"type": "log", "m": "=" * 50})
            yield _sse({"type": "log", "m": f"  리서치 주제: {topic}"})
            yield _sse({"type": "log", "m": "=" * 50})

            # ── Phase 1: 병렬 검색 ──────────────────────────
            yield _sse({"type": "phase", "n": 1, "label": "논문 · HBR · 강의 검색"})

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
                f_p = ex.submit(paper_agent.run,  topic)
                f_h = ex.submit(hbr_agent.run,    topic)
                f_m = ex.submit(mooc_agent.run,   topic)
                papers  = f_p.result()
                hbr     = f_h.result()
                courses = f_m.result()

            for ev in _flush(cap): yield ev
            yield _sse({"type": "log", "m": f"논문 {len(papers)}편 | HBR {len(hbr)}개 | 강의 {len(courses)}개 수집"})

            # ── Phase 2: Claude 분석 ─────────────────────────
            yield _sse({"type": "phase", "n": 2, "label": "Claude AI 통합 분석"})
            synthesis = synthesis_agent.run(topic, papers, hbr, courses)
            for ev in _flush(cap): yield ev

            # ── Phase 3: DOCX + PPTX 생성 ──────────────────
            yield _sse({"type": "phase", "n": 3, "label": "Word · PPT 문서 생성"})
            docx_path = docx_writer.run(synthesis)
            for ev in _flush(cap): yield ev

            pptx_path = pptx_agent.run(synthesis)
            for ev in _flush(cap): yield ev

            # 파일을 base64로 인코딩
            with open(docx_path, "rb") as f:
                docx_b64 = base64.b64encode(f.read()).decode()
            with open(pptx_path, "rb") as f:
                pptx_b64 = base64.b64encode(f.read()).decode()

            yield _sse({"type": "done", "success": True,
                        "docx_filename": os.path.basename(docx_path),
                        "docx_b64": docx_b64,
                        "pptx_filename": os.path.basename(pptx_path),
                        "pptx_b64": pptx_b64})

        except Exception as e:
            for ev in _flush(cap): yield ev
            yield _sse({"type": "done", "success": False, "error": str(e)})
        finally:
            sys.stdout = old_out

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    print("서버 시작: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
