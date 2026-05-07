import logging
import re
from pyproj import Transformer

logger = logging.getLogger(__name__)

# =============================================================================
# [Stage 54-B] 수리적 검증 기반 좌표계 후보군 (Candidate Pool)
# 국토지리정보원 표준 7-파라미터 (+towgs84) 적용
# =============================================================================
PROJ_STRINGS = {
    # Group A (60만 계열 - 현행 표준)
    "EPSG:5186": "+proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=600000 +ellps=GRS80 +units=m +no_defs",
    "EPSG:5187": "+proj=tmerc +lat_0=38 +lon_0=129 +k=1 +x_0=200000 +y_0=600000 +ellps=GRS80 +units=m +no_defs",
    # Group B (50만 계열 - 구형 도면 및 예외)
    "EPSG:5174": "+proj=tmerc +lat_0=38 +lon_0=127.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +towgs84=-145.907,505.034,685.756,-1.162,2.347,1.592,6.342 +no_defs",
    "EPSG:5176": "+proj=tmerc +lat_0=38 +lon_0=129.0028902777778 +k=1 +x_0=200000 +y_0=500000 +ellps=bessel +units=m +towgs84=-145.907,505.034,685.756,-1.162,2.347,1.592,6.342 +no_defs",
    "EPSG:5181": "+proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=500000 +ellps=GRS80 +units=m +no_defs",
    "EPSG:5183": "+proj=tmerc +lat_0=38 +lon_0=129 +k=1 +x_0=200000 +y_0=500000 +ellps=GRS80 +units=m +no_defs"
}

TRANSFORMER_POOL = {}
try:
    for epsg, proj in PROJ_STRINGS.items():
        TRANSFORMER_POOL[epsg] = Transformer.from_crs(proj, "EPSG:4326", always_xy=True)
    
    TRANSFORMER_POOL['WGS84'] = None
    # 출력 표준 (ITRF2000/GRS80 중부원점)
    transformer_4326_to_5186 = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)
except Exception as e:
    logger.error(f"Failed to initialize precision transformers: {e}")

# SpatialValidator 임포트 (SSOT 지오펜스 적용)
from core.spatial_validator import SpatialValidator
validator = SpatialValidator()

def normalize_coordinates(x_val, y_val, borehole_id="Unknown", source_crs=None):
    """
    x_val: 경도(Longitude) 또는 X좌표
    y_val: 위도(Latitude) 또는 Y좌표
    borehole_id: 시추번호 (로깅용)
    source_crs: 문서에서 추출된 EPSG 코드 (예: 'EPSG:5187')
    
    Returns: lon_wgs84, lat_wgs84, tm_x, tm_y, final_epsg
    """
    try:
        if not x_val or not y_val or str(x_val).strip() == "N/A" or str(y_val).strip() == "N/A":
            return "", "", "", "", source_crs or "UNKNOWN"
            
        x_str = str(x_val).replace(',', '').strip()
        y_str = str(y_val).replace(',', '').strip()
        
        # 숫자 외 문자 제거
        x_clean = re.sub(r'[^\d.]', '', x_str)
        y_clean = re.sub(r'[^\d.]', '', y_str)
        
        if not x_clean or not y_clean:
             return "", "", "", "", source_crs or "UNKNOWN"

        x = float(x_clean)
        y = float(y_clean)
    except Exception:
        return "", "", "", "", source_crs or "UNKNOWN"

    lon_wgs84, lat_wgs84 = None, None
    final_epsg = source_crs or "UNKNOWN"

    # [Step C: Scale Error Correction]
    # 동부원점(lon_0=129)은 수원시 기준 Easting이 ~21,000 수준으로 정상이므로 보정에서 제외
    DONGBU_CRS = ('EPSG:5187', 'EPSG:5183', 'EPSG:5176')
    if x < 30000 and source_crs != 'WGS84' and source_crs not in DONGBU_CRS:
        x *= 10

    # 메타데이터 기반 정밀 변환
    if source_crs == 'WGS84':
        lon_wgs84, lat_wgs84 = x, y
    elif source_crs and source_crs in TRANSFORMER_POOL:
        try:
            # [Axis Normalization] 한국 TM 좌표계 특성상 Northing(50만/60만)은 반드시 Easting(20만)보다 큼.
            # PDF상의 X, Y 라벨이 뒤바뀌어 있더라도(예: X=E, Y=N) 이를 자동으로 정렬하여 pyproj에 전달.
            easting, northing = (x, y) if x < y else (y, x)
            
            lon_temp, lat_temp = TRANSFORMER_POOL[source_crs].transform(easting, northing)
            lon_wgs84, lat_wgs84 = lon_temp, lat_temp
        except Exception as e:
            logger.error(f"[Transform Error: {borehole_id}] pyproj 변환 실패: {e}")
            lon_wgs84, lat_wgs84 = None, None
    elif source_crs is None and max(x, y) > 100000:
        # [Stage 55] CRS 미확정 시 Northing 수치로 50만/60만 추정
        northing_val = max(x, y)
        if northing_val > 550000:
            inferred_crs = "EPSG:5186"  # 60만 계열
        elif northing_val < 480000:
            inferred_crs = "EPSG:5181"  # 50만 계열
        else:
            inferred_crs = "EPSG:5186"  # 모호 구간 기본값
            logger.warning(f"[Ambiguous FN: {borehole_id}] Northing={northing_val} 모호 구간")
        
        try:
            easting, northing = (x, y) if x < y else (y, x)
            lon_temp, lat_temp = TRANSFORMER_POOL[inferred_crs].transform(easting, northing)
            lon_wgs84, lat_wgs84 = lon_temp, lat_temp
            final_epsg = inferred_crs + "_INFERRED"
        except Exception as e:
            logger.error(f"[Transform Error: {borehole_id}] 추정 CRS 변환 실패: {e}")
    else:
        logger.warning(f"[Missing CRS: {borehole_id}] 문서 메타데이터에서 좌표계를 찾지 못했습니다. WGS84 변환 생략.")

    # WGS84 좌표가 성공적으로 계산된 경우, 출력용 표준(EPSG:5186)으로 tm_x, tm_y 생성
    tm_x, tm_y = "", ""
    if lon_wgs84 is not None and lat_wgs84 is not None:
        try:
            tm_x_val, tm_y_val = transformer_4326_to_5186.transform(lon_wgs84, lat_wgs84)
            tm_x = round(tm_x_val, 3)
            tm_y = round(tm_y_val, 3)
            lon_wgs84 = round(lon_wgs84, 7)
            lat_wgs84 = round(lat_wgs84, 7)
        except Exception:
            pass
    else:
        # 변환을 포기한 경우 WGS84 필드를 비움 (기존 원본 X,Y만 CSV에 남음)
        lon_wgs84, lat_wgs84 = "", ""
        
    return lon_wgs84, lat_wgs84, tm_x, tm_y, final_epsg

