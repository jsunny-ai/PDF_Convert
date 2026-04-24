import pandas as pd
import numpy as np
import re

file_path = r"C:\antigravity\#1_2_PDF_CSV\서울특별시_CSV_통합_최종_V2.csv"

def audit():
    print("--- Final Data Integrity Audit Report ---")
    
    try:
        df = pd.read_csv(file_path, encoding='cp949')
    except:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    total_rows = len(df)
    print(f"1. Total Records: {total_rows}")
    
    # [Check 1] NaN & N/A
    nan_elev = df['표고'].isna().sum()
    na_strings = (df.astype(str).apply(lambda x: x.str.upper()) == 'N/A').sum().sum()
    
    print(f"2. Missing Data Statistics:")
    print(f"   ㄴ NaN in Elevation: {nan_elev}")
    print(f"   ㄴ 'N/A' String count: {na_strings}")
    
    # [Check 2] Multi-Borehole Detection (ID Separation)
    # 한 프로젝트 내에 여러 시추공이 있는 케이스 추출
    project_bh_counts = df.groupby('프로젝트명')['시추공명'].nunique()
    multi_bh_projects = project_bh_counts[project_bh_counts > 1]
    print(f"3. Multi-Borehole Detection (ID separation):")
    print(f"   ㄴ Projects with multiple boreholes: {len(multi_bh_projects)}")
    
    # [Check 3] Zero (0.0) Integrity
    zero_elev = (df['표고'] == 0.0).sum()
    print(f"4. Value Integrity (0.0 preservation):")
    print(f"   ㄴ Elevation = 0.0 count: {zero_elev}")
    
    # [Detailed Check] Known problematic projects
    targets = ["PJ_8-10", "PJ_12-10", "PJ_249-2"]
    print(f"5. Target Project Verification:")
    for pj in targets:
        pj_data = df[df['프로젝트명'] == pj]
        if not pj_data.empty:
            p_na = pj_data['표고'].isna().sum()
            bh_list = pj_data['시추공명'].unique()
            print(f"   ㄴ {pj}: {len(bh_list)} boreholes found ({', '.join(bh_list)}), NaNs: {p_na}")
        else:
            print(f"   ㄴ {pj}: NOT FOUND")

if __name__ == "__main__":
    audit()
