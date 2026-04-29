import pandas as pd
import os
import json

def patch_paldal():
    csv_path = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구\수원시팔달구_통합_데이터_v2.csv'
    json_path = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시팔달구\수원시팔달구_통합_데이터_v2.json'
    prefix = "수원시팔달구_"

    print("=== 팔달구 프로젝트명 일괄 보정 시작 ===")

    # 1. Patch CSV
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        def update_name(name):
            name = str(name)
            if not name.startswith(prefix):
                return f"{prefix}{name}"
            return name
        
        df['프로젝트명'] = df['프로젝트명'].apply(update_name)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"  [OK] CSV patched and saved: {csv_path}")
        print(f"  [Sample] CSV Top 5: {df['프로젝트명'].unique()[:5].tolist()}")
    else:
        print(f"  [Error] CSV not found: {csv_path}")

    # 2. Patch JSON
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for project in data.get('projects', []):
            name = project.get('project_name', '')
            if not name.startswith(prefix):
                project['project_name'] = f"{prefix}{name}"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [OK] JSON patched and saved: {json_path}")
    else:
        print(f"  [Error] JSON not found: {json_path}")

    print("=== 보정 완료 ===")

if __name__ == "__main__":
    patch_paldal()
