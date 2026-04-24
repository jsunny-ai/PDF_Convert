import os
import glob
import logging
import csv
import sys

# Globally configure JAVA PATH to avoid WinError 5 in subprocesses
os.environ['PATH'] = r'C:\antigravity\#1_2_PDF_CSV\jdk_folder\jdk-21.0.2\bin;' + os.environ.get('PATH', '')

# Ensure correct path
sys.path.append(r"C:\antigravity\#1_2_PDF_CSV")

from suwon_hybrid_runner import process_single_file
from pdf_parser_odl import natural_sort_key

# 로깅
logging.basicConfig(level=logging.INFO, format="%(message)s")

def run_specific_districts():
    base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    output_dir = r"C:\antigravity\#1_2_PDF_CSV"
    districts = ["수원시장안구", "수원시팔달구"]
    
    for district in districts:
        district_path = os.path.join(base_dir, district)
        if not os.path.exists(district_path):
            logging.error(f"❌ 폴더 없음: {district_path}")
            continue
            
        pdf_files = glob.glob(os.path.join(district_path, "*.pdf"))
        
        logging.info(f"🚀 [{district}] 총 {len(pdf_files)}개의 PDF 파일 처리를 시작합니다.")
        
        all_final_rows = []
        fail_count = 0
        count = 0
        total_files = len(pdf_files)
        
        for pdf in pdf_files:
            try:
                res = process_single_file(pdf, district)
                if res:
                    all_final_rows.extend(res)
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                logging.error(f"❌ '{os.path.basename(pdf)}' 오류: {e}")
            
            count += 1
            if count % 20 == 0 or count == total_files:
                logging.info(f"   ㄴ [{district} Progress] {count}/{total_files} 파일 완료...")

        if not all_final_rows:
            logging.error(f"❌ '{district}'에서 추출된 데이터가 없습니다.")
            continue

        # 정렬
        all_final_rows.sort(key=lambda x: (
            natural_sort_key(x.get("프로젝트명", "")),
            natural_sort_key(x.get("시추공명", "")),
            float(x.get("상심도") or 0)
        ))

        # CSV 저장
        output_filename = f"{district}_hybrid.csv"
        output_path = os.path.join(output_dir, output_filename)
        fieldnames = ["프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"]
        
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(all_final_rows)
                
            logging.info(f"🎉 [{district}] 생성 완료: {output_path} ({len(all_final_rows)}행) (실패: {fail_count})")
        except Exception as e:
            logging.error(f"❌ CSV 저장 에러: {e}")

if __name__ == "__main__":
    run_specific_districts()
