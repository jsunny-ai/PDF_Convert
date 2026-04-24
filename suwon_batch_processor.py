import os
import glob
import logging
import csv
import concurrent.futures

# 기존 고도화된 모듈 로드
from batch_processor_v2 import process_single_pdf_integrated
from pdf_parser_odl import natural_sort_key

def run_suwon_batch():
    base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    output_dir = r"C:\antigravity\#1_2_PDF_CSV"
    
    # 로깅 설정
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        fh = logging.FileHandler("suwon_batch_process.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    
    if not os.path.exists(base_dir):
        logging.error(f"❌ 설정된 경로를 찾을 수 없습니다: {base_dir}")
        return

    # 수원시 내의 각 구 폴더 (예: 수원시권선구, 수원시장안구, 수원시팔달구) 탐색
    districts = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    for district in districts:
        district_path = os.path.join(base_dir, district)
        pdf_files = glob.glob(os.path.join(district_path, "*.pdf"))
        
        if not pdf_files:
            logging.warning(f"⚠️ '{district}' 폴더에 PDF 파일이 없습니다.")
            continue
            
        logging.info(f"🚀 [{district}] 총 {len(pdf_files)}개의 PDF 파일 병렬 처리를 시작합니다.")
        
        all_final_rows = []
        fail_count = 0
        total_files = len(pdf_files)
        
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
                
                if count % 50 == 0 or count == total_files:
                    logging.info(f"   ㄴ [{district} Progress] {count}/{total_files} 파일 처리 완료...")

        if not all_final_rows:
            logging.error(f"❌ '{district}'에서 최소 한 개의 데이터도 추출되지 않았습니다.")
            continue

        # 정렬
        logging.info(f"⚖️ [{district}] 최종 {len(all_final_rows)}행 데이터 정렬 중...")
        all_final_rows.sort(key=lambda x: (
            natural_sort_key(x.get("프로젝트명", "")),
            natural_sort_key(x.get("시추공명", "")),
            float(x.get("상심도") or 0)
        ))

        # CSV 저장
        output_filename = f"{district}.csv"
        output_path = os.path.join(output_dir, output_filename)
        fieldnames = ["프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"]
        
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(all_final_rows)
                
            logging.info(f"🎉 [{district}] 통합 배치가 완료되었습니다!")
            logging.info(f"📁 생성 파일: {output_path}")
            logging.info(f"📊 총 레코드 수: {len(all_final_rows)} 행")
            if fail_count > 0:
                logging.warning(f"⚠️ [{district}] {fail_count}개 파일 처리 실패")
        except Exception as e:
            logging.error(f"❌ [{district}] CSV 저장 중 에러 발생: {e}")

if __name__ == "__main__":
    run_suwon_batch()
