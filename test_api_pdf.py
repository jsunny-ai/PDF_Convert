import requests
import json
import time

url = "http://127.0.0.1:5000/api/convert"
filepath = r"C:\antigravity\#1_2_PDF_CSV\test_upload.pdf"

print("1. 파일 (PDF) 업로드 및 하이브리드(ODL Fallback) 변환 요청 시작...")
start = time.time()
with open(filepath, "rb") as f:
    files = {"pdf_files": f}
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
else:
    print(f"오류: {response.text}")
