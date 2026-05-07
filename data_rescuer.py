import os
import pandas as pd
import glob
import logging
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.master_hybrid_extractor import MasterHybridExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rescue_migration.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def process_pdf_worker(pdf_path, dist):
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        project_name = f"{dist}_{base_name}"
        # 매번 새로운 extractor 인스턴스를 생성하여 병렬 충돌 방지
        local_extractor = MasterHybridExtractor()
        return local_extractor.process_file(pdf_path, project_name)
    except Exception as e:
        return None

def rescue_migration():
    """
    수원시 경계 Box에 의해 기각되었던 선형 인프라 및 경계면 데이터를 
    사업 단위 클러스터링(DBSCAN/Median) 로직으로 재평가하여 구제함.
    """
    logger.info("=== [STAGE 55] 지능형 데이터 구제(Rescue) 마이그레이션 가동 ===")
    
    # 1. PDF 저장소 설정
    pdf_base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    districts = ["수원시권선구", "수원시장안구", "수원시팔달구"]
    
    extractor = MasterHybridExtractor()
    final_output_dir = "data/03_final"
    os.makedirs(final_output_dir, exist_ok=True)

    summary_stats = []

    for dist in districts:
        dist_path = os.path.join(pdf_base_dir, dist)
        if not os.path.exists(dist_path):
            logger.warning(f"경로를 찾을 수 없음: {dist_path}")
            continue
        
        logger.info(f"\n>>> [{dist}] 구역 마이그레이션 시작")
        pdf_files = glob.glob(os.path.join(dist_path, "*.pdf"))
        
        all_data = []
        rescued_points = 0
        total_files = len(pdf_files)
        for i, pdf in enumerate(pdf_files):
            try:
                base_name = os.path.splitext(os.path.basename(pdf))[0]
                project_name = f"{dist}_{base_name}"
                result = extractor.process_file(pdf, project_name)
                if result:
                    all_data.extend(result)
                    count = sum(1 for r in result if r.get("lon_wgs84") != "")
                    rescued_points += count
                
                if (i+1) % 10 == 0:
                    logger.info(f"   - 진행률: {i+1}/{total_files} 파일 완료...")
            except Exception as e:
                logger.error(f"   [ERR] {pdf} 처리 실패: {e}")

        if all_data:
            # 데이터프레임 변환 및 정렬
            df = pd.DataFrame(all_data)
            
            # 컬럼 필터링 및 영문명 변경 (시추공명 포함 8개 컬럼)
            rename_map = {
                "프로젝트명": "project_name",
                "시추공명": "bh_id",
                "lon_wgs84": "lon_wgs84",
                "lat_wgs84": "lat_wgs84",
                "표고": "elevation",
                "상심도": "top_depth",
                "하심도": "bottom_depth",
                "지층명": "strata_name"
            }
            # 존재하는 컬럼만 선택 후 이름 변경
            df = df[[c for c in rename_map.keys() if c in df.columns]]
            df = df.rename(columns=rename_map)
            
            # 자연 정렬 (Natural Sort)
            from parsers.pdf_parser_odl import natural_sort_key
            if 'project_name' in df.columns and 'bh_id' in df.columns:
                df['project_name'] = df['project_name'].astype(str)
                df['bh_id'] = df['bh_id'].astype(str)
                df = df.sort_values(
                    by=['project_name', 'bh_id', 'top_depth'],
                    key=lambda x: x.map(natural_sort_key) if x.name != 'top_depth' else x
                )
            
            # 최종 파일 저장 (기존 파일에 덮어쓰기 또는 신규 생성) - CSV
            output_csv_path = os.path.join(final_output_dir, f"{dist}_hybrid_v2.csv")
            df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
            
            # JSON 저장
            output_json_path = os.path.join(final_output_dir, f"{dist}_hybrid_v2.json")
            df.to_json(output_json_path, orient="records", force_ascii=False, indent=4)
            
            logger.info(f"   ㄴ [{dist}] 완료: {len(df)}행 추출, 유효 좌표 {rescued_points}건 확보.")
            summary_stats.append({"구": dist, "전체행": len(df), "유효좌표": rescued_points})

    # 전체 통합 파일 생성
    merge_and_finalize(final_output_dir)
    
    logger.info("\n=== 마이그레이션 최종 요약 ===")
    for stat in summary_stats:
        logger.info(f" - {stat['구']}: {stat['유효좌표']}건 구제 성공 (총 {stat['전체행']}행)")

def merge_and_finalize(data_dir):
    """구별 데이터를 하나로 통합하여 수원시_전체_통합_시추데이터 생성"""
    files = glob.glob(os.path.join(data_dir, "*_hybrid_v2.csv"))
    if not files: return
    
    combined_df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    from parsers.pdf_parser_odl import natural_sort_key
    if 'project_name' in combined_df.columns and 'bh_id' in combined_df.columns:
        combined_df['project_name'] = combined_df['project_name'].astype(str)
        combined_df['bh_id'] = combined_df['bh_id'].astype(str)
        combined_df = combined_df.sort_values(
            by=['project_name', 'bh_id', 'top_depth'],
            key=lambda x: x.map(natural_sort_key) if x.name != 'top_depth' else x
        )
    
    master_csv_path = os.path.join(data_dir, "수원시_전체_통합_시추데이터_v2.csv")
    combined_df.to_csv(master_csv_path, index=False, encoding='utf-8-sig')
    
    master_json_path = os.path.join(data_dir, "수원시_전체_통합_시추데이터_v2.json")
    combined_df.to_json(master_json_path, orient="records", force_ascii=False, indent=4)
    
    logger.info(f"\n[MASTER] 최종 통합 데이터 생성 완료: {master_csv_path}, {master_json_path}")
    logger.info("\n[SAMPLE DATA - TOP 3 ROWS]")
    for idx, row in combined_df.head(3).iterrows():
        logger.info(dict(row))

if __name__ == "__main__":
    rescue_migration()
