import os
import logging
import pandas as pd
import uuid
import shutil
import secrets
import string
from urllib.parse import quote
from flask import Flask, request, jsonify, send_from_directory, send_file, make_response
from werkzeug.utils import secure_filename
from parsers import pdf_parser_odl
from parsers.pdf_parser_odl import natural_sort_key
import opendataloader_pdf
from core import table_merger
from core.master_hybrid_extractor import MasterHybridExtractor, get_csv_headers

app = Flask(__name__, static_folder='web', static_url_path='')

UPLOAD_FOLDER = os.path.join(app.root_path, 'data', '00_source', 'temp_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def ensure_unique_project_name(base_name, existing_names):
    """동일한 프로젝트명이 존재할 경우 뒤에 숫자를 붙여 고유성을 보장"""
    name = base_name
    counter = 1
    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1
    return name

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    # 1. 이번 요청을 위한 고유 요청 ID(UUID) 폴더 생성
    request_id = str(uuid.uuid4())
    request_folder = os.path.join(app.config['UPLOAD_FOLDER'], request_id)
    os.makedirs(request_folder, exist_ok=True)
    
    # 개별 CSV들을 모아둘 폴더 (압축용)
    individual_folder = os.path.join(request_folder, 'individual')
    os.makedirs(individual_folder, exist_ok=True)

    uploaded_files = request.files.getlist('pdf_files')
    if not uploaded_files or uploaded_files[0].filename == '':
        uploaded_files = request.files.getlist('pdf_file')
        if not uploaded_files or uploaded_files[0].filename == '':
            return jsonify({"error": "오류: 업로드된 파일을 찾을 수 없습니다."}), 400
    
    results = []
    all_combined_rows = []
    existing_project_names = set() # 이번 요청 내 프로젝트명 중복 방지 [NEW]
    
    for file in uploaded_files:
        if not file or file.filename == '':
            continue
            
        filename = secure_filename(file.filename)
        # 결과 리스트에 미리 추가 (나중에 상태 업데이트) [NEW]
        result_entry = {"status": "pending", "filename": filename}
        results.append(result_entry)
        
        if not (filename.lower().endswith('.pdf') or filename.lower().endswith('.docx') or filename.lower().endswith('.hwpx')):
            result_entry.update({"status": "error", "error": "지원하지 않는 파일 형식입니다."})
            continue

        try:
            # 1. 고유 프로젝트명 및 파일명 생성 [NEW]
            base_filename = os.path.splitext(secure_filename(file.filename))[0]
            project_suffix = request_id[:8]
            project_name = f"{base_filename}_{project_suffix}"
            
            # 실제 저장되는 파일명은 ASCII 고정하여 인코딩 오류 방지 [Stage 45-H]
            file_ext = os.path.splitext(filename)[1].lower()
            unique_filename = f"source_{project_suffix}{file_ext}"
            filepath = os.path.join(request_folder, unique_filename)
            file.save(filepath)
            
            existing_project_names.add(project_name)
            
            # 2. 3-Tier 하이브리드 파이프라인 가동 (HWPX -> PyMuPDF -> ODL)
            extractor = MasterHybridExtractor(output_dir=r"C:\antigravity\#1_2_PDF_CSV")
            merged = extractor.process_file(filepath, project_name)
            
            if merged and len(merged) > 0:
                extracted_name = merged[0].get("프로젝트명", "")
                if extracted_name and extracted_name != "N/A":
                    project_name = extracted_name
                    import re
                    safe_project_name = re.sub(r'[\\/*?:"<>|]', "", project_name)
                    csv_filename = f"{safe_project_name}.csv"
                    json_filename = f"{safe_project_name}.json"
                else:
                    csv_filename = f"converted_{project_suffix}.csv"
                    json_filename = f"converted_{project_suffix}.json"
            else:
                csv_filename = f"converted_{project_suffix}.csv"
                json_filename = f"converted_{project_suffix}.json"
                
            if merged:
                all_combined_rows.extend(merged)
            
                # 4. 개별 CSV 저장
                csv_path = os.path.join(individual_folder, csv_filename)
                df = pd.DataFrame(merged)
                
                # 컬럼 순서 고정
                column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고', '시추공명', '상심도', '하심도', '지층명']
                for col in column_order:
                    if col not in df.columns:
                        df[col] = ''
                df = df[column_order]
                
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')

                # 4.5. 계층형 JSON 생성 및 저장
                json_path = os.path.join(individual_folder, json_filename)
                boreholes_dict = {}
                for row in merged:
                    b_id = row.get("시추공명", "UNKNOWN")
                    if b_id not in boreholes_dict:
                        boreholes_dict[b_id] = {
                            "borehole_id": b_id,
                            "longitude": row.get("lon_wgs84", ""),
                            "latitude": row.get("lat_wgs84", ""),
                            "elevation": row.get("표고", ""),
                            "strata": []
                        }
                    boreholes_dict[b_id]["strata"].append({
                        "soil_type": row.get("지층명", ""),
                        "depth_top": row.get("상심도", ""),
                        "depth_bottom": row.get("하심도", "")
                    })
                
                json_output = {
                    "project_name": project_name,
                    "boreholes": list(boreholes_dict.values())
                }
                
                import json
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_output, f, ensure_ascii=False, indent=2)
            else:
                raise Exception("시추공 데이터를 찾을 수 없거나 파싱에 실패했습니다.")
            
            # 성공 결과 업데이트
            result_entry.update({
                "status": "success",
                "csv_filename": csv_filename,
                "json_filename": json_filename,
                "download_url": f"/api/download/{request_id}/individual/{csv_filename}",
                "json_download_url": f"/api/download/{request_id}/individual/{json_filename}",
                "project_name": project_name,
                "data": merged
            })
            logging.info(f"  [완료] {filename} -> {len(merged)} 행 추출 성공.")
            
        except Exception as e:
            logging.error(f"  [오류] {filename} 처리 실패: {str(e)}")
            result_entry.update({
                "status": "error", 
                "error": str(e)
            })
            continue # 다음 파일로 중단 없이 진행
                
    # 4. 통합 CSV 생성 (물리적 명칭은 ASCII 고정) [Stage 45-H]
    combined_csv_filename = "combined_master.csv"
    if True: # 무조건 생성하여 다운로드 응답을 활성화
        # 자연 정렬 적용
        from parsers.pdf_parser_odl import natural_sort_key
        if all_combined_rows:
            all_combined_rows.sort(key=lambda x: (natural_sort_key(x.get("프로젝트명", "")), natural_sort_key(x.get("시추공명", ""))))
        
        combined_df = pd.DataFrame(all_combined_rows)
        # 컬럼 순서 재배치 및 고정 (N치 정보 포함하지 않음)
        column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고', '시추공명', '상심도', '하심도', '지층명']
        for col in column_order:
            if col not in combined_df.columns:
                combined_df[col] = ''
        combined_df = combined_df[column_order]
        combined_df.to_csv(os.path.join(request_folder, combined_csv_filename), index=False, encoding='utf-8-sig')

    # 5. 개별 결과물 ZIP 압축
    zip_path_base = os.path.join(request_folder, "all_results_archive")
    shutil.make_archive(zip_path_base, 'zip', individual_folder)
    zip_filename = "all_results_archive.zip"
    
    # 6. 최종 정렬된 결과 리스트 반환
    from parsers.pdf_parser_odl import natural_sort_key
    results.sort(key=lambda x: natural_sort_key(x.get("filename", "")))

    return jsonify({
        "results": results,
        "combined_csv_url": f"/api/download/{request_id}/seoul_borehole_master.csv",
        "zip_url": f"/api/download/{request_id}/all_results_archive.zip"
    })

@app.route('/api/download/<request_id>/<path:filename>')
def download_file(request_id, filename):
    """UUID 폴더 내 파일을 안전하게 다운로드 (Stage 45-K: URL 경로 기반 파일명 고정)"""
    # 1. 물리적 파일명 매핑 및 경로 계산
    # [Stage 45-K] URL의 filename은 사용자에게 보여줄 '가상' 이름임. 
    # 실제 서버상의 파일은 앞서 ASCII로 정규화한 이름을 사용함.
    is_csv = filename.lower().endswith('.csv')
    is_json = filename.lower().endswith('.json')
    
    if is_csv:
        physical_name = "combined_master.csv"
    elif is_json:
        physical_name = filename.split('/')[-1]
    else:
        physical_name = "all_results_archive.zip"

    full_path = os.path.join(app.config['UPLOAD_FOLDER'], request_id, physical_name)
    
    if not os.path.exists(full_path) and (is_csv or is_json):
        individual_path = os.path.join(app.config['UPLOAD_FOLDER'], request_id, 'individual')
        if os.path.exists(individual_path):
            files = [f for f in os.listdir(individual_path) if f.endswith('.csv' if is_csv else '.json')]
            target_name = filename.split('/')[-1]
            if target_name in files:
                full_path = os.path.join(individual_path, target_name)
            elif files:
                full_path = os.path.join(individual_path, files[0])

    # 2. 파일 존재 여부 선제적 확인
    if not os.path.exists(full_path):
        logging.error(f"❌ 다운로드 실패: 파일을 찾을 수 없음 - {full_path}")
        return jsonify({"error": "요청하신 파일을 찾을 수 없습니다."}), 404

    # 3. 보정된 파일명 결정
    if is_csv:
        serve_name = "seoul_borehole_master.csv" if "master" in filename else filename.split('/')[-1]
    elif is_json:
        serve_name = filename.split('/')[-1]
    else:
        serve_name = "all_results_archive.zip"
    
    # 4. 파일 응답 생성 (헤더 중복 차단을 위해 정석적인 명시적 주입 적용) [Stage 45-M]
    try:
        # 파일 데이터를 읽어 응답 객체 생성
        response = make_response(send_file(full_path))
        
        # [Stage 45-M] 사용자 요청 사항: MIME 타입 및 UTF-8 BOM 강제 설정
        if is_csv:
            safe_headers = get_csv_headers()
            safe_headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(serve_name)}"
            for k, v in safe_headers.items():
                response.headers[k] = v
        elif is_json:
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(serve_name)}"
        else:
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = f'attachment; filename="{serve_name}"'
        
        # 보안 및 캐시 제어 헤더 추가
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        logging.info(f"✅ 다운로드 헤더 강제 주입 완료: {serve_name}")
        return response

    except Exception as e:
        logging.error(f"❌ 다운로드 처리 중 시스템 에러: {e}")
        return jsonify({"error": "다운로드 처리 중 내부 서버 오류가 발생했습니다."}), 500

if __name__ == '__main__':
    print("\n[SUCCESS] GeoBIM Full-Stack Flask Server Started!")
    print("[INFO] Try accessing http://127.0.0.1:5000 on your browser.\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
