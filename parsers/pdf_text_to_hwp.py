"""
PDF -> HWP 변환 (PyMuPDF 텍스트 추출 + Hancom COM으로 HWP 생성)
"""
import os
import fitz  # PyMuPDF
import win32com.client

def pdf_to_hwp_via_text(pdf_path, hwp_path):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found: {pdf_path}")
        return False

    # Step 1: Extract text from PDF
    print(f"[1/3] Extracting text from PDF...")
    doc = fitz.open(pdf_path)
    all_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        all_text.append(f"--- Page {page_num + 1} ---\n{text}")
    doc.close()
    
    full_text = "\n\n".join(all_text)
    print(f"  Extracted {len(full_text):,} characters from {len(all_text)} pages")

    # Step 2: Create HWP via Hancom COM
    print(f"[2/3] Creating HWP document...")
    hwp = None
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.XHwpWindows.Item(0).Visible = False
        try:
            hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
        except:
            pass

        # Create new document
        hwp.HAction.Run("FileNew")

        # Insert text
        print(f"[3/3] Inserting text into HWP...")
        
        # Use HAction to insert text line by line
        act = hwp.CreateAction("InsertText")
        pset = act.CreateSet()
        
        for line in full_text.split('\n'):
            act.GetDefault(pset)
            pset.SetItem("Text", line)
            act.Execute(pset)
            # Insert newline
            hwp.HAction.Run("BreakPara")
        
        # Save as HWP
        # Use temp path to avoid Korean path issues
        temp_hwp = r"C:\antigravity\#1_2_PDF_CSV\temp_output.hwp"
        
        save_act = hwp.HParameterSet.HFileOpenSave
        hwp.HAction.GetDefault("FileSaveAs_S", save_act.HSet)
        save_act.filename = temp_hwp
        save_act.Format = "HWP"
        result = hwp.HAction.Execute("FileSaveAs_S", save_act.HSet)
        
        if result or os.path.exists(temp_hwp):
            import shutil
            shutil.copy2(temp_hwp, hwp_path)
            os.remove(temp_hwp)
            size = os.path.getsize(hwp_path)
            print(f"\nSuccess! HWP saved to: {hwp_path}")
            print(f"File size: {size:,} bytes")
            return True
        else:
            print("Failed to save HWP file.")
            return False

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if hwp:
            try:
                hwp.Clear(1)
                hwp.Quit()
            except:
                pass

if __name__ == "__main__":
    pdf_file = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.pdf"
    hwp_file = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.hwp"
    pdf_to_hwp_via_text(pdf_file, hwp_file)
