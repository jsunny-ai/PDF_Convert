import pandas as pd

df = pd.read_csv(
    r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구\수원시팔달구_통합_데이터_v2.csv',
    encoding='utf-8-sig'
)

pj_rows = df[df['프로젝트명'].str.contains('PJ_', na=False)]
total_rows = len(df)
unique_projects = df['프로젝트명'].unique()

print(f"Total rows: {total_rows}")
print(f"PJ_ rows: {len(pj_rows)} (Target: 0)")
print(f"Unique projects: {len(unique_projects)}")
print()
print("=== Project Name Samples ===")
for p in unique_projects[:10]:
    print(f"  - {p}")

if len(pj_rows) == 0:
    print("\n✅ SUCCESS: No PJ_ dummy names found!")
else:
    print(f"\n❌ FAILURE: {len(pj_rows)} rows still contain PJ_")
