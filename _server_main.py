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


def _try_extract_project_name(pdf_path):
    """PDF 첫 페이지 표/텍스트에서 조사명·공사명·용역명·과업명을 직접 추출.
    찾지 못하면 None 반환."""
    import re
    _KW = {'조사명', '공사명', '용역명', '과업명'}
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if not len(doc):
            doc.close()
            return None
        page = doc[0]

        # ── 방법 1: 표 셀 레이블-값 쌍 탐색 ─────────────────────────────────
        try:
            tables = page.find_tables()
            for tbl in tables.tables:
                for row in tbl.extract():
                    for j, cell in enumerate(row):
                        text = str(cell).strip() if cell else ""
                        if text in _KW and j + 1 < len(row):
                            val = str(row[j + 1]).strip() if row[j + 1] else ""
                            if val and val not in _KW and len(val) >= 2:
                                doc.close()
                                return val
        except Exception:
            pass

        # ── 방법 2: 텍스트 라인 탐색 (같은 줄 / 다음 줄) ─────────────────────
        lines = [l.strip() for l in page.get_text("text").split('\n') if l.strip()]
        for k, line in enumerate(lines):
            # 같은 줄: "조사명 : 수원시팔달구지반조사"
            m = re.search(r'(?:조사명|공사명|용역명|과업명)\s*[:：]?\s*(.+)', line)
            if m:
                val = m.group(1).strip()
                if val and val not in _KW and len(val) >= 2:
                    doc.close()
                    return val
            # 다음 줄: 레이블 단독 → 바로 아랫줄이 값
            if line in _KW and k + 1 < len(lines):
                val = lines[k + 1]
                if val and val not in _KW and len(val) >= 2 \
                        and not re.match(r'^[\d\s\-\.\(\)]+$', val):
                    doc.close()
                    return val

        doc.close()
    except Exception:
        pass
    return None


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
    column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', 'meta_crs', '표고',
                    '시추공명', '상심도', '하심도', '지층명']

    for i, pdf_path in enumerate(pdf_files, 1):
        basename = os.path.basename(pdf_path)

        # ── 경로/파일 정보 계산 ─────────────────────────────────────────────────
        rel = os.path.relpath(pdf_path, BASE_DIR)
        parts = rel.split(os.sep)
        file_stem = os.path.splitext(parts[-1])[0]
        # process_file 에 전달할 초기 레이블 (폴더+파일명) — 조사명 탐지 기준값으로만 사용
        project_label = f"{parts[0]}_{file_stem}" if len(parts) > 1 else file_stem

        print(f"  [{i}/{len(pdf_files)}] 처리 중: {rel}", flush=True)
        try:
            merged = extractor.process_file(pdf_path, project_label)

            if merged:
                # ── 프로젝트명 결정 (우선순위 순) ───────────────────────────
                # 1순위: 파이프라인(HWPX Tier1 / Tier2)이 추출한 조사명
                extracted_pname = merged[0].get("프로젝트명", "")
                if extracted_pname and extracted_pname not in ("N/A", "", project_label):
                    final_label = extracted_pname
                else:
                    # 2순위: PDF 표/텍스트 직접 스캔으로 조사명 추출
                    scanned = _try_extract_project_name(pdf_path)
                    final_label = scanned if scanned else file_stem  # 3순위: 파일명

                for row in merged:
                    row["프로젝트명"] = final_label

                all_rows.extend(merged)
                print(f"       완료: {len(merged)}행 추출  →  프로젝트명: {final_label}",
                      flush=True)
            else:
                print(f"       [경고] 데이터를 추출하지 못했습니다: {basename}",
                      flush=True)
                failed_list.append({
                    "프로젝트명": file_stem,
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
                "crs": row.get("meta_crs", ""),
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
