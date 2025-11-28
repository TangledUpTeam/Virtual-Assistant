"""Insurance Manual PDF 처리 결과 분석"""

import json
from pathlib import Path

path = Path("app/domain/rag/Insurance/internal_insurance/processed/insurance_manual.json")

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

pages = data["pages"]
total = len(pages)

vision = sum(1 for p in pages if p["mode"] == "vision")
fallback = sum(1 for p in pages if p["mode"] == "vision-fallback")
text = sum(1 for p in pages if p["mode"] == "text")
empty = sum(1 for p in pages if p["mode"] == "empty")
error = sum(1 for p in pages if p["mode"] == "error")

print("=" * 50)
print("Insurance Manual PDF 처리 결과 분석")
print("=" * 50)
print(f"총 페이지: {total}")
print(f"Vision: {vision} ({vision/total:.1%})")
print(f"Vision-fallback: {fallback} ({fallback/total:.1%})")
print(f"Text: {text} ({text/total:.1%})")
print(f"Empty: {empty} ({empty/total:.1%})")
print(f"Error: {error} ({error/total:.1%})")
print("=" * 50)
print(f"Vision 사용률: {(vision + fallback)/total:.1%}")
print(f"Text 모드 비율: {text/total:.1%}")
print("=" * 50)

# 추가 통계
has_tables = sum(1 for p in pages if p.get("has_tables", False))
has_images = sum(1 for p in pages if p.get("has_images", False))
print(f"\n표 있는 페이지: {has_tables} ({has_tables/total:.1%})")
print(f"이미지 있는 페이지: {has_images} ({has_images/total:.1%})")

