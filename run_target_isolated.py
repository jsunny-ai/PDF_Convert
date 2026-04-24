import os
import glob
import logging
import csv
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

# Globally configure JAVA PATH to avoid WinError 5 in subprocesses
os.environ['PATH'] = r'C:\antigravity\#1_2_PDF_CSV\jdk_folder\jdk-21.0.2\bin;' + os.environ.get('PATH', '')

# Ensure correct path
sys.path.append(r"C:\antigravity\#1_2_PDF_CSV")

from suwon_hybrid_runner import process_single_file
from pdf_parser_odl import natural_sort_key

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def isolate_process_wrapper(pdf, district):
    return process_single_file(pdf, district)

def run_isolated_districts():
    base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    output_dir = r"C:\antigravity\#1_2_PDF_CSV"
    districts = ["수원시장안구", "수원시팔달구"]
    
    for district in districts:
        district_path = os.path.join(base_dir, district)
        if not os.path.exists(district_path):
            logging.error(f"폴더를 찾을 수 없습니다: {district_path}")
            continue
            
        pdf_files = glob.glob(os.path.join(district_path, "*.pdf"))
        # 파일명을 자연 정렬 (project1, project2, ... project10)
        pdf_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
        
        logging.info(f"\n=======================================================")
        logging.info(f" 🚀 [{district}] 총 {len(pdf_files)}개 PDF 파일 -> 격리 모드 하이브리드 추출 시작")
        logging.info(f"=======================================================\n")
        
        all_final_rows = []
        fail_count = 0
        
        # max_workers=1로 설정하여 한 번에 하나의 파일만 병렬 처리하되, 
        # 자식 프로세스의 메모리가 매번 분리되도록 한다. 
        # wait, ProcessPoolExecutor는 디폴트로 1개의 프로세스를 띄워놓고 재사용한다! 
        # 재사용되면 메모리 분리 효과가 제한적이다. 
        # mp.Process를 매번 새로 띄우는 것이 가장 확실하다.
        import multiprocessing as mp
        mp.set_start_method('spawn', force=True)

        for i, pdf in enumerate(pdf_files):
            logging.info(f"   ▶ [진행률] {i+1}/{len(pdf_files)} 완료...")
            
            with ProcessPoolExecutor(max_workers=1) as executor:
                try:
                    future = executor.submit(isolate_process_wrapper, pdf, district)
                    res = future.result()  # 동기식 대기
                    if res:
                        all_final_rows.extend(res)
                    else:
                        fail_count += 1
                except Exception as e:
                    logging.error(f"❌ 단일 처리 중 치명적 오류 ({os.path.basename(pdf)}): {e}")
                    fail_count += 1
        
        if not all_final_rows:
            logging.warning(f"⚠️ [{district}] 추출된 데이터가 없습니다. CSV 생성을 건너뜁니다.")
            continue
            
        csv_filename = f"{district}_hybrid.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        headers = [
            "구", "동", "프로젝트명", "공번", "대공분류", "X좌표", "Y좌표",
            "표고(m)", "관정깊이(m)", "지하수위(m)", "굴착일자",
            "매립층", "퇴적층", "풍화암", "연암", "보통암", "경암"
        ]
        
        try:
            with open(csv_path, mode="w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in all_final_rows:
                    writer.writerow([
                        row.get("구", ""),
                        row.get("동", ""),
                        row.get("프로젝트명", ""),
                        row.get("공번", ""),
                        row.get("대공분류", ""),
                        row.get("X좌표", ""),
                        row.get("Y좌표", ""),
                        row.get("표고(m)", ""),
                        row.get("관정깊이(m)", ""),
                        row.get("지하수위(m)", ""),
                        row.get("굴착일자", ""),
                        row.get("매립층", ""),
                        row.get("퇴적층", ""),
                        row.get("풍화암", ""),
                        row.get("연암", ""),
                        row.get("보통암", ""),
                        row.get("경암", "")
                    ])
            logging.info(f"✅ [{district}] 성공적으로 통합 CSV 완성! (저장경로: {csv_path}, 총 {len(all_final_rows)}행, 실패 {fail_count}개)")
        except Exception as e:
            logging.error(f"❌ [{district}] CSV 저장 중 오류 발생: {e}")

if __name__ == "__main__":
    run_isolated_districts()
