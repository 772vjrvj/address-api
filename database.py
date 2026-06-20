# database.py
import os
import json
import atexit
import threading

from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor, Json, execute_values
from dotenv import load_dotenv

from logger import get_logger

logger = get_logger()

# ====================================================
# 1. .env 로드
# ====================================================
# database.py 파일이 위치한 경로 기준으로 .env를 읽는다.
# utf-8-sig는 윈도우에서 생길 수 있는 BOM 문자를 방지하기 위함.
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"), override=False, encoding="utf-8-sig")


# ====================================================
# 2. 환경변수 안전 파싱 함수
# ====================================================
def get_env_int(name, default):
    """정수 환경변수 안전 파싱"""
    try:
        return int(os.getenv(name, default))
    except Exception:
        logger.warning(f"⚠️ 환경변수 {name} 값이 잘못되어 기본값 사용: {default}")
        return int(default)


def get_env_float(name, default):
    """실수 환경변수 안전 파싱"""
    try:
        return float(os.getenv(name, default))
    except Exception:
        logger.warning(f"⚠️ 환경변수 {name} 값이 잘못되어 기본값 사용: {default}")
        return float(default)


# ====================================================
# 3. DB 환경변수
# ====================================================
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# 커넥션 풀 크기
# 서버 요청이 여러 개 동시에 들어올 수 있으므로 ThreadedConnectionPool 사용
DB_POOL_MIN = get_env_int("DB_POOL_MIN", "1")
DB_POOL_MAX = get_env_int("DB_POOL_MAX", "10")

# 주소 캐시 검색 반경 meter
# 예: 15면 요청 좌표 기준 반경 15m 안에 저장된 주소를 캐시 hit로 판단
ADDRESS_CACHE_RADIUS_METER = get_env_float("ADDRESS_CACHE_RADIUS_METER", "15")


# ====================================================
# 4. 전역 커넥션 풀
# ====================================================
_pool = None

# 서버 시작 직후 여러 요청이 동시에 들어오면
# get_pool()이 동시에 호출되면서 pool이 중복 생성될 수 있으므로 lock 사용
_pool_lock = threading.Lock()


def get_pool():
    """
    서버가 살아있는 동안 유지될 PostgreSQL 커넥션 풀 반환.

    최초 1회만 ThreadedConnectionPool을 생성하고,
    이후 요청에서는 같은 pool을 재사용한다.
    """
    global _pool

    if _pool is not None:
        return _pool

    with _pool_lock:
        # lock을 기다리는 동안 다른 스레드가 이미 pool을 만들었을 수 있으므로 재확인
        if _pool is not None:
            return _pool

        try:
            missing_envs = []

            if not DB_NAME:
                missing_envs.append("DB_NAME")
            if not DB_USER:
                missing_envs.append("DB_USER")
            if not DB_PASSWORD:
                missing_envs.append("DB_PASSWORD")

            if missing_envs:
                raise ValueError(f"DB 환경변수 누락: {', '.join(missing_envs)}")

            _pool = ThreadedConnectionPool(
                minconn=DB_POOL_MIN,
                maxconn=DB_POOL_MAX,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )

            logger.info(
                f"✅ PostgreSQL Connection Pool 초기화 완료 "
                f"(min={DB_POOL_MIN}, max={DB_POOL_MAX}, host={DB_HOST}, port={DB_PORT})"
            )

            return _pool

        except Exception as e:
            logger.error(f"❌ PostgreSQL Connection Pool 생성 실패: {e}")
            raise


# ====================================================
# 5. 좌표 정규화
# ====================================================
def normalize_coord(lat, lng):
    """
    좌표 정규화.

    목적:
    - None, 0.0 같은 잘못된 좌표 방어
    - 문자열 좌표도 float로 변환
    - 소수점 미세 차이 때문에 같은 위치가 다른 좌표로 취급되는 문제 완화

    참고:
    - 소수점 6자리 정도면 대략 10cm 수준이라 주소 캐시 용도로 충분한 편
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


# ====================================================
# 6. JSON 값 안전 변환
# ====================================================
def safe_json_value(value):
    """
    PostgreSQL JSON/JSONB 값을 Python dict로 안전하게 변환.

    RealDictCursor 사용 시 JSONB 컬럼은 보통 dict로 오지만,
    환경/드라이버 상태에 따라 문자열로 올 가능성도 방어한다.
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}

    return {}


# ====================================================
# 7. 단건 주소 캐시 조회
# ====================================================
def get_address_from_postgres(lat, lng):
    """
    단건 공간 조회.

    입력된 위경도 기준 ADDRESS_CACHE_RADIUS_METER 반경 안에
    기존 주소 캐시가 있으면 그 주소를 반환한다.

    현재는 geo_service.py에서 batch 조회를 주로 쓰지만,
    기존 코드 호환이나 단건 테스트용으로 남겨둔다.
    """
    norm_lat, norm_lng = normalize_coord(lat, lng)

    if norm_lat is None or norm_lng is None:
        return None

    pool = get_pool()
    conn = None

    try:
        conn = pool.getconn()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                  SELECT
                      address_data,
                      road_address_data
                  FROM address_cache
                  WHERE ST_DWithin(
                                geom::geography,
                                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                                %s
                        )
                  ORDER BY updated_at DESC
                  LIMIT 1 \
                  """

            # 중요:
            # ST_MakePoint는 (경도, 위도) 순서다.
            cur.execute(sql, (norm_lng, norm_lat, ADDRESS_CACHE_RADIUS_METER))
            row = cur.fetchone()

            if row:
                return {
                    "address": safe_json_value(row["address_data"]),
                    "road_address": safe_json_value(row["road_address_data"])
                }

    except Exception as e:
        logger.error(
            f"❌ PostgreSQL 공간 단건 조회 오류: "
            f"lat={lat}, lng={lng}, error={e}"
        )

    finally:
        if conn:
            try:
                # SELECT만 해도 psycopg2에서는 트랜잭션이 열릴 수 있다.
                # rollback으로 정리하지 않으면 idle in transaction 상태로 남을 수 있음.
                conn.rollback()
            except Exception:
                pass

            pool.putconn(conn)

    return None


# ====================================================
# 8. 배치 주소 캐시 조회
# ====================================================
def get_addresses_from_postgres_batch(coords):
    """
    여러 좌표를 한 번에 공간 조회.

    coords 예시:
        [
            (37.566826, 126.978656),
            (37.123456, 127.123456)
        ]

    반환 예시:
        {
            (37.566826, 126.978656): {
                "address": {...},
                "road_address": {...}
            }
        }

    핵심:
    - 기존처럼 좌표마다 DB를 100번 조회하지 않는다.
    - 요청 좌표 100개를 DB에 한 번에 전달한다.
    - 각 요청 좌표 기준 반경 ADDRESS_CACHE_RADIUS_METER 안의 캐시를 찾는다.
    - 같은 좌표에 여러 캐시가 있으면 updated_at 최신 데이터 1개를 사용한다.
    """
    if not coords:
        return {}

    # ----------------------------------------------------
    # 1. 좌표 정규화 + 유효 좌표만 남김
    # ----------------------------------------------------
    normalized_coords = []

    for lat, lng in coords:
        norm_lat, norm_lng = normalize_coord(lat, lng)

        if norm_lat is None or norm_lng is None:
            continue

        normalized_coords.append((norm_lat, norm_lng))

    # 요청 안에 같은 좌표가 여러 번 들어올 수 있으므로 중복 제거
    # dict.fromkeys는 순서를 유지하면서 중복 제거 가능
    normalized_coords = list(dict.fromkeys(normalized_coords))

    if not normalized_coords:
        return {}

    pool = get_pool()
    conn = None

    try:
        conn = pool.getconn()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ----------------------------------------------------
            # execute_values 주의:
            # 기본 page_size가 100이라서 좌표가 200개면 SQL이 2번 나뉘어 실행될 수 있다.
            # 그 상태에서 cur.fetchall()을 하면 마지막 page 결과만 가져올 위험이 있다.
            #
            # 그래서 page_size=len(normalized_coords)로 설정해서
            # 이 배치 요청은 반드시 1번의 SQL로 실행되게 한다.
            #
            # 서버 api.py에서 MAX_BATCH_SIZE를 100~200 정도로 제한하는 전제라 안전하다.
            # ----------------------------------------------------
            sql = f"""
                WITH input_coords(lat, lng) AS (
                    VALUES %s
                ),
                matched AS (
                    SELECT DISTINCT ON (i.lat, i.lng)
                        i.lat AS input_lat,
                        i.lng AS input_lng,
                        ac.address_data,
                        ac.road_address_data,
                        ac.updated_at
                    FROM input_coords i
                    JOIN address_cache ac
                        ON ST_DWithin(
                            ac.geom::geography,
                            ST_SetSRID(ST_MakePoint(i.lng, i.lat), 4326)::geography,
                            {ADDRESS_CACHE_RADIUS_METER}
                        )
                    ORDER BY
                        i.lat,
                        i.lng,
                        ac.updated_at DESC
                )
                SELECT
                    input_lat,
                    input_lng,
                    address_data,
                    road_address_data
                FROM matched
            """

            execute_values(
                cur,
                sql,
                normalized_coords,
                template="(%s::double precision, %s::double precision)",
                page_size=len(normalized_coords)
            )

            rows = cur.fetchall()

            result_map = {}

            for row in rows:
                input_lat = round(float(row["input_lat"]), 6)
                input_lng = round(float(row["input_lng"]), 6)

                result_map[(input_lat, input_lng)] = {
                    "address": safe_json_value(row["address_data"]),
                    "road_address": safe_json_value(row["road_address_data"])
                }

            logger.info(
                f"📦 [DB 배치 공간 조회 완료] "
                f"요청좌표={len(normalized_coords)}건, "
                f"캐시히트={len(result_map)}건, "
                f"반경={ADDRESS_CACHE_RADIUS_METER}m"
            )

            return result_map

    except Exception as e:
        logger.error(f"❌ PostgreSQL 공간 배치 조회 오류: {e}")
        return {}

    finally:
        if conn:
            try:
                # SELECT 후 열린 트랜잭션 정리
                conn.rollback()
            except Exception:
                pass

            pool.putconn(conn)


# ====================================================
# 9. 주소 캐시 저장
# ====================================================
def save_to_postgres(lat, lng, kakao_doc):
    """
    새로운 주소 데이터와 공간 좌표 POINT 저장.

    현재 구조:
    - 좌표를 unique하게 강제하지 않는다.
    - 대신 조회할 때 ST_DWithin 반경으로 가까운 캐시를 찾는다.
    - 미세하게 다른 좌표가 들어와도 15m 안이면 같은 주소로 판단 가능하다.

    참고:
    - 너무 많은 중복 저장이 걱정되면 나중에 저장 전에 한번 더 단건 조회하거나,
      별도 중복 정리 job을 만들 수 있다.
    """
    norm_lat, norm_lng = normalize_coord(lat, lng)

    if norm_lat is None or norm_lng is None:
        logger.warning(f"⚠️ [DB 저장 스킵] 유효하지 않은 좌표: lat={lat}, lng={lng}")
        return

    pool = get_pool()
    conn = None

    try:
        conn = pool.getconn()

        with conn.cursor() as cur:
            sql = """
                  INSERT INTO address_cache (
                      geom,
                      address_data,
                      road_address_data
                  )
                  VALUES (
                             ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                             %s,
                             %s
                         ) \
                  """

            # ST_MakePoint는 (경도, 위도) 순서
            cur.execute(
                sql,
                (
                    norm_lng,
                    norm_lat,
                    Json(kakao_doc.get("address") or {}),
                    Json(kakao_doc.get("road_address") or {})
                )
            )

            conn.commit()

            logger.info(f"✅ [DB 저장 완료] lat={norm_lat}, lng={norm_lng}")

    except Exception as e:
        logger.error(
            f"❌ PostgreSQL 공간 저장 오류: "
            f"lat={lat}, lng={lng}, error={e}"
        )

        if conn:
            conn.rollback()

    finally:
        if conn:
            pool.putconn(conn)


# ====================================================
# 10. 커넥션 풀 종료
# ====================================================
def close_pool():
    """
    서버 종료 시 PostgreSQL 커넥션 풀 정리.

    일반적으로 서버 프로세스가 종료되면 OS가 연결을 정리하지만,
    atexit에 등록해두면 정상 종료 시 closeall()을 호출해서 더 깔끔하다.
    """
    global _pool

    if _pool:
        try:
            _pool.closeall()
            logger.info("✅ PostgreSQL Connection Pool 종료 완료")
        except Exception as e:
            logger.error(f"❌ PostgreSQL Connection Pool 종료 실패: {e}")
        finally:
            _pool = None


# Python 프로세스가 정상 종료될 때 close_pool() 자동 실행
atexit.register(close_pool)