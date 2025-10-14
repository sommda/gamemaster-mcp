# Gamemaster MCP Server - Tools and Resources Documentation

This document provides comprehensive documentation for all MCP tools and resources available in the Gamemaster MCP Server for D&D campaign management.

## Table of Contents

1. [Overview](#overview)
2. [MCP Tools](#mcp-tools)
   - [Campaign Management](#campaign-management)
   - [Character Management](#character-management)
   - [NPC Management](#npc-management)
   - [Monster Management](#monster-management)
   - [Location Management](#location-management)
   - [Quest Management](#quest-management)
   - [Game State Management](#game-state-management)
   - [Combat Management](#combat-management)
   - [Adventure Management](#adventure-management)
   - [Session Management](#session-management)
   - [Adventure Log](#adventure-log)
   - [Transcript Management](#transcript-management)
   - [Utility Tools](#utility-tools)
3. [MCP Resources](#mcp-resources)
4. [MCP Prompts](#mcp-prompts)
5. [Data Models](#data-models)
6. [Complete Data Model Reference](DATA_MODELS.md)

## Overview

The Gamemaster MCP Server is a comprehensive D&D campaign management server built with FastMCP 2.9.0+. It provides 30+ tools for managing all aspects of D&D campaigns, from character creation to monster encounters to hierarchical adventure tracking.

**Core Architecture:**
- **Campaign-centric design**: All data is organized within [Campaign](DATA_MODELS.md#campaign) objects
- **JSON persistence**: Campaigns stored as `{campaign_name}.json` files
- **In-memory operations**: Changes happen in memory and auto-save to disk
- **Event logging**: Separate adventure log for tracking campaign events

## MCP Tools

### Campaign Management

#### `create_campaign`
Creates a new D&D campaign and sets it as active.

**Parameters:**
- `name` (str, required): Campaign name
- `description` (str, required): Brief description or tagline
- `dm_name` (str, optional): Dungeon Master name
- `setting` (str | Path, optional): Campaign setting description in markdown or path to `.txt`/`.md` file

**Returns:** Success message with campaign name

#### `get_campaign_info`
Gets comprehensive information about the current active campaign.

**Parameters:** None

**Returns:** Formatted campaign information including:
- Name, description, DM name
- Setting details
- Counts of characters, NPCs, locations, quests, sessions
- Current game state (session, location, party level, combat status)

#### `list_campaigns`
Lists all available campaigns with current campaign indicator.

**Parameters:** None

**Returns:** List of campaign names with "(current)" marker

#### `load_campaign`
Loads a specific campaign and sets it as active.

**Parameters:**
- `name` (str, required): Campaign name to load

**Returns:** Success message confirming campaign load

### Character Management

#### `create_character`
Creates a new player character with full D&D 5e stats.

**Parameters:**
- `name` (str, required): Character name
- `character_class` (str, required): Character class
- `class_level` (int, required): Class level (1-20)
- `race` (str, required): Character race
- `player_name` (str, optional): Player controlling this character
- `description` (str, optional): Appearance and demeanor description
- `bio` (str, optional): Backstory, personality, and motivations
- `background` (str, optional): Character background
- `alignment` (str, optional): Character alignment
- `strength` (int, optional): Strength score (1-30, default: 10)
- `dexterity` (int, optional): Dexterity score (1-30, default: 10)
- `constitution` (int, optional): Constitution score (1-30, default: 10)
- `intelligence` (int, optional): Intelligence score (1-30, default: 10)
- `wisdom` (int, optional): Wisdom score (1-30, default: 10)
- `charisma` (int, optional): Charisma score (1-30, default: 10)

**Returns:** Success message with character details

#### `get_character`
Gets detailed character information including stats and inventory.

**Parameters:**
- `name_or_id` (str, required): Character name or ID

**Returns:** Formatted character sheet with:
- Basic info, ability scores with modifiers
- Combat stats (AC, HP, temp HP)
- Inventory count

#### `update_character`
Updates character properties including stats, HP, and descriptive fields.

**Parameters:**
- `name_or_id` (str, required): Character name or ID to update
- `name` (str, optional): New character name
- `player_name` (str, optional): Player name
- `description` (str, optional): Character description
- `bio` (str, optional): Character bio
- `background` (str, optional): Character background
- `alignment` (str, optional): Character alignment
- `hit_points_current` (int, optional): Current HP (≥0)
- `hit_points_max` (int, optional): Maximum HP (≥1)
- `temporary_hit_points` (int, optional): Temporary HP (≥0)
- `armor_class` (int, optional): Armor class
- `inspiration` (bool, optional): Inspiration status
- `notes` (str, optional): Additional notes
- Ability scores: `strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, `charisma` (int, optional): 1-30

**Returns:** List of updated fields

#### `bulk_update_characters`
Updates multiple characters simultaneously with relative changes.

**Parameters:**
- `names_or_ids` (list[str], required): List of character names or IDs
- `hp_change` (int, optional): HP change amount (positive or negative)
- `temp_hp_change` (int, optional): Temporary HP change amount
- Ability score changes: `strength_change`, `dexterity_change`, `constitution_change`, `intelligence_change`, `wisdom_change`, `charisma_change` (int, optional)

**Returns:** Summary of changes applied to each character

#### `add_item_to_character`
Adds an item to a character's inventory.

**Parameters:**
- `character_name_or_id` (str, required): Character name or ID
- `item_name` (str, required): Item name
- `description` (str, optional): Item description
- `quantity` (int, optional): Quantity (≥1, default: 1)
- `item_type` (str, optional): Item type - "weapon", "armor", "consumable", "misc" (default: "misc")
- `weight` (float, optional): Item weight (≥0)
- `value` (str, optional): Item value (e.g., '50 gp')

**Returns:** Confirmation of item addition

#### `list_characters`
Lists all characters in the current campaign.

**Parameters:** None

**Returns:** List of characters with level, race, and class

### NPC Management

#### `create_npc`
Creates a new non-player character.

**Parameters:**
- `name` (str, required): NPC name
- `description` (str, optional): Public description of the NPC
- `bio` (str, optional): Detailed private bio including secrets
- `race` (str, optional): NPC race
- `occupation` (str, optional): NPC occupation
- `location` (str, optional): Current location
- `attitude` (str, optional): Attitude towards party - "friendly", "neutral", "hostile", "unknown"
- `notes` (str, optional): Additional notes (default: "")

**Returns:** Success message with NPC name

#### `get_npc`
Gets detailed NPC information.

**Parameters:**
- `name` (str, required): NPC name

**Returns:** Formatted NPC information including race, occupation, location, attitude, description, bio, and notes

#### `list_npcs`
Lists all NPCs in the current campaign.

**Parameters:** None

**Returns:** List of NPCs with their locations

### Monster Management

#### `create_monster`
Creates a new monster instance and adds it to the current game state.

**Parameters:**
- `name` (str, required): Instance name for this specific monster
- `monster_type` (str, required): The type/species of monster (e.g., "Goblin", "Dragon")
- `hit_points_max` (int, required): Maximum hit points (≥1)
- `hit_points_current` (int, optional): Current hit points (defaults to max)
- `armor_class` (int, optional): Armor class (default: 10, ≥1)
- `size` (str, optional): Monster size (default: "Medium")
- `creature_type` (str, optional): Creature type (default: "humanoid")
- `alignment` (str, optional): Monster alignment (default: "neutral")
- `speed` (int, optional): Speed in feet per round (default: 30)
- `challenge_rating` (str, optional): Challenge rating (default: "1/8", e.g., "1/4", "2", "15")
- `experience_value` (int, optional): Experience points awarded (default: 25, ≥0)
- `description` (str, optional): Monster description
- `location` (str, optional): Where this monster is located
- `strength` (int, optional): Strength score (1-30, default: 10)
- `dexterity` (int, optional): Dexterity score (1-30, default: 10)
- `constitution` (int, optional): Constitution score (1-30, default: 10)
- `intelligence` (int, optional): Intelligence score (1-30, default: 10)
- `wisdom` (int, optional): Wisdom score (1-30, default: 10)
- `charisma` (int, optional): Charisma score (1-30, default: 10)

**Returns:** Success message with monster name, type, and HP

**Example:**
```
create_monster(
    name="Goblin Scout",
    monster_type="Goblin",
    hit_points_max=8,
    armor_class=14,
    size="Small",
    creature_type="humanoid",
    alignment="neutral evil",
    strength=8,
    dexterity=14,
    challenge_rating="1/4",
    experience_value=50,
    description="A sneaky goblin scout with keen eyes"
)
```

#### `get_monster`
Gets detailed monster information including full stat block.

**Parameters:**
- `name` (str, required): Monster name

**Returns:** Formatted monster information including:
- Basic info (name, type, size, alignment, AC, HP, speed, status)
- Challenge rating and XP value
- Complete ability scores with modifiers
- Attacks (if any) with to-hit bonuses and damage
- Special abilities, resistances, and immunities
- Skills, senses, and languages
- Location and description
- Additional notes

**Example Output:**
```
**Goblin Scout** (Goblin) - `abc12345`
**Size/Type:** Small humanoid
**Alignment:** neutral evil
**AC:** 14 **HP:** 5/8
**Speed:** 30 ft **Status:** injured
**Challenge Rating:** 1/4 (50 XP)

**Ability Scores:**
STR 8 (-1)  DEX 14 (+2)  CON 10 (+0)
INT 10 (+0)  WIS 8 (-1)  CHA 8 (-1)

**Attacks:**
  • Scimitar: +4 to hit, 1d6+2 damage

**Special Abilities:** Nimble Escape
**Location:** Forest Clearing
**Description:** A sneaky goblin scout with keen eyes.
```

#### `list_monsters`
Lists all monsters currently in the game state.

**Parameters:** None

**Returns:** List of active monsters with their status, HP, and location

**Example Output:**
```
**Active Monsters:**
• Goblin Scout (Goblin) [injured] (5/8 HP) at Forest Clearing
• Orc Warrior (Orc) (15/15 HP) at Cave Entrance
• Young Dragon (Dragon) (178/178 HP)
```

**Note:** Unlike NPCs which are stored at the campaign level, monsters are stored in the `GameState.monsters` list and represent active threats that the party is currently facing or aware of. When monsters are no longer relevant (defeated, fled, etc.), they can be removed from the game state.

### Location Management

#### `create_location`
Creates a new geographic location or settlement.

**Parameters:**
- `name` (str, required): Location name
- `location_type` (str, required): Type of location (city, town, village, dungeon, etc.)
- `description` (str, required): Location description
- `population` (int, optional): Population if applicable (≥0)
- `government` (str, optional): Government type
- `notable_features` (list[str], optional): Notable features
- `notes` (str, optional): Additional notes (default: "")

**Returns:** Success message with location name and type

#### `get_location`
Gets detailed location information.

**Parameters:**
- `name` (str, required): Location name

**Returns:** Formatted location information including description, population, government, notable features, and notes

#### `list_locations`
Lists all locations in the current campaign.

**Parameters:** None

**Returns:** List of locations with their types

### Quest Management

#### `create_quest`
Creates a new quest or mission.

**Parameters:**
- `title` (str, required): Quest title
- `description` (str, required): Quest description
- `giver` (str, optional): Quest giver (NPC name)
- `objectives` (list[str], optional): Quest objectives
- `reward` (str, optional): Quest reward
- `notes` (str, optional): Additional notes (default: "")

**Returns:** Success message with quest title

#### `update_quest`
Updates quest status or completes objectives.

**Parameters:**
- `title` (str, required): Quest title
- `status` (str, optional): New quest status - "active", "completed", "failed", "on_hold"
- `completed_objective` (str, optional): Objective to mark as completed

**Returns:** Success message

#### `list_quests`
Lists quests with optional status filtering.

**Parameters:**
- `status` (str, optional): Filter by status - "active", "completed", "failed", "on_hold"

**Returns:** List of quests with their status

### Game State Management

#### `update_game_state`
Updates the current game state.

**Parameters:**
- `current_location` (str, optional): Current party location
- `current_session` (int, optional): Current session number (≥1)
- `current_date_in_game` (str, optional): Current in-game date
- `party_level` (int, optional): Average party level (1-20)
- `party_funds` (str, optional): Party treasure/funds
- `in_combat` (bool, optional): Whether party is in combat
- `notes` (str, optional): Current situation notes

**Returns:** Success message

#### `get_game_state`
Gets the current game state.

**Parameters:** None

**Returns:** Formatted game state including campaign, session, location, date, party level, funds, combat status, active quests, and notes

#### `set_mode`
Sets the current game mode(s). Replaces existing modes.

**Parameters:**
- `modes` (str | list[str], required): Mode(s) to set. Can be a single mode string or list of modes

**Returns:** Success message with set modes and primary mode

**Available Modes:**
- `setup`: Mode used when setting up a campaign rather than actively playing it
- `town`: Mode used when in town (bartering, gathering information, etc)
- `outdoors`: Mode active when adventuring outdoors or traveling between locations
- `dungeon`: Party is in a dungeon
- `combat`: Party is in combat

**Behavior:**
- Multiple modes can be combined (e.g., ["combat", "dungeon"] for dungeon combat)
- Combat mode is automatically moved to first position if present
- The first mode is the "primary mode" for client display priority

**Examples:**
```
set_mode("town")                          # Single mode
set_mode(["outdoors", "combat"])          # Multiple modes - becomes ["combat", "outdoors"]
set_mode(["dungeon", "combat", "setup"])  # Combat prioritized - becomes ["combat", "dungeon", "setup"]
```

#### `get_mode`
Gets the current game mode(s).

**Parameters:** None

**Returns:** Current modes list with primary mode indication

### Combat Management

#### `start_combat`
Initiates a combat encounter with initiative order.

**Parameters:**
- `participants` (list[[CombatParticipant](DATA_MODELS.md#combatparticipant)], required): Combat participants with initiative order

**Returns:** Combat start message with initiative order and current turn

#### `end_combat`
Ends the current combat encounter and records it in the transcript.

**Parameters:**
- `result` (str, required): Combat result (e.g., "victory", "defeat", "fled")
- `summary` (str, required): Brief summary of how the combat ended
- `casualties` (list[str], optional): List of participants who died or were defeated

**Returns:** Combat end confirmation with transcript recording status

**Example:**
```python
end_combat(
    result="victory",
    summary="The heroes defeated the orc raiding party after an intense battle",
    casualties=["Orc Chieftain", "Goblin Scout x2"]
)
```

#### `next_turn`
Advances to the next turn in combat.

**Parameters:** None

**Returns:** Next participant's turn

---

### Adventure Management

#### `start_adventure`
Starts an adventure and begins recording interactions in the transcript as part of this adventure. All subsequent interactions, combats, and nested adventures will be recorded within this adventure node until `end_adventure` is called.

**Parameters:**
- `title` (str, required): Adventure title (e.g., "The Temple of Doom")
- `quest_id` (str, optional): Associated quest ID, if any

**Returns:** Success message confirming adventure start

**Example:**
```python
start_adventure(
    title="The Lost Temple",
    quest_id="QST67890"
)
```

**Usage Notes:**
- Adventures create a hierarchical structure in the transcript
- Combat encounters within adventures are nested under the adventure node
- Adventures can be nested within other adventures for complex story arcs
- All interactions are recorded in the context of the current adventure until it's ended

#### `end_adventure`
Ends the current adventure and records the summary in the transcript. This restores the previous context (parent adventure or transcript root).

**Parameters:**
- `summary` (str, required): Summary of what happened during the adventure
- `rewards` (list[str], optional): List of rewards obtained (items, XP, etc.)

**Returns:** Success message with adventure title confirmation

**Example:**
```python
end_adventure(
    summary="The party explored an ancient temple and retrieved the Sacred Crown after defeating the temple guardian",
    rewards=["Sacred Crown", "500 XP", "Ancient Scrolls"]
)
```

**Usage Notes:**
- The adventure summary is recorded in the transcript tree
- After ending, new interactions will be added to the parent context
- Rewards are tracked separately from the main adventure log

### Session Management

#### `add_session_note`
Adds comprehensive notes for a game session.

**Parameters:**
- `session_number` (int, required): Session number (≥1)
- `summary` (str, required): Session summary
- `title` (str, optional): Session title
- `events` (list[str], optional): Key events that occurred
- `characters_present` (list[str], optional): Characters present in session
- `experience_gained` (int, optional): Experience points gained (≥0)
- `treasure_found` (list[str], optional): Treasure or items found
- `notes` (str, optional): Additional notes (default: "")

**Returns:** Success message with session number

#### `get_sessions`
Gets all session notes with summaries.

**Parameters:** None

**Returns:** Formatted list of all sessions with dates, titles, and summary previews

### Adventure Log

#### `add_event`
Adds an event to the adventure log for tracking campaign history.

**Parameters:**
- `event_type` (str, required): Event type - "combat", "roleplay", "exploration", "quest", "character", "world", "session"
- `title` (str, required): Event title
- `description` (str, required): Event description
- `session_number` (int, optional): Session number (≥1)
- `characters_involved` (list[str], optional): Characters involved in the event
- `location` (str, optional): Location where event occurred
- `importance` (int, optional): Event importance 1-5 (default: 3)
- `tags` (list[str], optional): Tags for categorizing the event
- `campaign_name` (str, optional): Campaign name (uses current if None)

**Returns:** Success message with event type and title

#### `get_events`
Retrieves events from the adventure log with filtering options.

**Parameters:**
- `limit` (int, optional): Maximum number of events to return (≥1)
- `campaign` (str, optional): Filter by campaign name
- `event_type` (str, optional): Filter by event type - "combat", "roleplay", "exploration", "quest", "character", "world", "session"
- `search` (str, optional): Search events by title/description

**Returns:** Formatted list of events with timestamps, importance ratings, and descriptions

### Transcript Management

The transcript system uses a **hierarchical tree structure** to organize gameplay interactions. See [TranscriptTree](DATA_MODELS.md#transcripttree) in the data models documentation for details.

#### `record_interaction`
Records a player-game interaction in the transcript. Interactions are automatically added to the current context (adventure, combat, or transcript root).

**Parameters:**
- `player_entry` (str, required): Text input by the player
- `game_response` (str, required): Response sent by the game
- `campaign_name` (str, optional): Campaign name (uses current if None)
- `session_number` (int, optional): Session number (uses latest if None, ≥1)

**Returns:** None (records interaction)

**Usage Notes:**
- Interactions are automatically nested within the current context
- If inside an adventure, interactions are added to the adventure's actions
- If inside combat, interactions are added to the combat's actions
- If no adventure or combat is active, interactions are added to the transcript root
- The current context is tracked via `current_parent_id` in the transcript tree

**Example:**
```python
# Start an adventure
start_adventure(title="The Lost Temple")

# Record interaction - will be nested in the adventure
record_interaction(
    player_entry="We search for the temple entrance",
    game_response="You find hidden stairs leading underground..."
)

# Start combat within the adventure
start_combat(participants=[...])

# Record combat interaction - will be nested in the combat node
record_interaction(
    player_entry="I attack the guardian",
    game_response="Roll for attack: Natural 20! Critical hit!"
)

# End combat - returns to adventure context
end_combat(result="victory", summary="Defeated the temple guardian")

# End adventure - returns to transcript root
end_adventure(summary="Retrieved the Sacred Crown")
```

### Utility Tools

#### `roll_dice`
Rolls dice using D&D notation with advantage/disadvantage support.

**Parameters:**
- `dice_notation` (str, required): Dice notation (e.g., '1d20', '3d6+2')
- `advantage` (bool, optional): Roll with advantage (default: False)
- `disadvantage` (bool, optional): Roll with disadvantage (default: False)

**Returns:** Formatted roll result with individual dice and total

#### `calculate_experience`
Calculates experience points for an encounter based on D&D 5e rules.

**Parameters:**
- `party_size` (int, required): Number of party members (≥1)
- `party_level` (int, required): Average party level (1-20)
- `encounter_xp` (int, required): Total encounter XP value (≥0)

**Returns:** Formatted experience calculation with base XP, multiplier, and XP per player

## MCP Resources

The server provides several MCP resources for accessing campaign data:

### `resource://campaigns/{campaign_name}`
Returns a specific [Campaign](DATA_MODELS.md#campaign) object by name.

**Parameters:**
- `campaign_name` (str): Name of the campaign

**Returns:** Complete [Campaign](DATA_MODELS.md#campaign) object

### `resource://campaigns`
Returns list of all available campaign names.

**Parameters:** None

**Returns:** List of campaign names

### `resource://current_campaign`
Returns the name of the currently active campaign.

**Parameters:** None

**Returns:** Current campaign name

### `resource://characters/{character_name}`
Returns a specific [Character](DATA_MODELS.md#character) object by name.

**Parameters:**
- `character_name` (str): Name of the character

**Returns:** Complete [Character](DATA_MODELS.md#character) object with full D&D 5e character sheet

### `resource://campaigns/{campaign_name}/characters`
Returns all [Character](DATA_MODELS.md#character) objects for a specific campaign.

**Parameters:**
- `campaign_name` (str): Name of the campaign

**Returns:** List of complete [Character](DATA_MODELS.md#character) objects with full D&D 5e character sheets

### `resource://current_campaign/characters`
Returns all [Character](DATA_MODELS.md#character) objects for the currently active campaign.

**Parameters:** None

**Returns:** List of complete [Character](DATA_MODELS.md#character) objects with full D&D 5e character sheets, or empty list if no current campaign

### `resource://transcripts/{campaign_name}/{session_number}`
Returns transcript tree for a specific campaign session.

**Parameters:**
- `campaign_name` (str): Campaign name
- `session_number` (int): Session number

**Returns:** [TranscriptTree](DATA_MODELS.md#transcripttree) object with hierarchical structure of all interactions, combats, and adventures

**Note:** Old flat transcripts are automatically migrated to the tree format when accessed.

### `resource://current_transcript`
Returns transcript tree for the current campaign and latest session.

**Parameters:** None

**Returns:** Current [TranscriptTree](DATA_MODELS.md#transcripttree) object with hierarchical structure

**Example Response Structure:**
```json
{
  "id": "TRS12345",
  "node_type": "transcript",
  "campaign": "Rise of the Dragon Lords",
  "session_number": 5,
  "children": [
    {
      "node_type": "interaction",
      "user_text": "We enter the dragon's lair",
      "responses": [...]
    },
    {
      "node_type": "adventure",
      "title": "The Lost Temple",
      "actions": [
        {
          "node_type": "combat",
          "participants": ["Party", "Guardian"],
          "actions": [...]
        }
      ]
    }
  ],
  "current_parent_id": "TRS12345"
}
```

### `resource://current_campaign/game_state`
Returns the game state for the currently active campaign.

**Parameters:** None

**Returns:** [GameState](DATA_MODELS.md#gamestate) object containing current party location, session, combat status, and other game variables

### `resource://campaigns/{campaign_name}/game_state`
Returns the game state for a specific campaign.

**Parameters:**
- `campaign_name` (str): Name of the campaign

**Returns:** [GameState](DATA_MODELS.md#gamestate) object containing current party location, session, combat status, and other game variables

### `resource://current_campaign/mode`
Returns the current game mode(s) for the active campaign.

**Parameters:** None

**Returns:** JSON object containing:
- `modes` (list[str]): List of currently active modes
- `primary_mode` (str | None): The primary (first) mode, or None if no modes set

**Example Response:**
```json
{
  "modes": ["combat", "dungeon"],
  "primary_mode": "combat"
}
```

### `resource://modes`
Returns all available game modes with descriptions.

**Parameters:** None

**Returns:** List of mode objects, each containing:
- `mode` (str): Mode name
- `description` (str): Mode description

**Example Response:**
```json
[
  {
    "mode": "setup",
    "description": "Mode used when you're setting up a campaign rather than actively playing it"
  },
  {
    "mode": "town",
    "description": "Mode used when in town (typically bartering, gathering information, etc)"
  },
  {
    "mode": "outdoors",
    "description": "Mode active when adventuring outdoors or traveling between locations by land"
  },
  {
    "mode": "dungeon",
    "description": "Party is in a dungeon"
  },
  {
    "mode": "combat",
    "description": "Party is in combat"
  }
]
```

## MCP Prompts

The server provides intelligent prompts that adapt to the current game state and context.

### `current_prompt`

Generates the most appropriate system prompt for the current game state, providing comprehensive guidance for Dungeon Masters.

**Parameters:** None

**Returns:** Dynamic system prompt tailored for D&D campaign management

**Key Features:**
- **Campaign-Centric Guidance**: Emphasizes working within the active campaign context
- **Structured Data Management**: Encourages detailed entity creation and updates
- **Proactive Tool Chaining**: Suggests combining multiple tools for complex requests
- **Dynamic State Management**: Guides real-time updates during gameplay
- **Narrative Integration**: Balances data management with storytelling
- **Event Logging**: Promotes comprehensive adventure history tracking
- **Player Character Management**: Provides guidance for single or multi-character control

**Content Sections:**
1. **Core Principles**: Fundamental guidelines for campaign management
2. **In-Play Campaign Guidance**: Dynamic gameplay and narrative support
3. **Player Character Handling**: Instructions for character control scenarios
4. **Tool Integration**: Specific recommendations for tool usage patterns

This prompt adapts the MCP server's behavior to provide contextual assistance based on the current campaign state, active characters, and ongoing story elements.

## Data Models

The server uses comprehensive Pydantic models for data validation:

### Core Models

- **[`Campaign`](DATA_MODELS.md#campaign)**: Main container with characters, NPCs, locations, quests, game state
- **[`Character`](DATA_MODELS.md#character)**: Complete D&D 5e character sheet with abilities, inventory, spells
- **[`NPC`](DATA_MODELS.md#npc)**: Non-player character with description, bio, relationships
- **[`Location`](DATA_MODELS.md#location)**: Geographic location with features and connections
- **[`Quest`](DATA_MODELS.md#quest)**: Mission with objectives, status, and rewards
- **[`GameState`](DATA_MODELS.md#gamestate)**: Current party status, location, combat state
- **[`SessionNote`](DATA_MODELS.md#sessionnote)**: Session summary with events and treasure
- **[`AdventureEvent`](DATA_MODELS.md#adventureevent)**: Logged event with type, importance, and tags

### Supporting Models

- **[`AbilityScore`](DATA_MODELS.md#abilityscore)**: D&D ability score with automatic modifier calculation
- **[`CharacterClass`](DATA_MODELS.md#characterclass)**: Class with level, hit dice, and subclass
- **[`Race`](DATA_MODELS.md#race)**: Race with subrace and traits
- **[`Item`](DATA_MODELS.md#item)**: Equipment with type, weight, value, and properties
- **[`Spell`](DATA_MODELS.md#spell)**: Spell with level, school, components, and description
- **[`CombatParticipant`](DATA_MODELS.md#combatparticipant)**: Combat stats for initiative tracking
- **[`Attack`](DATA_MODELS.md#attack)**: Attack details with modifiers and damage
- **[`Transcript`](DATA_MODELS.md#transcript-legacy)**: Collection of interactions for a session (legacy format)
- **[`TranscriptEntry`](DATA_MODELS.md#transcriptentry-legacy)**: Individual player-game interaction (legacy format)
- **[`TranscriptTree`](DATA_MODELS.md#transcripttree)**: Hierarchical transcript structure with nested adventures and combats
- **[`TranscriptInteraction`](DATA_MODELS.md#transcriptinteraction)**: Single user-LLM exchange (leaf node)
- **[`TranscriptCombat`](DATA_MODELS.md#transcriptcombat)**: Combat encounter with nested actions (interior node)
- **[`TranscriptAdventure`](DATA_MODELS.md#transcriptadventure)**: Story arc with nested interactions and combats (interior node)

### Data Validation

All models include comprehensive validation:
- Ability scores: 1-30 range
- Character levels: 1-20 range
- HP values: Non-negative integers
- Required fields and optional parameters
- Automatic timestamps and ID generation
- Type safety with Pydantic annotations

## Usage Notes

1. **Campaign Context**: Always ensure a campaign is loaded before using character/NPC/location tools
2. **Error Handling**: Tools provide clear error messages for missing entities or invalid operations
3. **Auto-Save**: All changes are automatically persisted to JSON files
4. **ID vs Name**: Most tools accept either entity names or IDs for flexibility
5. **Bulk Operations**: Use bulk update tools for efficiency when modifying multiple entities
6. **Event Logging**: Use adventure log tools to maintain campaign history and narrative continuity