# Gamemaster MCP Server - Tools and Resources Documentation

This document provides comprehensive documentation for all MCP tools and resources available in the Gamemaster MCP Server for D&D campaign management.

## Table of Contents

1. [Overview](#overview)
2. [MCP Tools](#mcp-tools)
   - [Campaign Management](#campaign-management)
   - [Character Management](#character-management)
   - [NPC Management](#npc-management)
   - [Location Management](#location-management)
   - [Quest Management](#quest-management)
   - [Game State Management](#game-state-management)
   - [Combat Management](#combat-management)
   - [Session Management](#session-management)
   - [Adventure Log](#adventure-log)
   - [Transcript Management](#transcript-management)
   - [Utility Tools](#utility-tools)
3. [MCP Resources](#mcp-resources)
4. [Data Models](#data-models)
5. [Complete Data Model Reference](DATA_MODELS.md)

## Overview

The Gamemaster MCP Server is a comprehensive D&D campaign management server built with FastMCP 2.9.0+. It provides 25+ tools for managing all aspects of D&D campaigns, from character creation to adventure logging.

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

### Combat Management

#### `start_combat`
Initiates a combat encounter with initiative order.

**Parameters:**
- `participants` (list[[CombatParticipant](DATA_MODELS.md#combatparticipant)], required): Combat participants with initiative order

**Returns:** Combat start message with initiative order and current turn

#### `end_combat`
Ends the current combat encounter.

**Parameters:** None

**Returns:** Combat end confirmation

#### `next_turn`
Advances to the next turn in combat.

**Parameters:** None

**Returns:** Next participant's turn

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

#### `record_interaction`
Records a player-game interaction in the transcript.

**Parameters:**
- `player_entry` (str, required): Text input by the player
- `game_response` (str, required): Response sent by the game
- `campaign_name` (str, optional): Campaign name (uses current if None)
- `session_number` (int, optional): Session number (uses latest if None, ≥1)

**Returns:** None (records interaction)

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
Returns transcript for a specific campaign session.

**Parameters:**
- `campaign_name` (str): Campaign name
- `session_number` (int): Session number

**Returns:** [Transcript](DATA_MODELS.md#transcript) object with all interactions

### `resource://current_transcript`
Returns transcript for the current campaign and latest session.

**Parameters:** None

**Returns:** Current [Transcript](DATA_MODELS.md#transcript) object

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
- **[`TranscriptEntry`](DATA_MODELS.md#transcriptentry)**: Individual player-game interaction
- **[`Transcript`](DATA_MODELS.md#transcript)**: Collection of interactions for a session

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