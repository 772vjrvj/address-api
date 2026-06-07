1. git pull
2. 가상환경 만들기 python -m venv venv
3. 가상환경 세팅 Project Settings
4. 가상환경 활성화 venv\Scripts\activate


GIT BASH

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~
$ cd C:/Users/772vjrvj/Documents/GitHub

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub
$ git clone https://github.com/772vjrvj/address-api.git
Cloning into 'address-api'...
remote: Enumerating objects: 12, done.
remote: Counting objects: 100% (12/12), done.
remote: Compressing objects: 100% (10/10), done.
remote: Total 12 (delta 1), reused 12 (delta 1), pack-reused 0 (from 0)
Unpacking objects: 100% (12/12), done.

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub
$ cd address-api/

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub/address-api (main)
$ python -m venv venv

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub/address-api (main)
$ source venv/Scripts/activate
(venv)

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub/address-api (main)
$ pip install -r requirements.txt


touch .env
notepad .env

MASTER_API_KEY=my_secret_master_key_1234!

python run.py



https://developers.kakao.com/console/app/1479587/product/kakao-map


앱 / 제품 설정 / 카카오맵
사용 설정 상태 ON

실제 서버
http://220.94.196.191:5001/ping


2. 서버를 안정적으로 띄우는 "진짜 실전" 방법 (Waitress + PM2)
   실제 서비스를 할 거라면 Flask 기본 내장 서버(app.run())는 동시 접속 처리에 약해서 절대 쓰면 안 돼. 
3. 윈도우 환경에서 가장 쉽고 강력하게 "백그라운드에서 서버를 24시간 돌리고, 에러 나면 자동 재시작까지 해주는" 
4. 조합은 [Waitress + PM2] 야. (리눅스의 Nginx+Gunicorn 같은 느낌이야.)



(venv) PS E:\git\address-api> npm install -g pm2



# 1. 기존 에러난 프로세스 삭제
pm2 delete address-api

# 2. 환경변수를 추가해서 다시 시작
pm2 start run.py --interpreter "E:\git\address-api\venv\Scripts\python.exe" --name "address-api" --env PYTHONIOENCODING=utf-8


서버 일시 정지 (잠시 쉴 때):
pm2 stop address-api

서버 다시 시작 (코드 수정 후):
pm2 restart address-api

서버 완전히 삭제 (더 이상 안 쓸 때):
pm2 delete address-api


전체 현황 확인:
pm2 list


🛡️ 보너스: 윈도우 재부팅 시 자동 실행 설정
지금은 윈도우를 껐다 켜면 PM2도 같이 꺼질 거야. 컴퓨터를 껐다 켜도 자동으로 address-api가 살아나게 하려면 딱 한 번만 아래 명령어를 입력해 놔.
자동 실행 등록:
pm2 startup

현재 상태 저장:
pm2 save


1. 실시간 모니터링 (가장 많이 씀)
pm2 logs address-api

DOS
# 마지막 100줄만 보기
pm2 logs address-api --lines 100