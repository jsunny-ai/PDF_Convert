import os
import pandas as pd
from core.master_hybrid_extractor import MasterHybridExtractor

def rescue_gwonseon():
    root_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구"
    pdf_files = [f for f in os.listdir(root_dir) if f.lower().endswith('.pdf')]
    
    extractor = MasterHybridExtractor()
    all_rows = []
    
    for i, filename in enumerate(pdf_files, 1):
        pdf_path = os.path.join(root_dir, filename)
        project_name = f"수원시권선구_{os.path.splitext(filename)[0]}"
        print(f"[{i}/{len(pdf_files)}] Processing {filename}...")
        
        try:
            rows = extractor.process_file(pdf_path, project_name)
            if rows:
                all_rows.extend(rows)
        except Exception as e:
            print(f"  Error: {e}")
            
    if all_rows:
        df = pd.DataFrame(all_rows)
        # 컬럼 보존!!
        output_path = os.path.join(root_dir, "수원시권선구_통합_데이터.csv")
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"Saved {len(df)} rows to {output_path}")

if __name__ == "__main__":
    rescue_gwonseon()
