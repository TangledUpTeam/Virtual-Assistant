"""Collection 내용 확인"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.vector_store import get_unified_collection

# Collection 가져오기
col = get_unified_collection()

# 각 doc_type별 개수 확인
print("="*80)
print("Collection 내용 확인")
print("="*80)

# Daily
try:
    result_daily = col.get(limit=1, where={"doc_type": "daily"})
    daily_count = len(result_daily["ids"])
    print(f"Daily: {daily_count}개 (샘플 확인)")
except Exception as e:
    print(f"Daily: 확인 실패 - {e}")

# Weekly
try:
    result_weekly = col.get(limit=1, where={"doc_type": "weekly"})
    weekly_count = len(result_weekly["ids"])
    print(f"Weekly: {weekly_count}개 (샘플 확인)")
except Exception as e:
    print(f"Weekly: 0개")

# KPI
try:
    result_kpi = col.get(limit=1, where={"doc_type": "kpi"})
    kpi_count = len(result_kpi["ids"])
    print(f"KPI: {kpi_count}개 (샘플 확인)")
except Exception as e:
    print(f"KPI: 확인 실패 - {e}")

# Template
try:
    result_template = col.get(limit=1, where={"doc_type": "template"})
    template_count = len(result_template["ids"])
    print(f"Template: {template_count}개 (샘플 확인)")
except Exception as e:
    print(f"Template: 0개")

# 전체
print(f"\n전체 문서 수: {col.count()}개")
print("="*80)

