<!-- 생성일 2025.11.19 15:31 -->

# Task
- **Input**으로 주어진 *pdf*파일을 **json**형태의 청크파일로 변환하는 작업을 수행한다.

# Input
- backend/councel/dataset/adler/case 안에 있는 파일들을 모두 청크파일로 변환한다.
- backend/councel/dataset/adler/theory 안에 있는 파일들을 모두 청크파일로 변환한다.
- backend/councel/dataset/adler/interventions 안에 있는 파일들을 모두 청크파일로 변환한다.
- backend/councel/dataset/adler/qna 안에 있는 파일들을 모두 청크파일로 변환한다.
- backend/councel/dataset/adler/tone 안에 있는 파일들을 모두 청크파일로 변환한다.

# Rules

# Output Format

```json
{
  "id": "rogers_012",
  "text": "칼 로저스는 인간중심 상담 이론의 핵심은...",
  "metadata": {
    "source": "rogers_theory.md",
    "author": "Carl Rogers",
    "category": "theory",
    "topic": "client-centered therapy",
    "year": "1951",
    "tags": ["칼 로저스", "인간중심", "상담이론"],
    "chunk_index": 12,
    "total_chunks": 38
  }
}