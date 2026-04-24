import traceback
try:
    import win32com.client
    print("pywin32 is installed")
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        print("Hancom Office is installed and accessible via COM")
    except Exception as e:
        print("Hancom Office is NOT accessible. Error:", e)
except Exception as e:
    print("pywin32 is NOT installed.", e)
