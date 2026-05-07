# -*- coding: utf-8 -*-
"""공간 이상치 전수 추출 스크립트"""
import pandas as pd

CSV_PATH = r'c:\antigravity\#2\data\수원시_전체_통합_시추데이터.csv'

# 수원시 Bounding Box (요청서 기준)
LON_MIN, LON_MAX = 126.91, 127.10
LAT_MIN, LAT_MAX = 37.22, 37.33

df = pd.read_csv(CSV_PATH, encoding='utf-8')
print(f"[INFO] Total rows: {len(df)}")
print(f"[INFO] Columns: {list(df.columns)}")

# 고유 시추공 좌표 추출 (첫 행 기준)
unique = df.drop_duplicates(subset=['시추공명'], keep='first')
print(f"[INFO] Unique boreholes: {len(unique)}")

# 전체 좌표 범위
print(f"\n[RANGE] lon_wgs84: {df['lon_wgs84'].min():.6f} ~ {df['lon_wgs84'].max():.6f}")
print(f"[RANGE] lat_wgs84: {df['lat_wgs84'].min():.6f} ~ {df['lat_wgs84'].max():.6f}")

# 이상치 추출
mask = (
    (unique['lon_wgs84'] < LON_MIN) |
    (unique['lon_wgs84'] > LON_MAX) |
    (unique['lat_wgs84'] < LAT_MIN) |
    (unique['lat_wgs84'] > LAT_MAX)
)
outliers = unique[mask].copy()
print(f"\n[OUTLIER] Count: {len(outliers)} / {len(unique)} boreholes")

# 이상치 분류
cat1 = outliers[outliers['lon_wgs84'] < 126.0]
cat2 = outliers[(outliers['lat_wgs84'] < LAT_MIN) & (outliers['lon_wgs84'] >= 126.0)]
cat3 = outliers[(outliers['lon_wgs84'] > LON_MAX) | (outliers['lat_wgs84'] > LAT_MAX)]
# cat3 중 cat2와 겹치지 않는 것만
cat3 = cat3[~cat3.index.isin(cat1.index) & ~cat3.index.isin(cat2.index)]

print(f"\n[CAT1] TM 변환 실패 (lon < 126): {len(cat1)}")
print(f"[CAT2] 남측 경계 밖 (lat < {LAT_MIN}): {len(cat2)}")
print(f"[CAT3] 북/동 경계 밖 또는 타지역: {len(cat3)}")

# 전수 리스트 출력
print("\n" + "="*120)
print("CAT1: TM 변환 실패 (lon < 126)")
print("="*120)
print(f"{'시추공명':<15} {'lon_wgs84':>12} {'lat_wgs84':>12} {'tm_x':>15} {'tm_y':>15} {'프로젝트명'}")
print("-"*120)
for _, r in cat1.iterrows():
    tm_x = r.get('tm_x', '')
    tm_y = r.get('tm_y', '')
    print(f"{r['시추공명']:<15} {r['lon_wgs84']:>12.6f} {r['lat_wgs84']:>12.6f} {str(tm_x):>15} {str(tm_y):>15} {r['프로젝트명']}")

print("\n" + "="*120)
print("CAT2: 남측 경계 밖 (lat < 37.22)")
print("="*120)
print(f"{'시추공명':<15} {'lon_wgs84':>12} {'lat_wgs84':>12} {'tm_x':>15} {'tm_y':>15} {'프로젝트명'}")
print("-"*120)
for _, r in cat2.iterrows():
    tm_x = r.get('tm_x', '')
    tm_y = r.get('tm_y', '')
    print(f"{r['시추공명']:<15} {r['lon_wgs84']:>12.6f} {r['lat_wgs84']:>12.6f} {str(tm_x):>15} {str(tm_y):>15} {r['프로젝트명']}")

print("\n" + "="*120)
print("CAT3: 북/동 경계 밖 또는 타지역")
print("="*120)
print(f"{'시추공명':<15} {'lon_wgs84':>12} {'lat_wgs84':>12} {'tm_x':>15} {'tm_y':>15} {'프로젝트명'}")
print("-"*120)
for _, r in cat3.iterrows():
    tm_x = r.get('tm_x', '')
    tm_y = r.get('tm_y', '')
    print(f"{r['시추공명']:<15} {r['lon_wgs84']:>12.6f} {r['lat_wgs84']:>12.6f} {str(tm_x):>15} {str(tm_y):>15} {r['프로젝트명']}")

# TM 좌표 분석 (Cat1)
print("\n" + "="*120)
print("CAT1 TM 좌표 상세 분석")
print("="*120)
for _, r in cat1.iterrows():
    tm_x = r.get('tm_x', None)
    tm_y = r.get('tm_y', None)
    analysis = ""
    if pd.notna(tm_x):
        if tm_x < 100000:
            analysis = f"tm_x={tm_x:.3f} → 자릿수 부족 (정상: 197000~200000). 10x = {tm_x*10:.3f}"
        else:
            analysis = f"tm_x={tm_x:.3f} → 정상 범위"
    else:
        analysis = "tm_x 없음"
    print(f"{r['시추공명']:<15} {analysis}")

# 정상 범위 내 데이터 통계
normal = unique[~mask]
print(f"\n[NORMAL] 정상 범위 시추공: {len(normal)} / {len(unique)} ({len(normal)/len(unique)*100:.1f}%)")
print(f"[NORMAL] lon: {normal['lon_wgs84'].min():.6f} ~ {normal['lon_wgs84'].max():.6f}")
print(f"[NORMAL] lat: {normal['lat_wgs84'].min():.6f} ~ {normal['lat_wgs84'].max():.6f}")
