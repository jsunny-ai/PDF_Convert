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

# ─── PDF 자동 감지 및 처리 ────────────────────────────────────────────────────
_SKIP_DIRS = {'_internal', 'jdk_folder', 'data', '결과물', '__pycache__'}


def _find_pdf_files(search_dir):
    """search_dir 및 모든 하위 폴더에서 PDF 파일 경로 목록 반환."""
    found = []
    for root, dirs, files in os.walk(search_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname.lower().endswith('.pdf'):
                found.append(os.path.join(root, fname))
    return found


def _auto_process(pdf_files):
    """발견된 PDF를 MasterHybridExtractor로 일괄 처리하고 결과물/ 에 저장.

    출력: 결과물/통합_결과.csv  +  결과물/통합_결과.json  (파일 2개)
    프로젝트명: {상위폴더명}_{파일명}  (예: PJT1_보고서A)
               상위폴더 없으면 파일명만 사용
    """
    import json
    import pandas as pd
    import subprocess
    from core.master_hybrid_extractor import MasterHybridExtractor
    from parsers.pdf_parser_odl import natural_sort_key

    results_dir = os.path.join(BASE_DIR, '결과물')
    os.makedirs(results_dir, exist_ok=True)

    extractor = MasterHybridExtractor(output_dir=BASE_DIR)
    all_rows = []
    failed_list = []   # 추출 실패/누락 목록 {프로젝트명, 파일경로, 실패사유}
    column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고',
                    '시추공명', '상심도', '하심도', '지층명']

    for i, pdf_path in enumerate(pdf_files, 1):
        basename = os.path.basename(pdf_path)

        # ── 프로젝트명 = {상위폴더명}_{파일명} ──────────────────────────────────
        rel = os.path.relpath(pdf_path, BASE_DIR)
        parts = rel.split(os.sep)
        file_stem = os.path.splitext(parts[-1])[0]
        project_label = f"{parts[0]}_{file_stem}" if len(parts) > 1 else file_stem

        print(f"  [{i}/{len(pdf_files)}] 처리 중: {rel}  →  프로젝트명: {project_label}",
              flush=True)
        try:
            merged = extractor.process_file(pdf_path, project_label)

            if merged:
                # 모든 행의 프로젝트명을 폴더 기반 이름으로 강제 덮어쓰기
                for row in merged:
                    row["프로젝트명"] = project_label

                all_rows.extend(merged)
                print(f"       완료: {len(merged)}행 추출", flush=True)
            else:
                print(f"       [경고] 데이터를 추출하지 못했습니다: {basename}",
                      flush=True)
                failed_list.append({
                    "프로젝트명": project_label,
                    "파일경로": rel,
                    "실패사유": "데이터 추출 실패 (빈 결과)"
                })

        except Exception as exc:
            print(f"       [오류] {basename}: {exc}", flush=True)
            failed_list.append({
                "프로젝트명": project_label,
                "파일경로": rel,
                "실패사유": str(exc)
            })

    # ── 누락 목록 저장 (실패 건이 있을 때만) ─────────────────────────────────
    if failed_list:
        failed_df = pd.DataFrame(failed_list, columns=['프로젝트명', '파일경로', '실패사유'])
        failed_df.to_csv(
            os.path.join(results_dir, '누락_목록.csv'),
            index=False, encoding='utf-8-sig'
        )
        print(f"\n  [누락] {len(failed_list)}건 추출 실패 → 누락_목록.csv 저장됨",
              flush=True)

    if not all_rows:
        print("\n  [경고] 추출된 데이터가 없습니다.", flush=True)
        print("\n  처리가 완료되었습니다. Enter 를 누르면 종료됩니다.")
        input()
        return

    # ── 자연 정렬: 프로젝트명(숫자 포함) → 시추공명 순 ────────────────────────
    all_rows.sort(key=lambda r: (
        natural_sort_key(r.get("프로젝트명", "")),
        natural_sort_key(r.get("시추공명", ""))
    ))

    # ── 통합 CSV 저장 ──────────────────────────────────────────────────────────
    combined_df = pd.DataFrame(all_rows)
    for col in column_order:
        if col not in combined_df.columns:
            combined_df[col] = ''
    combined_df[column_order].to_csv(
        os.path.join(results_dir, '통합_결과.csv'),
        index=False, encoding='utf-8-sig'
    )
    print(f"\n  통합 CSV 저장 완료: 통합_결과.csv ({len(all_rows)}행)", flush=True)

    # ── 통합 JSON 저장 (프로젝트별 boreholes 구조) ────────────────────────────
    projects_dict: dict = {}
    for row in all_rows:
        pname = row.get("프로젝트명", "UNKNOWN")
        if pname not in projects_dict:
            projects_dict[pname] = {"project_name": pname, "boreholes": {}}
        b_id = row.get("시추공명", "UNKNOWN")
        if b_id not in projects_dict[pname]["boreholes"]:
            projects_dict[pname]["boreholes"][b_id] = {
                "borehole_id": b_id,
                "longitude": row.get("lon_wgs84", ""),
                "latitude": row.get("lat_wgs84", ""),
                "elevation": row.get("표고", ""),
                "strata": []
            }
        projects_dict[pname]["boreholes"][b_id]["strata"].append({
            "soil_type": row.get("지층명", ""),
            "depth_top": row.get("상심도", ""),
            "depth_bottom": row.get("하심도", "")
        })

    json_output = {
        "projects": [
            {**v, "boreholes": list(v["boreholes"].values())}
            for v in projects_dict.values()
        ]
    }
    with open(os.path.join(results_dir, '통합_결과.json'), 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"  통합 JSON 저장 완료: 통합_결과.json ({len(projects_dict)}개 프로젝트)",
          flush=True)

    # ── 결과물 폴더 탐색기로 열기 ─────────────────────────────────────────────
    try:
        subprocess.Popen(['explorer', results_dir])
    except Exception:
        pass

    print(f"\n{'='*50}")
    print(f"  결과물 저장 위치: {results_dir}")
    print(f"{'='*50}")
    print("\n  처리가 완료되었습니다. Enter 를 누르면 종료됩니다.")
    input()


# ─── 실행 분기 ────────────────────────────────────────────────────────────────
print('\n[GeoBIM] 시추공 데이터 변환 시스템 시작 중...')
print(f'[GeoBIM] 실행 폴더: {BASE_DIR}\n')

pdf_files = _find_pdf_files(BASE_DIR)

if pdf_files:
    # ── 자동 처리 모드 ─────────────────────────────────────────────────────────
    print(f'[GeoBIM] PDF {len(pdf_files)}개 발견 → 자동 처리 모드')
    for p in pdf_files:
        print(f'         · {os.path.relpath(p, BASE_DIR)}')
    print()
    _auto_process(pdf_files)

else:
    # ── 웹 서버 모드 (기존 동작) ───────────────────────────────────────────────
    print('[GeoBIM] PDF 없음 → 웹 서버 모드로 시작합니다.')

    import server  # noqa: E402

    server.app.static_folder = os.path.join(BUNDLE_DIR, 'web')

    upload_dir = os.path.join(BASE_DIR, 'data', '00_source', 'temp_uploads')
    os.makedirs(upload_dir, exist_ok=True)
    server.app.config['UPLOAD_FOLDER'] = upload_dir

    import threading
    import webbrowser

    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5000')

    threading.Thread(target=_open_browser, daemon=True).start()

    print('\n[GeoBIM] 시추공 데이터 변환 서버 시작')
    print('[GeoBIM] 브라우저: http://127.0.0.1:5000')
    print('[GeoBIM] 종료하려면 이 창을 닫으세요.\n')

    server.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
