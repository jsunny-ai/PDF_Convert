import pandas as pd
import os

districts = ['수원시권선구', '수원시장안구']
root = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시'

print("=== 수원시 대규모 배치 전환 결과 보고 ===")
for d in districts:
    path = os.path.join(root, d, f"{d}_통합_데이터.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, encoding='utf-8-sig')
        print(f"[{d}]")
        print(f"  - 추출된 전체 행: {len(df)}행")
        print(f"  - 추출된 시추공(BH) 수: {df['시추공명'].nunique()}개")
        print(f"  - 저장 위치: {path}")
    else:
        print(f"[{d}] 파일을 찾을 수 없습니다.")
    print("-" * 30)
