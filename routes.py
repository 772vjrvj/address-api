import os
from flask import Blueprint, request, jsonify
from functools import wraps
from dotenv import load_dotenv
from logger import get_logger

# 1. .env 파일 환경변수 로드
load_dotenv()

# Blueprint 생성
api_bp = Blueprint('api', __name__)
logger = get_logger()

# 2. .env에서 API 키 가져오기 (파일에 없으면 에러 방지용으로 빈 세트)
MASTER_KEY = os.getenv('MASTER_API_KEY')
VALID_API_KEYS = {MASTER_KEY} if MASTER_KEY else set()


# API Key 검증 데코레이터
def require_apikey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        request_key = request.headers.get('x-api-key')

        if request_key and request_key in VALID_API_KEYS:
            return view_function(*args, **kwargs)
        else:
            logger.warning(f"접근 거부: 잘못된 API Key 시도 (IP: {request.remote_addr})")
            return jsonify({"status": "error", "message": "Unauthorized API Key"}), 401

    return decorated_function


# ====================================================
# [테스트용 API] 스마트폰 브라우저 네트워크 연결 확인용 (Key 불필요)
# ====================================================
@api_bp.route('/ping', methods=['GET'])
def ping_test():
    logger.info(f"단순 접속 테스트 요청 수신 (IP: {request.remote_addr})")
    return jsonify({
        "status": "success",
        "message": "서버 통신이 완벽하게 뚫려있습니다! (Port 5001 정상 작동)"
    })


# ====================================================
# [본 기능 API] 주소 변환 기능 (Key 필수, POST 방식)
# ====================================================
@api_bp.route('/api/get_address', methods=['POST'])
@require_apikey
def get_address():
    data = request.get_json()
    if not data:
        logger.error(f"요청 실패: JSON 데이터 없음 (IP: {request.remote_addr})")
        return jsonify({"status": "error", "message": "No JSON payload"}), 400

    lat = data.get('lat')
    lng = data.get('lng')

    logger.info(f"요청 수신 - 위도: {lat}, 경도: {lng} (IP: {request.remote_addr})")

    # 향후 DB 조회 로직이 들어갈 자리
    dummy_address = "경기도 수원시 영통구 망포동 힐스테이트영통 110동"

    logger.info(f"응답 완료 - 매칭 주소: {dummy_address}")

    return jsonify({
        "status": "success",
        "address": dummy_address
    })