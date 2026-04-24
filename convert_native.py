from pdf2docx import parse
import os

pdf_file = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.pdf"
hwp_file = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report_converted.docx"

try:
    print(f"Converting {pdf_file} to Word (DOCX) which is compatible with Hancom...")
    parse(pdf_file, hwp_file)
    print(f"Successfully created: {hwp_file}")
except Exception as e:
    print(f"Error during conversion: {e}")
