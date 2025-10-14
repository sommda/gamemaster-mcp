# Transcript Feature Specification

## Overview

The Transcript feature records interactions between players and the game system during D&D campaign sessions. It captures player input and game responses in a structured format for later review and analysis. It may be used to generate context history for LLM calls, acting a bit like the saved context used in chat bots but with richer and more game-specific features.

## Motivation

### Why Tree Structure?

Current flat list structure has limitations:
1. **Lost Context**: Hard to understand what interactions belong together (e.g., which interactions are part of a combat vs exploration)
2. **No Hierarchy**: Cannot group related interactions into meaningful units (adventures, combats, story arcs)
3. **Poor LLM Context**: When feeding to an LLM, we lose the structural meaning - everything looks equally important
4. **Difficult Navigation**: Finding "that combat where we fought the dragon" requires scanning all entries linearly
5. **Limited Summarization**: Cannot create multi-level summaries (adventure summary vs individual interaction)

### Benefits of Tree Structure

1. **Semantic Grouping**: Combat nodes contain all related interactions, Adventure nodes contain complete story arcs
2. **Hierarchical Summarization**: Can summarize at any level (adventure, combat, or individual interaction)
3. **Better LLM Context**: Can provide different levels of detail based on context window size
4. **Easier Navigation**: "Show me all combats in adventure 2" becomes trivial
5. **Flexible Representation**: Can represent complex narrative structures (nested adventures, flashbacks, etc.)

## Structure

A Transcript has a tree structure. The Transcript itself serves as the root node and there is only one Transcript node in the tree.

### Node Types

* **Transcript** - Root node (only one per tree)
* **Interaction** - Leaf node representing user-LLM exchange
* **Combat** - Interior node representing a complete combat encounter
* **Adventure** - Interior node representing a quest or story arc with clear beginning and end

### Node Hierarchy Rules

```
Transcript (root)
├── Interaction (leaf)
├── Combat (interior)
│   └── Interaction* (leaves)
├── Adventure (interior)
│   ├── Interaction (leaf)
│   ├── Combat (interior)
│   │   └── Interaction* (leaves)
│   └── Adventure (interior, nested)
│       └── ...
└── ...
```

**Rules:**
- Transcript must be root (only one in tree)
- Interaction must be leaf (cannot have children)
- Combat and Adventure can contain children
- Combat can only contain Interactions (no nested Combats/Adventures)
- Adventure can contain Interactions, Combats, and nested Adventures

## Data Models

### Base Node Model

All nodes share common metadata:

```python
class TranscriptNode(BaseModel):
    """Base class for all transcript nodes."""
    id: str = Field(default_factory=lambda: random(length=8))
    node_type: Literal["transcript", "interaction", "combat", "adventure"]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Optional metadata
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
```

### Transcript Node

Root node containing the entire transcript tree.

```python
class Transcript(TranscriptNode):
    """Root node of the transcript tree."""
    node_type: Literal["transcript"] = "transcript"

    campaign: str  # Campaign name
    session_number: int  # Session this transcript covers

    # Children - can be any mix of interactions, combats, adventures
    children: list[Interaction | Combat | Adventure] = Field(default_factory=list)

    # Metadata
    started_at: datetime | None = None  # When first entry added
    ended_at: datetime | None = None    # When session ended
    characters_present: list[str] = Field(default_factory=list)
```

### Interaction Node

Leaf node representing a single user-LLM interaction.

```python
class ResponseText(BaseModel):
    """Text response from the LLM."""
    type: Literal["text"] = "text"
    content: str

class InteractionToolCall(BaseModel):
    """Details of a tool call made during interaction."""
    name: str  # Tool name
    id: str    # LLM-provided call ID
    input: dict[str, Any]  # Tool parameters
    response: str  # Tool result

class ResponseTools(BaseModel):
    """Tool call response from the LLM."""
    type: Literal["tools"] = "tools"
    calls: list[InteractionToolCall]

# Union type for responses
InteractionResponse = ResponseText | ResponseTools

class Interaction(TranscriptNode):
    """Leaf node representing single user-LLM exchange."""
    node_type: Literal["interaction"] = "interaction"

    # Core interaction data
    user_text: str  # User's input
    responses: list[InteractionResponse]  # LLM's response(s)

    # Optional metadata
    character_speaking: str | None = None  # Which PC said user_text
    importance: int = Field(ge=1, le=5, default=3)  # 1=trivial, 5=critical
```

### Combat Node

Interior node representing a complete combat encounter.

```python
class Combat(TranscriptNode):
    """Interior node representing a combat encounter."""
    node_type: Literal["combat"] = "combat"

    # Combat summary
    participants: list[str]  # All combatants (PCs, NPCs, monsters)
    result: str  # "victory", "defeat", "fled", "parley", etc.
    summary: str  # Brief description of what happened

    # Detailed combat log
    actions: list[Interaction]  # Blow-by-blow interactions

    # Combat metadata
    location: str | None = None
    rounds: int | None = None  # Number of rounds
    casualties: list[str] = Field(default_factory=list)  # Who died/went down
```

### Adventure Node

Interior node representing a story arc or quest.

```python
class Adventure(TranscriptNode):
    """Interior node representing a story arc or quest."""
    node_type: Literal["adventure"] = "adventure"

    # Adventure summary
    title: str | None = None  # Adventure name
    summary: str  # What this adventure was about

    # Adventure contents - can be mixed
    actions: list[Interaction | Combat | Adventure] = Field(default_factory=list)

    # Adventure metadata
    quest_id: str | None = None  # Link to Quest object if applicable
    locations: list[str] = Field(default_factory=list)  # Where adventure took place
    npcs_met: list[str] = Field(default_factory=list)  # NPCs encountered
    rewards: list[str] = Field(default_factory=list)  # XP, gold, items, etc.
```

## Backward Compatibility

### Migration Strategy

Existing transcripts have flat structure:
```json
{
  "id": "xyz",
  "campaign": "The Arena",
  "session_number": 0,
  "entries": [
    {"player_entry": "...", "game_response": "..."},
    ...
  ]
}
```

**Migration Approach:**

1. **Automatic Detection**: Check if JSON has `entries` field (old format) vs `children` field (new format)
2. **Convert on Load**: Transform old entries to new structure:
   ```python
   # Old format
   entries: [TranscriptEntry]

   # Converts to new format
   Transcript(
       children=[
           Interaction(
               user_text=entry.player_entry,
               responses=[ResponseText(content=entry.game_response)]
           )
           for entry in entries
       ]
   )
   ```
3. **Save in New Format**: Once loaded, save in new tree format
4. **Preserve Original**: Keep `.old` backup of original file

### Compatibility Layer

Provide helper methods for old API:

```python
class Transcript:
    def add_simple_entry(self, player_text: str, game_response: str):
        """Backward compatible: add flat interaction."""
        self.children.append(Interaction(
            user_text=player_text,
            responses=[ResponseText(content=game_response)]
        ))

    def get_flat_entries(self) -> list[tuple[str, str]]:
        """Backward compatible: return flat list of (user, response)."""
        # Flatten tree to list of interactions
        pass
```

## Implementation Plan

### Phase 1: Core Data Models (Week 1)

**Goals:**
- Define all node models in `models.py`
- Implement tree structure validation
- Create migration code for old format
- Comprehensive unit tests

**Tasks:**
1. Create `TranscriptNode` base class
2. Implement `Interaction`, `Combat`, `Adventure`, `Transcript` models
3. Add response types: `ResponseText`, `ResponseTools`, `InteractionToolCall`
4. Implement validation:
   - Transcript must be root
   - Interactions must be leaves
   - Combat can only contain Interactions
   - No circular references
5. Create migration function: `migrate_old_transcript(old_data) -> Transcript`
6. Write tests for all models and validation

**Deliverables:**
- Updated `models.py` with new classes
- Migration code in `storage.py`
- Test file: `tests/test_transcript_models.py`
- Updated `__all__` exports

### Phase 2: Storage Layer (Week 2)

**Goals:**
- Update storage to handle tree structure
- Implement migration on load
- Add tree manipulation helpers
- Maintain backward compatibility

**Tasks:**
1. Update `_load_transcript()`:
   - Detect old vs new format
   - Auto-migrate old format
   - Save backup of original
   - Restore `current_parent_id` from metadata or default to root
2. Update `_save_transcript()`:
   - Serialize tree to JSON
   - Handle nested structures
   - Pretty-print for readability
   - Save `current_parent_id` in metadata
3. Add current parent tracking:
   ```python
   def get_current_parent_id(campaign_name) -> str
   def set_current_parent_id(campaign_name, node_id)
   def get_current_parent_node(campaign_name) -> TranscriptNode
   ```
4. Add tree manipulation methods:
   ```python
   def add_interaction(user_text, responses, parent_id=None) -> Interaction
   def start_combat(participants, location=None) -> Combat
   def end_combat(result, summary, combat_id=None)
   def start_adventure(title) -> Adventure
   def end_adventure(summary, adventure_id=None)
   ```
5. Implement tree traversal:
   ```python
   def get_all_interactions(node) -> list[Interaction]
   def get_all_combats(node) -> list[Combat]
   def find_node_by_id(transcript, node_id) -> TranscriptNode
   def get_parent_node(transcript, node_id) -> TranscriptNode | None
   ```
6. Write storage tests including current parent behavior

**Deliverables:**
- Updated `storage.py` with new methods
- Test file: `tests/test_transcript_storage.py`
- Migration tested with real data
- Backup/restore functionality

### Phase 3: MCP Tools (Week 3)

**Goals:**
- Create intuitive tools for building transcript tree
- Support common workflows (combat, exploration, storytelling)
- Provide tree navigation and query tools

**New Tools:**

#### Basic Interaction Recording

```python
@tool_with_logging(mcp)
def record_interaction(
    user_text: str,
    responses: list[dict[str, Any]],  # Can be text or tool calls
    campaign_name: str | None = None,
    session_number: int | None = None,
    parent_id: str | None = None,  # Optional: override current parent
    character: str | None = None,
    importance: int = 3,
) -> str:
    """Record a user-LLM interaction in the transcript.

    If parent_id is None, interaction is added to current parent.
    """
```

#### Combat Management (Enhance Existing Tools)

**Existing tools** at `main.py:992-1018`:
- `start_combat(participants: list[CombatParticipant])` - starts combat, updates game_state
- `end_combat()` - ends combat, updates game_state (NO PARAMETERS CURRENTLY)

**Required changes**:

1. **Enhance `start_combat()`** - Add transcript Combat node creation:
   ```python
   @tool_with_logging(mcp, tags=["mode:town", "mode:dungeon", "mode:outdoors"])
   def start_combat(
       participants: list[CombatParticipant],
   ) -> str:
       """Start a combat encounter."""
       # Existing: Set initiative order
       initiative_order = sorted(participants, key=lambda x: x.initiative, reverse=True)
       storage.update_game_state(in_combat=True, initiative_order=initiative_order, ...)

       # NEW: Create Combat node in transcript and set as current parent
       participant_names = [p.name for p in participants]
       storage.start_transcript_combat(
           participants=participant_names,
           location=storage.get_game_state().current_location
       )

       return "Combat Started!..."
   ```

2. **Update `end_combat()`** - Add summary/result parameters and finalize Combat node:
   ```python
   @tool_with_logging(mcp, tags=["mode:combat"])
   def end_combat(
       result: Annotated[str, Field(description="Combat outcome: victory, defeat, fled, etc.")],
       summary: Annotated[str, Field(description="Brief summary of what happened in combat")],
       casualties: Annotated[list[str] | None, Field(description="Characters who died or went down")] = None,
   ) -> str:
       """End the current combat encounter."""
       # NEW: Finalize Combat node with summary and restore previous parent
       storage.end_transcript_combat(
           result=result,
           summary=summary,
           casualties=casualties or []
       )

       # Existing: Clear combat state
       storage.update_game_state(in_combat=False, initiative_order=[], current_turn=None)

       return f"Combat ended: {result}. {summary}"
   ```

#### Adventure Management

```python
@tool_with_logging(mcp)
def start_adventure(
    title: str,
    campaign_name: str | None = None,
    session_number: int | None = None,
) -> str:
    """Begin a new adventure arc in the transcript.

    Creates Adventure node under current parent, then sets it as new current parent.
    All subsequent interactions/combats go into this adventure until end_adventure().
    Supports nesting: if current parent is already an Adventure, creates nested adventure.
    Returns: adventure_id
    """

@tool_with_logging(mcp)
def end_adventure(
    summary: str,
    adventure_id: str | None = None,  # Optional: defaults to current parent if it's an Adventure
    rewards: list[str] | None = None,
    campaign_name: str | None = None,
) -> str:
    """End an adventure and finalize its summary.

    Resets current parent to the Adventure's parent node.
    """
```

**Deliverables:**
- Updated `main.py` with new tools
- Test file: `tests/test_transcript_tools.py`
- MCP tool documentation

### Phase 4: Context Generation and Resources (Week 4)

**Goals:**
- Generate LLM context at various detail levels
- Support different use cases (full detail, summary only, recent only)
- Provide single unified resource for transcript access

**Context Generation:**

```python
def generate_llm_context(
    transcript: Transcript,
    max_tokens: int = 8000,
    detail_level: Literal["full", "summary", "minimal"] = "summary",
    recent_n: int | None = None,
) -> str:
    """Generate LLM context from transcript.

    Args:
        max_tokens: Maximum context size
        detail_level:
            - full: Include all interaction text
            - summary: Include summaries + recent interactions
            - minimal: Only top-level summaries
        recent_n: Include full detail for N most recent interactions

    Returns formatted text suitable for LLM system prompt or context.
    """
```

**Resource (retain existing):**

Keep the current resource URIs as they already provide good access:

```python
@mcp.resource("resource://transcripts/{campaign_name}/{session_number}")
def get_transcript(campaign_name: str, session_number: int) -> Transcript:
    """Get complete transcript tree for a session."""

@mcp.resource("resource://current_transcript")
def get_current_transcript() -> Transcript:
    """Get transcript for current campaign/session."""
```

**Deliverables:**
- Context generation logic in `storage.py` or new `transcript_utils.py`
- Test with various context window sizes
- Documentation on usage patterns
- Examples of context at different detail levels

### Phase 5: Testing and Documentation (Week 5)

**Goals:**
- Comprehensive testing with real data
- Performance testing with large transcripts
- Complete documentation
- Migration guide

**Tasks:**
1. **Integration Tests**:
   - Test complete workflow (start session → interactions → combat → adventure → end)
   - Test migration with real transcript files
   - Test context generation with various sizes
2. **Performance Tests**:
   - Large transcript (1000+ interactions)
   - Deep nesting (10+ levels)
   - Search across multiple transcripts
3. **Documentation**:
   - Update README with transcript examples
   - Create migration guide
   - Document tree structure best practices
   - Add examples of common patterns
4. **Edge Cases**:
   - Empty transcripts
   - Malformed data
   - Concurrent modifications
   - Very long user_text/responses

**Deliverables:**
- Complete test suite
- Performance benchmarks
- User documentation
- Migration guide
- Example notebooks/scripts

## Usage Patterns

### Pattern 1: Simple Session Recording

```python
# Old way (still supported)
storage.add_transcript_entry("I attack the orc", "Roll for attack...")

# New way (same result)
record_interaction(
    user_text="I attack the orc",
    responses=[{"type": "text", "content": "Roll for attack..."}]
)
```

### Pattern 2: Combat Recording

```python
# Start combat - becomes current parent
combat_id = start_combat(
    participants=["Gareth", "Orc Warrior 1", "Orc Warrior 2"],
    location="Ancient Stone Circle"
)

# Record each round - automatically added to current parent (Combat)
record_interaction("I attack orc 1", [...])
record_interaction("I attack orc 2", [...])

# End combat - current parent returns to root
end_combat(
    result="victory",
    summary="Party defeated 2 orcs with no casualties"
)
```

### Pattern 3: Adventure Recording

```python
# Start adventure - becomes current parent
adv_id = start_adventure(title="The Lost Temple")

# Regular interactions - automatically added to current parent (Adventure)
record_interaction("We enter the temple", [...])
record_interaction("We search for traps", [...])

# Start combat within adventure - Combat becomes current parent
combat_id = start_combat(["Gareth", "Temple Guardian"])
record_interaction("I fight the guardian", [...])  # Added to Combat
record_interaction("I strike again", [...])        # Added to Combat

# End combat - current parent returns to Adventure
end_combat(result="victory", summary="Defeated guardian")

# More exploration - back to Adventure as current parent
record_interaction("We find the artifact", [...])

# End adventure - current parent returns to root
end_adventure(
    summary="Party explored temple and retrieved ancient artifact",
    rewards=["Ancient Medallion", "500 XP each"]
)
```

### Pattern 4: Nested Adventures

```python
# Main quest - becomes current parent
main_quest = start_adventure(title="Save the Kingdom")

# Interactions in main quest
record_interaction("We meet the king", [...])  # Added to "Save the Kingdom"

# Side quest within main quest - becomes current parent
side_quest = start_adventure(title="Help the Farmer")
record_interaction("We rescue chickens", [...])  # Added to "Help the Farmer"

# End side quest - current parent returns to main quest
end_adventure(summary="Farmer's chickens rescued")

# Continue main quest - back to main quest as current parent
record_interaction("We confront the villain", [...])  # Added to "Save the Kingdom"

# End main quest - current parent returns to root
end_adventure(summary="Kingdom saved!")
```

### Pattern 5: Context Generation for LLM

```python
# Get full recent context (for active gameplay)
context = generate_llm_context(
    transcript,
    max_tokens=6000,
    detail_level="full",
    recent_n=10  # Last 10 interactions in full detail
)

# Get summary context (for session recap)
context = generate_llm_context(
    transcript,
    max_tokens=2000,
    detail_level="summary"
)

# Get minimal context (for high-level planning)
context = generate_llm_context(
    transcript,
    max_tokens=500,
    detail_level="minimal"
)
```

## Technical Considerations

### Tree Traversal Algorithms

```python
def depth_first_walk(node: TranscriptNode, visitor: Callable):
    """Visit all nodes in depth-first order."""
    visitor(node)
    if hasattr(node, 'children'):
        for child in node.children:
            depth_first_walk(child, visitor)
    elif hasattr(node, 'actions'):
        for action in node.actions:
            depth_first_walk(action, visitor)

def find_node(root: Transcript, predicate: Callable) -> TranscriptNode | None:
    """Find first node matching predicate."""
    result = None
    def visitor(node):
        nonlocal result
        if result is None and predicate(node):
            result = node
    depth_first_walk(root, visitor)
    return result

def collect_nodes(root: Transcript, node_type: str) -> list[TranscriptNode]:
    """Collect all nodes of given type."""
    nodes = []
    depth_first_walk(root, lambda n: nodes.append(n) if n.node_type == node_type else None)
    return nodes
```

### Serialization Format

JSON structure preserves tree:

```json
{
  "node_type": "transcript",
  "id": "xyz",
  "campaign": "The Arena",
  "session_number": 0,
  "children": [
    {
      "node_type": "interaction",
      "id": "abc",
      "user_text": "I look around",
      "responses": [{"type": "text", "content": "You see..."}]
    },
    {
      "node_type": "combat",
      "id": "def",
      "participants": ["Gareth", "Orc"],
      "result": "victory",
      "summary": "Quick fight",
      "actions": [
        {"node_type": "interaction", "user_text": "I attack", ...},
        {"node_type": "interaction", "user_text": "I attack again", ...}
      ]
    },
    {
      "node_type": "adventure",
      "id": "ghi",
      "title": "Temple Quest",
      "summary": "Found the artifact",
      "actions": [
        {"node_type": "interaction", ...},
        {"node_type": "combat", ...}
      ]
    }
  ]
}
```

### Validation Rules

```python
def validate_transcript_tree(node: TranscriptNode, parent_type: str | None = None):
    """Validate tree structure rules."""

    # Rule: Only Transcript can be root
    if parent_type is None and node.node_type != "transcript":
        raise ValueError("Root must be Transcript")

    # Rule: Interaction must be leaf
    if node.node_type == "interaction":
        if hasattr(node, 'children') and node.children:
            raise ValueError("Interaction cannot have children")

    # Rule: Combat can only contain Interactions
    if node.node_type == "combat":
        for action in node.actions:
            if action.node_type != "interaction":
                raise ValueError("Combat can only contain Interactions")

    # Rule: Adventure can contain mix
    if node.node_type == "adventure":
        for action in node.actions:
            if action.node_type not in ["interaction", "combat", "adventure"]:
                raise ValueError("Adventure children must be Interaction, Combat, or Adventure")

    # Recurse
    if hasattr(node, 'children'):
        for child in node.children:
            validate_transcript_tree(child, node.node_type)
    elif hasattr(node, 'actions'):
        for action in node.actions:
            validate_transcript_tree(action, node.node_type)
```

## Current Parent Concept

### Overview

The storage layer maintains a **current parent** node for each campaign's transcript. This is the node to which new interactions will be added by default when no explicit `parent_id` is specified.

### Behavior

**Default State:**
- When a transcript is first created, the current parent is the Transcript root node itself
- Interactions added without specifying `parent_id` go directly under the root

**State Changes:**
- `start_combat()` creates a Combat node and sets it as current parent
- `start_adventure()` creates an Adventure node and sets it as current parent
- `end_combat()` resets current parent to the Combat's parent
- `end_adventure()` resets current parent to the Adventure's parent
- Explicit `parent_id` in `record_interaction()` does NOT change current parent

**Persistence:**
- Current parent ID is stored in memory as part of `DnDStorage` state
- Current parent ID is saved to transcript metadata for session continuity
- On transcript load, current parent is restored from metadata (or defaults to root)

### Storage Implementation

```python
class DnDStorage:
    def __init__(self, ...):
        # Track current parent for each campaign's transcript
        self._transcript_current_parent: dict[str, str] = {}  # campaign -> parent_node_id

    def get_current_parent(self, campaign_name: str) -> str:
        """Get current parent node ID for campaign's transcript."""
        return self._transcript_current_parent.get(campaign_name, None)

    def set_current_parent(self, campaign_name: str, node_id: str):
        """Set current parent node ID for campaign's transcript."""
        self._transcript_current_parent[campaign_name] = node_id
```

### Updated Transcript Model

```python
class Transcript(TranscriptNode):
    """Root node of the transcript tree."""
    node_type: Literal["transcript"] = "transcript"

    campaign: str
    session_number: int
    children: list[Interaction | Combat | Adventure] = Field(default_factory=list)

    # Current parent tracking
    current_parent_id: str | None = None  # ID of node where new interactions go

    # Metadata
    started_at: datetime | None = None
    ended_at: datetime | None = None
    characters_present: list[str] = Field(default_factory=list)
```

### Example Workflow

```python
# Session starts - current parent is Transcript root
record_interaction("We enter the dungeon", [...])  # Added to root
record_interaction("We see a door", [...])         # Added to root

# Start combat - current parent becomes Combat node
combat_id = start_combat(["Gareth", "Orc"])
record_interaction("I attack", [...])              # Added to Combat
record_interaction("I attack again", [...])        # Added to Combat

# End combat - current parent returns to root
end_combat(combat_id, "victory", "Quick fight")
record_interaction("We search the room", [...])    # Added to root again

# Start adventure - current parent becomes Adventure node
adv_id = start_adventure("The Lost Temple")
record_interaction("We enter temple", [...])       # Added to Adventure

# Start combat within adventure - current parent becomes Combat
combat_id = start_combat(["Gareth", "Guardian"])
record_interaction("I fight", [...])               # Added to Combat

# End combat - current parent returns to Adventure
end_combat(combat_id, "victory", "Defeated guardian")
record_interaction("We take artifact", [...])      # Added to Adventure

# End adventure - current parent returns to root
end_adventure(adv_id, "Retrieved artifact")
record_interaction("We leave temple", [...])       # Added to root
```

## Open Questions

1. **Maximum Depth**: Should we limit tree depth to prevent pathological cases?
   - Suggested limit: 10 levels deep
   - Error or flatten to max depth?

3. **Summary Auto-generation**: Should summaries be auto-generated by LLM or user-provided?
   - Combat summaries: likely auto-generated
   - Adventure summaries: likely user-provided
   - Hybrid approach?

4. **Timestamp Precision**: Should we track timing at interaction level or node level?
   - Current: Only created_at/updated_at
   - Alternative: Track duration, round timing in combat

5. **Concurrent Modifications**: How to handle multiple LLM agents modifying transcript?
   - Lock file?
   - Append-only log with replay?
   - Accept potential conflicts?

6. **Pruning Old Data**: Should old transcripts be pruned or archived?
   - Keep everything forever?
   - Archive after N days?
   - Compress old sessions?

7. **Export Formats**: What export formats are most useful?
   - Markdown for readability
   - JSON for data interchange
   - HTML for web viewing
   - PDF for archival

## Success Criteria

1. **Backward Compatibility**: All existing transcripts load and work correctly
2. **Tree Structure**: Can represent complex session structures (nested adventures, multiple combats)
3. **Performance**: Load/save 1000+ interaction transcript in < 1 second
4. **Context Generation**: Generate appropriate LLM context at various detail levels
5. **Usability**: Intuitive tools for common patterns (combat, adventure, exploration)
6. **Search**: Find specific interactions/combats quickly
7. **Testing**: 90%+ code coverage, all edge cases handled
8. **Documentation**: Clear examples and migration guide

## Future Enhancements

### Phase 6: Advanced Features (Future)

- **Branching**: Support "what-if" branches (alternate outcomes)
- **Merge**: Combine multiple transcripts (multi-party sessions)
- **Diff**: Compare two transcripts or sessions
- **Replay**: Step through transcript as if playing again
- **Analytics**: Statistics on session (combat frequency, NPC interactions, etc.)
- **Export**: Generate session reports, battle maps, timeline visualizations
- **Compression**: Compress old transcripts while preserving structure
- **Sync**: Multi-user transcript editing with conflict resolution
