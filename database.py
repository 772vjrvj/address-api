import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv
from logger import get_logger

logger = get_logger()

# 절대 경로로 .env 로드 (BOM 유령 문자 방지 포함)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), override=True, encoding='utf-8-sig')

# 환경변수에서 설정값 읽기
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

_pool = None

def get_pool():
    """서버가 살아있는 동안 유지될 커넥션 풀 반환"""
    global _pool
    if _pool is None:
        try:
            # 최소 1개, 최대 10개의 고정 연결을 유지하는 풀 생성
            _pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            logger.info("✅ PostgreSQL Connection Pool 초기화 완료")
        except Exception as e:
            logger.error(f"❌ PostgreSQL Connection Pool 생성 실패: {e}")
            raise e
    return _pool

def get_address_from_postgres(lat, lng):
    """
    [폴리곤/공간 연산 방식]
    입력된 위경도 좌표 기준, 반경 약 15미터 이내에 기존에 저장된 주소가 있다면
    동일한 건물/영역으로 판단하여 캐시 주소를 반환합니다.
    """
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ST_DWithin(geom1, geom2, 거리_미터) -> 4326(위경도 좌표계)을
            # geography 타입으로 캐스팅하면 실제 '미터(m)' 단위로 오차 범위를 제어할 수 있음
            sql = """
                  SELECT address_data, road_address_data
                  FROM address_cache
                  WHERE ST_DWithin(
                                geom,
                                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                                15
                        )
                  ORDER BY updated_at DESC
                  LIMIT 1 \
                  """
            # ST_MakePoint에는 (경도, 위도) 순서로 넣어야 정석!
            cur.execute(sql, (lng, lat))
            row = cur.fetchone()
            if row:
                return {"address": row['address_data'], "road_address": row['road_address_data']}
    except Exception as e:
        logger.error(f"PostgreSQL 공간 조회 오류: {e}")
    finally:
        if conn:
            pool.putconn(conn)
    return None

def save_to_postgres(lat, lng, kakao_doc):
    """새로운 주소 데이터와 공간 좌표(POINT) 저장"""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            # 점 방식과 달리 공간 데이터는 좌표가 미세하게 다르면 계속 쌓이므로
            # 일반 INSERT로 공간 데이터를 축적합니다. (어차피 위에서 반경으로 걸러내므로 무한 증식 안 됨)
            sql = """
                  INSERT INTO address_cache (geom, address_data, road_address_data)
                  VALUES (ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s) \
                  """
            cur.execute(sql, (lng, lat, Json(kakao_doc.get('address')), Json(kakao_doc.get('road_address'))))
            conn.commit()
    except Exception as e:
        logger.error(f"PostgreSQL 공간 저장 오류: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            pool.putconn(conn)