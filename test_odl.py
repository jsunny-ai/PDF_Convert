import logging
import opendataloader_pdf
import traceback
import os
import sys

os.environ['PATH'] = r'C:\antigravity\#1_2_PDF_CSV\jdk_folder\jdk-21.0.2\bin;' + os.environ.get('PATH', '')

try:
    pdf_path = r'C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시장안구\page2_project2_report.pdf'
    if not os.path.exists(pdf_path):
        print("PDF Not Found.")
        sys.exit(1)
        
    opendataloader_pdf.convert(
        input_path=[pdf_path], 
        output_dir=r'C:\antigravity\#1_2_PDF_CSV\MD_Storage\Fallback_Ext', 
        format='markdown'
    )
    print("Success")
except Exception as e:
    traceback.print_exc()
