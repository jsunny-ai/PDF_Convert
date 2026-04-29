import pandas as pd

# 기존
df_old = pd.read_csv(r'C:\antigravity\#1_2_PDF_CSV\data\03_final\수원시팔달구_hybrid.csv', encoding='utf-8-sig')
# 신규
df_new = pd.read_csv(r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구\수원시팔달구_통합_데이터.csv', encoding='utf-8-sig')

print("=== OLD FILE ===")
print(f"Rows: {len(df_old)}")
print(f"Cols: {list(df_old.columns)}")
print(f"Unique projects: {df_old['프로젝트명'].nunique()}")
print()

print("=== NEW FILE ===")
print(f"Rows: {len(df_new)}")
print(f"Cols: {list(df_new.columns)}")
print(f"Unique projects: {df_new['프로젝트명'].nunique()}")
print()

# Project name normalization for comparison
# Old: 수원시팔달구_page1_project1_report -> strip prefix
def strip_prefix(name):
    if name.startswith("수원시팔달구_"):
        return name[len("수원시팔달구_"):]
    return name

df_old['proj_key'] = df_old['프로젝트명'].apply(strip_prefix)
df_new['proj_key'] = df_new['프로젝트명']

old_projects = set(df_old['proj_key'].unique())
new_projects = set(df_new['proj_key'].unique())
print(f"Old-only projects: {len(old_projects - new_projects)}")
print(f"New-only projects: {len(new_projects - old_projects)}")
print(f"Common projects: {len(old_projects & new_projects)}")
print()

# Row count comparison for common projects (top 15 by diff)
print("=== ROW COUNT DIFF (common projects, top 15) ===")
common = old_projects & new_projects
diffs = []
for p in common:
    old_cnt = len(df_old[df_old['proj_key']==p])
    new_cnt = len(df_new[df_new['proj_key']==p])
    diffs.append((p, old_cnt, new_cnt, old_cnt - new_cnt))
diffs.sort(key=lambda x: -abs(x[3]))
for p, o, n, d in diffs[:15]:
    print(f"  {p}: old={o}, new={n}, diff={d}")
print()

# Old-only projects (top 20)
print("=== OLD-ONLY PROJECTS (sample 20) ===")
old_only = sorted(list(old_projects - new_projects))[:20]
for p in old_only:
    cnt = len(df_old[df_old['proj_key']==p])
    print(f"  {p}: {cnt} rows")
print()

# BH count per project (sample)
print("=== BH COUNT PER PROJECT (sample 5 common) ===")
sample_common = sorted(list(common))[:5]
for p in sample_common:
    old_bh = df_old[df_old['proj_key']==p]['시추공명'].nunique()
    new_bh = df_new[df_new['proj_key']==p]['시추공명'].nunique()
    print(f"  {p}: old_BH={old_bh}, new_BH={new_bh}")

# Detailed comparison for one project
print()
print("=== DETAIL: page1_project1_report ===")
old_p1 = df_old[df_old['proj_key']=='page1_project1_report']
new_p1 = df_new[df_new['proj_key']=='page1_project1_report']
print(f"Old rows: {len(old_p1)}, BHs: {sorted(old_p1['시추공명'].unique())}")
print(f"New rows: {len(new_p1)}, BHs: {sorted(new_p1['시추공명'].unique())}")
print()
for bh in sorted(old_p1['시추공명'].unique()):
    old_bh_data = old_p1[old_p1['시추공명']==bh][['상심도','하심도','지층명']].values.tolist()
    new_bh_data = new_p1[new_p1['시추공명']==bh][['상심도','하심도','지층명']].values.tolist() if bh in new_p1['시추공명'].values else []
    print(f"  {bh}: old={old_bh_data}")
    print(f"  {bh}: new={new_bh_data}")
