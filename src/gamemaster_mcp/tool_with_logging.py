import inspect
import json
import logging
from functools import wraps
from typing import Any, Callable

tool_log = logging.getLogger("mcp.tools")
logging.basicConfig(level=logging.INFO)


def tool_with_logging(
    mcp_app,
    *,
    exclude: set[str] | None = None,  # arg names to redact entirely
    redact: dict[str, Callable[[Any], Any]] | None = None,  # per-arg redactors
    max_str_len: int = 500,  # truncate long strings
):
    """
    Decorator factory. Use in place of @mcp.tool:
        @tool_with_logging(mcp)
        def my_tool(...): ...
    """
    exclude = exclude or set()
    redact = redact or {}

    def shorten(v: Any) -> Any:
        # Make best-effort to keep logs readable & safe
        if v is None:
            return None
        if isinstance(v, (int, float, bool)):
            return v
        if isinstance(v, bytes):
            return f"<bytes:{len(v)}>"
        if isinstance(v, (list, tuple)):
            return [shorten(x) for x in v]
        if isinstance(v, dict):
            return {str(k): shorten(vv) for k, vv in v.items()}
        s = str(v)
        if len(s) > max_str_len:
            return s[:max_str_len] + f"... <{len(s) - max_str_len} more chars>"
        return s

    def make_safe_args(fn: Callable, args, kwargs):
        sig = inspect.signature(fn)
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        safe = {}
        for k, v in bound.arguments.items():
            if k in exclude:
                safe[k] = "<redacted>"
            elif k in redact:
                try:
                    safe[k] = shorten(redact[k](v))
                except Exception:
                    safe[k] = "<redaction_error>"
            else:
                safe[k] = shorten(v)
        return safe

    def decorator(fn: Callable):
        is_coro = inspect.iscoroutinefunction(fn)
        tool_name = fn.__name__

        if is_coro:

            @wraps(fn)
            async def wrapper(*args, **kwargs):
                safe = make_safe_args(fn, args, kwargs)
                try:
                    payload = json.dumps(safe, default=str)
                except Exception:
                    payload = str(safe)
                tool_log.info("Tool call: %s(%s)", tool_name, payload)
                return await fn(*args, **kwargs)
        else:

            @wraps(fn)
            def wrapper(*args, **kwargs):
                safe = make_safe_args(fn, args, kwargs)
                try:
                    payload = json.dumps(safe, default=str)
                except Exception:
                    payload = str(safe)
                tool_log.info("Tool call: %s(%s)", tool_name, payload)
                return fn(*args, **kwargs)

        # Register the (wrapped) function as a tool
        return mcp_app.tool(wrapper)

    return decorator
