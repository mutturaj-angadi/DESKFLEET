from unittest.mock import patch

from app.tools.registry import TOOL_REGISTRY, call_tool


def test_allowlisted_tools_are_exactly_three():
    assert set(TOOL_REGISTRY.keys()) == {"get_order_status", "get_product", "search_products"}


def test_off_allowlist_tool_is_blocked():
    result = call_tool("delete_all_orders", {"order_id": "ORD-5001"})
    assert result["status"] == "blocked"
    assert "not in the tool allowlist" in result["reason"]


def test_off_allowlist_tool_never_executes():
    """A blocked call must not touch any underlying function."""
    with patch("app.tools.order.get_order_status") as mocked:
        call_tool("get_order_status_v2", {"order_id": "ORD-5001"})
        mocked.assert_not_called()


def test_allowlisted_tool_call_invokes_underlying_function():
    with patch.dict(
        TOOL_REGISTRY,
        {"get_order_status": lambda order_id: {"order_id": order_id, "status": "shipped"}},
    ):
        result = call_tool("get_order_status", {"order_id": "ORD-5001"})
        assert result["status"] == "ok"
        assert result["result"]["status"] == "shipped"


def test_invalid_arguments_return_error_not_crash():
    with patch.dict(TOOL_REGISTRY, {"get_order_status": lambda order_id: {"status": "ok"}}):
        result = call_tool("get_order_status", {"wrong_arg": "x"})
        assert result["status"] == "error"


def test_tool_error_result_marks_status_error():
    with patch.dict(
        TOOL_REGISTRY, {"get_order_status": lambda order_id: {"error": "Order not found"}}
    ):
        result = call_tool("get_order_status", {"order_id": "ORD-9999"})
        assert result["status"] == "error"
