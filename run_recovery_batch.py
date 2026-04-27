import os
import glob
import logging
import csv
import time
import sys
# 로컬 패키지(core, parsers) 우선 참조 강제
sys.path.insert(0, os.getcwd())

from core.master_hybrid_extractor import MasterHybridExtractor
from parsers.pdf_parser_odl import natural_sort_key

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    fh = logging.FileHandler("recovery_batch.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

def process_single_file(pdf_path, district_name, extractor):
    try:
        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        # 권선구와 동일한 프로젝트 명명 규칙 적용
        project_name = f"{district_name}_{base_name}"
        
        # 3-tier 하이브리드 추출 및 병합 적용
        merged_rows = extractor.process_file(pdf_path, project_name)
        return merged_rows
    except Exception as e:
        import traceback
        logging.error(f"❌ '{os.path.basename(pdf_path)}' 처리 중 오류: {e}")
        logging.error(traceback.format_exc())
        return []

def run_recovery_batch():
    base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    output_dir = r"C:\antigravity\#1_2_PDF_CSV\data\03_final"
    os.makedirs(output_dir, exist_ok=True)
    
    # 복구 대상 구 설정 (장안구, 팔달구)
    target_districts = ["수원시장안구", "수원시팔달구"]
    
    # 하이브리드 추출기 인스턴스 생성
    extractor = MasterHybridExtractor(output_dir=r"C:\antigravity\#1_2_PDF_CSV")
    
    for district in target_districts:
        district_path = os.path.join(base_dir, district)
        if not os.path.exists(district_path):
            logging.warning(f"⚠️ '{district}' 폴더를 찾을 수 없습니다. 스킵합니다.")
            continue
            
        pdf_files = glob.glob(os.path.join(district_path, "*.pdf"))
        if not pdf_files:
            logging.warning(f"⚠️ '{district}' 폴더에 PDF 파일이 없습니다. 스킵합니다.")
            continue
            
        logging.info(f"🚀 [{district}] 총 {len(pdf_files)}개의 PDF 파일 복구 배치를 시작합니다.")
        
        all_final_rows = []
        fail_count = 0
        total_files = len(pdf_files)
        
        # HWP COM 객체 간섭을 최소화하기 위해 순차 처리 (필요시 ProcessPool 대신 순차 처리 권장)
        for idx, pdf in enumerate(pdf_files):
            res = process_single_file(pdf, district, extractor)
            if res:
                all_final_rows.extend(res)
                logging.info(f"   [{idx+1}/{total_files}] ✅ {os.path.basename(pdf)} 추출 성공 ({len(res)}행)")
            else:
                fail_count += 1
                logging.warning(f"   [{idx+1}/{total_files}] ⚠️ {os.path.basename(pdf)} 데이터 없음")
            
            # COM 컨트롤 안정화를 위한 미세 지연
            time.sleep(0.5)

        if not all_final_rows:
            logging.error(f"❌ '{district}'에서 추출된 데이터가 없습니다.")
            continue

        # 정렬 (프로젝트명 -> 시추공명 -> 상심도)
        logging.info(f"⚖️ [{district}] 데이터 정렬 및 최적화 중...")
        all_final_rows.sort(key=lambda x: (
            natural_sort_key(x.get("프로젝트명", "")),
            natural_sort_key(x.get("시추공명", "")),
            float(x.get("상심도") or 0)
        ))

        # CSV 저장 (기존 불량 파일 덮어쓰기)
        output_filename = f"{district}_hybrid.csv"
        output_path = os.path.join(output_dir, output_filename)
        # 현재 시스템 표준 8대 컬럼 규격 강제
        fieldnames = ["프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"]
        
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(all_final_rows)
                
            logging.info(f"🎉 [{district}] 복구 완료! 생성 파일: {output_path} ({len(all_final_rows)}행)")
        except Exception as e:
            logging.error(f"❌ [{district}] CSV 저장 에러: {e}")

if __name__ == "__main__":
    run_recovery_batch()
