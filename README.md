# 지반조사 시추공 데이터 하이브리드 추출 파이프라인 (Borehole Data Extraction Pipeline)

본 프로젝트는 PDF 형태의 복잡한 지반조사 보고서 및 시추주상도에서 시추공 위치 좌표, 표고, 심도별 지층 정보를 자동으로 추출하여 **V-World 및 3D 지층 모델링 API 연계에 최적화된 CSV 및 JSON 형식으로 변환**하는 자동화 웹 서비스입니다.

## 🚀 핵심 아키텍처 및 특징 (Key Features)

단 하나의 정보 유실도 허용하지 않으면서 대용량 파일의 처리 속도를 극대화하기 위해 **4단계 하이브리드 파이프라인(4-Stage Hybrid Pipeline)**으로 설계되었습니다.

* **Stage 1: 고속 메타데이터 스캔 & 지연 평가 (Lazy Evaluation)**
  * `PyMuPDF`와 `pyhwpx`를 활용해 전체 페이지를 0.5초 내에 스캔하여 시추번호 및 기본 메타데이터 추출.
  * 데이터 무결성이 확인된 문서는 무거운 AI 비전 엔진(ODL)을 생략하는 분기 처리를 통해 **처리 속도 극대화**.
* **Stage 2: ODL(OpenDataLoader) 병렬 AI 비전 분석 & I/O 최적화**
  * 스캔본 및 복잡한 표 처리를 위한 Java 기반 AI 비전 레이아웃 분석.
  * **In-Memory I/O 스트림** 적용으로 다중 스레드 구동 시 발생하는 File Lock(WinError 5) 원천 차단.
  * **JVM 데몬화(Daemonization)**를 통해 서브프로세스 콜드 스타트(Cold Start) 대기 시간 0초 달성.
* **Stage 3: 논리적 지층 병합 및 식별자 보정 (Table Merger)**
  * 파편화된 11종의 지층명을 **4대 대분류(토사, 풍화암, 연암, 경암)**로 강제 정규화.
  * 연속된 동일 지층의 상/하심도를 단일 행으로 정밀 병합.
  * 시추번호가 'BH-'로 불완전하게 잘린 엣지 케이스를 감지하여 `BH-a1`, `BH-a2`로 **자동 넘버링(Sequential Auto-numbering)**.
* **Stage 4: 동적 좌표 정규화 (Dynamic Coordinate Normalization)**
  * 원본 데이터의 Scale을 분석하여 경위도와 TM 좌표계 동적 판별.
  * 위도/경도 값이 반대로 입력된 휴먼 에러를 런타임에 감지하고 보정하는 **Lat/Lon Swap 방어 로직**.
  * `pyproj`를 활용하여 2번 프로젝트(V-World API) 규격인 `lon_wgs84`, `lat_wgs84` 단일 좌표계로 JSON/CSV 페이로드 최적화.

## 📁 디렉토리 구조 (Directory Structure)

유지보수와 확장을 고려하여 관심사 분리(SoC) 원칙에 따라 모듈화되어 있습니다.

```text
📦 Borehole-Extraction-Pipeline
 ┣ 📂 core/          # 하이브리드 메인 엔진, 테이블 병합, 좌표계 정규화 등 핵심 비즈니스 로직
 ┣ 📂 parsers/       # HWPX, PyMuPDF, ODL 등 각 모듈별 독립 텍스트/테이블 추출기
 ┣ 📂 web/           # 파일 업로드, 진행 상태 UI 및 다운로드 통신을 담당하는 프론트엔드 (app.js, index.html)
 ┣ 📂 config/        # geo_settings.json 등 환경별 설정 파일
 ┣ 📂 docs/          # 좌표계 감사·기술 가이드 등 사람이 읽는 기술 문서 (런타임 무관)
 ┣ 📂 scripts/
 ┃   ┣ 📂 batch/     # 일회성 오프라인 데이터 마이그레이션 스크립트 (라이브 서비스 경로 아님)
 ┃   ┗ 📂 smoke/     # 라이브 서버 대상 수동 호출 스모크 스크립트
 ┣ 📂 data/          # 원본 PDF, 추출된 CSV/JSON 결과물 격리 보관소 (.gitignore)
 ┣ 📜 server.py      # Flask 기반 백엔드 웹 서버 라우팅 (API Endpoints)
 ┣ 📜 run_borehole_system.bat # 원클릭 서버 가동 및 웹 브라우저 자동 실행 배치 파일
 ┗ 📜 run_java.bat   # JDK 환경 변수 부트스트랩