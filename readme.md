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



# 2026-06-20

블루그린 배포 Caddy 프록시 서버

   1. 설명
      
      로드밸런싱 = 여러 서버/프로세스에 요청을 나눠주는 것
      무중단 배포 = 고객 요청을 최대한 끊지 않고 새 버전으로 교체하는 것
      블루그린 배포 = 구버전/신버전을 둘 다 띄운 뒤 한 번에 전환하는 것
      롤링 배포 = 서버를 하나씩 교체하는 것
      
      블루그린 배포
      
      cd E:\git\address-api
      pm2 start ecosystem.config.js --only address-api-blue
      
      pm2 list
      pm2 logs address-api-blue
      
      curl http://127.0.0.1:5101/ping


   2. Caddy 다운로드
      Caddy 다운로드
      https://caddyserver.com/download

      Platform → Windows amd64
      Standard features → 그대로
      Extra features → 0 그대로
      Download 클릭


서버 중지 후 삭제
pm2 stop address-api
pm2 delete address-api


그 다음 5001 비었는지 확인:
netstat -ano | findstr :5001

blue 서버 5101 실행
pm2 start ecosystem.config.js --only address-api-blue

로그확인
pm2 logs address-api-blue

파워쉘 확인
curl http://127.0.0.1:5101/ping




caddyfile 생성
.\make_caddyfile.bat

caddy 실행
.\start_caddy.bat

1. make_caddyfile.bat 실행
   → C:\caddy\Caddyfile 생성

2. start_caddy.bat 실행
   → Caddy 5001 실행

** caddy 안되면 v3에 caddy.exe 검사 예외 설정 추가





1. Caddy 백그라운드 실행
C:\caddy\caddy.exe start --config C:\caddy\Caddyfile --adapter caddyfile

netstat -ano | findstr :5001
curl http://127.0.0.1:5001/ping


2. Caddy 중지
C:\caddy\caddy.exe stop


3. Caddy 설정 변경 후 재적용
나중에 5101 → 5102로 바꿀 때는:
C:\caddy\caddy.exe reload --config C:\caddy\Caddyfile --adapter caddyfile


start_caddy_background.bat = CMD 창 닫아도 Caddy 유지
stop_caddy.bat = Caddy 중지
reload_caddy.bat = Caddyfile 변경 반영

netstat -ano | findstr :5001
netstat -ano | findstr :5101

tasklist /FI "PID eq 44496"



외부 사용자
↓
공인IP:5001
↓
공유기 포트포워딩
↓
내 PC 172.30.1.8:5001
↓
Caddy PID 44496
↓
127.0.0.1:5101
↓
PM2 address-api-blue




최종 구조
고객 프로그램
↓
공인IP:5001
↓
Caddy :5001
↓
blue  127.0.0.1:5101
또는
green 127.0.0.1:5102



1. blue 서버 실행
   powershell 관리자로 실행
   cd E:\git\address-api
   pm2 start ecosystem.config.js --only address-api-blue

확인:

curl http://127.0.0.1:5101/ping



2. Caddyfile이 blue를 보게 설정

C:\caddy\Caddyfile

:5001 {
reverse_proxy 127.0.0.1:5101
}



3. Caddy 백그라운드 실행

처음 실행은 reload가 아니라 start야.

C:\caddy\caddy.exe start --config C:\caddy\Caddyfile --adapter caddyfile

확인:

curl http://127.0.0.1:5001/ping

성공하면:

5001 → Caddy → 5101 blue




새 버전 배포할 때 순서
1. green 서버 실행
   cd E:\git\address-api
   pm2 start ecosystem.config.js --only address-api-green

확인:

curl http://127.0.0.1:5102/ping


2. Caddyfile을 green으로 변경

C:\caddy\Caddyfile

:5001 {
reverse_proxy 127.0.0.1:5102
}




3. Caddy reload

이때는 이미 Caddy가 떠 있으니까 reload가 맞아.

C:\caddy\caddy.exe reload --config C:\caddy\Caddyfile --adapter caddyfile

확인:

curl http://127.0.0.1:5001/ping

이제 구조는:

5001 → Caddy → 5102 green





4. 기존 blue 서버 중지

green이 정상인 걸 확인한 뒤에만 blue를 끄면 돼.

pm2 stop address-api-blue



PM2로 5101/5102 서버를 띄우고, Caddy 5001은 계속 열어둔 채 reverse_proxy 대상만 5101 ↔ 5102로 바꾸는 방식이야.