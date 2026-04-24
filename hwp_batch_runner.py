"""
Stage 46: 인덱스 기반 배치 처리 모듈
수원시 3개 구(권선구, 장안구, 팔달구)의 PDF를 병렬로 처리하여 구별 CSV를 생성합니다.
"""
import os
import glob
import logging
import csv
import concurrent.futures

from hwp_indexed_extractor import process_single_pdf_indexed
from pdf_parser_odl import natural_sort_key

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    _fh = logging.FileHandler("stage46_batch.log", encoding="utf-8")
    _fh.setFormatter(_fmt)
    logger.addHandler(_fh)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    logger.addHandler(_sh)

# 경로 설정
BASE_DIR = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
OUTPUT_DIR = r"C:\antigravity\#1_2_PDF_CSV"
FIELDNAMES = ["프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"]


def run_suwon_indexed_batch():
    """수원시 전체 구를 순회하며 인덱스 기반 추출 후 구별 CSV 생성"""
    
    if not os.path.exists(BASE_DIR):
        logging.error(f"❌ 기본 경로를 찾을 수 없습니다: {BASE_DIR}")
        return
    
    districts = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    logging.info(f"🚀 [Stage 46] 인덱스 기반 정밀 추출 시작 — 대상 구: {districts}")
    
    grand_total_rows = 0
    grand_total_na = 0
    
    for district in districts:
        district_path = os.path.join(BASE_DIR, district)
        pdf_files = glob.glob(os.path.join(district_path, "*.pdf"))
        
        if not pdf_files:
            logging.warning(f"⚠️ '{district}' 폴더에 PDF 파일이 없습니다.")
            continue
        
        total_files = len(pdf_files)
        logging.info(f"\n{'='*60}")
        logging.info(f"📂 [{district}] {total_files}개 PDF 병렬 처리 시작")
        logging.info(f"{'='*60}")
        
        all_rows = []
        fail_count = 0
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            future_to_pdf = {
                executor.submit(process_single_pdf_indexed, pdf): pdf 
                for pdf in pdf_files
            }
            
            count = 0
            for future in concurrent.futures.as_completed(future_to_pdf):
                count += 1
                try:
                    rows = future.result()
                    if rows:
                        all_rows.extend(rows)
                    else:
                        fail_count += 1
                except Exception as e:
                    fail_count += 1
                    pdf_file = future_to_pdf[future]
                    logging.error(f"❌ Worker crashed: {os.path.basename(pdf_file)} — {e}")
                
                if count % 50 == 0 or count == total_files:
                    logging.info(f"   ㄴ [{district}] {count}/{total_files} 완료...")
        
        if not all_rows:
            logging.error(f"❌ '{district}'에서 데이터 추출 실패")
            continue
        
        # 정렬: 프로젝트명 → 시추공명 → 상심도
        logging.info(f"⚖️ [{district}] {len(all_rows)}행 정렬 중...")
        all_rows.sort(key=lambda x: (
            natural_sort_key(x.get("프로젝트명", "")),
            natural_sort_key(x.get("시추공명", "")),
            float(x.get("상심도") or 0)
        ))
        
        # N/A 통계
        na_count = sum(1 for r in all_rows if any(v == "N/A" for v in r.values()))
        
        # CSV 저장
        output_filename = f"{district}_Stage46.csv"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(all_rows)
            
            logging.info(f"🎉 [{district}] 완료!")
            logging.info(f"   📁 파일: {output_path}")
            logging.info(f"   📊 레코드: {len(all_rows)}행")
            logging.info(f"   ⚠️ 실패: {fail_count}개 파일")
            logging.info(f"   🔍 N/A 포함 행: {na_count}개")
            
            grand_total_rows += len(all_rows)
            grand_total_na += na_count
            
        except Exception as e:
            logging.error(f"❌ [{district}] CSV 저장 오류: {e}")
    
    logging.info(f"\n{'='*60}")
    logging.info(f"🏆 [Stage 46] 전체 배치 처리 완료!")
    logging.info(f"   📊 총 레코드: {grand_total_rows}행")
    logging.info(f"   🔍 총 N/A 행: {grand_total_na}개")
    logging.info(f"{'='*60}")


if __name__ == "__main__":
    run_suwon_indexed_batch()
