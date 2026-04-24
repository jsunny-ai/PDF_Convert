import os
import re
import shutil
import json
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

# ==========================================
# 1. 파일 분석 및 처리 엔진 (FileOrganizer)
# ==========================================
class FileOrganizer:
    # 파일 시그니처 (Magic Numbers) 사전
    SIGNATURES = {
        b"%PDF-": ".pdf",
        b"PK\x03\x04": ".zip",
        b"\x89PNG\r\n\x1a\n": ".png",
        b"\xff\xd8\xff": ".jpg",
        b"GIF87a": ".gif",
        b"GIF89a": ".gif",
        b"BM": ".bmp",
        b"\xef\xbb\xbf": ".csv",  # UTF-8 BOM CSV
        b"ID3": ".mp3",
        b"\x00\x00\x00\x18ftyp": ".mp4",
        b"\x52\x49\x46\x46": ".wav",  # or .webp, .avi depending on sub-type
    }

    UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

    def __init__(self, target_dir):
        self.target_dir = target_dir
        self.logs = []
        self.log_file = os.path.join(target_dir, "uuid_cleanup_log.json")

    def detect_extension(self, file_path):
        """파일 헤더를 읽어 적절한 확장자 추론"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                for sig, ext in self.SIGNATURES.items():
                    if header.startswith(sig):
                        return ext
            return ".bin"  # 알 수 없는 경우 이진 파일로 간주
        except Exception:
            return ".bin"

    def scan_files(self):
        """대상 폴더 스캔 및 변경 예정 목록 반환"""
        if not os.path.isdir(self.target_dir):
            return []

        candidates = []
        for filename in os.listdir(self.target_dir):
            base, ext = os.path.splitext(filename)
            # 확장자가 없거나 UUID 패턴인 경우
            if self.UUID_REGEX.match(base):
                file_path = os.path.join(self.target_dir, filename)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    date_str = datetime.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')
                    inferred_ext = self.detect_extension(file_path)
                    
                    new_name = f"recovered_{date_str}_{base[:8]}{inferred_ext}"
                    candidates.append({
                        "original": filename,
                        "new": new_name,
                        "path": file_path,
                        "type": inferred_ext
                    })
        return candidates

    def execute_rename(self, candidates, progress_callback=None):
        """일괄 이름 변경 실행"""
        success_count = 0
        current_logs = []

        for i, item in enumerate(candidates):
            old_path = item['path']
            # 중복 방지 처리
            new_name = item['new']
            new_path = os.path.join(self.target_dir, new_name)
            
            counter = 1
            while os.path.exists(new_path):
                name_part, ext_part = os.path.splitext(new_name)
                new_path = os.path.join(self.target_dir, f"{name_part}_{counter}{ext_part}")
                counter += 1

            try:
                os.rename(old_path, new_path)
                current_logs.append({"old": item['original'], "new": os.path.basename(new_path)})
                success_count += 1
            except Exception as e:
                logging.error(f"Rename failed: {item['original']} -> {e}")

            if progress_callback:
                progress_callback(i + 1, len(candidates))

        # 로그 저장
        self.save_logs(current_logs)
        return success_count

    def save_logs(self, new_entries):
        history = []
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.append({
            "timestamp": datetime.now().isoformat(),
            "changes": new_entries
        })
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def undo_last(self):
        """마지막 작업 되돌리기"""
        if not os.path.exists(self.log_file):
            return 0

        with open(self.log_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        if not history:
            return 0

        last_session = history.pop()
        undo_count = 0
        
        for change in last_session['changes']:
            current_path = os.path.join(self.target_dir, change['new'])
            original_path = os.path.join(self.target_dir, change['old'])
            
            if os.path.exists(current_path) and not os.path.exists(original_path):
                os.rename(current_path, original_path)
                undo_count += 1

        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
            
        return undo_count

# ==========================================
# 2. GUI 인터페이스 (AppGUI)
# ==========================================
class UUIDCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UUID Cleaner - 파일 이름 및 확장자 복구 도구")
        self.root.geometry("800x600")
        
        self.target_dir = tk.StringVar()
        self.candidates = []
        self.organizer = None

        self.setup_ui()

    def setup_ui(self):
        # 상단: 폴더 선택
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="대상 폴더:").pack(side=tk.LEFT)
        ttk.Entry(top_frame, textvariable=self.target_dir, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="찾아보기", command=self.browse_folder).pack(side=tk.LEFT)

        # 중앙: 미리보기 목록
        mid_frame = ttk.Frame(self.root, padding="10")
        mid_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("original", "arrow", "new", "type")
        self.tree = ttk.Treeview(mid_frame, columns=columns, show="headings")
        self.tree.heading("original", text="현재 파일명 (UUID)")
        self.tree.heading("arrow", text="▶")
        self.tree.heading("new", text="복구 예정 파일명")
        self.tree.heading("type", text="추론 형식")
        
        self.tree.column("arrow", width=30, anchor=tk.CENTER)
        self.tree.column("type", width=80, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 하단: 컨트롤 및 상태
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)

        self.progress = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=5)

        ttk.Button(bottom_frame, text="스캔/미리보기", command=self.scan).pack(side=tk.RIGHT, padx=5)
        self.run_btn = ttk.Button(bottom_frame, text="일괄 처리 실행", command=self.run, state=tk.DISABLED)
        self.run_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="되돌리기 (Undo)", command=self.undo).pack(side=tk.RIGHT, padx=5)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.target_dir.set(folder)
            self.organizer = FileOrganizer(folder)
            self.scan()

    def scan(self):
        if not self.target_dir.get():
            messagebox.showwarning("경고", "먼저 폴더를 선택해주세요.")
            return

        self.organizer = FileOrganizer(self.target_dir.get())
        self.candidates = self.organizer.scan_files()
        
        # 트리 뷰 갱신
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        if not self.candidates:
            messagebox.showinfo("알림", "정리할 UUID 패턴의 파일을 찾지 못했습니다.")
            self.run_btn.config(state=tk.DISABLED)
            return

        for item in self.candidates:
            self.tree.insert("", tk.END, values=(item['original'], "→", item['new'], item['type']))
        
        self.run_btn.config(state=tk.NORMAL)
        self.progress['value'] = 0

    def run(self):
        if not self.candidates: return
        
        confirm = messagebox.askyesno("확인", f"{len(self.candidates)}개의 파일 이름을 변경하시겠습니까?\n이 작업은 나중에 되돌릴 수 있습니다.")
        if not confirm: return

        def update_progress(current, total):
            self.progress['value'] = (current / total) * 100
            self.root.update_idletasks()

        count = self.organizer.execute_rename(self.candidates, update_progress)
        messagebox.showinfo("완료", f"{count}개의 파일이 성공적으로 정리되었습니다.")
        self.scan()

    def undo(self):
        if not self.target_dir.get(): return
        
        confirm = messagebox.askyesno("Undo 확인", "가장 최근의 이름 변경 작업을 되돌리시겠습니까?")
        if not confirm: return

        count = self.organizer.undo_last()
        if count > 0:
            messagebox.showinfo("Undo 완료", f"{count}개의 파일이 이전 이름으로 복구되었습니다.")
            self.scan()
        else:
            messagebox.showwarning("실패", "되돌릴 작업 내역이 없거나 파일이 이동되었습니다.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    root = tk.Tk()
    app = UUIDCleanerApp(root)
    root.mainloop()
