import os
import sys
import win32com.client

def convert_pdf_to_hwp(pdf_path, hwp_path):
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        sys.exit(1)
        
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        # Hide GUI
        hwp.XHwpWindows.Item(0).Visible = False
        
        # Suppress dialogs natively if possible
        hwp.SetMessageBoxMode(0x20) # 0x20 = no message boxes
        
        # Security bypass (if registered)
        hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
        
        # Try opening PDF
        print(f"Attempting to open PDF: {pdf_path}")
        success = hwp.Open(pdf_path, "PDF", "")
        
        if not success:
            print("Direct PDF open failed, attempting default Open...")
            success = hwp.Open(pdf_path)
            
        if not success:
            print("Failed to open PDF in Hancom Office.")
        else:
            print(f"Opened successfully. Saving as HWP: {hwp_path}")
            # Save as HWP
            hwp.SaveAs(hwp_path, "HWP", "")
            print("Success!")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            hwp.Clear(1) # discard changes
            hwp.Quit()
        except:
            pass

if __name__ == "__main__":
    pdf_file = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.pdf"
    hwp_file = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.hwp"
    convert_pdf_to_hwp(pdf_file, hwp_file)
