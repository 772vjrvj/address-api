import os
from flask import Blueprint, request, jsonify
from functools import wraps
from dotenv import load_dotenv

from geo_service import process_reverse_batch_service
from logger import get_logger

# ====================================================
# 1. .env 파일 환경변수 로드 (절대 경로 방식으로 변경!)
# ====================================================
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')

# 🌟 1. 윈도우 특유의 눈에 안 보이는 문자(BOM)를 무시하고 강제로 읽게 만듦
load_dotenv(env_path, override=True, encoding='utf-8-sig')

MASTER_KEY = os.getenv('MASTER_API_KEY')
VALID_API_KEYS = {MASTER_KEY} if MASTER_KEY else set()

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
# [본 기능 API] 20개 리스트 주소 일괄 변환 (경로 수정됨)
# ====================================================
@api_bp.route('/geocode/reverse-batch', methods=['POST'])
@require_apikey
def get_address_batch():
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({"status": "error", "message": "Payload must be a JSON array"}), 400

        logger.info(f"배치 요청 수신 - 건수: {len(data)}건")

        # 서비스 로직 호출
        results = process_reverse_batch_service(data)

        return jsonify(results) # 정상일 때 결과 리스트 반환

    except Exception as e:
        logger.error(f"서버 내부 에러 발생: {e}")
        # 에러 발생 시에도 JSON 리스트 []를 반환하여 클라이언트가 멈추지 않게 함
        return jsonify([]), 200