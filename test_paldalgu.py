import os
import sys
import glob
import pandas as pd
import time
from core.master_hybrid_extractor import MasterHybridExtractor

sys.stdout.reconfigure(encoding='utf-8')

def run_test():
    target_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구"
    column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고', '시추공명', '상심도', '하심도', '지층명']
    
    extractor = MasterHybridExtractor(output_dir=r"C:\antigravity\#1_2_PDF_CSV")
    pdf_files = glob.glob(os.path.join(target_dir, "*.pdf"))
    
    print(f"[시작] 발견된 PDF 갯수: {len(pdf_files)}개. 팔달구 폴더 내부 배치 변환을 시작합니다.", flush=True)
    
    success, fail, err = 0, 0, 0
    start = time.time()
    
    for i, fp in enumerate(pdf_files, 1):
        base_name = os.path.splitext(os.path.basename(fp))[0]
        csv_path = os.path.join(target_dir, f"{base_name}.csv") # 동일한 폴더에 저장
        
        try:
            merged = extractor.process_file(fp, base_name)
            if merged and len(merged) > 0:
                df = pd.DataFrame(merged)
                
                # 최적화된 V-World 8열 규격을 적용
                for col in column_order:
                    if col not in df.columns:
                        df[col] = ''
                df = df[column_order]
                
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                success += 1
                if i % 10 == 0 or i == len(pdf_files):
                    print(f"[{i}/{len(pdf_files)}] [성공] 변환 완료됨: {base_name}.csv", flush=True)
            else:
                fail += 1
                if i % 10 == 0 or i == len(pdf_files):
                    print(f"[{i}/{len(pdf_files)}] [추출실패] 추출 데이터 없음: {base_name}", flush=True)
        except Exception as e:
            err += 1
            print(f"[{i}/{len(pdf_files)}] [오류] 시스템 에러({base_name}): {str(e)}", flush=True)
            
    print(f"\n[종료] 변환 및 정규화 작업이 종료되었습니다. 소요 시간: {time.time()-start:.1f}초")
    print(f"결과: 성공 {success}개, 실패(결측) {fail}개, 시스템에러 {err}개")

if __name__ == '__main__':
    run_test()
