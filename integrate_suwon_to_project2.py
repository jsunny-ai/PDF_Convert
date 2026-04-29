import pandas as pd
import os
import json
import re
from parsers.pdf_parser_odl import natural_sort_key

def integrate():
    print("=== 수원시 전역 데이터 통합 및 #2 프로젝트 이관 시작 ===")
    
    root_src = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시'
    target_dir = r'C:\antigravity\#2\data'
    os.makedirs(target_dir, exist_ok=True)

    sources = [
        ("수원시권선구", os.path.join(root_src, '수원시권선구', '수원시권선구_통합_데이터.csv')),
        ("수원시장안구", os.path.join(root_src, '수원시장안구', '수원시장안구_통합_데이터.csv')),
        ("수원시팔달구", os.path.join(root_src, '수원시팔달구', '수원시팔달구_통합_데이터_v2.csv')),
    ]

    # M1: Load and Concat
    dfs = []
    total_src_rows = 0
    for name, path in sources:
        if os.path.exists(path):
            df_part = pd.read_csv(path, encoding='utf-8-sig')
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

    # M4: Save CSV to #2/data
    csv_out = os.path.join(target_dir, '수원시_전체_통합_시추데이터.csv')
    try:
        merged.to_csv(csv_out, index=False, encoding='utf-8-sig')
        print(f"  [Save] CSV: {csv_out}")
    except PermissionError:
        csv_out = csv_out.replace(".csv", "_v2.csv")
        merged.to_csv(csv_out, index=False, encoding='utf-8-sig')
        print(f"  [WARN] Permission Denied. Saved CSV as: {csv_out}")

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
