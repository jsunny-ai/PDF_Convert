import os
import sys
import glob
import pandas as pd
import time
from core.master_hybrid_extractor import MasterHybridExtractor

sys.stdout.reconfigure(encoding='utf-8')

def run_integration():
    target_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구"
    output_filename = "수원시팔달구_통합_데이터_v2.csv"
    output_path = os.path.join(target_dir, output_filename)
    
    column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고', '시추공명', '상심도', '하심도', '지층명']
    
    extractor = MasterHybridExtractor(output_dir=r"C:\antigravity\#1_2_PDF_CSV")
    pdf_files = glob.glob(os.path.join(target_dir, "*.pdf"))
    
    print(f"🚀 [통합 시작] 총 {len(pdf_files)}개의 PDF를 분석하여 하나의 CSV로 통합합니다.", flush=True)
    
    all_rows = []
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    for i, fp in enumerate(pdf_files, 1):
        base_name = os.path.splitext(os.path.basename(fp))[0]
        
        try:
            # 1. 3-Tier 파이프라인 추출
            merged = extractor.process_file(fp, base_name)
            
            if merged and len(merged) > 0:
                all_rows.extend(merged)
                success_count += 1
                if i % 10 == 0 or i == len(pdf_files):
                    print(f"[{i}/{len(pdf_files)}] ✅ 성공: {base_name} (누적 {len(all_rows)} 행)", flush=True)
            else:
                fail_count += 1
                print(f"[{i}/{len(pdf_files)}] ⚠️ 데이터 없음: {base_name}", flush=True)
                
        except Exception as e:
            fail_count += 1
            print(f"[{i}/{len(pdf_files)}] ❌ 에러: {base_name} -> {str(e)}", flush=True)
            
    # 2. 통합 데이터프레임 생성 및 저장
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        # 컬럼 규격화 및 정렬
        for col in column_order:
            if col not in df.columns:
                df[col] = ''
        df = df[column_order]
        
        # 자연 정렬 적용
        from parsers.pdf_parser_odl import natural_sort_key
        # 정렬 기준 컬럼을 문자열로 강제 변환하여 unhashable type: 'list' 오류 방지
        df['프로젝트명'] = df['프로젝트명'].astype(str)
        df['시추공명'] = df['시추공명'].astype(str)
        df = df.sort_values(by=['프로젝트명', '시추공명'], key=lambda x: x.map(natural_sort_key))
        
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"\n✨ [통합 완료] 모든 데이터가 성공적으로 병합되었습니다.")
        print(f"📂 저장 위치: {output_path}")
        print(f"📊 최종 결과: 총 {success_count}개 파일 성공, {fail_count}개 실패. 전체 {len(df)} 행 추출됨.")
        print(f"⏱️ 총 소요 시간: {time.time() - start_time:.1f}초")
    else:
        print("\n❌ 추출된 데이터가 없어 통합 파일을 생성하지 못했습니다.")

if __name__ == '__main__':
    run_integration()
