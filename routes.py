# routes.py
import os
from functools import wraps

from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

from logger import get_logger


# ====================================================
# 1. .env 파일 환경변수 로드
# ====================================================
# 중요:
# geo_service.py가 import될 때 KAKAO_REST_API_KEY 등을 읽을 수 있으므로
# geo_service import 전에 .env를 먼저 로드해둔다.
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, ".env")

load_dotenv(env_path, override=False, encoding="utf-8-sig")


# ====================================================
# 2. 서비스 import
# ====================================================
# .env 로드 후 import하는 것이 안전하다.
from geo_service import process_reverse_batch_service


# ====================================================
# 3. 기본 설정
# ====================================================
api_bp = Blueprint("api", __name__)
logger = get_logger()

MASTER_KEY = os.getenv("MASTER_API_KEY")
VALID_API_KEYS = {MASTER_KEY} if MASTER_KEY else set()

try:
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "200"))
except Exception:
    MAX_BATCH_SIZE = 200


# ====================================================
# 4. API Key 검증 데코레이터
# ====================================================
def require_apikey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        request_key = request.headers.get("x-api-key")

        if request_key and request_key in VALID_API_KEYS:
            return view_function(*args, **kwargs)

        logger.warning(f"접근 거부: 잘못된 API Key 시도 (IP: {request.remote_addr})")

        return jsonify({
            "status": "error",
            "message": "Unauthorized API Key"
        }), 401

    return decorated_function


# ====================================================
# 5. 테스트용 API
# ====================================================
# 스마트폰/브라우저/외부 PC에서 서버 접속이 되는지 확인하는 용도
# API Key 불필요
@api_bp.route("/ping", methods=["GET"])
def ping_test():
    logger.info(f"단순 접속 테스트 요청 수신 (IP: {request.remote_addr})")

    return jsonify({
        "status": "success",
        "message": "서버 통신이 완벽하게 뚫려있습니다! (Port 5001 정상 작동)"
    })


# ====================================================
# 6. 주소 일괄 변환 API
# ====================================================
# 요청 예시:
# [
#   {"id": "123", "lat": 37.566826, "lng": 126.978656},
#   {"id": "124", "lat": 37.123456, "lng": 127.123456}
# ]
#
# 처리 방식:
# 1. 서버에서 DB batch 조회
# 2. DB 캐시 hit는 바로 반환
# 3. DB miss만 Kakao API 순차 호출
# 4. 결과는 요청 순서대로 리스트 반환
@api_bp.route("/geocode/reverse-batch", methods=["POST"])
@require_apikey
def get_address_batch():
    try:
        # silent=True:
        # JSON 형식이 아니어도 Flask가 예외를 터뜨리지 않고 None 반환
        data = request.get_json(silent=True)

        if data is None or not isinstance(data, list):
            return jsonify({
                "status": "error",
                "message": "Payload must be a JSON array"
            }), 400

        # 빈 배열은 정상 요청으로 보고 빈 배열 반환
        if len(data) == 0:
            return jsonify([])

        # 너무 큰 요청 방어
        # 화면에서는 chunk_size=100 추천
        # 서버는 MAX_BATCH_SIZE=200 정도로 제한 추천
        if len(data) > MAX_BATCH_SIZE:
            logger.warning(
                f"배치 요청 크기 초과 - 요청={len(data)}건, 제한={MAX_BATCH_SIZE}건, IP={request.remote_addr}"
            )

            return jsonify({
                "status": "error",
                "message": f"Payload too large. Max batch size is {MAX_BATCH_SIZE}"
            }), 413

        logger.info(f"배치 요청 수신 - 건수: {len(data)}건, IP={request.remote_addr}")

        results = process_reverse_batch_service(data)

        return jsonify(results)

    except Exception as e:
        logger.error(f"서버 내부 에러 발생: {e}")

        # 기존 클라이언트가 멈추지 않게 하기 위해 빈 리스트 반환 유지
        # 다만 실제 장애 확인을 위해 로그는 반드시 남긴다.
        return jsonify([]), 200