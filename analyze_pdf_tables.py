"""PDF 전체 페이지의 표 구조 상세 분석"""
import fitz

pdf_path = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.pdf"
doc = fitz.open(pdf_path)

print(f"Total pages: {len(doc)}\n")

for page_idx in range(len(doc)):
    page = doc[page_idx]
    tables = page.find_tables()
    
    if not tables.tables:
        print(f"Page {page_idx+1}: No tables")
        continue
        
    for t_idx, table in enumerate(tables.tables):
        data = table.extract()
        
        # Table 1 = 헤더(메타데이터), Table 2 = 지층 데이터
        if t_idx == 0:
            print(f"Page {page_idx+1} - Table 1 (Header/Meta) [{table.row_count}x{table.col_count}]:")
            for r_idx, row in enumerate(data):
                cleaned = []
                for c_idx, c in enumerate(row):
                    val = str(c).replace('\n', ' ').strip() if c else ''
                    cleaned.append(f"[{r_idx},{c_idx}]={val[:40]}")
                print(f"  {' | '.join(cleaned)}")
        elif t_idx == 1:
            print(f"Page {page_idx+1} - Table 2 (Strata Data) [{table.row_count}x{table.col_count}]:")
            # 관심 컬럼: 심도(col0), 표고(col1), 층두께(col2), 지층명(col4~5)
            for r_idx, row in enumerate(data[:5]):  # 처음 5행만
                col0 = str(row[0]).strip() if row[0] else ''
                col1 = str(row[1]).strip() if row[1] else ''
                col2 = str(row[2]).strip() if row[2] else ''
                col4 = str(row[4]).strip().replace('\n',' ') if len(row) > 4 and row[4] else ''
                col5 = str(row[5]).strip().replace('\n',' ')[:30] if len(row) > 5 and row[5] else ''
                print(f"  Row{r_idx}: depth={col0} | elev={col1} | thick={col2} | type={col4} | desc={col5}")
            if len(data) > 5:
                print(f"  ... ({len(data)-5} more rows)")
    print()

doc.close()
