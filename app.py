"""Flask 웹 애플리케이션 - 리더십 리서치 자동화"""
import io
import json
import os
import sys
import threading
import concurrent.futures
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

app = Flask(__name__)

# ── 전역 상태 ─────────────────────────────────────────────
_state = {
    "running": False,
    "done": False,
    "success": False,
    "logs": [],
    "output_file": None,
    "error": None,
}
_lock = threading.Lock()


def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    with _lock:
        _state["logs"].append({"t": ts, "m": msg})


# ── 라우트 ────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    offset = request.args.get("offset", 0, type=int)
    with _lock:
        return jsonify({
            "running": _state["running"],
            "done": _state["done"],
            "success": _state["success"],
            "error": _state["error"],
            "logs": _state["logs"][offset:],
            "total": len(_state["logs"]),
            "file": os.path.basename(_state["output_file"]) if _state["output_file"] else None,
        })


@app.route("/api/run", methods=["POST"])
def api_run():
    with _lock:
        if _state["running"]:
            return jsonify({"error": "이미 실행 중입니다"}), 400

        data = request.get_json() or {}
        api_key = data.get("api_key", "").strip()
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return jsonify({"error": "ANTHROPIC_API_KEY가 필요합니다"}), 400

        _state.update({
            "running": True, "done": False, "success": False,
            "logs": [], "output_file": None, "error": None,
        })

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/download")
def api_download():
    with _lock:
        path = _state["output_file"]
    if not path or not os.path.exists(path):
        return jsonify({"error": "파일이 없습니다"}), 404
    return send_file(path, as_attachment=True)


# ── 워커 (백그라운드 스레드) ──────────────────────────────

class _LogCapture(io.TextIOBase):
    """print() 출력을 _log()로 전달하는 스트림"""
    def __init__(self, original):
        self._orig = original

    def write(self, text):
        if text.strip():
            _log(text.strip())
        self._orig.write(text)
        return len(text)

    def flush(self):
        self._orig.flush()


def _worker():
    old_stdout = sys.stdout
    sys.stdout = _LogCapture(old_stdout)
    try:
        from agents import paper_agent, hbr_agent, mooc_agent, synthesis_agent, docx_writer

        _log("=" * 52)
        _log("  리더십 모델링 & 리더 성장 로드맵 리서치 시작")
        _log("=" * 52)

        _log("\n▶ Phase 1 | 병렬 검색 실행 중...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_p = ex.submit(paper_agent.run)
            f_h = ex.submit(hbr_agent.run)
            f_m = ex.submit(mooc_agent.run)
            papers  = f_p.result()
            hbr     = f_h.result()
            courses = f_m.result()

        _log(f"   논문 {len(papers)}편 | HBR {len(hbr)}개 | 강의 {len(courses)}개 수집")

        _log("\n▶ Phase 2 | Claude API 통합 분석 중...")
        synthesis = synthesis_agent.run(papers, hbr, courses)

        _log("\n▶ Phase 3 | DOCX 파일 생성 중...")
        out_path = docx_writer.run(synthesis)

        with _lock:
            _state["output_file"] = out_path
            _state["success"] = True

        _log(f"\n✓ 완료! → {os.path.basename(out_path)}")

    except Exception as e:
        _log(f"\n✗ 오류 발생: {e}")
        with _lock:
            _state["error"] = str(e)
    finally:
        sys.stdout = old_stdout
        with _lock:
            _state["running"] = False
            _state["done"] = True


if __name__ == "__main__":
    print("서버 시작: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
