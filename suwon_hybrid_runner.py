import os
import glob
import logging
import csv
import concurrent.futures

from master_hybrid_extractor import MasterHybridExtractor
from pdf_parser_odl import natural_sort_key

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    fh = logging.FileHandler("suwon_hybrid_batch.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

def process_single_file(pdf_path, district_name):
    try:
        # 하이브리드 추출기 인스턴스를 워커 내부에서 생성 (스레드/프로세스 안전)
        extractor = MasterHybridExtractor(output_dir=r"C:\antigravity\#1_2_PDF_CSV")
        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        project_name = f"{district_name}_{base_name}"
        
        # 3-tier 하이브리드 추출 및 병합 적용
        merged_rows = extractor.process_file(pdf_path, project_name)
        return merged_rows
    except Exception as e:
        logging.error(f"❌ '{os.path.basename(pdf_path)}' 처리 중 크래시: {e}")
        return []

def run_suwon_hybrid_batch():
    base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    output_dir = r"C:\antigravity\#1_2_PDF_CSV"
    
    if not os.path.exists(base_dir):
        logging.error(f"❌ 설정된 경로를 찾을 수 없습니다: {base_dir}")
        return

    districts = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    for district in districts:
        district_path = os.path.join(base_dir, district)
        pdf_files = glob.glob(os.path.join(district_path, "*.pdf"))
        
        if not pdf_files:
            logging.warning(f"⚠️ '{district}' 폴더에 PDF 파일이 없습니다.")
            continue
            
        logging.info(f"🚀 [{district}] 총 {len(pdf_files)}개의 PDF 파일 하이브리드 처리를 시작합니다.")
        
        all_final_rows = []
        fail_count = 0
        count = 0
        total_files = len(pdf_files)
        
        # 윈도우 COM 객체 (HWP) 충돌을 방지하기 위해 순차 처리 적용
        for pdf in pdf_files:
            try:
                res = process_single_file(pdf, district)
                if res:
                    all_final_rows.extend(res)
                else:
                    fail_count += 1
                time.sleep(1)
            except Exception as e:
                fail_count += 1
                logging.error(f"❌ '{os.path.basename(pdf)}' 단일 처리 중 오류: {e}")
            
            count += 1
            if count % 10 == 0 or count == total_files:
                logging.info(f"   ㄴ [{district} Progress] {count}/{total_files} 파일 완료...")

        if not all_final_rows:
            logging.error(f"❌ '{district}'에서 추출된 데이터가 없습니다.")
            continue

        # 정렬
        logging.info(f"⚖️ [{district}] 최종 {len(all_final_rows)}행 데이터 정렬 중...")
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
                
            logging.info(f"🎉 [{district}] 생성 완료: {output_path} ({len(all_final_rows)}행)")
        except Exception as e:
            logging.error(f"❌ CSV 저장 에러: {e}")

if __name__ == "__main__":
    run_suwon_hybrid_batch()
