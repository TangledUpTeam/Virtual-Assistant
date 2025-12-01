"""
Insurance RAG PDF 추출 모듈 - 프롬프트 정의

Vision OCR 및 LLM 병합에 사용되는 프롬프트 문자열
"""

# Vision OCR 프롬프트
VISION_OCR_PROMPT = (
    "You are an expert OCR and document formatter for Korean insurance manuals.\n"
    "Read the page image and output a clean, well-structured Markdown representation.\n"
    "- Preserve headings, bullet points, tables.\n"
    "- Only transcribe; do not add any explanation.\n"
)

# LLM 병합 프롬프트 템플릿
LLM_MERGE_PROMPT_TEMPLATE = """당신은 보험약관 문서를 재구성하는 전문가입니다.

아래 두 개의 출처에서 추출한 텍스트를 합쳐
중복된 문장/문단/표는 하나로 통합하고,
구조가 자연스럽고 잘 정리된 Markdown 형태로 정리해주세요.

규칙:
- 동일하거나 유사한 내용은 하나로만 유지합니다.
- Vision OCR 특유의 오탈자는 raw_text 내용을 우선합니다.
- 표는 Vision OCR의 Markdown 테이블 형식을 우선합니다.
- 원래 문서의 논리 구조(제목 → 내용 → 표 → 내용)를 유지해주세요.
- 생성하지 말고, 주어진 내용만 재구성하세요.

아래는 두 가지 입력입니다.

[TEXT MODE EXTRACTED]
{raw_text}

[VISION OCR]
{vision_markdown}"""


def get_llm_merge_prompt(raw_text: str, vision_markdown: str) -> str:
    """
    LLM 병합 프롬프트 생성
    
    Args:
        raw_text: PyMuPDF로 추출한 원문 텍스트
        vision_markdown: Vision OCR로 추출한 Markdown 텍스트
        
    Returns:
        완성된 프롬프트 문자열
    """
    return LLM_MERGE_PROMPT_TEMPLATE.format(
        raw_text=raw_text if raw_text.strip() else "(텍스트 없음)",
        vision_markdown=vision_markdown if vision_markdown.strip() else "(Vision OCR 결과 없음)"
    )

