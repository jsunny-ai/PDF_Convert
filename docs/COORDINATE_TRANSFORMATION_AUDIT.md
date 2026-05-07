# 좌표 변환 로직 수학적 무결성 검토 보고서 (Coordinate Transformation Audit)

본 문서는 시스템에서 사용 중인 좌표 변환 로직의 수학적 정의, 투영 파라미터(Proj4), 및 국토지리정보원 표준 준수 여부를 검토한 결과입니다.

---

## 1. 핵심 변환 로직 (`coordinate_transformer.py`)

시스템은 `pyproj` 라이브러리를 사용하여 EPSG 표준 기반의 좌표 변환을 수행합니다. 특히 Stage 54 업데이트를 통해 문서에 명시된 좌표계 메타데이터(`source_crs`)를 최우선으로 신뢰하도록 설계되었습니다.

```python
# [핵심 로직 요약]
# 1. 문서 추출 좌표계(source_crs)가 있을 경우 해당 EPSG 코드를 강제 할당
if source_crs in TRANSFORMER_POOL:
    lon_wgs84, lat_wgs84 = TRANSFORMER_POOL[source_crs].transform(x, y)
# 2. 메타데이터가 없을 경우 Y(Northing) 수치 범위를 기준으로 투영 가산값(50만 vs 60만) 추정
elif y < 480000:
    lon_wgs84, lat_wgs84 = TRANSFORMER_POOL['EPSG:5174'].transform(x, y) # Bessel 중부
else:
    lon_wgs84, lat_wgs84 = TRANSFORMER_POOL['EPSG:5186'].transform(x, y) # GRS80 중부
```

---

## 2. 투영 정의 파라미터 (Proj4 Strings)

각 좌표계별 투영 엔진 내부 파라미터 설정값입니다.

| 좌표계 명칭 | EPSG 코드 | Proj4 정의 문자열 | 비고 (가산값 등) |
|:---:|:---:|:---|:---|
| **GRS80 중부원점** | `5186` | `+proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=600000 +ellps=GRS80 +units=m` | 현행 표준 (가산값 60만) |
| **GRS80 동부원점** | `5187` | `+proj=tmerc +lat_0=38 +lon_0=129 +k=1 +x_0=200000 +y_0=600000 +ellps=GRS80 +units=m` | 강원/경북권 표준 |
| **Bessel 중부원점** | `5174` | `+proj=tmerc +lat_0=38 +lon_0=127.00289... +k=1 +x_0=200000 +y_0=500000 +ellps=bessel` | 구형 도면 (가산값 50만) |
| **Bessel 동부원점** | `5176` | `+proj=tmerc +lat_0=38 +lon_0=129.00289... +k=1 +x_0=200000 +y_0=500000 +ellps=bessel` | 구형 도면 (동부원점) |

---

## 3. 수학적 연산 순서 및 전처리 (Processing Sequence)

1.  **자료 정제 (Cleaning)**: 문자열 내 쉼표(,) 및 특수기호를 제거하고 부동 소수점으로 변환합니다.
2.  **경위도 반전 체크 (Lat/Lon Swap)**: 입력값이 대한민국 경위도 범위(위도 33~39, 경도 124~132)에 속할 경우, 변환 없이 즉시 채택하거나 반전된 경우를 교정합니다.
3.  **단위 보정 (Scale Correction)**: TM 좌표의 X값이 3만 미만인 경우, 자릿수 누락으로 판단하여 `x = x * 10` 보정을 수행합니다.
4.  **투영 원점 가산 (False Easting/Northing)**:
    *   `+x_0=200000`: 모든 TM 좌표계에서 동일하게 20만m를 가산합니다.
    *   `+y_0=600000` (GRS80) vs `+y_0=500000` (Bessel): 타원체 종류에 따라 남북 방향 가산값이 10만m 차이납니다. 
5.  **타원체 변환 (Datum Transformation)**: Bessel(구소삼각원점)에서 GRS80(ITRF2000)으로의 변환은 `pyproj` 내장 Molodensky 또는 7-파라미터 변환 모델을 따릅니다.

---

## 4. 표준 규격 준수 확인

*   본 로직은 국토지리정보원(NGII) 고시 **좌표변환 매개변수** 및 **공공측량 표준**을 준수합니다.
*   최근 도입된 `meta_crs` 우선 로직은 실제 도면 제작 시의 의도(Metadata)를 수학적 추론보다 우선시함으로써 변환 오차 발생 가능성을 최소화하였습니다.
