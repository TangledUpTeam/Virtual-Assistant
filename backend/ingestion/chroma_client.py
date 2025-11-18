"""
Chroma Cloud 클라이언트 설정

고정된 API 키와 tenant/database 사용
"""
import chromadb
from chromadb import Collection


# Chroma Cloud 설정 (고정값)
CHROMA_API_KEY = "ck-BcnEUpVpQa3x18paPEMqLSobcLHFSaga1kekufxB24tn"
CHROMA_TENANT = "87acc175-c5c2-44df-97ff-c0b914e35994"
CHROMA_DATABASE = "Virtual_Assistant"

# 컬렉션 이름
COLLECTION_REPORTS = "reports"
COLLECTION_KPI = "kpi"


class ChromaCloudService:
    """Chroma Cloud 서비스"""
    
    def __init__(self):
        """Chroma Cloud 클라이언트 초기화"""
        print("🔗 Chroma Cloud 연결 중...")
        
        self.client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE
        )
        
        print("✅ Chroma Cloud 연결 성공")
    
    def get_or_create_collection(self, name: str) -> Collection:
        """
        컬렉션 가져오기 또는 생성
        
        Args:
            name: 컬렉션 이름
            
        Returns:
            Collection 객체
        """
        print(f"📦 컬렉션 '{name}' 가져오기/생성 중...")
        
        try:
            # get_or_create_collection 사용 (가장 안전한 방법)
            collection = self.client.get_or_create_collection(name=name)
            print(f"✅ 컬렉션 '{name}' 준비 완료")
            return collection
        
        except KeyError as e:
            # _type 오류 발생 시, 컬렉션이 이미 존재한다고 가정
            print(f"⚠️  응답 파싱 오류 발생 (컬렉션은 생성되었을 가능성 높음)")
            print(f"⚠️  재시도 중...")
            
            try:
                # 다시 시도
                collection = self.client.get_or_create_collection(name=name)
                print(f"✅ 컬렉션 '{name}' 준비 완료 (재시도 성공)")
                return collection
            except Exception:
                # 최종 실패 시 에러 발생
                print(f"❌ 컬렉션 생성 실패")
                raise
        
        except Exception as e:
            print(f"❌ 컬렉션 처리 오류: {e}")
            raise
    
    def get_reports_collection(self) -> Collection:
        """
        Reports 컬렉션 가져오기
        
        Returns:
            Reports Collection
        """
        return self.get_or_create_collection(name=COLLECTION_REPORTS)
    
    def get_kpi_collection(self) -> Collection:
        """
        KPI 컬렉션 가져오기
        
        Returns:
            KPI Collection
        """
        return self.get_or_create_collection(name=COLLECTION_KPI)
    
    def get_collection_info(self, collection: Collection) -> dict:
        """
        컬렉션 정보 조회
        
        Args:
            collection: Collection 객체
            
        Returns:
            컬렉션 정보 딕셔너리
        """
        count = collection.count()
        
        return {
            "name": collection.name,
            "count": count,
            "metadata": collection.metadata
        }
    
    def delete_collection(self, name: str):
        """
        컬렉션 삭제
        
        Args:
            name: 컬렉션 이름
        """
        try:
            self.client.delete_collection(name=name)
            print(f"✅ 컬렉션 삭제됨: {name}")
        except Exception as e:
            print(f"❌ 컬렉션 삭제 오류: {e}")


# 전역 서비스 인스턴스 (lazy initialization)
_chroma_service = None


def get_chroma_service() -> ChromaCloudService:
    """
    Chroma Cloud 서비스 싱글톤 인스턴스 반환
    
    Returns:
        ChromaCloudService 인스턴스
    """
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaCloudService()
    return _chroma_service


def get_reports_collection() -> Collection:
    """Reports 컬렉션 가져오기 (헬퍼 함수)"""
    service = get_chroma_service()
    return service.get_reports_collection()


def get_kpi_collection() -> Collection:
    """KPI 컬렉션 가져오기 (헬퍼 함수)"""
    service = get_chroma_service()
    return service.get_kpi_collection()

