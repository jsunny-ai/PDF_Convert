import pandas as pd

df = pd.read_csv(
    r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구\수원시팔달구_통합_데이터.csv',
    encoding='utf-8-sig'
)

pj_rows = df[df['프로젝트명'].str.startswith('PJ_')]
non_pj_rows = df[~df['프로젝트명'].str.startswith('PJ_')]

print(f"Total rows: {len(df)}")
print(f"PJ_ rows: {len(pj_rows)} ({len(pj_rows)/len(df)*100:.1f}%)")
print(f"Non-PJ rows: {len(non_pj_rows)} ({len(non_pj_rows)/len(df)*100:.1f}%)")
print()

print("=== PJ_ unique values (sample 20) ===")
pj_unique = sorted(pj_rows['프로젝트명'].unique())
for p in pj_unique[:20]:
    cnt = len(pj_rows[pj_rows['프로젝트명']==p])
    print(f"  {p}: {cnt} rows")
print(f"  ... total {len(pj_unique)} unique PJ_ names")
print()

print("=== Non-PJ unique values (sample 20) ===")
non_pj_unique = sorted(non_pj_rows['프로젝트명'].unique())
for p in non_pj_unique[:20]:
    cnt = len(non_pj_rows[non_pj_rows['프로젝트명']==p])
    print(f"  {p}: {cnt} rows")
print(f"  ... total {len(non_pj_unique)} unique non-PJ names")
