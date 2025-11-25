"""
일일보고서 워크플로우 테스트 통합 스크립트

FSM, TodayPlan, MainTasks 흐름 테스트

사용법:
    python -m debug.test_daily_workflow --plan      # TodayPlan 체인만
    python -m debug.test_daily_workflow --fsm       # FSM만
    python -m debug.test_daily_workflow --flow      # 전체 흐름
"""
import sys
from pathlib import Path
import argparse
from datetime import date

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from app.domain.daily.fsm_state import DailyFSMContext
from app.domain.daily.time_slots import generate_time_slots
from app.domain.daily.task_parser import TaskParser
from app.domain.daily.daily_fsm import DailyReportFSM
from app.domain.daily.daily_builder import build_daily_report
from app.domain.daily.main_tasks_store import get_main_tasks_store
from app.domain.planner.today_plan_chain import TodayPlanGenerator
from app.domain.planner.tools import YesterdayReportTool
from app.domain.planner.schemas import TodayPlanRequest
from app.infrastructure.database.session import SessionLocal
from app.llm.client import get_llm


def test_today_plan(owner: str = "김보험", target_date: date = None):
    """TodayPlan 체인 테스트"""
    print("=" * 80)
    print("📋 TodayPlan 체인 테스트")
    print("=" * 80)
    
    if target_date is None:
        target_date = date.today()
    
    print(f"\n작성자: {owner}, 날짜: {target_date}")
    
    db = SessionLocal()
    
    try:
        # TodayPlan 생성
        print(f"\n⏳ 추천 업무 생성 중...")
        
        retriever_tool = YesterdayReportTool(db)
        llm_client = get_llm(model="gpt-4o-mini")
        generator = TodayPlanGenerator(retriever_tool, llm_client, vector_retriever=None)
        
        request = TodayPlanRequest(owner=owner, target_date=target_date)
        
        # 동기 실행
        import asyncio
        result = asyncio.run(generator.generate(request))
        
        print(f"✅ 추천 업무 생성 완료!")
        print(f"   요약: {result.summary}")
        print(f"   업무 수: {len(result.tasks)}")
        
        print(f"\n📋 추천 업무 목록:")
        for i, task in enumerate(result.tasks, 1):
            print(f"   [{i}] {task.title}")
            print(f"       - 설명: {task.description}")
            print(f"       - 우선순위: {task.priority} / 예상시간: {task.expected_time}")
            print(f"       - 카테고리: {task.category}")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_fsm_simple(owner: str = "김보험"):
    """FSM 간단 테스트"""
    print("=" * 80)
    print("🔄 일일보고서 FSM 테스트")
    print("=" * 80)
    
    print(f"\n작성자: {owner}")
    
    try:
        # 시간대 생성
        time_ranges = generate_time_slots("09:00", "12:00", 60)
        print(f"\n생성된 시간대: {time_ranges}")
        
        # FSM 컨텍스트 생성
        context = DailyFSMContext(
            owner=owner,
            target_date=date.today(),
            time_ranges=time_ranges,
            today_main_tasks=[],  # 빈 리스트로 테스트
            session_id="test_session"
        )
        
        # FSM 초기화
        llm_client = get_llm(model="gpt-4o-mini")
        parser = TaskParser(llm_client)
        fsm = DailyReportFSM(parser)
        
        # 세션 시작
        print(f"\n⏳ FSM 세션 시작...")
        result = fsm.start_session(context)
        
        print(f"✅ FSM 초기화 완료!")
        print(f"   첫 질문: {result['question']}")
        print(f"   세션 ID: {result['session_id']}")
        
        # 시뮬레이션: 첫 번째 답변
        print(f"\n⏳ 첫 번째 답변 처리...")
        test_answer = "고객 3명 상담 및 보험 계약 검토"
        result = fsm.process_answer(result["state"], test_answer)
        
        print(f"✅ 답변 처리 완료!")
        print(f"   다음 질문: {result.get('question', 'N/A')}")
        print(f"   수집된 업무: {len(result['state'].time_tasks)}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_flow(owner: str = "김보험"):
    """전체 워크플로우 테스트"""
    print("=" * 80)
    print("🔄 일일보고서 전체 워크플로우 테스트")
    print("=" * 80)
    
    print(f"\n작성자: {owner}")
    target_date = date.today()
    
    # Step 1: TodayPlan으로 업무 추천
    print(f"\n[1단계] 업무 추천")
    print("-" * 80)
    
    db = SessionLocal()
    
    try:
        retriever_tool = YesterdayReportTool(db)
        llm_client = get_llm(model="gpt-4o-mini")
        generator = TodayPlanGenerator(retriever_tool, llm_client, vector_retriever=None)
        
        request = TodayPlanRequest(owner=owner, target_date=target_date)
        
        import asyncio
        plan_result = asyncio.run(generator.generate(request))
        
        print(f"✅ 추천 업무: {len(plan_result.tasks)}개")
        for i, task in enumerate(plan_result.tasks[:3], 1):
            print(f"   {i}. {task.title}")
        
        # Step 2: 업무 선택 및 저장
        print(f"\n[2단계] 업무 선택 및 저장")
        print("-" * 80)
        
        selected_tasks = []
        for task in plan_result.tasks[:3]:
            selected_tasks.append({
                "title": task.title,
                "description": task.description,
                "category": task.category,
                "priority": task.priority,
                "expected_time": task.expected_time
            })
        
        store = get_main_tasks_store()
        store.save(owner, target_date, selected_tasks, append=False)
        
        print(f"✅ {len(selected_tasks)}개 업무 저장 완료")
        
        # Step 3: 저장된 업무 조회
        print(f"\n[3단계] 저장된 업무 조회")
        print("-" * 80)
        
        retrieved_tasks = store.get(owner, target_date)
        print(f"✅ 조회된 업무: {len(retrieved_tasks)}개")
        for i, task in enumerate(retrieved_tasks, 1):
            print(f"   {i}. {task.get('title', 'N/A')}")
        
        # Step 4: FSM 시작 (간단 시뮬레이션)
        print(f"\n[4단계] FSM 시작 (시뮬레이션)")
        print("-" * 80)
        
        time_ranges = generate_time_slots("09:00", "12:00", 60)
        context = DailyFSMContext(
            owner=owner,
            target_date=target_date,
            time_ranges=time_ranges,
            today_main_tasks=retrieved_tasks,
            session_id="test_flow_session"
        )
        
        parser = TaskParser(llm_client)
        fsm = DailyReportFSM(parser)
        result = fsm.start_session(context)
        
        print(f"✅ FSM 세션 시작 완료")
        print(f"   첫 질문: {result['question']}")
        
        print(f"\n✅ 전체 워크플로우 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='일일보고서 워크플로우 테스트')
    parser.add_argument('--plan', action='store_true', help='TodayPlan만 테스트')
    parser.add_argument('--fsm', action='store_true', help='FSM만 테스트')
    parser.add_argument('--flow', action='store_true', help='전체 흐름 테스트')
    parser.add_argument('--owner', default='김보험', help='작성자')
    args = parser.parse_args()
    
    print()
    print("=" * 80)
    print("🔬 일일보고서 워크플로우 테스트")
    print("=" * 80)
    print()
    
    if args.plan:
        test_today_plan(args.owner)
    elif args.fsm:
        test_fsm_simple(args.owner)
    elif args.flow:
        test_full_flow(args.owner)
    else:
        print("⚠️  테스트 모드를 지정해주세요.")
        print("   예: python -m debug.test_daily_workflow --flow")
    
    print()


if __name__ == "__main__":
    main()

