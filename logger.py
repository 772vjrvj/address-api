# logger.py
import logging
from logging.handlers import TimedRotatingFileHandler
import os


def get_logger():
    """
    주소 변환 API 서버 공통 로거 생성 함수.

    기능:
    1. 터미널과 파일에 동시에 로그 출력
    2. 매일 자정마다 로그 파일 자동 분리
    3. 최근 10일치 로그만 보관
    4. Flask / Waitress 환경에서 중복 핸들러 등록 방지
    5. 윈도우 환경 한글 로그 깨짐 방지
    6. blue / green 서버 동시 실행 시 로그 파일 충돌 방지
       - 5101 서버: logs/server_5101.log
       - 5102 서버: logs/server_5102.log
    """

    # ====================================================
    # 1. 로거 객체 생성
    # ====================================================
    logger = logging.getLogger("AddressAPI")

    # 이미 핸들러가 등록되어 있으면 그대로 반환
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # ====================================================
    # 2. 로그 폴더 생성
    # ====================================================
    basedir = os.path.abspath(os.path.dirname(__file__))
    log_dir = os.path.join(basedir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # ====================================================
    # 3. 로그 파일명 결정
    # ====================================================
    # PM2 ecosystem.config.js 에서 SERVER_PORT=5101 / 5102 로 들어온다.
    # 포트별로 로그 파일을 분리해야 blue / green 동시 실행 시
    # Windows 파일 잠금 충돌이 발생하지 않는다.
    server_port = os.getenv("SERVER_PORT", "unknown").strip() or "unknown"

    # 혹시 모를 이상 문자를 제거해서 파일명 안전하게 처리
    safe_server_port = "".join(
        ch for ch in server_port
        if ch.isalnum() or ch in ("_", "-")
    )

    log_file_name = f"server_{safe_server_port}.log"
    log_file_path = os.path.join(log_dir, log_file_name)

    # ====================================================
    # 4. 로그 포맷
    # ====================================================
    log_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # ====================================================
    # 5. 콘솔 로그 핸들러
    # ====================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    # ====================================================
    # 6. 파일 로그 핸들러
    # ====================================================
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when="midnight",
        interval=1,
        backupCount=10,
        encoding="utf-8",
        delay=True
    )

    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    logger.info(f"로그 파일 사용: {log_file_path}")

    return logger