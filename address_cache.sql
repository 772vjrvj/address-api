-- 1. PostGIS 확장 기능 활성화 (이미 되어있을 수도 있지만 안전하게 실행)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. 기존 테이블 삭제 후 공간 정보용 테이블로 재생성
DROP TABLE IF EXISTS address_cache CASCADE;

CREATE TABLE address_cache (
                               id SERIAL PRIMARY KEY,
    -- 공간 데이터 타입인 POINT (위경도 좌표 점)
                               geom GEOMETRY(Point, 4326),
                               address_data JSONB,
                               road_address_data JSONB,
                               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 공간 인덱스(GIST) 생성 (폴리곤 및 반경 조회 속도를 기하급수적으로 올림)
CREATE INDEX idx_address_cache_geom ON address_cache USING gist (geom);
