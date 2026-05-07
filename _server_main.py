"""EXE 엔트리포인트 — PyInstaller 번들 실행 시 server.py 대신 이 파일이 호출됩니다.

개발 환경에서 직접 실행하지 말 것. EXE 빌드 전용.
"""
import sys
import os

# ─── 경로 결정 ────────────────────────────────────────────────────────────────
# BUNDLE_DIR : 번들 내 리소스(web/, config/, pyproj data, JAR) 위치
# BASE_DIR   : 실행 파일(.exe) 이 있는 폴더 — 쓰기 가능 데이터 저장소
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = BUNDLE_DIR

os.chdir(BASE_DIR)
sys.path.insert(0, BUNDLE_DIR)

# ─── PROJ 데이터 경로 (pyproj) ────────────────────────────────────────────────
os.environ['PROJ_DATA'] = os.path.join(BUNDLE_DIR, 'proj_data')

# ─── Java / JDK 경로 (opendataloader ODL JAR 실행용) ──────────────────────────
jdk_path = os.path.join(BASE_DIR, 'jdk_folder')
if os.path.isdir(jdk_path):
    os.environ['JAVA_HOME'] = jdk_path
    os.environ['PATH'] = (os.path.join(jdk_path, 'bin')
                          + os.pathsep + os.environ.get('PATH', ''))

# ─── Flask 앱 import (이 시점에 server.py의 모듈 레벨 코드가 실행됨) ──────────
import server  # noqa: E402

# ─── Flask 경로 패치 (frozen 환경에서 올바른 경로로 덮어쓰기) ─────────────────
server.app.static_folder = os.path.join(BUNDLE_DIR, 'web')

upload_dir = os.path.join(BASE_DIR, 'data', '00_source', 'temp_uploads')
os.makedirs(upload_dir, exist_ok=True)
server.app.config['UPLOAD_FOLDER'] = upload_dir

# ─── 브라우저 자동 실행 ───────────────────────────────────────────────────────
import threading
import webbrowser

def _open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

threading.Thread(target=_open_browser, daemon=True).start()

# ─── 서버 기동 ────────────────────────────────────────────────────────────────
print('\n[GeoBIM] 시추공 데이터 변환 서버 시작')
print('[GeoBIM] 브라우저: http://127.0.0.1:5000')
print('[GeoBIM] 종료하려면 이 창을 닫으세요.\n')

server.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
