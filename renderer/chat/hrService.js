/**
 * HR 관련 질문 처리 서비스
 * RAG API를 통해 내부 문서 기반 답변 제공
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// HR 관련 키워드 목록 (internal_docs 기반)
const HR_KEYWORDS = [
  '연차', '휴가', '근로시간', '유연근무', '근무지', '변경',
  '급여', '성과급', '연말정산', '명세서',
  '복지', '건강검진', '보험', '선택적', '제휴',
  '교육', '승진', '인사평가', '포상', '의무교육',
  '법인카드', '규정', '정보보호', '개인정보', '가치평가',
  '금융소비자', '프로세스', '신청', '지원', '기준'
];

/**
 * HR 관련 질문인지 확인
 * @param {string} text - 사용자 입력 텍스트
 * @returns {boolean} HR 질문 여부
 */
export function isHRQuestion(text) {
  return HR_KEYWORDS.some(keyword => text.includes(keyword));
}

/**
 * RAG API를 통해 HR 관련 질문에 답변
 * @param {string} query - 사용자 질문
 * @returns {Promise<{type: string, data: any}>}
 */
export async function queryHRDocument(query) {
  try {
    console.log('📚 HR RAG API 호출:', query);
    
    const response = await fetch(`${API_BASE_URL}/rag/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        top_k: 3  // 상위 3개 문서 청크 검색
      })
    });
    
    if (!response.ok) {
      throw new Error(`RAG API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ HR RAG 응답:', result);
    
    // 답변에는 이미 출처 정보가 포함되어 있음 (예: "출처: 연차규정.txt")
    return {
      type: 'text',
      data: result.answer
    };
  } catch (error) {
    console.error('❌ HR RAG API 호출 오류:', error);
    return {
      type: 'error',
      data: 'HR 문서 검색 중 오류가 발생했습니다. 백엔드 서버가 실행 중인지 확인해주세요.'
    };
  }
}

/**
 * HR 키워드 목록 가져오기 (디버깅/확장용)
 * @returns {Array<string>} HR 키워드 배열
 */
export function getHRKeywords() {
  return [...HR_KEYWORDS];
}

/**
 * Notion 컨텍스트를 포함한 HR 질의
 * @param {string} query - 사용자 질문
 * @param {string} notionContext - Notion 페이지 내용 (마크다운)
 * @returns {Promise<{type: string, data: any}>}
 */
export async function queryHRWithNotion(query, notionContext) {
  try {
    console.log('📚 HR RAG API 호출 (Notion 컨텍스트 포함):', query);
    
    // Notion 컨텍스트를 질문에 추가
    const enhancedQuery = `${query}\n\n참고 자료:\n${notionContext}`;
    
    const response = await fetch(`${API_BASE_URL}/rag/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: enhancedQuery,
        top_k: 3
      })
    });
    
    if (!response.ok) {
      throw new Error(`RAG API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ HR RAG 응답 (Notion 컨텍스트 포함):', result);
    
    return {
      type: 'text',
      data: result.answer
    };
  } catch (error) {
    console.error('❌ HR RAG API 호출 오류:', error);
    return {
      type: 'error',
      data: 'HR 문서 검색 중 오류가 발생했습니다.'
    };
  }
}

