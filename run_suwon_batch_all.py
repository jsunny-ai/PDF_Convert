import os
import logging
import pandas as pd
from core.master_hybrid_extractor import MasterHybridExtractor
from core.table_merger import merge_multi_page_tables
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("batch_process_districts.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_district(district_name, input_dir):
    logger.info(f"=== [{district_name}] 대규모 배치 처리 시작 ===")
    extractor = MasterHybridExtractor()
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    pdf_files = sorted(pdf_files)
    
    all_rows = []
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    for i, filename in enumerate(pdf_files, 1):
        pdf_path = os.path.join(input_dir, filename)
        base_name = os.path.splitext(filename)[0]
        
        # 프로젝트명 결정 (구명 + 파일명)
        project_name = f"{district_name}_{base_name}"
        
        try:
            # 4단계 하이브리드 엔진 가동
            merged_rows = extractor.process_file(pdf_path, project_name)
            
            if merged_rows:
                all_rows.extend(merged_rows)
                success_count += 1
                logger.info(f"[{i}/{len(pdf_files)}] ✅ 성공: {filename} ({len(merged_rows)} 행)")
            else:
                fail_count += 1
                logger.warning(f"[{i}/{len(pdf_files)}] ⚠️ 데이터 없음: {filename}")
                
        except Exception as e:
            fail_count += 1
            logger.error(f"[{i}/{len(pdf_files)}] ❌ 에러: {filename} -> {str(e)}")
            
    # 최종 통합 CSV 생성
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        # 컬럼 순서 정리
        column_order = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고', '시추공명', '상심도', '하심도', '지층명', 'tm_x', 'tm_y']
        existing_cols = [c for c in column_order if c in df.columns]
        df = df[existing_cols]
        
        # 자연 정렬 (Natural Sort) 강제 적용
        from parsers.pdf_parser_odl import natural_sort_key
        if '프로젝트명' in df.columns and '시추공명' in df.columns:
            df['프로젝트명'] = df['프로젝트명'].astype(str)
            df['시추공명'] = df['시추공명'].astype(str)
            df = df.sort_values(
                by=['프로젝트명', '시추공명', '상심도'],
                key=lambda x: x.map(natural_sort_key) if x.name != '상심도' else x
            )
            
        output_filename = f"{district_name}_통합_데이터.csv"
        output_path = os.path.join(input_dir, output_filename)
        
        # Permission Error 방지를 위해 v2 시도 및 예외처리
        try:
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        except PermissionError:
            output_path = output_path.replace(".csv", "_v2.csv")
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
        total_bh = df['시추공명'].nunique() if '시추공명' in df.columns else 0
        
        elapsed = time.time() - start_time
        logger.info(f"=== [{district_name}] 처리 완료 ===")
        logger.info(f"📊 요약: {len(pdf_files)}개 파일 중 {success_count}개 성공, {fail_count}개 실패")
        logger.info(f"📈 결과: 총 {len(df)}개 행, {total_bh}개 시추공 추출됨")
        logger.info(f"📂 저장: {output_path}")
        logger.info(f"⏱️ 소요시간: {elapsed:.1f}초")
        
        return {
            "district": district_name,
            "pdf_count": len(pdf_files),
            "success": success_count,
            "fail": fail_count,
            "rows": len(df),
            "bh_count": total_bh,
            "path": output_path
        }
    else:
        logger.error(f"❌ [{district_name}] 추출된 데이터가 없습니다.")
        return None

def main():
    root_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    districts = [
        {"name": "수원시권선구", "path": os.path.join(root_dir, "수원시권선구")},
        {"name": "수원시장안구", "path": os.path.join(root_dir, "수원시장안구")}
    ]
    
    results = []
    for d in districts:
        if os.path.exists(d["path"]):
            res = process_district(d["name"], d["path"])
            if res:
                results.append(res)
        else:
            logger.error(f"Directory not found: {d['path']}")
            
    print("\n" + "="*50)
    print("📢 수원시 대규모 배치 전환 결과 보고")
    print("="*50)
    for r in results:
        print(f"[{r['district']}]")
        print(f"  - 처리 PDF: {r['pdf_count']}개 (성공: {r['success']})")
        print(f"  - 추출 BH: {r['bh_count']}개")
        print(f"  - 전체 행: {r['rows']}행")
        print(f"  - 저장 경로: {r['path']}")
        print("-" * 30)

if __name__ == "__main__":
    main()
