from table_merger import merge_multi_page_tables
import json

raw_rows = [
    {
        "프로젝트명": "test_proj",
        "시추공명": "BH-1",
        "경도": "127",
        "위도": "37",
        "표고": "10.0",
        "상심도": 0.0,
        "하심도": 1.5,
        "지층명": "매립층"
    },
    {
        "프로젝트명": "test_proj",
        "시추공명": "BH-1",
        "경도": "127",
        "위도": "37",
        "표고": "10.0",
        "상심도": 1.5,
        "하심도": 3.0,
        "지층명": "풍화암"
    }
]

merged = merge_multi_page_tables([{"data": raw_rows}])
print(json.dumps(merged, indent=2, ensure_ascii=False))
