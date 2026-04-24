"""다양한 PDF 파일의 표 구조 일관성 확인"""
import fitz
import os
import glob

base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
districts = os.listdir(base_dir)

for district in districts:
    d_path = os.path.join(base_dir, district)
    pdfs = glob.glob(os.path.join(d_path, "*.pdf"))
    # 각 구에서 3개 파일만 샘플링
    samples = pdfs[:3]
    
    for pdf_path in samples:
        fname = os.path.basename(pdf_path)
        doc = fitz.open(pdf_path)
        page = doc[0]  # 첫 페이지만
        tables = page.find_tables()
        
        summary = f"[{district}/{fname}] pages={len(doc)}, tables_on_p1={len(tables.tables)}"
        
        for t_idx, tbl in enumerate(tables.tables):
            data = tbl.extract()
            summary += f" | T{t_idx+1}({tbl.row_count}x{tbl.col_count})"
            
            # 헤더표에서 시추번호와 좌표 위치 확인
            if t_idx == 0 and tbl.row_count >= 2:
                bh_id = str(data[0][7]).strip() if len(data[0]) > 7 and data[0][7] else 'N/A'
                coords = str(data[1][5]).strip()[:50] if len(data[1]) > 5 and data[1][5] else 'N/A'
                elev = str(data[1][7]).strip() if len(data[1]) > 7 and data[1][7] else 'N/A'
                summary += f" BH={bh_id}, coords={coords}, elev={elev}"
        
        print(summary)
        doc.close()
    print()
