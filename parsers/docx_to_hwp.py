import os
import shutil
import win32com.client

def convert_docx_to_hwp():
    src_docx = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report_converted.docx"
    final_hwp = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.hwp"
    
    # Copy to temp path without Korean characters
    temp_dir = r"C:\antigravity\#1_2_PDF_CSV\temp_convert"
    os.makedirs(temp_dir, exist_ok=True)
    temp_docx = os.path.join(temp_dir, "input.docx")
    temp_hwp = os.path.join(temp_dir, "output.hwp")
    
    shutil.copy2(src_docx, temp_docx)
    print(f"Copied DOCX to: {temp_docx}")
    print(f"File size: {os.path.getsize(temp_docx):,} bytes")

    hwp = None
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.XHwpWindows.Item(0).Visible = False
        try:
            hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
        except:
            pass

        # Try multiple approaches
        methods = [
            ("Open(path)", lambda: hwp.Open(temp_docx)),
            ("Open(path, DOCX)", lambda: hwp.Open(temp_docx, "DOCX", "")),
            ("Open(path, MS-WORD)", lambda: hwp.Open(temp_docx, "MS-WORD", "")),
            ("Open(path, empty, forceopen)", lambda: hwp.Open(temp_docx, "", "forceopen:true")),
        ]
        
        for name, method in methods:
            try:
                result = method()
                print(f"  {name}: result={result}")
                if result:
                    hwp.SaveAs(temp_hwp, "HWP", "")
                    shutil.copy2(temp_hwp, final_hwp)
                    print(f"\nSuccess! HWP saved to: {final_hwp}")
                    print(f"HWP file size: {os.path.getsize(final_hwp):,} bytes")
                    return True
            except Exception as e:
                print(f"  {name}: ERROR - {e}")
        
        # Try HAction method
        try:
            pset = hwp.HParameterSet.HFileOpenSave
            hwp.HAction.GetDefault("FileOpen", pset.HSet)
            pset.filename = temp_docx
            pset.Format = "DOCX"
            result = hwp.HAction.Execute("FileOpen", pset.HSet)
            print(f"  HAction(DOCX): result={result}")
            if result:
                pset2 = hwp.HParameterSet.HFileOpenSave
                hwp.HAction.GetDefault("FileSaveAs_S", pset2.HSet)
                pset2.filename = temp_hwp
                pset2.Format = "HWP"
                hwp.HAction.Execute("FileSaveAs_S", pset2.HSet)
                shutil.copy2(temp_hwp, final_hwp)
                print(f"\nSuccess! HWP saved to: {final_hwp}")
                return True
        except Exception as e:
            print(f"  HAction(DOCX): ERROR - {e}")

        print("\nAll methods failed to open DOCX in Hancom.")
        return False

    except Exception as e:
        print(f"General error: {e}")
        return False
    finally:
        if hwp:
            try:
                hwp.Clear(1)
                hwp.Quit()
            except:
                pass
        # Cleanup temp
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

if __name__ == "__main__":
    convert_docx_to_hwp()
