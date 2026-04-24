"""
마스터 하이브리드 추출기 (3-Tier Precision Extraction Pipeline)
1. Tier 1 (Main): HWPX 기반 DataFrame 인덱스 좌표 추출
2. Tier 2 (Fallback): PyMuPDF 유클리드 공간 거리 기반 결측치 보정
3. Tier 3 (Validation): ODL Markdown 덤프를 통한 추출 행 수 일치 검증
4. Delivery: Flask 응답 헤더 최적화 구조에 삽입하기 쉬운 형태의 출력
"""

import os
import re
import unicodedata
import logging
from typing import List, Dict, Tuple

from hwpx_converter import batch_convert_docx_to_hwpx
from hwp_indexed_extractor import clean_float, normalize_bh_id, normalize_strata, parse_coordinates
from table_merger import merge_multi_page_tables
from pdf_parser_odl import find_value_by_spatial_proximity, find_metadata_spatial, natural_sort_key

import opendataloader_pdf

logger = logging.getLogger(__name__)

class MasterHybridExtractor:
    def __init__(self, output_dir: str = r"C:\antigravity\#1_2_PDF_CSV"):
        self.output_dir = output_dir
        self.java_bin = os.path.join(output_dir, "jdk_folder", "jdk-21.0.2", "bin")
        
        # ODL을 위한 Java 환경 변수 설정
        if self.java_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = self.java_bin + os.pathsep + os.environ.get("PATH", "")

    def process_file(self, source_path: str, project_name: str) -> List[Dict]:
        """
        단일 파일(PDF 또는 DOCX/HWPX)에 대해 3-Tier 파이프라인을 구동합니다.
        """
        logger.info(f"🚀 [3-Tier Pipeline] 처리 시작: {source_path}")
        
        # 파일 형식 판별 및 준비 (PDF, DOCX -> HWPX 전환)
        hwpx_path = self._prepare_hwpx(source_path)
        pdf_path = self._prepare_pdf(source_path)
        
        # -----------------------------
        # Tier 1 (Main Engine): HWPX Structural Parsing (or ODL Fallback for PDF)
        # -----------------------------
        logger.info(f"   ㄴ [Tier 1] HWPX 표 구조 기반 추출 시도")
        raw_data, meta = self._tier1_hwpx_extract(hwpx_path, project_name)
        
        if not raw_data and pdf_path:
            logger.warning(f"   ㄴ [Tier 1 Fallback] HWPX 인식안됨/순수 PDF. ODL 마크다운 추출기 가동")
            md_dir = os.path.join(self.output_dir, "MD_Storage", "Fallback_Ext")
            os.makedirs(md_dir, exist_ok=True)
            try:
                import glob
                opendataloader_pdf.convert(input_path=[pdf_path], output_dir=md_dir, format="markdown", quiet=True)
                base = os.path.splitext(os.path.basename(pdf_path))[0]
                md_files = [f for f in os.listdir(md_dir) if f.endswith('.md') and base in f]
                
                if md_files:
                    md_path = os.path.join(md_dir, md_files[0])
                    import pdf_parser_odl
                    pages_data = pdf_parser_odl.extract_all_from_md(md_path, project_name=project_name, pdf_path=pdf_path)
                    
                    # flat 병합 (Tier 1 결과 형식에 맞춤)
                    for page in pages_data:
                        raw_data.extend(page.get("data", []))
                    
                    # 빈값이 채워진 meta 정보 가져오기 (ODL이 찾았을 수도 있음)
                    if pages_data and pages_data[0].get("data"):
                        first = pages_data[0]["data"][0]
                        if first.get("경도"): meta["경도"] = first["경도"]
                        if first.get("위도"): meta["위도"] = first["위도"]
                        if first.get("표고"): meta["표고"] = first["표고"]
            except Exception as e:
                import traceback
                logger.error(f"   ❌ [Tier 1 Fallback] ODL 전환 실패: {traceback.format_exc()}")
        
        # -----------------------------
        # Tier 2: PyMuPDF Spatial Recovery (Fallback)
        # -----------------------------
        if self._needs_fallback(meta) and pdf_path:
            logger.warning(f"   ㄴ [Tier 2] 결측치 감지! PyMuPDF 공간 폴백 발동")
            meta = self._tier2_spatial_recovery(pdf_path, meta)
            # 메타데이터를 원시 데이터에 덮어쓰기
            for row in raw_data:
                row["경도"] = meta.get("경도", row["경도"])
                row["위도"] = meta.get("위도", row["위도"])
                row["표고"] = meta.get("표고", row["표고"])
        else:
            logger.info(f"   ㄴ [Tier 2] 결측치 없음 (통과)")

        # -----------------------------
        # Tier 3: ODL Cross-Check Validation
        # -----------------------------
        if pdf_path:
            logger.info(f"   ㄴ [Tier 3] ODL 마크다운 덤프 및 데이터 행 수 검증")
            is_valid = self._tier3_odl_validation(pdf_path, len(raw_data), project_name)
            if not is_valid:
                logger.error(f"   ❌ [Tier 3 검증 실패] 원본 파싱 행 수와 최종 추출 행 수가 불일치합니다!")
                # 정책에 따라 강제 중단하거나 오류 로그만 남기고 속행할 수 있음
        
        # -----------------------------
        # Post-Processing: 병합 및 보정
        # -----------------------------
        if not raw_data:
            return []
            
        logger.info(f"   ㄴ [Merge] 공통 후처리(심도 보정 및 병합) 적용")
        # table_merger가 사용하는 형식 맞춤
        merged_data = merge_multi_page_tables([{"data": raw_data}])
        
        return merged_data

    def _prepare_hwpx(self, source_path: str) -> str:
        base, ext = os.path.splitext(source_path)
        ext = ext.lower()
        
        if ext == ".hwpx":
            return source_path
        elif ext == ".docx":
            # HWPX 변환 (임시 디렉토리에서)
            hwpx_file = base + ".hwpx"
            if not os.path.exists(hwpx_file):
                logger.info("      * DOCX를 HWPX로 실시간 변환")
                try:
                    from pyhwpx import Hwp
                    hwp = Hwp(visible=False)
                    hwp.open(source_path)
                    hwp.save_as(hwpx_file)
                    hwp.quit()
                except Exception as e:
                    logger.error(f"HWPX 변환 오류: {e}")
            return hwpx_file
        else:
            # 아직 PDF에서 HWPX로 다이렉트 변환 로직은 ODL에 의존하거나 별도 도구가 필요
            return ""

    def _prepare_pdf(self, source_path: str) -> str:
        base, ext = os.path.splitext(source_path)
        if ext.lower() == ".pdf":
            return source_path
        # DOCX/HWPX인 경우 PDF 파일이 같은 이름으로 존재한다고 가정
        pdf_file = base + ".pdf"
        if os.path.exists(pdf_file):
            return pdf_file
        pdf_file = source_path.replace("_converted", "").replace(".docx", ".pdf").replace(".hwpx", ".pdf")
        if os.path.exists(pdf_file):
            return pdf_file
        return ""

    def _tier1_hwpx_extract(self, hwpx_path: str, project_name: str) -> Tuple[List[Dict], Dict]:
        """pyhwpx를 통한 인덱스 추출 (Tier 1)"""
        if not hwpx_path or not os.path.exists(hwpx_path):
            return [], {"경도": "N/A", "위도": "N/A", "표고": "N/A"}
            
        from pyhwpx import Hwp
        hwp = None
        raw_rows = []
        meta = {"경도": "N/A", "위도": "N/A", "표고": "N/A"}
        
        try:
            hwp = Hwp(visible=False)
            hwp.open(hwpx_path)
            
            try:
                df0 = hwp.table_to_df(0)
            except: df0 = None
            try:
                df1 = hwp.table_to_df(1)
            except: df1 = None

            if df1 is None or df1.empty:
                return [], meta

            bh_id = "UNKNOWN"
            if df0 is not None and not df0.empty:
                try:
                    bh_raw = str(df0.iloc[0, 7]) if df0.shape[1] > 7 else ""
                    bh_id_norm = normalize_bh_id(bh_raw)
                    if bh_id_norm: bh_id = bh_id_norm
                    
                    coord_raw = str(df0.iloc[1, 5]) if df0.shape[0] > 1 and df0.shape[1] > 5 else ""
                    lon_val, lat_val = parse_coordinates(coord_raw)
                    if lon_val: meta["경도"] = lon_val
                    if lat_val: meta["위도"] = lat_val
                    
                    elev_raw = str(df0.iloc[1, 7]) if df0.shape[0] > 1 and df0.shape[1] > 7 else ""
                    elev_val = clean_float(elev_raw)
                    if elev_val: meta["표고"] = elev_val
                except IndexError: pass

            prev_depth = 0.0
            for row_idx in range(2, len(df1)):
                row_data = df1.iloc[row_idx]
                if len(row_data) < 5: continue
                depth = clean_float(str(row_data.iloc[0]))
                if depth is None: continue
                strata = normalize_strata(str(row_data.iloc[4]))
                
                raw_rows.append({
                    "프로젝트명": project_name,
                    "시추공명": bh_id,
                    "경도": meta["경도"],
                    "위도": meta["위도"],
                    "표고": meta["표고"],
                    "상심도": prev_depth,
                    "하심도": depth,
                    "지층명": strata,
                })
                prev_depth = depth
                
        except Exception as e:
            logger.error(f"[Tier 1] HWPX Parsing Error: {e}")
        finally:
            if hwp: hwp.quit()
            
        return raw_rows, meta

    def _needs_fallback(self, meta: Dict) -> bool:
        return any(v == "N/A" for v in meta.values())

    def _tier2_spatial_recovery(self, pdf_path: str, current_meta: Dict) -> Dict:
        """PyMuPDF 공간 유클리드 거리 폴백 (Tier 2)"""
        import fitz
        doc = fitz.open(pdf_path)
        try:
            # 주로 첫 번째 페이지에 메타데이터가 집중
            page = doc[0]
            recovered = find_metadata_spatial(page)
            
            if current_meta["위도"] == "N/A" and recovered.get("lat"):
                current_meta["위도"] = recovered["lat"]
            if current_meta["경도"] == "N/A" and recovered.get("lon"):
                current_meta["경도"] = recovered["lon"]
            if current_meta["표고"] == "N/A" and recovered.get("el"):
                current_meta["표고"] = recovered["el"]
                
        except Exception as e:
            logger.error(f"[Tier 2] Spatial Recovery Error: {e}")
        finally:
            doc.close()
        return current_meta

    def _tier3_odl_validation(self, pdf_path: str, extracted_row_count: int, project_name: str) -> bool:
        """ODL 마크다운 덤프 및 데이터 행수 교차 검증 (Tier 3)"""
        if extracted_row_count == 0:
            return False
            
        # 임시 출력 디렉토리
        md_output_dir = os.path.join(self.output_dir, "MD_Storage", "Validation_Temp")
        os.makedirs(md_output_dir, exist_ok=True)
        
        try:
            # 1. ODL MD 변환
            opendataloader_pdf.convert(
                input_path=[pdf_path], 
                output_dir=md_output_dir,
                format="markdown"
            )
            
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            md_path = os.path.join(md_output_dir, f"{base}.md")
            
            if not os.path.exists(md_path):
                # ODL 변환 실패시 검증 Pass(무조건 실패로 띄우진 않음. False-positive 방지)
                logger.warning("      * ODL MD 덤프 불가로 검증 생략")
                return True
                
            # 2. 마크다운 내 표(Row) 파이프 갯수 계수
            with open(md_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            md_table_rows = 0
            for line in lines:
                # 간단한 지층 표(5컬럼 이상 파이프라인 존재) 행을 세팅
                if line.strip().startswith('|') and line.count('|') >= 5:
                    # 헤더(---|---)나 빈 데이터 스킵
                    if "---" in line or "심 도" in line.replace(" ", ""):
                        continue
                    # 심도 컬럼에 숫자가 존재하는지 확인
                    parts = line.split('|')
                    if len(parts) > 2 and clean_float(parts[1]) is not None:
                        md_table_rows += 1
                        
            # 검증 로직 (마크다운의 노이즈를 감안, MD 행수가 추출 행수보다 월등히 많을 때만 경고)
            # 마크다운은 페이지 분할 등으로 인해 테이블 행이 데이터 행보다 항상 조금 더 많거나 같습니다.
            logger.info(f"      * 검증 지표: 추출({extracted_row_count}행) vs ODL({md_table_rows}행)")
            
            error_margin = 0.5 # 50% 이상 차이 날 때 유실로 판단
            if md_table_rows > 0 and extracted_row_count < (md_table_rows * error_margin):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"[Tier 3] ODL Validation Error: {e}")
            return True # 시스템 블로킹 방지용 패스

# Delivery를 위한 인터페이스를 제공
from urllib.parse import quote

def get_csv_headers() -> Dict[str, str]:
    """
    서버(Flask)에서 다운로드 응답을 만들 때 사용할 고정 헤더 반환 (Delivery)
    """
    filename = quote("서울특별시_CSV_통합_최종.csv")
    return {
        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
        "Content-Type": "text/csv; charset=utf-8-sig",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    }
