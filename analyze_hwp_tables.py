"""HWP 파일 내부 표(Table) 구조 분석 스크립트"""
import win32com.client

hwp_path = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page1_project1_report.hwp"

hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
hwp.XHwpWindows.Item(0).Visible = False
try:
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
except:
    pass

hwp.Open(hwp_path)

# 문서 전체 컨트롤(표 포함) 탐색
ctrl = hwp.HeadCtrl
table_idx = 0

while ctrl:
    if ctrl.CtrlID == "tbl":
        table_idx += 1
        tbl = ctrl.GetAncestorSet(0)
        # 표의 행/열 정보
        rows = ctrl.RowCount if hasattr(ctrl, 'RowCount') else "N/A"
        cols = ctrl.ColCount if hasattr(ctrl, 'ColCount') else "N/A"
        print(f"\n=== Table {table_idx} (Rows={rows}, Cols={cols}) ===")
        
        # 셀 순회
        try:
            cell_list = ctrl.CellList
            if cell_list:
                for ci in range(cell_list.Count):
                    cell = cell_list.Item(ci)
                    addr = cell.Addr if hasattr(cell, 'Addr') else f"Cell_{ci}"
                    print(f"  [{addr}] = (cell index {ci})")
        except:
            pass
    ctrl = ctrl.Next

print(f"\nTotal tables found: {table_idx}")

hwp.Clear(1)
hwp.Quit()
