"""Stage 46 단일 파일 테스트"""
import json
from hwp_indexed_extractor import process_single_pdf_indexed

pdf_path = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.pdf"

print(f"Testing: {pdf_path}\n")
rows = process_single_pdf_indexed(pdf_path)

print(f"\n{'='*60}")
print(f"Total rows: {len(rows)}")
print(f"{'='*60}")

# 시추공별 요약
bh_ids = set(r['시추공명'] for r in rows)
for bh_id in sorted(bh_ids):
    bh_rows = [r for r in rows if r['시추공명'] == bh_id]
    print(f"\n[{bh_id}] {len(bh_rows)} layers")
    print(f"  경도={bh_rows[0]['경도']}, 위도={bh_rows[0]['위도']}, 표고={bh_rows[0]['표고']}")
    for r in bh_rows:
        print(f"  {r['상심도']} ~ {r['하심도']}m : {r['지층명']}")

# N/A 체크
na_rows = [r for r in rows if any(v == "N/A" for v in r.values())]
print(f"\nN/A rows: {len(na_rows)}")
