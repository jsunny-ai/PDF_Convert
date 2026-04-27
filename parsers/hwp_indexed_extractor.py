"""
Stage 46: 인덱스 기반 시추 데이터 정밀 추출 모듈
PyMuPDF find_tables() API를 사용하여 PDF 표의 셀 인덱스(Row/Col)를 직접 타겟팅합니다.
"""
import os
import re
import logging
import unicodedata
import fitz  # PyMuPDF

# 기존 유틸 함수 재사용
import parsers.pdf_parser_odl as ppo
normalize_strata_name = ppo.normalize_strata_name
natural_sort_key = ppo.natural_sort_key

logger = logging.getLogger(__name__)

# =============================================================================
# 1. 셀 데이터 정제 함수 (Cell Data Cleansing)
# =============================================================================

def clean_cell_text(raw):
    """HWP/PDF 표 셀에서 추출된 텍스트의 제어 문자, 줄바꿈, 여백 등을 제거"""
    if raw is None:
        return ""
    text = unicodedata.normalize('NFKC', str(raw))
    # 제어 문자 제거 (0x00~0x08, 0x0b, 0x0c, 0x0e~0x1f, 0x7f)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # 줄바꿈/탭 → 공백
    text = re.sub(r'[\r\n\t]+', ' ', text)
    # 연속 공백 → 단일 공백
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def clean_float(val):
    """숫자 추출: 숫자, 소수점, 마이너스 외의 문자를 완벽히 제거하고 float로 변환"""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # 범위 표기(~) → 마지막 값 사용
    if '~' in s:
        s = s.split('~')[-1]
    
    # 1. 숫자, 소수점, 마이너스 부호만 남기기 (정규식 강화)
    cleaned = re.sub(r'[^\d\.\-]', '', s)
    
    # 2. 다중 소수점 처리 (예: 123.45.67 -> 123.4567)
    if cleaned.count('.') > 1:
        parts = cleaned.split('.')
        cleaned = parts[0] + '.' + "".join(parts[1:])
        
    if not cleaned or cleaned == '.' or cleaned == '-': return None
    
    try:
        return float(cleaned)
    except ValueError:
        return None

def validate_suwon_coordinates(x, y):
    """
    수원시 로컬 좌표계 범위(TM) 검증 (1차 수치 검증)
    """
    if x is None or y is None: return False
    x_valid = (170000 <= x <= 230000)
    y_valid = (470000 <= y <= 550000)
    return x_valid and y_valid


def normalize_bh_id(raw_id):
    """
    시추번호 정규화: 공백 제거, 대문자화, 하이픈 표준화.
    숫자 앞의 '0'(Zero-padding)이 유실되지 않도록 문자열 기반으로 정규화합니다.
    """
    if not raw_id: return ""
    text = clean_cell_text(raw_id).upper()
    
    # 1. 알파벳, 숫자, 하이픈 외 제거
    text = re.sub(r'[^A-Z0-9-]', '', text)
    
    # 2. 중복 하이픈 정리
    text = re.sub(r'-+', '-', text)
    
    return text.strip('-')


def normalize_strata(raw_text):
    """지층명 정규화: 기존 함수 래핑"""
    text = clean_cell_text(raw_text)
    return normalize_strata_name(text)


def extract_project_info(filename):
    """파일명에서 프로젝트 정보 추출 (예: page1_project1_report.pdf → PJ_1-1)"""
    page_match = re.search(r'page(\d+)', filename, re.IGNORECASE)
    proj_match = re.search(r'project(\d+)', filename, re.IGNORECASE)
    page_num = page_match.group(1) if page_match else "?"
    proj_num = proj_match.group(1) if proj_match else "?"
    return f"PJ_{page_num}-{proj_num}"


# =============================================================================
# 2. 좌표 파싱 (Index-Based Mapping)
# =============================================================================

def parse_coordinates(coord_text):
    """Table1[1,5] 좌표 문자열에서 X(N), Y(E) 값 추출
    
    입력 예: "X(N): 197344.925 Y(E): 522283.946"
    또는:    "X(N): 197344.925\nY(E): 522283.946"
    """
    lon = None  # X(N) → 경도
    lat = None  # Y(E) → 위도
    
    if not coord_text:
        return lon, lat
    
    text = clean_cell_text(coord_text)
    
    # X(N) 패턴
    x_match = re.search(r'X\s*\(?N?\)?\s*[:：]\s*([\d.]+)', text, re.IGNORECASE)
    if x_match:
        lon = clean_float(x_match.group(1))
    
    # Y(E) 패턴
    y_match = re.search(r'Y\s*\(?E?\)?\s*[:：]\s*([\d.]+)', text, re.IGNORECASE)
    if y_match:
        lat = clean_float(y_match.group(1))
    
    # 패턴 매칭 실패 시 숫자 2개 직접 추출 시도
    if lon is None or lat is None:
        nums = re.findall(r'(\d{5,7}\.\d{2,4})', text)
        if len(nums) >= 2:
            vals = sorted([float(n) for n in nums], reverse=True)
            if lon is None:
                lon = vals[0]
            if lat is None:
                lat = vals[1] if len(vals) > 1 else None
    
    # [NEW] 수원시 로컬 좌표계 1차 수치 검증
    if lon is not None and lat is not None:
        if not validate_suwon_coordinates(lon, lat):
            logger.warning(f"  ⚠️ [Validation Warning] 좌표 범위 이탈: X={lon}, Y={lat}")

    return lon, lat


# =============================================================================
# 3. 단일 PDF 인덱스 기반 추출 함수 (Core Extraction)
# =============================================================================

def process_single_pdf_indexed(pdf_path):
    """
    단일 PDF 파일에서 인덱스 기반으로 시추 데이터를 추출합니다.
    
    Returns:
        List[Dict]: [{"프로젝트명", "경도", "위도", "표고", "시추공명", "상심도", "하심도", "지층명"}, ...]
    """
    filename = os.path.basename(pdf_path)
    project_name = extract_project_info(filename)
    
    doc = None
    try:
        doc = fitz.open(pdf_path)
        
        # 시추공별 데이터 수집: {bh_id: {"meta": {...}, "strata": [...]}}
        boreholes = {}
        current_bh_id = None
        
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            tables = page.find_tables()
            
            if len(tables.tables) < 2:
                logger.warning(f"  [{filename}] Page {page_idx+1}: 표 {len(tables.tables)}개 감지 (최소 2개 필요)")
                continue
            
            table1_data = tables.tables[0].extract()
            table2_data = tables.tables[1].extract()
            
            # ── Table 1: 메타데이터 추출 ──
            if len(table1_data) >= 2 and len(table1_data[0]) >= 8:
                bh_id_raw = table1_data[0][7]
                bh_id = normalize_bh_id(bh_id_raw)
                
                if bh_id:
                    current_bh_id = bh_id
                    
                    if bh_id not in boreholes:
                        # 좌표 파싱
                        coord_text = table1_data[1][5] if len(table1_data[1]) > 5 else ""
                        lon, lat = parse_coordinates(coord_text)
                        
                        # 표고
                        elev_raw = table1_data[1][7] if len(table1_data[1]) > 7 else None
                        elev = clean_float(elev_raw)
                        
                        boreholes[bh_id] = {
                            "meta": {
                                "경도": lon if lon is not None else "N/A",
                                "위도": lat if lat is not None else "N/A",
                                "표고": elev if elev is not None else "N/A",
                            },
                            "strata": []
                        }
            
            if not current_bh_id:
                continue
            
            # ── Table 2: 지층 데이터 추출 (Row 2부터) ──
            for row_idx in range(2, len(table2_data)):
                row = table2_data[row_idx]
                if len(row) < 5:
                    continue
                
                depth = clean_float(row[0])   # Col 0: 하심도
                if depth is None:
                    continue  # 빈 행(SPT 반복행) 스킵
                
                strata_raw = row[4] if row[4] else ""  # Col 4: 지층명
                strata = normalize_strata(strata_raw)
                
                # 중복 심도 방지 (동일 시추공 내)
                existing_depths = [s['depth'] for s in boreholes[current_bh_id]['strata']]
                if depth not in existing_depths:
                    boreholes[current_bh_id]['strata'].append({
                        'depth': depth,
                        'strata': strata,
                    })
        
        # ── 최종 포맷팅: 상심도/하심도 계산 ──
        formatted = []
        for bh_id, bh_data in boreholes.items():
            meta = bh_data['meta']
            strata_list = sorted(bh_data['strata'], key=lambda x: x['depth'])
            
            prev_depth = 0.0
            for item in strata_list:
                formatted.append({
                    "프로젝트명": project_name,
                    "시추공명": bh_id,
                    "경도": meta["경도"],
                    "위도": meta["위도"],
                    "표고": meta["표고"],
                    "상심도": prev_depth,
                    "하심도": item['depth'],
                    "지층명": item['strata'],
                })
                prev_depth = item['depth']
        
        if formatted:
            logger.info(f"  ✅ [{filename}] {len(boreholes)}개 시추공, {len(formatted)}개 레코드 추출 완료")
        else:
            logger.warning(f"  ⚠️ [{filename}] 추출된 데이터 없음")
        
        return formatted
    
    except Exception as e:
        logger.error(f"  ❌ [{filename}] 처리 오류: {e}")
        return []
    finally:
        if doc:
            doc.close()
