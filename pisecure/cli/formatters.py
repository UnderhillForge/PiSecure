"""
CLI Output Formatters

Handles all output formatting including Rich styling, JSON output, and plain text.
Centralizes formatting logic so commands stay simple.
"""

from rich.console import Console
from rich.table import Table
from typing import Any, Dict, List, Optional
import json


console = Console()


def print_output(message: str, style: Optional[str] = None) -> None:
    """Print message with optional Rich style."""
    if style:
        console.print(message, style=style)
    else:
        console.print(message)


def strip_rich_formatting(text: str) -> str:
    """Remove Rich markup from text."""
    import re

    return re.sub(r"\[/?[a-z]*\]", "", text)


def print_success(message: str) -> None:
    """Print success message in green."""
    console.print(f"✓ {message}", style="green")


def print_error(message: str) -> None:
    """Print error message in red."""
    console.print(f"✗ {message}", style="red")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    console.print(f"⚠ {message}", style="yellow")


def print_info(message: str) -> None:
    """Print info message in blue."""
    console.print(f"ℹ {message}", style="blue")


def print_table(title: str, columns: List[str], rows: List[List[Any]]) -> None:
    """Print a formatted table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(x) for x in row])
    console.print(table)


def print_json(data: Dict[str, Any], indent: int = 2) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=indent))


def print_dict(data: Dict[str, Any]) -> None:
    """Print dictionary in readable format."""
    for key, value in data.items():
        console.print(f"{key}: {value}")
