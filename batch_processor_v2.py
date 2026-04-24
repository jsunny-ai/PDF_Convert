import os
import glob
import logging
import csv
import re
import concurrent.futures
import shutil
import gc
from pathlib import Path

# 기존 고도화된 모듈 로드
import opendataloader_pdf
import pdf_parser_odl
from pdf_parser_odl import extract_all_from_md
from pdf_parser_odl import natural_sort_key
from table_merger import merge_multi_page_tables

# 로깅 설정 (pdf_parser의 basicConfig 선점 문제 방지를 위해 핸들러 직접 추가)
_logger = logging.getLogger()
_logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
if not any(isinstance(h, logging.FileHandler) for h in _logger.handlers):
    _fh = logging.FileHandler("batch_process.log", encoding="utf-8")
    _fh.setFormatter(_fmt)
    _logger.addHandler(_fh)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in _logger.handlers):
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    _logger.addHandler(_sh)

# 경로 설정
INPUT_DIR = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage"
OUTPUT_DIR = r"C:\antigravity\#1_2_PDF_CSV"
OUTPUT_FILENAME = "서울특별시_CSV_통합_최종_V2.csv"

def extract_project_info(filename: str) -> str:
    """파일명에서 페이지와 프로젝트 번호를 추출하여 '페이지-프로젝트' 형식으로 반환 (예: page105_project13 -> PJ_105-13)"""
    page_match = re.search(r'page(\d+)', filename, re.IGNORECASE)
    proj_match = re.search(r'project(\d+)', filename, re.IGNORECASE)
    
    page_num = page_match.group(1) if page_match else "?"
    proj_num = proj_match.group(1) if proj_match else "?"
    
    return f"PJ_{page_num}-{proj_num}"

def process_single_pdf_integrated(pdf_path):
    """
    단일 PDF 파일을 파싱하고, [중요] 마크다운이 없는 경우 실시간 ODL 변환을 수행합니다.
    """
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]
    project_name = extract_project_info(filename)
    
    # 마크다운 예상 경로 (pdf_parser_odl.py의 경로와 동기화)
    md_storage_root = r"C:\antigravity\#1_2_PDF_CSV\MD_Storage"
    md_path = os.path.join(md_storage_root, f"{base_name}.md")
    
    try:
        # 1. 마크다운 파일 존재 여부 확인 및 실시간 변환
        if not os.path.exists(md_path):
            # Java 환경 설정 (server.py와 동일)
            java_bin = r"C:\antigravity\#1_2_PDF_CSV\jdk_folder\jdk-21.0.2\bin"
            if java_bin not in os.environ.get("PATH", ""):
                os.environ["PATH"] = java_bin + os.pathsep + os.environ.get("PATH", "")
            
            # ODL 변환 전용 임시 폴더 (충돌 방지)
            temp_md_dir = os.path.join(md_storage_root, "_temp_batch", base_name)
            os.makedirs(temp_md_dir, exist_ok=True)
            
            opendataloader_pdf.convert(
                input_path=[pdf_path], 
                output_dir=temp_md_dir,
                format="markdown"
            )
            
            # 생성된 마크다운을 MD_Storage 루트로 이동 (추후 재사용/캐시 목적)
            md_files = [f for f in os.listdir(temp_md_dir) if f.endswith('.md')]
            if md_files:
                shutil.move(os.path.join(temp_md_dir, md_files[0]), md_path)
                # 추출된 이미지 디렉토리도 있을 수 있으나 여기서는 생략(또는 이동)
            
        # 2. 파일 내 모든 페이지 추출 (마크다운 기반)
        if not os.path.exists(md_path):
            logging.warning(f"  [변환 실패] '{filename}'의 마크다운을 생성할 수 없습니다.")
            return []
            
        all_pages_data = extract_all_from_md(md_path, project_name=project_name, pdf_path=pdf_path)
        
        # 3. 파일 내 페이지 간 병합 및 심도 보정 수행
        merged_rows = merge_multi_page_tables(all_pages_data)
        
        # 명시적인 리소스 해제
        del all_pages_data
        gc.collect()
        
        return merged_rows
    except Exception as e:
        logging.error(f"❌ '{filename}' 처리 중 오류: {e}")
        return []

def run_integrated_batch_parallel():
    # 1. 출력 디렉토리 보장
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # 2. PDF 파일 리스트 확보
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdf_files:
        logging.error(f"❌ '{INPUT_DIR}'에서 PDF 파일을 찾을 수 없습니다.")
        return

    total_files = len(pdf_files)
    logging.info(f"🚀 총 {total_files}개의 PDF 파일 병렬 처리를 시작합니다. (사이트 로직 동기화 버전)")
    
    # 3. 병렬 처리 (파일 단위로 추출+병합 완료 후 수집)
    all_final_rows = []
    # ProcessPoolExecutor로 병렬성 확보
    fail_count = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        future_to_pdf = {executor.submit(process_single_pdf_integrated, pdf): pdf for pdf in pdf_files}
        
        count = 0
        for future in concurrent.futures.as_completed(future_to_pdf):
            count += 1
            try:
                res = future.result()
                if res:
                    all_final_rows.extend(res)
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                pdf_file_path = future_to_pdf[future]
                logging.error(f"❌ Worker crashed for {os.path.basename(pdf_file_path)}: {e}")
            
            if count % 100 == 0 or count == total_files:
                logging.info(f"   ㄴ [Progress] {count}/{total_files} 파일 처리 완료...")

    if not all_final_rows:
        logging.error("❌ 추출된 데이터가 없습니다.")
        return

    # 4. 최종 데이터 정렬 (프로젝트명 -> 시추공명 -> 상심도)
    # server.py와 동일한 정렬 방식 유지
    logging.info(f"⚖️ 최종 {len(all_final_rows)}행 데이터 정렬 중...")
    all_final_rows.sort(key=lambda x: (
        natural_sort_key(x.get("프로젝트명", "")),
        natural_sort_key(x.get("시추공명", "")),
        float(x.get("상심도") or 0)
    ))

    # 5. 통합 CSV 저장 (UTF-8-SIG)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    fieldnames = ["프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"]
    
    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_final_rows)
            
        logging.info("=" * 50)
        logging.info(f"🎉 사이트 로직과 동기화된 통합 배치 처리가 완료되었습니다!")
        logging.info(f"📁 최종 파일: {output_path}")
        logging.info(f"📊 총 레코드 수: {len(all_final_rows)} 행")
        if fail_count > 0:
            logging.warning(f"⚠️ {fail_count}개 파일 처리 실패 (로그 파일 참조)")
        logging.info("=" * 50)
        
    except Exception as e:
        logging.error(f"❌ CSV 저장 중 에러 발생: {e}")

if __name__ == "__main__":
    run_integrated_batch_parallel()
