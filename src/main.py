#!/usr/bin/env python3
"""
CLI entry point for the D&D MCP Server (FastMCP 2.12+ compatible).
"""

from gamemaster_mcp.main import main


def cli_main():
    """Main CLI entry point."""
    main()


if __name__ == "__main__":
    cli_main()
