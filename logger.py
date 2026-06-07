import logging
from logging.handlers import TimedRotatingFileHandler
import os

def get_logger():
    """
    서버의 실시간 로그를 터미널과 파일에 동시에 기록하고 관리하는 로거를 생성합니다.
    매일 자정에 로그 파일을 분리하며, 최신 10일치 파일만 자동으로 유지합니다.
    """

    # 1. 로그를 저장할 폴더가 없으면 안전하게 자동 생성
    # (이미 폴더가 존재한다면 에러 없이 넘어감)
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. 고유한 이름('AddressAPI')을 가진 로거 객체 생성 및 레벨 설정
    logger = logging.getLogger('AddressAPI')

    # 중복 세팅 방지: 로거에 이미 핸들러가 등록되어 있다면 기존 로거를 그대로 반환
    # (Flask 앱 리로드 시 로그가 중복 출력되는 현상을 방지함)
    if len(logger.handlers) > 0:
        return logger

    # INFO 레벨 이상의 로그(INFO, WARNING, ERROR, CRITICAL)만 기록함
    logger.setLevel(logging.INFO)

    # 3. 로그 출력 포맷 설정 (시간, 로그레벨, 메시지 내용을 직관적으로 표기)
    # 출력 예시: [2026-06-07 14:15:30] INFO - 요청 수신 - 위도: 37.123, 경도: 127.123
    log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

    # =================================================================
    # [핸들러 1] 터미널(콘솔) 실시간 출력 핸들러
    # =================================================================
    # 모니터링 창을 띄워두었을 때 관리자가 즉각적으로 현황을 파악할 수 있도록 돕습니다.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    # =================================================================
    # [핸들러 2] 파일 자동 로테이션 저장 핸들러 (핵심 기능)
    # =================================================================
    # - filename: 실시간으로 로그를 기록할 기본 파일명입니다.
    # - when='midnight': 매일 밤 12시(자정)를 기준으로 파일을 분리합니다.
    # - interval=1: 1일 주기로 로테이션을 수행합니다.
    # - backupCount=10: 과거 로그 파일을 최대 10개만 보관하고, 초과 시 가장 오래된 파일을 자동 삭제합니다.
    # - encoding='utf-8': 삼성 노트북(윈도우 환경)에서 한글 메시지가 깨지지 않도록 절대적인 인코딩을 보장합니다.
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'server.log'),
        when='midnight',
        interval=1,
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    return logger