import requests
from logger import get_logger

# 🌟 격리된 데이터베이스 모듈 기능 가져오기
from database import get_address_from_postgres, save_to_postgres

logger = get_logger()

REST_API_KEY = "85c3a19945eb6dc379dcf148b1f4455c"

def fetch_from_kakao(lat, lng):
    """단건 카카오 역지오코딩 API 호출 함수 (기존 성공 코드 보존)"""
    if not lat or not lng or lat == 0.0 or lng == 0.0:
        logger.warning(f"⚠️ [카카오 API 스킵] 유효하지 않은 좌표: lat={lat}, lng={lng}")
        return None

    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {REST_API_KEY}"}
    params = {"x": lng, "y": lat}

    logger.info(f"🚀 [카카오 API 요청] 좌표: lat={lat}, lng={lng}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('documents'):
                logger.info(f"✅ [카카오 API 성공] 주소 변환 완료 (lat={lat}, lng={lng})")
                return data['documents'][0]
            else:
                logger.warning(f"⚠️ [카카오 API 결과 없음] 해당 좌표에 매칭되는 주소 없음 (lat={lat}, lng={lng})")
        else:
            logger.error(f"❌ [카카오 API 에러] 상태 코드: {response.status_code} / 응답: {response.text[:200]}")
    except Exception as e:
        logger.error(f"❌ [카카오 API 통신 실패] (lat={lat}, lng={lng}) / 에러: {e}")

    return None

def process_reverse_batch_service(items):
    """
    20개의 리스트를 받아서 DB 캐시 확인 및 카카오 API로 변환 후 결과 반환
    """
    results = []

    for item in items:
        req_id = item.get('id')
        lat = item.get('lat')
        lng = item.get('lng')

        # 🌟 [1단계] PostgreSQL DB 조회 로직 활성화
        db_result = get_address_from_postgres(lat, lng)
        if db_result:
            logger.info(f"📦 [DB 캐시 히트] 좌표 자원 탐색 성공 (lat={lat}, lng={lng})")
            db_result["id"] = req_id  # 크롤러가 보낸 식별 ID 동기화
            results.append(db_result)
            continue

        # [2단계] DB 캐시 미스 시 카카오 API 찌르기
        kakao_doc = fetch_from_kakao(lat, lng)

        if kakao_doc:
            result_item = {
                "id": req_id,
                "address": kakao_doc.get("address") or {},
                "road_address": kakao_doc.get("road_address") or {}
            }

            # 🌟 [3단계] 새로 구한 주소 정보를 로컬 캐시 DB에 저장
            save_to_postgres(lat, lng, kakao_doc)
        else:
            result_item = {"id": req_id, "address": {}, "road_address": {}}

        results.append(result_item)

    return results