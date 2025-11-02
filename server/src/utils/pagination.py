"""Pagination utilities for API responses."""

from typing import Dict, Optional
from urllib.parse import urlencode


def build_link_header(
    base_url: str,
    page: int,
    page_size: int,
    total_items: int,
    query_params: Optional[Dict[str, str]] = None
) -> str:
    """Build Link header according to RFC 5988 for pagination.
    
    Args:
        base_url: Base URL of the endpoint (without query params)
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_items: Total number of items
        query_params: Additional query parameters to include
        
    Returns:
        Link header value with rel='first', 'last', 'next', 'prev'
        
    Example:
        </api/v1/sessions/s_123/games?page=1&page_size=10>; rel="first",
        </api/v1/sessions/s_123/games?page=5&page_size=10>; rel="last",
        </api/v1/sessions/s_123/games?page=3&page_size=10>; rel="next",
        </api/v1/sessions/s_123/games?page=1&page_size=10>; rel="prev"
    """
    if query_params is None:
        query_params = {}
    
    # Calculate total pages
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    
    links = []
    
    # First page
    first_params = {**query_params, "page": "1", "page_size": str(page_size)}
    first_url = f"{base_url}?{urlencode(first_params)}"
    links.append(f'<{first_url}>; rel="first"')
    
    # Last page
    last_params = {**query_params, "page": str(total_pages), "page_size": str(page_size)}
    last_url = f"{base_url}?{urlencode(last_params)}"
    links.append(f'<{last_url}>; rel="last"')
    
    # Next page (if not on last page)
    if page < total_pages:
        next_params = {**query_params, "page": str(page + 1), "page_size": str(page_size)}
        next_url = f"{base_url}?{urlencode(next_params)}"
        links.append(f'<{next_url}>; rel="next"')
    
    # Previous page (if not on first page)
    if page > 1:
        prev_params = {**query_params, "page": str(page - 1), "page_size": str(page_size)}
        prev_url = f"{base_url}?{urlencode(prev_params)}"
        links.append(f'<{prev_url}>; rel="prev"')
    
    return ", ".join(links)


def build_pagination_response(
    items: list,
    page: int,
    page_size: int,
    total_items: int
) -> Dict:
    """Build standardized pagination response.
    
    Args:
        items: List of items for current page
        page: Current page number
        page_size: Items per page
        total_items: Total number of items
        
    Returns:
        Dictionary with items, pagination metadata
    """
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }
