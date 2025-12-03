"""Notion API Tool (공식 SDK 사용)"""
from typing import Optional, Dict, Any, List
from notion_client import AsyncClient
from notion_client.errors import APIResponseError
from .token_manager import load_token
from .notion_utils import blocks_to_markdown, markdown_to_blocks

async def create_page(user_id: str, parent_page_id: str, title: str, content: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Notion 페이지 생성"""
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        page_data = {
            "parent": {"page_id": parent_page_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}}
        }
        
        if content:
            page_data["children"] = content
        else:
            page_data["children"] = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]
        
        result = await notion.pages.create(**page_data)
        
        return {"success": True, "data": {"page_id": result.get("id"), "url": result.get("url"), "created_time": result.get("created_time"), "title": title}, "error": None}
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"페이지 생성 중 오류: {str(e)}"}

async def add_database_item(user_id: str, database_id: str, properties_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Notion 데이터베이스에 항목 추가"""
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        result = await notion.pages.create(parent={"database_id": database_id}, properties=properties_dict)
        
        return {"success": True, "data": {"page_id": result.get("id"), "url": result.get("url"), "created_time": result.get("created_time"), "properties": result.get("properties", {})}, "error": None}
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"데이터베이스 항목 추가 중 오류: {str(e)}"}

async def query_database(user_id: str, database_id: str, filter_dict: Optional[Dict] = None, sorts: Optional[List[Dict]] = None, page_size: int = 100) -> Dict[str, Any]:
    """Notion 데이터베이스 쿼리"""
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        query_params = {"page_size": page_size}
        if filter_dict:
            query_params["filter"] = filter_dict
        if sorts:
            query_params["sorts"] = sorts
        
        result = await notion.databases.query(database_id=database_id, **query_params)
        
        results = result.get("results", [])
        items = []
        for item in results:
            properties = item.get("properties", {})
            simple_props = {}
            for key, value in properties.items():
                prop_type = value.get("type")
                if prop_type == "title":
                    title_list = value.get("title", [])
                    simple_props[key] = title_list[0].get("text", {}).get("content", "") if title_list else ""
                elif prop_type == "rich_text":
                    text_list = value.get("rich_text", [])
                    simple_props[key] = text_list[0].get("text", {}).get("content", "") if text_list else ""
                elif prop_type == "select":
                    select_obj = value.get("select")
                    simple_props[key] = select_obj.get("name", "") if select_obj else ""
                elif prop_type == "date":
                    date_obj = value.get("date")
                    simple_props[key] = date_obj.get("start", "") if date_obj else ""
                elif prop_type == "number":
                    simple_props[key] = value.get("number")
                elif prop_type == "checkbox":
                    simple_props[key] = value.get("checkbox", False)
            
            items.append({"id": item.get("id"), "url": item.get("url"), "properties": simple_props})
        
        return {"success": True, "data": {"count": len(items), "items": items, "has_more": result.get("has_more", False)}, "error": None}
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"데이터베이스 쿼리 중 오류: {str(e)}"}

async def update_page(user_id: str, page_id: str, properties_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Notion 페이지 속성 업데이트"""
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        result = await notion.pages.update(page_id=page_id, properties=properties_dict)
        
        return {"success": True, "data": {"page_id": result.get("id"), "url": result.get("url"), "last_edited_time": result.get("last_edited_time")}, "error": None}
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"페이지 업데이트 중 오류: {str(e)}"}

async def append_block_children(user_id: str, block_id: str, children: List[Dict]) -> Dict[str, Any]:
    """Notion 블록에 자식 블록 추가"""
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        result = await notion.blocks.children.append(block_id=block_id, children=children)
        
        return {"success": True, "data": {"results": result.get("results", [])}, "error": None}
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"블록 추가 중 오류: {str(e)}"}


async def get_page_content(user_id: str, page_id: str) -> Dict[str, Any]:
    """
    Notion 페이지 내용을 마크다운으로 가져오기
    
    Args:
        user_id: 사용자 ID
        page_id: Notion 페이지 ID
    
    Returns:
        {"success": bool, "data": {"markdown": str, "title": str}, "error": str}
    """
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        # 페이지 정보 가져오기 (제목)
        page = await notion.pages.retrieve(page_id=page_id)
        
        # 제목 추출
        title = "Untitled"
        properties = page.get("properties", {})
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    title = title_array[0].get("text", {}).get("content", "Untitled")
                break
        
        # 페이지 블록 가져오기
        blocks_response = await notion.blocks.children.list(block_id=page_id)
        blocks = blocks_response.get("results", [])
        
        # 마크다운으로 변환
        markdown = blocks_to_markdown(blocks)
        
        return {
            "success": True,
            "data": {
                "markdown": markdown,
                "title": title,
                "page_id": page_id
            },
            "error": None
        }
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"페이지 내용 가져오기 중 오류: {str(e)}"}


async def search_pages(user_id: str, query: str, page_size: int = 10) -> Dict[str, Any]:
    """
    Notion 페이지 검색
    
    Args:
        user_id: 사용자 ID
        query: 검색 쿼리
        page_size: 결과 개수
    
    Returns:
        {"success": bool, "data": {"pages": List}, "error": str}
    """
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        # Notion 검색 API 호출
        search_response = await notion.search(
            query=query,
            filter={"property": "object", "value": "page"},
            page_size=page_size
        )
        
        results = search_response.get("results", [])
        pages = []
        
        for page in results:
            page_id = page.get("id")
            
            # 제목 추출
            title = "Untitled"
            properties = page.get("properties", {})
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_array = prop_value.get("title", [])
                    if title_array:
                        title = title_array[0].get("text", {}).get("content", "Untitled")
                    break
            
            pages.append({
                "id": page_id,
                "title": title,
                "url": page.get("url", "")
            })
        
        return {
            "success": True,
            "data": {
                "pages": pages,
                "count": len(pages)
            },
            "error": None
        }
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"페이지 검색 중 오류: {str(e)}"}


async def create_page_from_markdown(user_id: str, parent_id: str, title: str, markdown: str) -> Dict[str, Any]:
    """
    마크다운 내용으로 Notion 페이지 생성
    
    Args:
        user_id: 사용자 ID
        parent_id: 부모 페이지 ID
        title: 페이지 제목
        markdown: 마크다운 내용
    
    Returns:
        {"success": bool, "data": {"page_id": str, "url": str}, "error": str}
    """
    try:
        token_data = await load_token(user_id, "notion")
        if not token_data:
            return {"success": False, "data": None, "error": "Notion 토큰을 찾을 수 없습니다."}
        
        access_token = token_data.get("access_token")
        notion = AsyncClient(auth=access_token)
        
        # 마크다운을 Notion 블록으로 변환
        blocks = markdown_to_blocks(markdown)
        
        # 페이지 생성
        page_data = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            "children": blocks[:100]  # Notion API는 한 번에 최대 100개 블록만 허용
        }
        
        result = await notion.pages.create(**page_data)
        
        return {
            "success": True,
            "data": {
                "page_id": result.get("id"),
                "url": result.get("url"),
                "title": title
            },
            "error": None
        }
    except APIResponseError as e:
        return {"success": False, "data": None, "error": f"Notion API 오류: {e.message}"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"페이지 생성 중 오류: {str(e)}"}

