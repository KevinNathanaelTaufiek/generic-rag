import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


@pytest.mark.asyncio
async def test_search_web_executor_success():
    """search_web_executor returns formatted results string"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": "Test Title", "snippet": "Test snippet", "url": "https://example.com"}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        from app.core.tools import search_web_executor
        result = await search_web_executor(query="test query")
        assert "Test Title" in result
        assert "Test snippet" in result


@pytest.mark.asyncio
async def test_search_web_executor_http_error():
    """search_web_executor returns error string on HTTP 500"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    http_error = httpx.HTTPStatusError(
        "500 Server Error",
        request=MagicMock(),
        response=mock_response,
    )

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with patch("httpx.AsyncClient", return_value=mock_client):
        from app.core.tools import search_web_executor
        result = await search_web_executor(query="test")
        assert "error" in result.lower() or "failed" in result.lower() or "unavailable" in result.lower()


@pytest.mark.asyncio
async def test_send_notification_executor_success():
    """send_notification_executor returns confirmation string"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sent": True, "to": "admin", "timestamp": "2026-01-01T00:00:00Z"
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        from app.core.tools import send_notification_executor
        result = await send_notification_executor(to="admin", message="hello")
        assert "admin" in result
        assert "sent" in result.lower()


@pytest.mark.asyncio
async def test_crud_data_executor_success():
    """crud_data_executor returns result string"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True, "action": "create", "resource": "users", "data": {"name": "Kevin"}
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        from app.core.tools import crud_data_executor
        result = await crud_data_executor(action="create", resource="users", data={"name": "Kevin"})
        assert "success" in result.lower() or "Kevin" in result
