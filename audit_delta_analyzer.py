import pandas as pd
import numpy as np
import os
import re
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 6371000 for meters
    return c * r * 1000 # returns meters

def normalize_proj_name(name):
    if not isinstance(name, str): return ""
    # Remove district prefix if exists
    name = re.sub(r'^수원시팔달구_', '', name)
    return name

def normalize_bh_id(bh_id):
    if not isinstance(bh_id, str): return ""
    # Standardize BH IDs (remove hyphens, spaces, uppercase)
    return re.sub(r'[^A-Z0-9]', '', bh_id.upper())

def map_to_4_tiers(strata):
    if not isinstance(strata, str): return "토사"
    s = strata.strip()
    if any(k in s for k in ['매립', '퇴적', '풍화토', '토사']):
        return "토사"
    if '풍화암' in s:
        return "풍화암"
    if any(k in s for k in ['연암', '리핑암']):
        return "연암"
    if any(k in s for k in ['보통암', '경암', '발파암', '화강암']):
        return "경암"
    return "토사" # Default

def run_audit():
    old_path = r'c:\antigravity\#1_2_PDF_CSV\data\03_final\수원시팔달구_hybrid.csv'
    new_path = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구\수원시팔달구_통합_데이터_v2.csv'

    print("=== Stage 52: 데이터 정합성 교차 검증 및 오차율 분석 ===\n")

    # Load data
    try:
        df_old = pd.read_csv(old_path, encoding='utf-8-sig')
        df_new = pd.read_csv(new_path, encoding='utf-8-sig')
    except Exception as e:
        print(f"Error loading CSVs: {e}")
        return

    # 0. Basic Preprocessing
    df_old['proj_norm'] = df_old['프로젝트명'].apply(normalize_proj_name)
    df_new['proj_norm'] = df_new['프로젝트명'].apply(normalize_proj_name)
    
    df_old['bh_norm'] = df_old['시추공명'].apply(normalize_bh_id)
    df_new['bh_norm'] = df_new['시추공명'].apply(normalize_bh_id)

    # 1. 시추공(Borehole ID) 잔존율 및 누락 분석
    old_bh_set = set(zip(df_old['proj_norm'], df_old['bh_norm']))
    new_bh_set = set(zip(df_new['proj_norm'], df_new['bh_norm']))
    
    common_bh = old_bh_set.intersection(new_bh_set)
    missing_bh = old_bh_set - new_bh_set
    new_only_bh = new_bh_set - old_bh_set

    survival_rate = (len(common_bh) / len(old_bh_set)) * 100 if old_bh_set else 0
    
    print(f"1. 시추공(Borehole ID) 잔존율 및 누락 분석")
    print(f"   - 기존 시추공 수: {len(old_bh_set)}")
    print(f"   - 신규 시추공 수: {len(new_bh_set)} (신규 추가: {len(new_only_bh)})")
    print(f"   - 시추공 잔존율: {survival_rate:.2f}%")
    print(f"   - 누락된 시추공 수: {len(missing_bh)}")
    if missing_bh:
        sample_missing = list(missing_bh)[:10]
        print(f"   - 누락 시취공 샘플: {sample_missing}")
    print()

    # 2. 심도(Depth) 및 지층 분류 오차율
    # Aggregate thickness by 4 tiers for each BH
    df_old['tier4'] = df_old['지층명'].apply(map_to_4_tiers)
    df_new['tier4'] = df_new['지층명'].apply(map_to_4_tiers)
    
    # Calculate thickness
    df_old['thickness'] = df_old['하심도'] - df_old['상심도']
    df_new['thickness'] = df_new['하심도'] - df_new['상심도']

    # Group by (proj, bh)
    old_depths = df_old.groupby(['proj_norm', 'bh_norm'])['thickness'].sum().reset_index()
    new_depths = df_new.groupby(['proj_norm', 'bh_norm'])['thickness'].sum().reset_index()

    depth_merge = pd.merge(old_depths, new_depths, on=['proj_norm', 'bh_norm'], suffixes=('_old', '_new'))
    depth_merge['delta'] = abs(depth_merge['thickness_old'] - depth_merge['thickness_new'])
    
    error_1m_plus = depth_merge[depth_merge['delta'] >= 1.0]
    error_rate = (len(error_1m_plus) / len(depth_merge)) * 100 if not depth_merge.empty else 0

    print(f"2. 심도(Depth) 및 지층 분류 오차율")
    print(f"   - 대조 대상 시추공 수: {len(depth_merge)}")
    print(f"   - 심도 오차 1.0m 이상 발생 시추공 수: {len(error_1m_plus)}")
    print(f"   - 심도 오차율 (1.0m+): {error_rate:.2f}%")
    print(f"   - 평균 심도 오차: {depth_merge['delta'].mean():.3f}m")
    print()

    # 3. 공간 좌표(WGS84) 정합성
    # Get one coordinate per BH (assuming same for all rows of a BH)
    old_coords = df_old.groupby(['proj_norm', 'bh_norm'])[['lon_wgs84', 'lat_wgs84']].first().reset_index()
    new_coords = df_new.groupby(['proj_norm', 'bh_norm'])[['lon_wgs84', 'lat_wgs84']].first().reset_index()

    coord_merge = pd.merge(old_coords, new_coords, on=['proj_norm', 'bh_norm'], suffixes=('_old', '_new'))
    
    # Filter out N/A coordinates
    coord_merge = coord_merge.dropna(subset=['lon_wgs84_old', 'lat_wgs84_old', 'lon_wgs84_new', 'lat_wgs84_new'])
    
    if not coord_merge.empty:
        coord_merge['dist_err'] = coord_merge.apply(
            lambda x: haversine(x['lon_wgs84_old'], x['lat_wgs84_old'], x['lon_wgs84_new'], x['lat_wgs84_new']), 
            axis=1
        )
        avg_dist = coord_merge['dist_err'].mean()
        max_dist = coord_merge['dist_err'].max()
        
        print(f"3. 공간 좌표(WGS84) 정합성")
        print(f"   - 좌표 비교 가능 시추공 수: {len(coord_merge)}")
        print(f"   - 평균 좌표 거리 오차: {avg_dist:.4f}m")
        print(f"   - 최대 좌표 거리 오차: {max_dist:.4f}m")
        
        print("\n=== [DEBUG] 오차 극심 시추공 샘플 (Top 5) ===")
        high_err = coord_merge.sort_values('dist_err', ascending=False).head(5)
        for _, r in high_err.iterrows():
            print(f"  [{r['proj_norm']} / {r['bh_norm']}] DistErr: {r['dist_err']:.1f}m")
            print(f"    - Old: ({r['lon_wgs84_old']}, {r['lat_wgs84_old']})")
            print(f"    - New: ({r['lon_wgs84_new']}, {r['lat_wgs84_new']})")
    else:
        print(f"3. 공간 좌표(WGS84) 정합성")
        print(f"   - 비교 가능한 유효 좌표 데이터가 없습니다.")

    print("\n" + "="*60)
    print("분석 완료")

if __name__ == "__main__":
    run_audit()
