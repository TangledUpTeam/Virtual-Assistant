"""
Brainstorming SessionManager 동시성 테스트

여러 스레드가 동시에 세션을 생성하고 수정하는 상황을 시뮬레이션합니다.
Race condition, 데이터 무결성, 성능을 검증합니다.
"""

import threading
import time
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from app.domain.brainstorming.session_manager import SessionManager


def test_concurrent_session_creation():
    """
    테스트 1: 동시 세션 생성
    - 100개 스레드가 동시에 세션 생성
    - 세션 ID 중복 없어야 함
    - 디렉토리도 각각 생성되어야 함
    """
    print("\n" + "="*60)
    print("📋 테스트 1: 동시 세션 생성 (100개 스레드)")
    print("="*60)
    
    session_manager = SessionManager()
    session_ids = []
    errors = []
    lock = threading.Lock()
    
    def create_session():
        try:
            session_id = session_manager.create_session()
            with lock:
                session_ids.append(session_id)
        except Exception as e:
            with lock:
                errors.append(str(e))
    
    # 100개 스레드 동시 실행
    threads = [threading.Thread(target=create_session) for _ in range(100)]
    
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.time()
    
    # 결과 검증
    unique_sessions = set(session_ids)
    
    print(f"✅ 완료 시간: {end - start:.3f}초")
    print(f"✅ 생성된 세션 수: {len(session_ids)}")
    print(f"✅ 고유 세션 수: {len(unique_sessions)}")
    print(f"✅ 오류 수: {len(errors)}")
    
    # 디렉토리 생성 확인
    directories_exist = 0
    for session_id in session_ids:
        session = session_manager.get_session(session_id)
        if session and Path(session['directory']).exists():
            directories_exist += 1
    
    print(f"✅ 생성된 디렉토리 수: {directories_exist}")
    
    # 중복 체크
    if (len(session_ids) == len(unique_sessions) == 100 and 
        directories_exist == 100 and len(errors) == 0):
        print("✅ 성공: 세션 ID 중복 없음, 디렉토리 정상 생성!")
        return True
    else:
        print(f"❌ 실패: 세션 ID 중복 또는 디렉토리 생성 실패!")
        if errors:
            print(f"   오류: {errors[:3]}")
        return False


def test_concurrent_session_updates():
    """
    테스트 2: 동시 세션 업데이트
    - 10개 세션에 각각 50개 스레드가 업데이트
    - 데이터 무결성 확인
    """
    print("\n" + "="*60)
    print("📋 테스트 2: 동시 세션 업데이트 (10 세션 × 50 업데이트)")
    print("="*60)
    
    session_manager = SessionManager()
    
    # 10개 세션 생성
    session_ids = [session_manager.create_session() for _ in range(10)]
    errors = []
    lock = threading.Lock()
    
    def update_session(session_id, worker_id):
        """세션의 q3_associations에 데이터 추가"""
        try:
            session = session_manager.get_session(session_id)
            if session:
                current_associations = session.get('q3_associations', [])
                new_associations = current_associations + [f"keyword_{worker_id}"]
                
                session_manager.update_session(
                    session_id,
                    {'q3_associations': new_associations}
                )
        except Exception as e:
            with lock:
                errors.append(f"{session_id}: {str(e)}")
    
    # 각 세션마다 50개 스레드가 동시에 업데이트
    threads = []
    for i, session_id in enumerate(session_ids):
        for j in range(50):
            worker_id = i * 50 + j
            t = threading.Thread(target=update_session, args=(session_id, worker_id))
            threads.append(t)
    
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.time()
    
    # 결과 검증
    print(f"✅ 완료 시간: {end - start:.3f}초")
    print(f"✅ 총 스레드 수: {len(threads)}")
    print(f"✅ 오류 수: {len(errors)}")
    
    # 각 세션의 키워드 개수 확인
    all_correct = True
    for session_id in session_ids:
        session = session_manager.get_session(session_id)
        if session:
            associations = session.get('q3_associations', [])
            # Race condition이 있으면 50개보다 적을 수 있음
            if len(associations) < 50:
                print(f"⚠️  세션 {session_id[:8]}: {len(associations)}/50 키워드 (일부 손실)")
                all_correct = False
        else:
            print(f"❌ 세션 {session_id[:8]}: 세션 없음")
            all_correct = False
    
    if all_correct and len(errors) == 0:
        print("✅ 성공: 모든 세션 업데이트 정상!")
        return True
    else:
        print(f"❌ 실패: 데이터 손실 또는 오류 발생!")
        print(f"   (Race condition으로 인한 데이터 손실 가능성)")
        if errors:
            print(f"   오류: {errors[:3]}")
        return False


def test_concurrent_mixed_operations():
    """
    테스트 3: 혼합 작업 (생성 + 읽기 + 쓰기 + 삭제)
    - 실제 아이디어 생성 시나리오와 유사
    """
    print("\n" + "="*60)
    print("📋 테스트 3: 혼합 작업 (실제 사용 시나리오)")
    print("="*60)
    
    session_manager = SessionManager()
    session_ids = []
    errors = []
    lock = threading.Lock()
    
    def brainstorming_workflow(worker_id):
        """실제 브레인스토밍 워크플로우 시뮬레이션"""
        try:
            # 1. 세션 생성
            session_id = session_manager.create_session()
            with lock:
                session_ids.append(session_id)
            
            # 2. Q1 입력
            session_manager.update_session(
                session_id,
                {'q1_purpose': f'Worker {worker_id}의 아이디어'}
            )
            
            # 3. Q2 생성
            session_manager.update_session(
                session_id,
                {'q2_warmup': ['질문1', '질문2']}
            )
            
            # 4. Q3 입력
            associations = [f'키워드{i}' for i in range(10)]
            session_manager.update_session(
                session_id,
                {'q3_associations': associations}
            )
            
            # 5. 아이디어 생성
            ideas = [
                {'title': f'아이디어 {i}', 'content': '내용'}
                for i in range(3)
            ]
            session_manager.update_session(
                session_id,
                {'ideas': ideas}
            )
            
            # 6. 세션 정보 조회
            session = session_manager.get_session(session_id)
            assert session is not None, "세션 조회 실패"
            assert len(session['q3_associations']) == 10, "키워드 개수 불일치"
            assert len(session['ideas']) == 3, "아이디어 개수 불일치"
            
            # 7. 일부 세션 삭제 (50% 확률)
            if worker_id % 2 == 0:
                session_manager.delete_session(session_id)
                
        except Exception as e:
            with lock:
                errors.append(f"Worker {worker_id}: {str(e)}")
    
    # 50명의 사용자 동시 브레인스토밍
    threads = [threading.Thread(target=brainstorming_workflow, args=(i,)) for i in range(50)]
    
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.time()
    
    # 결과 검증
    remaining_sessions = session_manager.list_sessions()
    
    print(f"✅ 완료 시간: {end - start:.3f}초")
    print(f"✅ 생성된 세션 수: {len(session_ids)}")
    print(f"✅ 남은 세션 수: {len(remaining_sessions)}")
    print(f"✅ 오류 수: {len(errors)}")
    
    if len(errors) == 0 and len(session_ids) == 50:
        print("✅ 성공: 모든 브레인스토밍 워크플로우 정상 완료!")
        print(f"   (삭제된 세션: 약 {50 - len(remaining_sessions)}개)")
        return True
    else:
        print(f"❌ 실패: 오류 발생!")
        if errors:
            print(f"   오류: {errors[:3]}")
        return False


def test_performance_benchmark():
    """
    테스트 4: 성능 벤치마크
    - 대량 요청 처리 속도 측정
    """
    print("\n" + "="*60)
    print("📋 테스트 4: 성능 벤치마크 (500개 세션 워크플로우)")
    print("="*60)
    
    session_manager = SessionManager()
    
    def worker(worker_id):
        """전체 워크플로우 실행"""
        session_id = session_manager.create_session()
        
        # Q1-Q3 업데이트
        session_manager.update_session(
            session_id,
            {
                'q1_purpose': f'목적 {worker_id}',
                'q2_warmup': ['질문1', '질문2'],
                'q3_associations': [f'키워드{i}' for i in range(10)]
            }
        )
        
        # 아이디어 생성
        session_manager.update_session(
            session_id,
            {
                'ideas': [
                    {'title': f'아이디어 {i}', 'content': '내용'}
                    for i in range(3)
                ]
            }
        )
        
        # 조회
        session_manager.get_session(session_id)
    
    # 500명의 사용자 동시 접속
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(500)]
    
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.time()
    
    total_time = end - start
    ops_per_sec = (500 * 4) / total_time  # 4 operations per thread
    
    print(f"✅ 완료 시간: {total_time:.3f}초")
    print(f"✅ 총 작업 수: {500 * 4:,}개")
    print(f"✅ 처리량: {ops_per_sec:,.0f} ops/sec")
    print(f"✅ 평균 응답 시간: {(total_time / 500) * 1000:.2f}ms")
    
    # 성능 기준: 500명이 15초 이내에 처리되어야 함
    if total_time < 15.0:
        print(f"✅ 성공: 성능 기준 통과! ({total_time:.2f}초 < 15초)")
        return True
    else:
        print(f"⚠️  경고: 성능 기준 미달 ({total_time:.2f}초 > 15초)")
        return False


def cleanup_test_sessions():
    """테스트 후 생성된 세션 정리"""
    print("\n🧹 테스트 세션 정리 중...")
    
    session_manager = SessionManager()
    session_ids = session_manager.list_sessions()
    
    for session_id in session_ids:
        try:
            session_manager.delete_session(session_id)
        except Exception as e:
            print(f"⚠️  세션 {session_id[:8]} 삭제 실패: {e}")
    
    print(f"✅ {len(session_ids)}개 세션 정리 완료")


def main():
    """모든 테스트 실행"""
    print("\n🚀 Brainstorming SessionManager 동시성 테스트 시작")
    print("="*60)
    
    results = []
    
    try:
        # 테스트 실행
        results.append(("동시 세션 생성", test_concurrent_session_creation()))
        results.append(("동시 세션 업데이트", test_concurrent_session_updates()))
        results.append(("혼합 작업", test_concurrent_mixed_operations()))
        results.append(("성능 벤치마크", test_performance_benchmark()))
        
    finally:
        # 테스트 세션 정리
        cleanup_test_sessions()
    
    # 최종 결과
    print("\n" + "="*60)
    print("📊 최종 결과")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print("\n" + "="*60)
    print(f"🎯 전체: {passed}/{total} 테스트 통과")
    print("="*60)
    
    if passed == total:
        print("✅ 모든 동시성 테스트 통과! 🎉")
        return 0
    else:
        print("❌ 일부 테스트 실패")
        return 1


if __name__ == "__main__":
    exit(main())

