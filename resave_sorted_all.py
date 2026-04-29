import pandas as pd
import os
import json
import re
from parsers.pdf_parser_odl import natural_sort_key

def migrate_district(csv_path):
    print(f"\n[Processing] {csv_path}")
    if not os.path.exists(csv_path):
        print(f"  ❌ File not found: {csv_path}")
        return

    # 1. Load CSV
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception as e:
        print(f"  ❌ Error loading CSV: {e}")
        return

    orig_len = len(df)
    
    # 2. Natural Sort
    if '프로젝트명' in df.columns and '시추공명' in df.columns:
        df['프로젝트명'] = df['프로젝트명'].astype(str)
        df['시추공명'] = df['시추공명'].astype(str)
        
        # Sort by Proj -> BH -> Depth
        df = df.sort_values(
            by=['프로젝트명', '시추공명', '상심도'],
            key=lambda x: x.map(natural_sort_key) if x.name != '상심도' else x
        )
    
    # Validation: Row count must be the same
    if len(df) != orig_len:
        print(f"  ❌ CRITICAL: Row count changed ({orig_len} -> {len(df)}). Aborting.")
        return

    # 3. Resave CSV (Overwrite)
    try:
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"  [OK] CSV Resaved: {csv_path}")
    except PermissionError:
        new_csv = csv_path.replace(".csv", "_sorted.csv")
        df.to_csv(new_csv, index=False, encoding='utf-8-sig')
        print(f"  [WARN] CSV Saved as {new_csv} due to PermissionError")

    # 4. Generate Hierarchical JSON
    json_path = csv_path.replace(".csv", ".json")
    
    hierarchical_data = {
        "district": os.path.basename(csv_path).split('_')[0],
        "total_boreholes": int(df['시추공명'].nunique()),
        "total_rows": int(len(df)),
        "projects": []
    }
    
    # Grouping logic
    for proj_name, proj_group in df.groupby('프로젝트명', sort=False):
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
        
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(hierarchical_data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] JSON Created: {json_path}")

    # Sample Print for Verification
    print(f"  [DEBUG] Top 5 BHs after sorting: {df['시추공명'].unique()[:5].tolist()}")

def main():
    root = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시'
    targets = [
        os.path.join(root, '수원시권선구', '수원시권선구_통합_데이터.csv'),
        os.path.join(root, '수원시장안구', '수원시장안구_통합_데이터.csv'),
        os.path.join(root, '수원시팔달구', '수원시팔달구_통합_데이터_v2.csv')
    ]
    
    for target in targets:
        migrate_district(target)

if __name__ == "__main__":
    main()
