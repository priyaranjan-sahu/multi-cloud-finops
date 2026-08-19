"""Command-line tooling for the Multi-Cloud FinOps platform.

Run any tool from the repository root with:

    python -m scripts.<tool> [options]

The tools print emoji-heavy progress output, so this module reconfigures
stdout to UTF-8 (with lossy replacement) to stay usable on Windows consoles
that default to a legacy code page.
"""

import sys


def configure_stdout() -> None:
    """Force UTF-8 output so emoji progress markers render everywhere."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


configure_stdout()