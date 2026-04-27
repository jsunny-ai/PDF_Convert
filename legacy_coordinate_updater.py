import os
import pandas as pd
import re
from core.coordinate_transformer import normalize_coordinates

def update_legacy_csvs():
    target_dir = r"c:\antigravity\#1_2_PDF_CSV\data\03_final"
    targets = ["수원시권선구_hybrid.csv", "수원시장안구_hybrid.csv", "수원시팔달구_hybrid.csv"]
    
    for filename in targets:
        filepath = os.path.join(target_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        print(f"\n--- Processing: {filename} ---")
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        
        # We need lon_wgs84, lat_wgs84, tm_x, tm_y
        new_lons, new_lats, new_tm_xs, new_tm_ys = [], [], [], []
        
        swap_count = 0
        success_count = 0
        
        for idx, row in df.iterrows():
            lon_str, lat_str = str(row.get('경도', '')), str(row.get('위도', ''))
            
            try:
                x_val = float(re.sub(r'[^\d.]', '', lon_str.replace(',', '')))
                y_val = float(re.sub(r'[^\d.]', '', lat_str.replace(',', '')))
                if 33.0 <= x_val <= 39.0 and 124.0 <= y_val <= 132.0:
                    swap_count += 1
            except: pass

            lon, lat, tmx, tmy = normalize_coordinates(lon_str, lat_str, borehole_id=row.get('시추공명', 'Unnamed'))
            
            new_lons.append(lon)
            new_lats.append(lat)
            new_tm_xs.append(tmx)
            new_tm_ys.append(tmy)
            
            if lon != "":
                success_count += 1
        
        df['lon_wgs84'] = new_lons
        df['lat_wgs84'] = new_lats
        df['tm_x'] = new_tm_xs
        df['tm_y'] = new_tm_ys
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"[{filename}] 보정 완료: 총 {len(df)}행 (변환 성공: {success_count}행, 반전 보정: {swap_count}건)")

if __name__ == '__main__':
    update_legacy_csvs()
