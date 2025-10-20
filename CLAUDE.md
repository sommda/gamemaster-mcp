# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
uv run pytest
```

### Type Checking  
```bash
uv run mypy src/
```

### Linting and Formatting
```bash
uv run ruff check .
uv run ruff format .
```

### Running the Server
```bash
# Development mode (editable install)
uv pip install -e .[dev]
uv run gamemaster-mcp

# Direct execution
uvx . gamemaster-mcp
```

### Installation
```bash
# Create virtual environment
uv venv

# Install with dev dependencies
uv pip install -e .[dev]
```

## Architecture Overview

### Core Framework
This is a **FastMCP 2.12+ server** for D&D campaign management. FastMCP automatically generates JSON schemas from type annotations and handles parameter validation.

### Key Components

**`src/gamemaster_mcp/main.py`**: FastMCP server with 25+ tools using `@mcp.tool` decorators
**`src/gamemaster_mcp/models.py`**: Pydantic data models for D&D entities (Campaign, Character, NPC, etc.)
**`src/gamemaster_mcp/storage.py`**: JSON file persistence layer with `DnDStorage` class

### Data Architecture
- **Campaign-centric design**: Single active `Campaign` object contains all characters, NPCs, locations, quests
- **JSON persistence**: Campaigns stored as `{campaign_name}.json` files
- **Adventure log**: Global event log stored separately in `adventure_log.json`
- **In-memory operations**: All changes happen in memory, then auto-saved to disk

### Tool Implementation Pattern
```python
@mcp.tool
def tool_name(
    required_param: Annotated[str, Field(description="Description")],
    optional_param: Annotated[Optional[str], Field(description="Optional")] = None,
    validated_param: Annotated[int, Field(description="Range", ge=1, le=20)] = 10,
) -> str:
    """Tool description for LLM interface."""
    # Implementation
    return "Success message"
```

### Storage Layer (`DnDStorage`)
- **Current campaign**: `_current_campaign` holds active campaign in memory
- **Auto-save**: All mutations automatically persist to JSON files
- **CRUD operations**: Create, Read, Update, Delete for all entity types
- **Event logging**: Separate adventure log with search/filter capabilities

### Key Models
- **`Campaign`**: Top-level container with characters, NPCs, locations, quests, game state
- **`Character`**: Full D&D 5e character sheet with abilities, inventory, spells
- **`GameState`**: Current party location, active quests, combat status
- **`AdventureEvent`**: Categorized event logging with importance ratings

### Dependencies
- FastMCP 2.12.5+ for MCP server framework
- Pydantic 2.12.3+ for data validation and models
- Python 3.12+ required

### Testing
Use `npx @mcpjam/inspector` for interactive tool testing during development.