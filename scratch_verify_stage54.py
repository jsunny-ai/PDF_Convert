import pandas as pd
import os

path = r'c:\antigravity\#2\data\수원시_전체_통합_시추데이터.csv'
if not os.path.exists(path):
    # Try v2
    path = r'c:\antigravity\#2\data\수원시_전체_통합_시추데이터_v2.csv'

df = pd.read_csv(path, encoding='utf-8-sig')
print(f"Total Rows: {len(df)}")
if 'is_buffer_zone' in df.columns:
    buffer_rows = df[df['is_buffer_zone'] == True]
    print(f"Buffer Zone Rows: {len(buffer_rows)}")
    unique_buffer_bh = buffer_rows['시추공명'].nunique()
    print(f"Rescued Boreholes (Buffer Zone): {unique_buffer_bh}")
else:
    print("Column 'is_buffer_zone' NOT found.")

unique_bh = df['시추공명'].nunique()
print(f"Total Unique Boreholes: {unique_bh}")

# Check quarantined
q_path = r'c:\antigravity\#2\data\수원시_전체_격리_시추데이터.csv'
if os.path.exists(q_path):
    q_df = pd.read_csv(q_path)
    print(f"Quarantined Rows: {len(q_df)}")
    print(f"Quarantined Unique Boreholes: {q_df['시추공명'].nunique()}")
