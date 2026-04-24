"""
HWPX 위치 기반 전체 데이터 파이프라인 오케스트레이션
DOCX -> HWPX 변환, 데이터 추출, 병합 및 CSV 생성의 전체 라이프사이클을 관리합니다.
"""

import os
import glob
import logging
import csv
import concurrent.futures

from hwpx_converter import batch_convert_docx_to_hwpx
from hwpx_extractor import process_single_hwpx_indexed
from table_merger import merge_multi_page_tables
from pdf_parser_odl import natural_sort_key

# 로거 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    fh = logging.FileHandler("hwpx_pipeline.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

def process_single_file(hwpx_path):
    """멀티프로세싱을 위한 단일 파일 처리 래퍼"""
    # 1. HWPX 정밀 추출
    rows = process_single_hwpx_indexed(hwpx_path)
    if not rows:
        return []
        
    # 2. Table Merger 적용 (심도 연속성 보정 및 동일 지층 병합)
    # table_merger는 입력이 List[dict] 형식이거나 dict 형식이어야 함
    merged = merge_multi_page_tables([{"data": rows}])
    return merged

def run_hwpx_integrated_pipeline():
    base_dir = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage"
    output_dir = r"C:\antigravity\#1_2_PDF_CSV"
    output_filename = "HWPX_위치기반_통합.csv"
    
    # ========================================================
    # 1단계: 문서 변환 전처리 (DOCX -> HWPX 일괄 변환)
    # ========================================================
    logger.info("=" * 60)
    logger.info("🛠️ [Phase 1] DOCX -> HWPX 전처리 시작")
    # batch_convert_docx_to_hwpx가 이미 변환된 파일 경로들도 리턴한다고 가정
    hwpx_files = batch_convert_docx_to_hwpx(base_dir)
    
    # converter에서 반환받지 못한 경우 직접 glob 탐색
    if not hwpx_files:
        hwpx_files = glob.glob(os.path.join(base_dir, "**", "*_converted.hwpx"), recursive=True)
        
    if not hwpx_files:
        logger.error("❌ 처리할 HWPX 파일이 없습니다. 파이프라인을 종료합니다.")
        return

    logger.info(f"✅ 총 {len(hwpx_files)}개의 HWPX 파일 확보 완료")
    
    # ========================================================
    # 2단계: 위치 기반 데이터 매핑 및 파싱 (병렬화)
    # ========================================================
    logger.info("=" * 60)
    logger.info(f"🚀 [Phase 2] HWPX 표 좌표 기반 데이터 정밀 추출 시작 ({len(hwpx_files)}건)")
    
    all_final_rows = []
    fail_count = 0
    total_files = len(hwpx_files)
    
    # pyhwpx의 HWP COM 객체는 한 워커당 1개씩 떠야 하므로
    # ProcessPool 대신 ThreadPool을 사용하거나 적은 Process를 사용해야 함 (COM 충돌 방지)
    # 안정성을 위해 ThreadPool 추천 (pyhwpx는 내부적으로 COM 객체 격리가 어려울 수 있음)
    # 여기서는 안전하게 ProcessPoolExecutor (max_workers=4)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        future_to_hwpx = {executor.submit(process_single_file, h_path): h_path for h_path in hwpx_files}
        
        count = 0
        for future in concurrent.futures.as_completed(future_to_hwpx):
            count += 1
            h_path = future_to_hwpx[future]
            try:
                res = future.result()
                if res:
                    all_final_rows.extend(res)
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"❌ 추출 중 크래시 발생 [{os.path.basename(h_path)}]: {e}")
            
            if count % 10 == 0 or count == total_files:
                logger.info(f"   ㄴ 진행률: {count}/{total_files} 완료...")

    if not all_final_rows:
        logger.error("❌ 추출된 데이터가 전혀 없습니다. 파이프라인 종료.")
        return

    # ========================================================
    # 3단계: 통합 CSV 정렬 및 저장
    # ========================================================
    logger.info("=" * 60)
    logger.info(f"⚖️ [Phase 3] 정렬 및 CSV 통합 저장 (총 {len(all_final_rows)}행)")
    
    # 정렬: 프로젝트명 -> 시추공명 -> 상심도
    all_final_rows.sort(key=lambda x: (
        natural_sort_key(x.get("프로젝트명", "")),
        natural_sort_key(x.get("시추공명", "")),
        float(x.get("상심도") or 0)
    ))

    # CSV 저장
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    fieldnames = ["프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"]
    
    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_final_rows)
            
        logger.info("=" * 60)
        logger.info("🎉 HWPX 위치 기반 데이터 파이프라인 전면 개편 성공!")
        logger.info(f"📁 최종 산출물: {output_path}")
        logger.info(f"📊 총 레코드 수: {len(all_final_rows)} 행")
        if fail_count > 0:
            logger.warning(f"⚠️ 처리 실패 파일: {fail_count}건")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ CSV 최종 저장 중 치명적 오류: {e}")

if __name__ == "__main__":
    # COM Multi Threading을 위한 설정 제안
    import pythoncom
    pythoncom.CoInitialize()
    run_hwpx_integrated_pipeline()
    pythoncom.CoUninitialize()
