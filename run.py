# run.py
import os
import sys
import io

from flask import Flask
from waitress import serve

from routes import api_bp
from logger import get_logger


# ====================================================
# 1. 콘솔 출력 UTF-8 설정
# ====================================================
# 윈도우 콘솔 / PM2 / 로그 파일 환경에서 한글 로그 깨짐 방지.
# Python 3.7+ 에서는 reconfigure가 가장 안전하다.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    # 일부 환경에서는 reconfigure가 없거나 실패할 수 있으므로 fallback 처리
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding="utf-8")
    except Exception:
        pass


# ====================================================
# 2. Flask App 생성
# ====================================================
app = Flask(__name__)

# jsonify 한글이 \uc11c\ubc84 이런 식으로 escape 되지 않도록 설정
app.json.ensure_ascii = False

# API 라우터 등록
# 등록 후 실제 경로:
# - GET  /ping
# - POST /geocode/reverse-batch
app.register_blueprint(api_bp)


logger = get_logger()


# ====================================================
# 3. Waitress 서버 실행
# ====================================================
if __name__ == "__main__":
    # 환경변수로 조절 가능하게 해두면 나중에 튜닝하기 편함
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "5001"))
    WAITRESS_THREADS = int(os.getenv("WAITRESS_THREADS", "4"))

    logger.info("=========================================")
    logger.info(f"B-2 주소 변환 API 서버 구동 시작 (Port: {SERVER_PORT})")
    logger.info(f"Host={SERVER_HOST}, Threads={WAITRESS_THREADS}")
    logger.info("=========================================")

    serve(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        threads=WAITRESS_THREADS
    )