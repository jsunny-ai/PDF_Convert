import os
import sys
import platform
import shutil
import json
import logging
import subprocess
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import urllib.request
import psutil

# Windows 전용 라이브러리 (조건부 임포트)
if platform.system() == "Windows":
    import winreg
else:
    winreg = None

# ==========================================
# 1. 진단 엔진 (DiagnosticEngine)
# ==========================================
class DiagnosticEngine:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()

    def run_all_checks(self, progress_callback=None):
        checks = [
            ("시스템 기본 정보", self.check_system_info),
            ("디스크 및 파일 시스템", self.check_disk_status),
            ("브라우저 환경 분석", self.check_browser_envs),
            ("네트워크 및 프록시 설정", self.check_network),
            ("보안 소프트웨어 간섭", self.check_security_apps),
            ("Windows 레지스트리 (파일명 설정)", self.check_registry),
            ("임시 폴더 상태", self.check_temp_folders)
        ]
        
        total = len(checks)
        for i, (name, func) in enumerate(checks):
            logging.info(f"진단 중: {name}")
            try:
                func()
            except Exception as e:
                self.results[name] = {"status": "Error", "message": str(e)}
            
            if progress_callback:
                progress_callback(i + 1, total, name)

    def check_system_info(self):
        self.results["시스템 기본 정보"] = {
            "OS": f"{platform.system()} {platform.release()}",
            "Architecture": platform.machine(),
            "Python Version": sys.version.split()[0],
            "Status": "Pass"
        }

    def check_disk_status(self):
        downloads_path = os.path.expanduser("~/Downloads")
        usage = shutil.disk_usage(os.path.dirname(downloads_path))
        free_gb = usage.free / (1024**3)
        
        status = "Pass" if free_gb > 1 else "Warning"
        self.results["디스크 및 파일 시스템"] = {
            "Downloads 경로": downloads_path,
            "여유 공간": f"{free_gb:.2f} GB",
            "쓰기 권한": "정상" if os.access(downloads_path, os.W_OK) else "제한됨",
            "Status": status,
            "Recommendation": "여유 공간이 1GB 미만입니다. 디스크를 정리하세요." if status == "Warning" else "정상"
        }

    def check_browser_envs(self):
        # 크롬/파이어폭스 기본 경로 확인 및 설정 파일 분석 (간략화)
        browser_info = []
        user_data = os.environ.get('LOCALAPPDATA', '')
        paths = {
            "Chrome": os.path.join(user_data, "Google/Chrome/User Data/Default"),
            "Edge": os.path.join(user_data, "Microsoft/Edge/User Data/Default")
        }
        
        for name, path in paths.items():
            if os.path.exists(path):
                browser_info.append(f"{name}: 설치됨")
        
        self.results["브라우저 환경 분석"] = {
            "감지된 브라우저": ", ".join(browser_info) if browser_info else "없음",
            "Status": "Pass"
        }

    def check_network(self):
        proxies = urllib.request.getproxies()
        status = "Warning" if proxies else "Pass"
        self.results["네트워크 및 프록시 설정"] = {
            "프록시 사용": "예" if proxies else "아니오",
            "상세 내역": str(proxies),
            "Status": status,
            "Recommendation": "프록시가 설정되어 있습니다. 다운로드 파일 변조의 원인이 될 수 있습니다." if status == "Warning" else "정상"
        }

    def check_security_apps(self):
        security_list = ["v3", "alyac", "nprotect", "kaspersky", "mcafee", "avast", "defender"]
        detected = []
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower()
                for s in security_list:
                    if s in name:
                        detected.append(name)
            except: pass
        
        detected = list(set(detected))
        status = "Warning" if detected else "Pass"
        self.results["보안 소프트웨어 간섭"] = {
            "감지된 보안 앱": ", ".join(detected) if detected else "없음",
            "Status": status,
            "Recommendation": "보안 프로그램이 다운로드 파일을 즉시 격리하거나 이름을 변경할 수 있습니다." if status == "Warning" else "정상"
        }

    def check_registry(self):
        if not winreg:
            self.results["Windows 레지스트리 (파일명 설정)"] = {"Status": "Not Applicable", "message": "Windows가 아닙니다."}
            return

        # 다운로드 시 확장자 숨김 관련 옵션 체크
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced")
            value, _ = winreg.QueryValueEx(key, "HideFileExt")
            status = "Warning" if value == 1 else "Pass"
            self.results["Windows 레지스트리 (파일명 설정)"] = {
                "알려진 확장자 숨기기(HideFileExt)": "켜짐 (Warning)" if value == 1 else "꺼짐 (Pass)",
                "Status": status,
                "Recommendation": "확장자가 숨겨져 있어 파일이 손상된 것처럼 보일 수 있습니다." if status == "Warning" else "정상"
            }
        except:
            self.results["Windows 레지스트리 (파일명 설정)"] = {"Status": "Error", "message": "레지스트리에 접근할 수 없습니다."}

    def check_temp_folders(self):
        temp_dir = os.environ.get('TEMP', '')
        size = 0
        file_count = 0
        try:
            for f in os.listdir(temp_dir):
                fp = os.path.join(temp_dir, f)
                if os.path.isfile(fp):
                    size += os.path.getsize(fp)
                    file_count += 1
        except: pass
        
        status = "Warning" if size > 1024**3 else "Pass" # 1GB
        self.results["임시 폴더 상태"] = {
            "경로": temp_dir,
            "파일 수": f"{file_count}개",
            "총 용량": f"{size / (1024**2):.2f} MB",
            "Status": status,
            "Recommendation": "임시 폴더가 너무 큽니다. 다운로드 캐시 오류를 유발할 수 있으니 정리하십시오." if status == "Warning" else "정상"
        }

# ==========================================
# 2. 리포트 생성기 (ReportGenerator)
# ==========================================
class ReportGenerator:
    @staticmethod
    def generate_html(results, output_path):
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Download Inspector Report</title>
            <style>
                body { font-family: 'Malgun Gothic', sans-serif; padding: 40px; background: #f4f7f6; }
                .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
                .header { color: #4f46e5; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; }
                .status-Pass { color: #10b981; font-weight: bold; }
                .status-Warning { color: #f59e0b; font-weight: bold; }
                .status-Error { color: #ef4444; font-weight: bold; }
                table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
                .recommendation { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 10px; margin-top: 10px; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <h1 class="header">Download Inspector - 진단 결과 보고서</h1>
            <p>진단 생성 일시: {timestamp}</p>
            {content}
        </body>
        </html>
        """
        
        content = ""
        for name, data in results.items():
            status_class = f"status-{data.get('Status', 'Pass')}"
            rows = ""
            recommendation = data.get("Recommendation", "")
            
            for key, val in data.items():
                if key not in ["Status", "Recommendation"]:
                    rows += f"<tr><th>{key}</th><td>{val}</td></tr>"
            
            rec_div = f'<div class="recommendation">💡 <strong>가이드:</strong> {recommendation}</div>' if recommendation and recommendation != "정상" else ""
            
            content += f"""
            <div class="card">
                <h2>{name} <span class="{status_class}">[{data.get('Status', 'Pass')}]</span></h2>
                <table>{rows}</table>
                {rec_div}
            </div>
            """
        
        final_html = html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            content=content
        )
        
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(final_html)

# ==========================================
# 3. GUI 인터페이스 (InspectorGUI)
# ==========================================
class InspectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Download Inspector V1.0")
        self.root.geometry("700x550")
        self.engine = DiagnosticEngine()
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.configure("TButton", font=("Malgun Gothic", 10))
        
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="시스템 및 다운로드 환경 진단 도구", font=("Malgun Gothic", 16, "bold")).pack(pady=10)
        
        self.btn_start = ttk.Button(main_frame, text="종합 진단 시작", command=self.start_diagnosis)
        self.btn_start.pack(pady=10)

        # 상태 진행 표시
        self.progress_var = tk.DoubleVar()
        self.pb = ttk.Progressbar(main_frame, length=500, mode='determinate', variable=self.progress_var)
        self.pb.pack(pady=5)
        self.status_label = ttk.Label(main_frame, text="대기 중...")
        self.status_label.pack()

        # 진단 결과 요약 목록
        self.result_text = tk.Text(main_frame, height=15, width=80, font=("Consolas", 10))
        self.result_text.pack(pady=10)

        self.btn_report = ttk.Button(main_frame, text="HTML 보고서 열기", command=self.open_report, state="disabled")
        self.btn_report.pack(side=tk.RIGHT, padx=5)
        
        self.btn_fix = ttk.Button(main_frame, text="권장 설정 자동 수정 (Auto-Fix)", command=self.auto_fix, state="disabled")
        self.btn_fix.pack(side=tk.RIGHT, padx=5)

    def start_diagnosis(self):
        self.btn_start.config(state="disabled")
        self.result_text.delete(1.0, tk.END)
        
        def run():
            def callback(curr, total, name):
                self.progress_var.set((curr/total)*100)
                self.status_label.config(text=f"진단 중: {name} ({curr}/{total})")
                self.root.update_idletasks()

            self.engine.run_all_checks(callback)
            self.root.after(0, self.finish_diagnosis)

        threading.Thread(target=run).start()

    def finish_diagnosis(self):
        self.status_label.config(text="진단 완료!")
        self.btn_start.config(state="normal")
        self.btn_report.config(state="normal")
        self.btn_fix.config(state="normal")
        
        summary = "--- 진단 결과 요약 ---\n"
        for name, data in self.engine.results.items():
            status = data.get("Status", "N/A")
            summary += f"[{status}] {name}\n"
        
        self.result_text.insert(tk.END, summary)
        
        # 보고서 자동 생성
        ReportGenerator.generate_html(self.engine.results, "diagnostic_report.html")

    def open_report(self):
        path = os.path.abspath("diagnostic_report.html")
        webbrowser.open(f"file://{path}")

    def auto_fix(self):
        if not winreg: return
        
        confirm = messagebox.askyesno("확인", "Windows의 알려진 확장자 숨기기 옵션을 해제하고 권장 설정을 적용하시겠습니까?")
        if confirm:
            try:
                # 확장자 숨기기 해제
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "HideFileExt", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                
                messagebox.showinfo("성공", "권장 설정이 반영되었습니다. 탐색기를 재시작하거나 재부팅 후 확인하세요.")
            except Exception as e:
                messagebox.showerror("오류", f"설정 변경 중 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # CLI 모드
        engine = DiagnosticEngine()
        print("Starting System Diagnosis...")
        engine.run_all_checks(lambda c, t, n: print(f"[{c}/{t}] Checking {n}..."))
        ReportGenerator.generate_html(engine.results, "diagnostic_report.html")
        print("\nDiagnosis Complete. Report saved to diagnostic_report.html")
    else:
        root = tk.Tk()
        app = InspectorGUI(root)
        root.mainloop()
