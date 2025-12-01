# Insurance RAG Tests

This directory contains unit tests for the Insurance RAG system.

## Running Tests

```bash
# Run all tests
python -m app.domain.rag.Insurance.tests.test_chunker
python -m app.domain.rag.Insurance.tests.test_page_processor

# Or use pytest
pytest app/domain/rag/Insurance/tests/
```

## Test Coverage

- `test_chunker.py`: Table splitting prevention tests
- `test_page_processor.py`: Page processing logic tests (with mocks)

All tests use mocks and do NOT make external API calls.
