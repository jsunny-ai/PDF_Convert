"""GeoBIM Borehole System — EXE 빌더.

실행: python build_exe.py
출력: dist/GeoBIM_Borehole/ (폴더 전체가 배포 단위)
"""
import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_NAME = 'GeoBIM_Borehole'
ENTRY = os.path.join(ROOT, '_server_main.py')

# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def run(cmd, **kw):
    print('  $', ' '.join(cmd) if isinstance(cmd, list) else cmd)
    subprocess.check_call(cmd, **kw)


def step(n, msg):
    print(f'\n[{n}] {msg}')

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: PyInstaller 설치
# ─────────────────────────────────────────────────────────────────────────────
step(1, 'PyInstaller 확인 및 설치')
try:
    import PyInstaller  # noqa: F401
    print('  PyInstaller 이미 설치됨.')
except ImportError:
    run([sys.executable, '-m', 'pip', 'install', 'pyinstaller', '--quiet'])

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: 데이터 파일 경로 수집
# ─────────────────────────────────────────────────────────────────────────────
step(2, '번들 경로 수집')

import pyproj
import opendataloader_pdf

proj_data_src = os.path.join(os.path.dirname(pyproj.__file__),
                             'proj_dir', 'share', 'proj')
odl_jar_src   = os.path.join(os.path.dirname(opendataloader_pdf.__file__), 'jar')

print(f'  PROJ 데이터: {proj_data_src}')
print(f'  ODL JAR   : {odl_jar_src}')

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: PyInstaller 실행
# ─────────────────────────────────────────────────────────────────────────────
step(3, 'PyInstaller 빌드')

# --add-data 구분자는 Windows ':', Linux ';'
SEP = ';'

pyinstaller_args = [
    sys.executable, '-m', 'PyInstaller',
    '--noconfirm',
    '--onedir',
    '--name', DIST_NAME,
    '--distpath', os.path.join(ROOT, 'dist'),
    '--workpath', os.path.join(ROOT, '_build_work'),
    '--specpath', ROOT,
    '--console',                           # 콘솔 창 표시 (에러 확인용)

    # 번들 데이터 ─────────────────────────────────────────────────────────────
    '--add-data', f'{os.path.join(ROOT, "web")}{SEP}web',
    '--add-data', f'{os.path.join(ROOT, "config")}{SEP}config',
    '--add-data', f'{proj_data_src}{SEP}proj_data',
    '--add-data', f'{odl_jar_src}{SEP}opendataloader_pdf/jar',

    # 숨겨진 임포트 ───────────────────────────────────────────────────────────
    '--hidden-import', 'flask',
    '--hidden-import', 'flask.json.provider',
    '--hidden-import', 'werkzeug',
    '--hidden-import', 'werkzeug.serving',
    '--hidden-import', 'jinja2',
    '--hidden-import', 'jinja2.ext',
    '--hidden-import', 'pandas',
    '--hidden-import', 'pandas._libs.tslibs.base',
    '--hidden-import', 'pyproj',
    '--hidden-import', 'pyproj.transformer',
    '--hidden-import', 'fitz',          # PyMuPDF
    '--hidden-import', 'pyhwpx',
    '--hidden-import', 'opendataloader_pdf',
    '--hidden-import', 'core',
    '--hidden-import', 'core.master_hybrid_extractor',
    '--hidden-import', 'core.table_merger',
    '--hidden-import', 'core.coordinate_transformer',
    '--hidden-import', 'core.spatial_validator',
    '--hidden-import', 'core.sentinel_daemon',
    '--hidden-import', 'parsers',
    '--hidden-import', 'parsers.pdf_parser_odl',
    '--hidden-import', 'parsers.hwp_indexed_extractor',
    '--hidden-import', 'parsers.hwpx_converter',

    # 제외 ────────────────────────────────────────────────────────────────────
    '--exclude-module', 'tkinter',
    '--exclude-module', 'unittest',
    '--exclude-module', 'test',

    ENTRY,
]

run(pyinstaller_args)

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: 후처리 — 배포 폴더 완성
# ─────────────────────────────────────────────────────────────────────────────
step(4, '배포 폴더 후처리')

dist_dir = os.path.join(ROOT, 'dist', DIST_NAME)

# 4-A. JDK 폴더 복사 (있으면)
jdk_src = os.path.join(ROOT, 'jdk_folder')
jdk_dst = os.path.join(dist_dir, 'jdk_folder')
if os.path.isdir(jdk_src) and not os.path.isdir(jdk_dst):
    print('  JDK 폴더 복사 중...')
    shutil.copytree(jdk_src, jdk_dst)
    print(f'  JDK 복사 완료: {jdk_dst}')
elif not os.path.isdir(jdk_src):
    print('  [경고] jdk_folder 없음 - PDF->Markdown 변환(ODL)은 JDK 21 필요')

# 4-B. 런처 BAT 생성
launcher_src = os.path.join(ROOT, 'run_borehole_system.bat')
launcher_dst = os.path.join(dist_dir, 'GeoBIM_시작.bat')
bat_content = f"""\
@echo off
chcp 65001 >nul
title GeoBIM 시추공 데이터 변환 시스템

echo ===================================================
echo     GeoBIM Borehole Data Conversion System
echo ===================================================
echo.

cd /d "%~dp0"

:: JDK 환경 변수 (jdk_folder 하위 bin)
if exist "%~dp0jdk_folder\\bin\\java.exe" (
    set JAVA_HOME=%~dp0jdk_folder
    set PATH=%~dp0jdk_folder\\bin;%PATH%
    echo [OK] JDK 감지: %~dp0jdk_folder
) else (
    echo [경고] jdk_folder 없음 - ODL 기반 PDF 변환 불가
)

echo [시작] GeoBIM 서버를 실행합니다...
echo [안내] 브라우저에서 http://127.0.0.1:5000 으로 자동 접속됩니다.
echo.
start "" "{DIST_NAME}.exe"
"""
with open(launcher_dst, 'w', encoding='cp949') as f:
    f.write(bat_content)
print(f'  런처 생성: {launcher_dst}')

# 4-C. data 폴더 생성 (업로드 저장소)
data_dir = os.path.join(dist_dir, 'data', '00_source', 'temp_uploads')
os.makedirs(data_dir, exist_ok=True)
print(f'  data 폴더 생성: {data_dir}')

# ─────────────────────────────────────────────────────────────────────────────
# 최종 보고
# ─────────────────────────────────────────────────────────────────────────────
total_mb = sum(
    os.path.getsize(os.path.join(r, f))
    for r, _, fs in os.walk(dist_dir)
    for f in fs
) / 1024 / 1024

print(f"""
===================================================
  빌드 완료
===================================================
  출력 폴더 : {dist_dir}
  용량       : {total_mb:.1f} MB
  실행 파일  : {os.path.join(dist_dir, DIST_NAME + '.exe')}
  런처       : {launcher_dst}

  배포 방법:
    dist/{DIST_NAME}/ 폴더 전체를 사용자 PC에 복사
    → GeoBIM_시작.bat 실행 (또는 {DIST_NAME}.exe 직접 실행)

  [주의] HWP 파싱은 한컴오피스가 설치된 PC에서만 동작합니다.
""")
