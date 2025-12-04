"""Notion 블록과 마크다운 간 변환 유틸리티"""
from typing import List, Dict, Any


def blocks_to_markdown(blocks: List[Dict[str, Any]]) -> str:
    """
    Notion 블록을 마크다운으로 변환
    
    Args:
        blocks: Notion 블록 리스트
    
    Returns:
        마크다운 문자열
    """
    markdown_lines = []
    
    for block in blocks:
        block_type = block.get("type")
        
        if block_type == "paragraph":
            text = _extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
            if text:
                markdown_lines.append(text)
                markdown_lines.append("")  # 단락 사이 공백
        
        elif block_type == "heading_1":
            text = _extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
            if text:
                markdown_lines.append(f"# {text}")
                markdown_lines.append("")
        
        elif block_type == "heading_2":
            text = _extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
            if text:
                markdown_lines.append(f"## {text}")
                markdown_lines.append("")
        
        elif block_type == "heading_3":
            text = _extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
            if text:
                markdown_lines.append(f"### {text}")
                markdown_lines.append("")
        
        elif block_type == "bulleted_list_item":
            text = _extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
            if text:
                markdown_lines.append(f"- {text}")
        
        elif block_type == "numbered_list_item":
            text = _extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
            if text:
                markdown_lines.append(f"1. {text}")
        
        elif block_type == "code":
            code_data = block.get("code", {})
            text = _extract_rich_text(code_data.get("rich_text", []))
            language = code_data.get("language", "")
            if text:
                markdown_lines.append(f"```{language}")
                markdown_lines.append(text)
                markdown_lines.append("```")
                markdown_lines.append("")
        
        elif block_type == "quote":
            text = _extract_rich_text(block.get("quote", {}).get("rich_text", []))
            if text:
                markdown_lines.append(f"> {text}")
                markdown_lines.append("")
        
        elif block_type == "divider":
            markdown_lines.append("---")
            markdown_lines.append("")
        
        elif block_type == "to_do":
            to_do_data = block.get("to_do", {})
            text = _extract_rich_text(to_do_data.get("rich_text", []))
            checked = to_do_data.get("checked", False)
            checkbox = "[x]" if checked else "[ ]"
            if text:
                markdown_lines.append(f"- {checkbox} {text}")
    
    return "\n".join(markdown_lines)


def _extract_rich_text(rich_text_array: List[Dict[str, Any]]) -> str:
    """
    Notion rich_text 배열에서 텍스트 추출
    
    Args:
        rich_text_array: Notion rich_text 배열
    
    Returns:
        추출된 텍스트
    """
    texts = []
    for item in rich_text_array:
        if item.get("type") == "text":
            text = item.get("text", {}).get("content", "")
            
            # 스타일 적용 (볼드, 이탤릭 등)
            annotations = item.get("annotations", {})
            if annotations.get("bold"):
                text = f"**{text}**"
            if annotations.get("italic"):
                text = f"*{text}*"
            if annotations.get("code"):
                text = f"`{text}`"
            if annotations.get("strikethrough"):
                text = f"~~{text}~~"
            
            texts.append(text)
    
    return "".join(texts)


def markdown_to_blocks(markdown: str) -> List[Dict[str, Any]]:
    """
    마크다운을 Notion 블록으로 변환
    
    Args:
        markdown: 마크다운 문자열
    
    Returns:
        Notion 블록 리스트
    """
    blocks = []
    lines = markdown.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 빈 줄 건너뛰기
        if not line:
            i += 1
            continue
        
        # 헤딩
        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        
        # 코드 블록
        elif line.startswith("```"):
            language = line[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_content = "\n".join(code_lines)
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": code_content}}],
                    "language": language
                }
            })
        
        # 인용구
        elif line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        
        # 구분선
        elif line == "---":
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        
        # 불릿 리스트
        elif line.startswith("- ") and not line.startswith("- [ ]") and not line.startswith("- [x]"):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        
        # 체크박스
        elif line.startswith("- [ ]") or line.startswith("- [x]"):
            checked = line.startswith("- [x]")
            text = line[5:].strip()
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": text}}],
                    "checked": checked
                }
            })
        
        # 숫자 리스트
        elif line[0].isdigit() and ". " in line:
            text = line.split(". ", 1)[1]
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            })
        
        # 일반 단락
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })
        
        i += 1
    
    return blocks

