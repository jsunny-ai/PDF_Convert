@echo off
chcp 65001 >nul
echo ===================================================
echo     GeoBIM Borehole System Initialization
echo ===================================================

:: 1. 프로젝트 루트 경로로 이동
cd /d "C:\antigravity\#1_2_PDF_CSV"
echo [Info] Moved to directory: C:\antigravity\#1_2_PDF_CSV

:: 2. 보조 데몬(Sentinel Daemon) 백그라운드 실행
::    (루트 폴더에 있는 sentinel_daemon.py를 함께 실행함)
echo [Info] Starting Sentinel Daemon...
start "FileName Sentinel Daemon" cmd /k "python core\sentinel_daemon.py"

:: 3. 메인 서버(server.py) 실행
echo [Info] Starting GeoBIM Borehole Server...
start "GeoBIM Borehole Server" cmd /k "python server.py"

:: 4. 서버 로딩을 위한 대기 (5초)
echo [Info] Waiting for the server to spin up (5 seconds)...
timeout /t 5

:: 5. 브라우저로 로컬 대시보드 자동 실행
echo [Info] Opening Browser at http://127.0.0.1:5000...
start http://127.0.0.1:5000

echo ===================================================
echo     All systems are running. You may close this.
echo ===================================================
exit
