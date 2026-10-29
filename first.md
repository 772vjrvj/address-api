이번 문제는 서비스는 중지돼 있는데 별도 caddy.exe 프로세스가 2019 포트를 잡고 있던 것 때문입니다.

다음에 똑같이 안 올라오면 이 순서만 기억하시면 됩니다:

Get-NetTCPConnection -LocalPort 2019 -State Listen -ErrorAction SilentlyContinue

프로세스가 있으면:

$connection = Get-NetTCPConnection -LocalPort 2019 -State Listen
Stop-Process -Id $connection.OwningProcess -Force
Start-Service caddy

그리고 확인:

Get-Service caddy


1. Caddy 실행 및 확인

Start-Service caddy
Get-Service caddy


Status   Name    DisplayName
------   ----    -----------
Running  caddy   caddy


netstat -ano | findstr :5001

curl.exe http://127.0.0.1:5001/ping



2. PM2 address-api-blue 실행
cd E:\git\address-api

현재 PM2 상태 확인:
pm2 list

PM2에 이미 등록되어 있는 경우
pm2 start address-api-blue

PM2에 등록되어 있지 않은 경우
pm2 start ecosystem.config.js --only address-api-blue

실행 상태 확인:
pm2 list

3. 서버 연결 확인
curl.exe http://127.0.0.1:5101/ping
curl.exe http://127.0.0.1:5001/ping


5101 → address-api-blue 직접 접속
5001 → Caddy → address-api-blue 접속

4. 로그 계속 보기
pm2 logs address-api-blue

   
로그 보기를 종료할 때는:
Ctrl + C




1. Caddy 종료
Stop-Service caddy

종료 확인:
Get-Service caddy

Status   Name
------   ----
Stopped  caddy

Start-Service caddy

2. PM2 서버 종료

stop은 프로세스 등록은 유지하면서 서버만 중지합니다. 나중에 다시 실행할 때는 다음 명령만 쓰면 됩니다.
pm2 stop address-api-blue

pm2 list
address-api-blue    stopped
pm2 start address-api-blue

PM2 목록에서도 완전히 제거하려면
pm2 delete address-api-blue

delete를 하면 다음 실행 시 ecosystem 파일로 다시 등록해야 합니다.

cd E:\git\address-api
pm2 start ecosystem.config.js --only address-api-blue



3. PM2 로그 계속 보기
pm2 logs address-api-blue

최근 100줄부터 보여주고 이후 로그도 계속 표시:
pm2 logs address-api-blue --lines 100

로그 화면만 종료:
Ctrl + C


4. PowerShell의 Tail 방식으로 로그 계속 보기

Blue 서버 로그가 server_5101.log라면:

Get-Content E:\git\address-api\logs\server_5101.log -Wait -Tail 100 -Encoding UTF8

Green 서버 로그가 server_5102.log라면:

Get-Content E:\git\address-api\logs\server_5102.log -Wait -Tail 100 -Encoding UTF8

옵션 의미:

-Tail 100      마지막 100줄부터 표시
-Wait          새 로그가 생기면 계속 표시
-Encoding UTF8 한글 깨짐 방지

종료는 동일하게:

Ctrl + C