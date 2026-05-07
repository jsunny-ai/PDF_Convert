from core.master_hybrid_extractor import MasterHybridExtractor
import json
import logging

logging.basicConfig(level=logging.INFO)

def test_clustering():
    pdf_path = r"C:\antigravity\#1_1_PDF_Download\PDF_Storage\경기도 수원시\수원시권선구\page2_project4_report.pdf"
    extractor = MasterHybridExtractor()
    
    print(f"--- Testing PDF: {pdf_path} ---")
    result = extractor.process_file(pdf_path, "TestProject")
    
    if result:
        print(f"Extracted {len(result)} rows.")
        # 좌표 확인
        valid_coords = [r for r in result if r.get("lon_wgs84") != ""]
        print(f"Valid coordinates: {len(valid_coords)}")
        for r in result[:3]:
            print(f"BH: {r.get('시추공명')}, Lon: {r.get('lon_wgs84')}, Lat: {r.get('lat_wgs84')}, CRS: {r.get('meta_crs')}")
    else:
        print("Extraction failed or no data.")

if __name__ == "__main__":
    test_clustering()
