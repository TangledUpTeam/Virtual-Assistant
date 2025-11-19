"""
Daily Report FSM

시간대별 일일보고서 입력 FSM (Simple State Machine)

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Dict, Any
from app.domain.daily.fsm_state import DailyFSMContext, DailyState
from app.domain.daily.task_parser import TaskParser


class DailyReportFSM:
    """일일보고서 입력 FSM (단순 상태 머신)"""
    
    def __init__(self, task_parser: TaskParser):
        """
        초기화
        
        Args:
            task_parser: TaskParser 인스턴스
        """
        self.task_parser = task_parser
    
    def _ask_question(self, context: DailyFSMContext) -> DailyFSMContext:
        """시간대 질문 생성"""
        if context.current_index < len(context.time_ranges):
            time_range = context.time_ranges[context.current_index]
            context.current_question = f"{time_range} 무엇을 했나요?"
            context.current_state = DailyState.ASK_TIME_RANGE
        else:
            context.current_state = DailyState.FINISHED
            context.finished = True
            context.current_question = ""
        
        return context
    
    def _parse_answer(self, context: DailyFSMContext) -> DailyFSMContext:
        """답변 파싱 및 저장"""
        if context.last_answer and context.current_index < len(context.time_ranges):
            time_range = context.time_ranges[context.current_index]
            
            # LLM으로 파싱
            task_dict = self.task_parser.parse_sync(
                text=context.last_answer,
                time_range=time_range
            )
            
            # time_tasks에 추가
            context.time_tasks.append(task_dict)
            context.current_state = DailyState.PARSE_TASK
        
        return context
    
    def _move_next(self, context: DailyFSMContext) -> DailyFSMContext:
        """다음 시간대로 이동"""
        context.current_index += 1
        context.last_answer = ""
        context.current_state = DailyState.NEXT_TIME_RANGE
        
        if context.current_index >= len(context.time_ranges):
            context.current_state = DailyState.FINISHED
            context.finished = True
        
        return context
    
    def start_session(self, context: DailyFSMContext) -> Dict[str, Any]:
        """
        세션 시작
        
        Args:
            context: 초기 컨텍스트
            
        Returns:
            첫 질문 정보
        """
        # 초기화
        context.current_state = DailyState.WAIT_START
        context.current_index = 0
        context.finished = False
        
        # 첫 질문 생성
        context = self._ask_question(context)
        
        return {
            "session_id": context.session_id,
            "question": context.current_question,
            "current_index": context.current_index,
            "total_ranges": len(context.time_ranges),
            "finished": context.finished,
            "state": context
        }
    
    def process_answer(
        self,
        context: DailyFSMContext,
        answer: str
    ) -> Dict[str, Any]:
        """
        답변 처리
        
        Args:
            context: 현재 컨텍스트
            answer: 사용자 답변
            
        Returns:
            다음 질문 또는 완료 정보
        """
        # 답변 저장
        context.last_answer = answer
        context.current_state = DailyState.RECEIVE_ANSWER
        
        # 답변 파싱 및 저장
        context = self._parse_answer(context)
        
        # 다음 시간대로 이동
        context = self._move_next(context)
        
        # 다음 질문 생성 (완료되지 않았으면)
        if not context.finished:
            context = self._ask_question(context)
        
        return {
            "session_id": context.session_id,
            "question": context.current_question if not context.finished else "",
            "current_index": context.current_index,
            "total_ranges": len(context.time_ranges),
            "finished": context.finished,
            "state": context,
            "tasks_collected": len(context.time_tasks)
        }

