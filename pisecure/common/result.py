"""
Result Type - Explicit error handling

Instead of:
    try:
        result = some_operation()
    except Exception as e:
        handle_error(e)

Use:
    result = some_operation()
    if result.is_ok():
        handle_success(result.unwrap())
    else:
        handle_error(result.error())

Benefits:
- Errors are part of the return type (visible in function signature)
- Explicit error handling required
- No hidden exceptions
- Better for API contracts
"""

from typing import TypeVar, Generic, Union, Optional, Callable


T = TypeVar("T")
E = TypeVar("E")


class Result(Generic[T]):
    """
    Result type representing either success (Ok) or failure (Err).

    Generic over value type T.
    """

    def __init__(self, ok: bool, value: Optional[T] = None, error: str = ""):
        self.ok = ok
        self.value = value
        self.error_msg = error

    def is_ok(self) -> bool:
        """Check if result is Ok."""
        return self.ok

    def is_err(self) -> bool:
        """Check if result is Err."""
        return not self.ok

    def unwrap(self) -> T:
        """Get the value, panicking if Err."""
        if not self.ok:
            raise RuntimeError(f"Called unwrap on Err: {self.error_msg}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or return default if Err."""
        return self.value if self.ok else default

    def error(self) -> str:
        """Get the error message."""
        return self.error_msg

    def map(self, f: Callable[[T], "Result"]) -> "Result":
        """Apply a function to the value if Ok."""
        if self.ok:
            return f(self.value)
        return self

    def map_err(self, f: Callable[[str], str]) -> "Result[T]":
        """Apply a function to the error if Err."""
        if not self.ok:
            return Err(f(self.error_msg))
        return self

    def __repr__(self) -> str:
        if self.ok:
            return f"Ok({self.value!r})"
        return f"Err({self.error_msg!r})"

    def __bool__(self) -> bool:
        """Result is truthy if Ok."""
        return self.ok


def Ok(value: T) -> Result[T]:
    """Create an Ok result."""
    return Result(True, value=value)


def Err(error: str) -> Result:
    """Create an Err result."""
    return Result(False, error=error)
