import logging
import re
from pyproj import Transformer

logger = logging.getLogger(__name__)

try:
    transformer_5174_to_4326 = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
    transformer_5186_to_4326 = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
    transformer_4326_to_5186 = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)
except Exception as e:
    logger.error(f"Failed to initialize pyproj transformers: {e}")

def normalize_coordinates(x_val, y_val, borehole_id="Unknown"):
    """
    x_val: 경도(Longitude) 또는 X좌표
    y_val: 위도(Latitude) 또는 Y좌표
    borehole_id: 시추번호 (로깅용)
    
    Returns: lon_wgs84, lat_wgs84, tm_x, tm_y
    """
    try:
        if not x_val or not y_val or str(x_val).strip() == "N/A" or str(y_val).strip() == "N/A":
            return "", "", "", ""
            
        x_str = str(x_val).replace(',', '').strip()
        y_str = str(y_val).replace(',', '').strip()
        
        # 숫자 외 문자 제거
        x_clean = re.sub(r'[^\d.]', '', x_str)
        y_clean = re.sub(r'[^\d.]', '', y_str)
        
        if not x_clean or not y_clean:
             return "", "", "", ""

        x = float(x_clean)
        y = float(y_clean)
    except Exception:
        return "", "", "", ""

    # Lat/Lon Swap 감지 및 보정 방어 로직 (X가 위도이고 Y가 경도인 Edge Case)
    # 대한민국 기준 위도: 33.0 ~ 39.0 / 경도: 124.0 ~ 132.0
    if 33.0 <= x <= 39.0 and 124.0 <= y <= 132.0:
        print(f"[Warning] 시추번호 {borehole_id}: 경위도 반전 감지됨. 자동 보정 완료.")
        logger.warning(f"시추번호 {borehole_id}: 경위도 반전 감지됨. 자동 보정 완료.")
        x, y = y, x

    if x < 150 and y < 50:
        # WGS84 좌표계로 간주
        lon_wgs84, lat_wgs84 = x, y
        tm_x, tm_y = transformer_4326_to_5186.transform(lon_wgs84, lat_wgs84)
    else:
        # TM 좌표계로 간주 (X/Y 스케일)
        if y < 480000:
            # EPSG:5174 (Bessel)
            lon_wgs84, lat_wgs84 = transformer_5174_to_4326.transform(x, y)
        else:
            # EPSG:5186 (GRS80)
            lon_wgs84, lat_wgs84 = transformer_5186_to_4326.transform(x, y)
            
        tm_x, tm_y = transformer_4326_to_5186.transform(lon_wgs84, lat_wgs84)
        
    return round(lon_wgs84, 7), round(lat_wgs84, 7), round(tm_x, 3), round(tm_y, 3)
