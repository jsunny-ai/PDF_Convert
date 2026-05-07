import os
import shutil
import glob
import time
import logging
from run_suwon_batch_all import main as run_batch_main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def create_backup_and_move_files():
    # 1. 대상 디렉토리 설정
    work_dir = r"C:\antigravity\#1_2_PDF_CSV"
    pdf_storage_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시"
    
    backup_dir = os.path.join(work_dir, "backup")
    os.makedirs(backup_dir, exist_ok=True)
    logger.info(f"백업 폴더 생성됨: {backup_dir}")

    # 이동할 파일 탐색 패턴
    search_patterns = [
        os.path.join(work_dir, "*.csv"),
        os.path.join(work_dir, "*.json"),
        os.path.join(work_dir, "data", "*.csv"),
        os.path.join(work_dir, "data", "*.json"),
        os.path.join(pdf_storage_dir, "*", "*.csv"),
        os.path.join(pdf_storage_dir, "*", "*.json")
    ]

    moved_count = 0
    for pattern in search_patterns:
        for file_path in glob.glob(pattern):
            if os.path.isfile(file_path):
                # 백업 폴더 안에 동일한 이름이 있으면 덮어쓰기 방지를 위해 타임스탬프 추가
                filename = os.path.basename(file_path)
                dest_path = os.path.join(backup_dir, filename)
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(backup_dir, f"{name}_{int(time.time())}{ext}")
                
                try:
                    shutil.move(file_path, dest_path)
                    logger.info(f"이동 완료: {file_path} -> {dest_path}")
                    moved_count += 1
                except Exception as e:
                    logger.error(f"파일 이동 실패: {file_path} ({e})")

    logger.info(f"총 {moved_count}개의 파일이 안전하게 백업되었습니다.")

def main():
    logger.info("=== 좌표계 정밀 재구축 및 데이터 재생성 시스템 가동 ===")
    
    # 1단계: 백업
    logger.info("\n[1단계] 기존 파일 백업 진행")
    create_backup_and_move_files()
    
    # 2단계: 파이프라인 재가동 (run_suwon_batch_all 사용)
    logger.info("\n[2단계] 전체 PDF 데이터 정밀 재추출 및 변환 시작")
    # 원본 batch 스크립트의 main 함수를 호출하여 동일한 파이프라인(수정된 로직 적용됨) 수행
    run_batch_main()
    
    logger.info("\n=== 모든 작업이 성공적으로 완료되었습니다 ===")

if __name__ == "__main__":
    main()
