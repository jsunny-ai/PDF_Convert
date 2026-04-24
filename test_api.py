import requests
import json
import time

url = "http://127.0.0.1:5000/api/convert"
filepath = r"C:\antigravity\#1_2_PDF_CSV\Documents\page1_project1_report_converted.docx"

print("1. 파일 업로드 및 하이브리드 변환 요청 시작...")
start = time.time()
with open(filepath, "rb") as f:
    files = {"pdf_files": (filepath.split("\\")[-1], f)}
    response = requests.post(url, files=files)

print(f"응답 코드: {response.status_code}")
print(f"소요 시간: {time.time() - start:.2f}초")

if response.status_code == 200:
    data = response.json()
    print("성공! 응답 데이터 요약:")
    for res in data.get("results", []):
        print(f" - {res['filename']}: {res['status']} ({len(res.get('data',[]))} rows)")
        if 'error' in res:
            print(f"   에러: {res['error']}")
        
    download_url = "http://127.0.0.1:5000" + data.get("combined_csv_url", "")
    print(f"\n2. 다운로드 헤더 검증 시작: {download_url}")
    dl_resp = requests.get(download_url)
    print(f"다운로드 응답 코드: {dl_resp.status_code}")
    print("응답 헤더:")
    for k, v in dl_resp.headers.items():
        if k in ["Content-Disposition", "Content-Type", "Cache-Control"]:
            print(f" [{k}]: {v}")
    
    # UTF-8-SIG BOM 확인
    content = dl_resp.content
    if content.startswith(b'\xef\xbb\xbf'):
        print("\n[OK] UTF-8-SIG BOM 헤더가 정상적으로 포함되어 있습니다.")
        first_lines = content.decode('utf-8-sig').splitlines()[:5]
        for idx, line in enumerate(first_lines):
            print(f" Row {idx+1}: {line}")
    else:
        print("\n[FAIL] UTF-8-SIG BOM 헤더 누락!")
else:
    print(f"오류: {response.text}")
