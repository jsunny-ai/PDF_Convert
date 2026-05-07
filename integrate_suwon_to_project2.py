import pandas as pd
import os
import json
import re
from parsers.pdf_parser_odl import natural_sort_key
from core.spatial_validator import SpatialValidator
import shutil

def integrate():
    print("=== 수원시 전역 데이터 통합 및 #2 프로젝트 이관 시작 ===")
    
    root_src = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시'
    target_dir = r'C:\antigravity\#2\data'
    config_src = r'C:\antigravity\#1_2_PDF_CSV\config\geo_settings.json'
    config_dest_dir = r'C:\antigravity\#2\config'
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(config_dest_dir, exist_ok=True)

    # M0: Config Sync (SSOT)
    if os.path.exists(config_src):
        shutil.copy2(config_src, os.path.join(config_dest_dir, 'geo_settings.json'))
        print("  [Config] Sync geo_settings.json to #2/config/")

    sources = [
        ("수원시권선구", os.path.join(root_src, '수원시권선구', '수원시권선구_통합_데이터.csv')),
        ("수원시장안구", os.path.join(root_src, '수원시장안구', '수원시장안구_통합_데이터.csv')),
        ("수원시팔달구", os.path.join(root_src, '수원시팔달구', '수원시팔달구_통합_데이터.csv')),
    ]

    # M1: Load and Concat
    dfs = []
    total_src_rows = 0
    for name, path in sources:
        if os.path.exists(path):
            df_part = pd.read_csv(path, encoding='utf-8-sig')
            
            # [Stage 54-Final] 팔달구 접두사 누락 방지
            if name == "수원시팔달구":
                def add_paldal_prefix(pname):
                    pname = str(pname)
                    if not pname.startswith("수원시팔달구_"):
                        return f"수원시팔달구_{pname}"
                    return pname
                df_part['프로젝트명'] = df_part['프로젝트명'].apply(add_paldal_prefix)
                
            print(f"  [Load] {name}: {len(df_part)} rows")
            dfs.append(df_part)
            total_src_rows += len(df_part)
        else:
            print(f"  [Error] Missing source: {path}")

    if not dfs:
        print("  [Abort] No data to merge.")
        return

    merged = pd.concat(dfs, ignore_index=True)
    print(f"  [Merge] Combined total: {len(merged)} rows")

    # M1-1: Force Recompute Coordinates with Latest Logic
    print("  [Recompute] Applying latest coordinate correction logic...")
    from core.coordinate_transformer import normalize_coordinates
    
    new_coords = []
    for idx, row in merged.iterrows():
        # [Strict Rule] 원본 TM 데이터('경도', '위도')가 있으면 최우선 사용
        # lon_wgs84는 이미 변환된 값일 수 있으므로 폴백으로만 사용
        raw_x = row.get('경도') if pd.notna(row.get('경도')) else row.get('lon_wgs84')
        raw_y = row.get('위도') if pd.notna(row.get('위도')) else row.get('lat_wgs84')
        
        bh_id = row.get('시추공명', 'Unknown')
        
        # meta_crs가 'EPSG:'로 시작하지 않는 노이즈(REJECT_OUTLIER 등)면 None 처리하여 재탐색 유도
        meta_crs = row.get('meta_crs')
        if not str(meta_crs).startswith('EPSG:'):
            meta_crs = None
            
        lon, lat, tmx, tmy, final_epsg = normalize_coordinates(
            raw_x, raw_y, 
            borehole_id=bh_id, 
            source_crs=meta_crs
        )
        new_coords.append((lon, lat, tmx, tmy, final_epsg))
    
    coords_df = pd.DataFrame(new_coords, columns=['lon_wgs84', 'lat_wgs84', 'tm_x', 'tm_y', 'meta_crs'])
    merged[['lon_wgs84', 'lat_wgs84', 'tm_x', 'tm_y', 'meta_crs']] = coords_df

    # M2: Global Natural Sort
    print("  [Sort] Applying global natural sort...")
    merged['프로젝트명'] = merged['프로젝트명'].astype(str)
    merged['시추공명'] = merged['시추공명'].astype(str)
    merged = merged.sort_values(
        by=['프로젝트명', '시추공명', '상심도'],
        key=lambda x: x.map(natural_sort_key) if x.name != '상심도' else x
    )

    # M3: Deduplication
    print("  [Dedupe] Checking for duplicates...")
    orig_len = len(merged)
    # Check all key columns for duplication
    dedupe_cols = ['프로젝트명', '시추공명', '상심도', '하심도', '지층명']
    merged = merged.drop_duplicates(subset=dedupe_cols, keep='first')
    diff = orig_len - len(merged)
    print(f"  [Dedupe] Removed {diff} duplicate rows. Final row count: {len(merged)}")

    # M3-1: Spatial Geo-Fence (Smart Validation)
    print("  [Geo-Fence] Applying Smart Spatial Validation (Hard/Soft/Reject)...")
    validator = SpatialValidator()
    
    results = []
    for idx, row in merged.iterrows():
        lon, lat = row['lon_wgs84'], row['lat_wgs84']
        
        # [Stage 55] lon/lat이 숫자가 아닌 경우(변환 실패 등) 처리
        try:
            lon_f = float(lon)
            lat_f = float(lat)
            status = validator.classify(lon_f, lat_f)
        except (ValueError, TypeError):
            status = 'reject'
            
        results.append(status)
    
    merged['spatial_status'] = results
    
    # is_buffer_zone 태그 부착 (UI 시각화용)
    merged['is_buffer_zone'] = merged['spatial_status'] == 'soft'
    
    mask_normal = merged['spatial_status'].isin(['hard', 'soft'])
    normal_df = merged[mask_normal].copy()
    quarantine_df = merged[~mask_normal].copy()
    
    print(f"  [Geo-Fence] Normal(Hard/Soft): {len(normal_df)} rows, Quarantined(Reject): {len(quarantine_df)} rows")
    
    if not quarantine_df.empty:
        q_out = os.path.join(target_dir, '수원시_전체_격리_시추데이터.csv')
        quarantine_df.to_csv(q_out, index=False, encoding='utf-8-sig')
        print(f"  [Quarantine] Saved outliers to: {q_out}")
        
    merged = normal_df # 이후 저장은 정상 데이터만 진행

    # M3-2: Remove TM coordinates for consistency (Jangan/Paldal format unification)
    print("  [Standardize] Removing TM coordinate columns (tm_x, tm_y)...")
    merged = merged.drop(columns=[c for c in ['tm_x', 'tm_y'] if c in merged.columns])

    # M4: Save CSV to #2/data
    csv_out = os.path.join(target_dir, '수원시_전체_통합_시추데이터.csv')
    try:
        merged.to_csv(csv_out, index=False, encoding='utf-8-sig')
        print(f"  [Save] CSV (Cleaned): {csv_out}")
    except PermissionError:
        print(f"  [Error] Permission Denied. Close the file if it's open: {csv_out}")
        # Fallback to v2 if necessary
        csv_out_v2 = csv_out.replace(".csv", "_v2.csv")
        merged.to_csv(csv_out_v2, index=False, encoding='utf-8-sig')
        print(f"  [WARN] Saved CSV as: {csv_out_v2}")

    # M5: Save JSON to #2/data
    json_out = os.path.join(target_dir, '수원시_전체_통합_시추데이터.json')
    
    hierarchical_data = {
        "region": "수원시 전역",
        "total_districts": len(sources),
        "total_boreholes": int(merged['시추공명'].nunique()),
        "total_rows": int(len(merged)),
        "projects": []
    }
    
    # Hierarchical grouping
    for proj_name, proj_group in merged.groupby('프로젝트명', sort=False):
        project_entry = {
            "project_name": str(proj_name),
            "boreholes": []
        }
        for bh_id, bh_group in proj_group.groupby('시추공명', sort=False):
            first_row = bh_group.iloc[0]
            borehole_entry = {
                "bh_id": str(bh_id),
                "lon_wgs84": float(first_row['lon_wgs84']) if pd.notnull(first_row['lon_wgs84']) else None,
                "lat_wgs84": float(first_row['lat_wgs84']) if pd.notnull(first_row['lat_wgs84']) else None,
                "elevation": float(first_row['표고']) if pd.notnull(first_row['표고']) else None,
                "is_buffer_zone": bool(first_row['is_buffer_zone']), # [Stage 54]
                "spatial_status": str(first_row.get('spatial_status', 'unknown')),
                "meta_crs": str(first_row.get('meta_crs', 'N/A')),
                "layers": []
            }
            for _, row in bh_group.iterrows():
                borehole_entry["layers"].append({
                    "from": float(row['상심도']),
                    "to": float(row['하심도']),
                    "strata": str(row['지층명'])
                })
            project_entry["boreholes"].append(borehole_entry)
        hierarchical_data["projects"].append(project_entry)

    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump(hierarchical_data, f, ensure_ascii=False, indent=2)
    print(f"  [Save] JSON: {json_out}")

    # M6: Final Verification
    print("\n=== [M6] 최종 데이터 규격 검증 ===")
    
    # V1: Row count
    if len(merged) != (total_src_rows - diff):
        print("  [FAIL] V1: Row count mismatch.")
    else:
        print("  [PASS] V1: Row count integrity.")

    # V2: Columns
    required = ['프로젝트명', 'lon_wgs84', 'lat_wgs84', '표고', '시추공명', '상심도', '하심도', '지층명']
    missing_cols = [c for c in required if c not in merged.columns]
    if missing_cols:
        print(f"  [FAIL] V2: Missing columns: {missing_cols}")
    else:
        print("  [PASS] V2: All required columns present.")

    # V3: Coordinate range (Suwon)
    out_of_bounds = merged[
        (merged['lon_wgs84'] < 126.8) | (merged['lon_wgs84'] > 127.2) |
        (merged['lat_wgs84'] < 37.1) | (merged['lat_wgs84'] > 37.4)
    ]
    if not out_of_bounds.empty:
        print(f"  [WARN] V3: {len(out_of_bounds)} rows have coordinates outside Suwon boundary.")
    else:
        print("  [PASS] V3: All coordinates within Suwon boundary.")

    # V5: JSON consistency
    if hierarchical_data["total_rows"] != len(merged):
        print("  [FAIL] V5: JSON row count mismatch.")
    else:
        print("  [PASS] V5: JSON consistency.")

    print("\n[Done] 이관 작업 완료.")

if __name__ == "__main__":
    integrate()
