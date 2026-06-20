# geo_service.py
import os
import time
import copy
import threading
import requests
from dotenv import load_dotenv

from logger import get_logger

from database import (
    get_addresses_from_postgres_batch,
    save_to_postgres,
)

logger = get_logger()

# ====================================================
# .env 로드
# api.py import 순서와 상관없이 geo_service 자체에서 안전하게 로드
# ====================================================
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"), override=False, encoding="utf-8-sig")

REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

try:
    KAKAO_MIN_INTERVAL = float(os.getenv("KAKAO_MIN_INTERVAL", "0.2"))
except Exception:
    KAKAO_MIN_INTERVAL = 0.2

# 카카오 API는 서버 전체 기준 1개씩만 실행
_kakao_api_semaphore = threading.BoundedSemaphore(1)

# 서버 전체 기준 카카오 호출 간격 제어용
_kakao_rate_lock = threading.Lock()
_last_kakao_call_time = 0.0


def normalize_coord(lat, lng):
    """
    좌표 정규화.
    같은 위치인데 소수점 미세 차이 때문에 DB 캐시가 안 먹는 문제 방지.
    """
    try:
        if lat is None or lng is None:
            return None, None

        lat = float(lat)
        lng = float(lng)

        if lat == 0.0 or lng == 0.0:
            return None, None

        return round(lat, 6), round(lng, 6)

    except Exception:
        return None, None


def wait_kakao_rate_limit():
    """
    여러 요청이 동시에 들어와도 카카오 API는 서버 전체 기준으로 천천히 호출되게 제한.
    """
    global _last_kakao_call_time

    with _kakao_rate_lock:
        now = time.time()
        elapsed = now - _last_kakao_call_time

        if elapsed < KAKAO_MIN_INTERVAL:
            time.sleep(KAKAO_MIN_INTERVAL - elapsed)

        _last_kakao_call_time = time.time()


def empty_result(req_id):
    return {
        "id": req_id,
        "address": {},
        "road_address": {}
    }


def fetch_from_kakao(lat, lng):
    """
    카카오 역지오코딩 API 단건 호출.
    서버 전체에서 동시에 1개만 호출되도록 제한.
    """
    if not REST_API_KEY:
        logger.error("❌ KAKAO_REST_API_KEY 환경변수가 없습니다.")
        return None

    if lat is None or lng is None:
        logger.warning(f"⚠️ [카카오 API 스킵] 유효하지 않은 좌표: lat={lat}, lng={lng}")
        return None

    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"

    headers = {
        "Authorization": f"KakaoAK {REST_API_KEY}"
    }

    params = {
        "x": lng,
        "y": lat
    }

    # ====================================================
    # 핵심:
    # 카카오 API 요청 자체를 서버 전체에서 1개씩만 실행
    # ====================================================
    with _kakao_api_semaphore:
        wait_kakao_rate_limit()

        logger.info(f"🚀 [카카오 API 요청] lat={lat}, lng={lng}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if data.get("documents"):
                    logger.info(f"✅ [카카오 API 성공] lat={lat}, lng={lng}")
                    return data["documents"][0]

                logger.warning(f"⚠️ [카카오 API 결과 없음] lat={lat}, lng={lng}")
                return None

            if response.status_code == 429:
                logger.warning(f"⚠️ [카카오 API 429 제한] lat={lat}, lng={lng}")
                time.sleep(2)
                return None

            logger.error(
                f"❌ [카카오 API 에러] status={response.status_code}, body={response.text[:200]}"
            )
            return None

        except Exception as e:
            logger.error(f"❌ [카카오 API 통신 실패] lat={lat}, lng={lng}, error={e}")
            return None

def process_reverse_batch_service(items):
    """
    처리 순서:
    1. 요청 좌표 정규화
    2. 요청 안에서 중복 좌표 제거
    3. DB에서 batch 조회
    4. DB hit 결과 먼저 채움
    5. DB miss 좌표만 카카오 API 순차 호출
    6. 결과를 원래 요청 순서대로 반환
    """
    if not items:
        return []

    start_time = time.time()

    results = [None] * len(items)

    # coord_key -> 요청 index 리스트
    # 같은 좌표가 요청 안에 여러 번 들어오면 카카오를 한 번만 호출하기 위함
    coord_to_indexes = {}

    # ====================================================
    # 1. 좌표 정규화 + 요청 내부 중복 그룹핑
    # ====================================================
    for index, item in enumerate(items):
        req_id = item.get("id")
        lat = item.get("lat")
        lng = item.get("lng")

        norm_lat, norm_lng = normalize_coord(lat, lng)

        if norm_lat is None or norm_lng is None:
            logger.warning(f"⚠️ [좌표 스킵] id={req_id}, lat={lat}, lng={lng}")
            results[index] = empty_result(req_id)
            continue

        coord_key = (norm_lat, norm_lng)
        coord_to_indexes.setdefault(coord_key, []).append(index)

    unique_coords = list(coord_to_indexes.keys())

    if not unique_coords:
        return results

    logger.info(
        f"📌 [배치 시작] 요청={len(items)}건, 유효좌표={len(unique_coords)}건"
    )

    # ====================================================
    # 2. DB batch 조회
    # ====================================================
    try:
        db_result_map = get_addresses_from_postgres_batch(unique_coords)
    except Exception as e:
        logger.error(f"❌ [DB 배치 조회 실패] error={e}")
        db_result_map = {}

    db_hit_count = 0
    db_miss_coords = []

    # ====================================================
    # 3. DB hit 결과 먼저 채우기
    # ====================================================
    for coord_key in unique_coords:
        db_result = db_result_map.get(coord_key)

        if db_result:
            db_hit_count += 1

            for index in coord_to_indexes[coord_key]:
                req_id = items[index].get("id")

                result_item = copy.deepcopy(db_result)
                result_item["id"] = req_id

                results[index] = result_item

        else:
            db_miss_coords.append(coord_key)

    logger.info(
        f"📦 [DB 조회 완료] hit={db_hit_count}건, miss={len(db_miss_coords)}건"
    )

    # ====================================================
    # 4. DB miss만 카카오 API 순차 호출
    # ====================================================
    kakao_success_count = 0
    kakao_fail_count = 0

    for coord_key in db_miss_coords:
        lat, lng = coord_key

        kakao_doc = fetch_from_kakao(lat, lng)

        if kakao_doc:
            base_result = {
                "address": kakao_doc.get("address") or {},
                "road_address": kakao_doc.get("road_address") or {}
            }

            kakao_success_count += 1

            try:
                save_to_postgres(lat, lng, kakao_doc)
            except Exception as e:
                logger.error(f"❌ [DB 저장 실패] lat={lat}, lng={lng}, error={e}")

        else:
            base_result = {
                "address": {},
                "road_address": {}
            }

            kakao_fail_count += 1

        # 같은 좌표를 요청한 모든 item에 결과 복사
        for index in coord_to_indexes[coord_key]:
            req_id = items[index].get("id")

            result_item = copy.deepcopy(base_result)
            result_item["id"] = req_id

            results[index] = result_item

    # 혹시 None 남은 것 방어
    for index, result in enumerate(results):
        if result is None:
            results[index] = empty_result(items[index].get("id"))

    elapsed = time.time() - start_time

    logger.info(
        f"✅ [배치 완료] 요청={len(items)}건, "
        f"DB hit={db_hit_count}건, "
        f"카카오 성공={kakao_success_count}건, "
        f"카카오 실패={kakao_fail_count}건, "
        f"소요={elapsed:.2f}초"
    )

    return results