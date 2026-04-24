"""
HWPX 위치 기반 데이터 추출 엔진
표의 인덱스와 행(Row), 열(Column) 좌표를 파악하여 필요한 값을 추출합니다.
pyhwpx 라이브러리를 활용합니다.
"""

import os
import logging
from pyhwpx import Hwp

# 기존 정리 함수 재사용
from hwp_indexed_extractor import clean_float, normalize_bh_id, normalize_strata, parse_coordinates

logger = logging.getLogger(__name__)

def extract_project_info(filename: str) -> str:
    """파일명에서 프로젝트 정보 추출 (예: page1_project1_report -> PJ_1-1)"""
    import re
    page_match = re.search(r'page(\d+)', filename, re.IGNORECASE)
    proj_match = re.search(r'project(\d+)', filename, re.IGNORECASE)
    page_num = page_match.group(1) if page_match else "?"
    proj_num = proj_match.group(1) if proj_match else "?"
    return f"PJ_{page_num}-{proj_num}"

def process_single_hwpx_indexed(hwpx_path: str):
    """
    HWPX 파일 내부의 [표 인덱스][행][열] 좌표를 통해 정밀 데이터를 추출합니다.
    """
    filename = os.path.basename(hwpx_path)
    project_name = extract_project_info(filename)
    
    hwp = None
    try:
        hwp = Hwp(visible=False)
        hwp.open(hwpx_path)
        
        # Table 0: 메타데이터 표 (인덱스 0)
        # HWP 파일 내부의 구체적인 Table 구조 정보는 DataFrame으로 변환(pyhwpx의 table_to_df 사용)하여
        # 행렬 좌표(Row, Col)에 직관적으로 접근합니다. 주변 노이즈 텍스트는 DataFrame 구조에서 자연스레 분리됩니다.
        
        try:
            df0 = hwp.table_to_df(0)
        except Exception as e:
            logger.warning(f"⚠️ [{filename}] 메타데이터 표(Table 0) 인식 오류: {e}")
            df0 = None
            
        try:
            df1 = hwp.table_to_df(1)
        except Exception as e:
            logger.warning(f"⚠️ [{filename}] 지층 데이터 표(Table 1) 인식 오류: {e}")
            df1 = None

        if df1 is None or df1.empty:
            logger.error(f"❌ [{filename}] 핵심 데이터 표(Table 1) 없음. 추출 스킵")
            return []

        # ==================== 메타데이터 추출 ====================
        bh_id = "UNKNOWN"
        lon, lat, elev = "N/A", "N/A", "N/A"
        
        if df0 is not None and not df0.empty:
            try:
                # Row 0, Col 7 : 시추공명
                bh_raw = str(df0.iloc[0, 7]) if df0.shape[1] > 7 else ""
                bh_id_norm = normalize_bh_id(bh_raw)
                if bh_id_norm:
                    bh_id = bh_id_norm
                
                # Row 1, Col 5 : 좌표 X/Y ("X(N): 197344 Y(E): 522283" 형태)
                coord_raw = str(df0.iloc[1, 5]) if df0.shape[0] > 1 and df0.shape[1] > 5 else ""
                lon_val, lat_val = parse_coordinates(coord_raw)
                if lon_val is not None: lon = lon_val
                if lat_val is not None: lat = lat_val
                
                # Row 1, Col 7 : 표고 (EL)
                elev_raw = str(df0.iloc[1, 7]) if df0.shape[0] > 1 and df0.shape[1] > 7 else ""
                elev_val = clean_float(elev_raw)
                if elev_val is not None: elev = elev_val
                
            except IndexError as e:
                logger.warning(f"⚠️ [{filename}] Table 0 셀 좌표 이탈 (구조 상이): {e}")
        
        # ==================== 지층 데이터 추출 ====================
        formatted = []
        prev_depth = 0.0
        
        # Row 2부터 데이터 시작으로 간주 (Row 0,1은 헤더)
        for row_idx in range(2, len(df1)):
            row_data = df1.iloc[row_idx]
            
            if len(row_data) < 5:
                continue
                
            # Col 0: 하심도
            depth_raw = str(row_data.iloc[0])
            depth = clean_float(depth_raw)
            if depth is None:
                continue # 빈 칸 스킵
                
            # Col 4: 지층명
            # DataFrame을 사용하므로 같은 셀에 위치한 개행문자나 쓰레기값도 격리되어 노이즈 배제가 용이함
            strata_raw = str(row_data.iloc[4])
            strata = normalize_strata(strata_raw)
            
            # 동일 심도 중복 체크 방지
            existing_depths = [s['하심도'] for s in formatted]
            if depth not in existing_depths:
                formatted.append({
                    "프로젝트명": project_name,
                    "시추공명": bh_id,
                    "경도": lon,
                    "위도": lat,
                    "표고": elev,
                    "상심도": prev_depth,
                    "하심도": depth,
                    "지층명": strata,
                })
                prev_depth = depth

        if formatted:
            logger.info(f"✅ [{filename}] {len(formatted)}행 위치기반 추출 성공 (시추공: {bh_id})")
            
        return formatted

    except Exception as e:
        logger.error(f"❌ [{filename}] HWPX 위치 파싱 치명적 오류: {e}")
        return []
    finally:
        if hwp:
            hwp.quit()

