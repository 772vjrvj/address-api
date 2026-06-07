from flask import Flask
from waitress import serve
from routes import api_bp
from logger import get_logger

app = Flask(__name__)

# 분리해둔 API 라우팅 모듈을 조립
app.register_blueprint(api_bp)

logger = get_logger()

if __name__ == '__main__':
    logger.info("=========================================")
    logger.info("B-2 주소 변환 API 서버 구동 시작 (Port: 5001)")
    logger.info("=========================================")

    serve(app, host='0.0.0.0', port=5001, threads=4)