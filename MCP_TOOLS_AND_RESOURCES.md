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
   - [Hex Map Management](#hex-map-management)
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

The Gamemaster MCP Server is a comprehensive D&D campaign management server built with FastMCP 2.12+. It provides 40+ tools for managing all aspects of D&D campaigns, from character creation to monster encounters to wilderness hex mapping with hierarchical location organization.

**Core Architecture:**
- **Campaign-centric design**: All data is organized within [Campaign](DATA_MODELS.md#campaign) objects
- **JSON persistence**: Campaigns stored as `{campaign_name}.json` files
- **In-memory operations**: Changes happen in memory and auto-save to disk
- **Event logging**: Separate adventure log for tracking campaign events
- **Hierarchical locations**: Parent-child relationships for locations with campaign root support
- **Hex map integration**: Wilderness exploration with hex-based maps linked to locations

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

Locations support hierarchical organization (parent-child relationships) and hex map integration for seamless wilderness exploration.

#### `create_location`
Creates a new geographic location or settlement with optional hierarchy and map placement.

**Parameters:**
- `name` (str, required): Location name
- `location_type` (str, required): Type of location (city, town, village, dungeon, etc.)
- `description` (str, required): Location description
- `population` (int, optional): Population if applicable (≥0)
- `government` (str, optional): Government type
- `notable_features` (list[str], optional): Notable features
- `notes` (str, optional): Additional notes (default: "")
- `parent_location_id` (str, optional): ID of parent location in hierarchy
- `location_scale` (LocationScale, optional): Scale/scope (LOCAL, BUILDING, SETTLEMENT, AREA, etc.)
- `primary_map` (str, optional): Name of hex map this location appears on
- `hex_x` (int, optional): X coordinate on hex map
- `hex_y` (int, optional): Y coordinate on hex map

**Returns:** Success message with location details and hierarchy/map info if provided

**Example:**
```python
create_location(
    name="Waterdeep",
    location_type="city",
    description="The City of Splendors",
    location_scale="settlement",
    primary_map="Sword Coast",
    hex_x=12,
    hex_y=8
)
```

#### `get_location`
Gets detailed location information including hierarchy and map placement.

**Parameters:**
- `name` (str, required): Location name

**Returns:** Formatted location information including:
- Basic info (ID, type, scale, description, population, government)
- Hierarchy path from root (if applicable)
- Child locations (nested tree view)
- Map placement (map name and coordinates)
- Notable features and notes

#### `list_locations`
Lists all locations in the current campaign.

**Parameters:** None

**Returns:** List of locations with their types

#### `delete_location`
Deletes a location from the campaign with optional recursive deletion of children.

**Parameters:**
- `location_id` (str, required): ID of location to delete
- `recursive` (bool, optional): If True, delete all child locations. If False, prevent deletion if location has children (default: False)

**Returns:** Success message with count of deleted locations

**Note:** Similar to `rm -rf`, use recursive=True carefully!

#### Root Location Management

#### `get_root_location`
Gets information about the campaign's root location.

**Parameters:** None

**Returns:** Root location details and list of top-level locations

#### `set_root_location`
Sets an existing location as the campaign root.

**Parameters:**
- `location_id` (str, required): ID of location to become root

**Returns:** Success message with orphaned location count

**Note:** The location must not have a parent. All orphaned locations become children of the new root.

#### `get_top_level_locations`
Lists all top-level locations (direct children of root, or orphans if no root).

**Parameters:** None

**Returns:** List of top-level locations with IDs and scales

#### Hierarchy Management

#### `set_location_parent`
Sets or clears the parent location for a location.

**Parameters:**
- `child_location_id` (str, required): ID of child location
- `parent_location_id` (str, optional): ID of parent location, or None to make child a top-level location

**Returns:** Success message with parent-child relationship

#### `get_location_hierarchy`
Gets the hierarchical context for a location.

**Parameters:**
- `location_id` (str, required): ID of location to get hierarchy for
- `include_children` (bool, optional): Include child locations (default: True)
- `include_ancestors` (bool, optional): Include ancestor locations (default: True)

**Returns:** Full hierarchy tree with:
- Path from root (ancestor chain)
- Current location
- Child locations (nested tree)

#### `list_child_locations`
Lists all child locations within a parent location.

**Parameters:**
- `parent_location_id` (str, required): ID of parent location
- `recursive` (bool, optional): If True, list all descendants recursively (default: False)

**Returns:** List of child locations (flat list for direct children, tree view for recursive)

#### Map Integration

#### `place_location_on_map`
Places a location on a hex map at specific coordinates.

**Parameters:**
- `location_id` (str, required): ID of location to place
- `map_name` (str, required): Name of hex map
- `x` (int, required): X coordinate on map
- `y` (int, required): Y coordinate on map
- `create_poi` (bool, optional): Automatically create a corresponding PointOfInterest (default: True)

**Returns:** Success message with POI creation status

#### `list_locations_on_map`
Lists all locations that appear on a specific map.

**Parameters:**
- `map_name` (str, required): Name of hex map
- `location_type` (str, optional): Filter by location type

**Returns:** List of locations with coordinates

#### `sync_location_and_poi`
Synchronizes a Location with its corresponding PointOfInterest.

**Parameters:**
- `location_id` (str, required): ID of location
- `poi_id` (str, required): ID of POI to sync with

**Returns:** Success message

**Note:** Syncs map placement, coordinates, and bidirectional linking.

#### Migration Tools

#### `upgrade_location`
Upgrades an existing location to use new hierarchy and map fields.

**Parameters:**
- `location_id` (str, required): ID of location to upgrade
- `location_type` (LocationType, optional): Set structured LocationType enum
- `location_scale` (LocationScale, optional): Set scale level
- `parent_location_id` (str, optional): Set parent in hierarchy
- `primary_map` (str, optional): Set primary map reference
- `hex_x` (int, optional): X coordinate on map
- `hex_y` (int, optional): Y coordinate on map
- `infer_scale_from_type` (bool, optional): Automatically set location_scale based on type (default: False)

**Returns:** List of upgraded fields

**Note:** Only updates fields that are currently None/empty. Safe for selective migration.

#### `list_unmigrated_locations`
Lists locations that haven't been upgraded to new format.

**Parameters:** None

**Returns:** List of unmigrated locations with suggestion to use `upgrade_location`

**Unmigrated Criteria:**
- No parent (and not root)
- No children
- No map placement

### Hex Map Management

Hex maps provide wilderness exploration and travel tracking using hexagonal grids. Each hex can contain terrain, Points of Interest (POIs), and integrate with Locations.

**Current Map Concept:**
Most hex map tools have an optional `map_name` parameter that defaults to the "current map". The current map is automatically determined based on the current location in the campaign's game state. When the current location (or any parent location in the hierarchy) has a `primary_map` field set, that map becomes the current map. This allows you to omit `map_name` from hex map tools when working with the party's current location, and the system will automatically use the contextually appropriate map.

**Terrain Types (24 total):**
Grasslands: `grass`, `scrub`, `plains` | Forests: `forest`, `light_forest`, `dense_forest`, `jungle` | Wetlands: `marsh`, `swamp` | Elevation: `hills`, `mountains` | Arid: `desert`, `badlands`, `wasteland` | Cold: `tundra`, `glacier` | Special: `volcanic`, `coastal`, `water` | Populated: `urban`, `farmland`

**POI Types (13 total):**
Settlements: `city`, `town`, `village`, `inn` | Structures: `castle`, `temple`, `tower`, `shrine` | Exploration: `dungeon`, `ruins`, `cave`, `camp`, `landmark`

#### `create_hex_map`
Creates a new hex-based wilderness map.

**Parameters:**
- `name` (str, required): Map name (e.g., "Sword Coast", "Barovia")
- `description` (str, optional): Map description
- `hex_size_miles` (int, optional): Miles per hex side (default: 6 miles = ~31 sq mi per hex)
- `default_terrain` (TerrainType, optional): Default terrain for unspecified hexes (default: "plains")

**Returns:** Success message with map name

#### `get_hex_map`
Gets information about a specific hex map.

**Parameters:**
- `name` (str, required): Map name

**Returns:** Formatted map information including hex count, roads, rivers, and terrain summary

#### `list_hex_maps`
Lists all hex maps in the current campaign.

**Parameters:** None

**Returns:** List of map names with hex counts

#### `add_or_update_hex`
Adds or updates a hex on a map.

**Parameters:**
- `x` (int, required): X coordinate
- `y` (int, required): Y coordinate
- `terrain` (TerrainType, required): Terrain type
- `explored` (bool, optional): Whether party has explored this hex (default: False)
- `elevation` (int, optional): Elevation in meters above sea level
- `notes` (str, optional): Hex notes
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Success message with hex coordinate

#### `get_hex`
Gets information about a specific hex.

**Parameters:**
- `x` (int, required): X coordinate
- `y` (int, required): Y coordinate
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Formatted hex information including terrain, POIs, discovery status, and notes

#### `add_poi_to_hex`
Adds a Point of Interest to a hex.

**Parameters:**
- `x` (int, required): X coordinate of hex
- `y` (int, required): Y coordinate of hex
- `name` (str, required): POI name
- `poi_type` (POIType, required): Type of POI (city, town, village, ruins, dungeon, castle, temple, tower, cave, inn, camp, shrine, landmark)
- `description` (str, optional): POI description
- `location_id` (str, optional): Associated Location ID for bidirectional linking
- `discovered` (bool, optional): Whether party has discovered this POI (default: False)
- `notes` (str, optional): POI notes
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Success message with POI ID

#### `list_pois_on_map`
Lists all Points of Interest on a map.

**Parameters:**
- `poi_type` (POIType, optional): Filter by POI type
- `discovered_only` (bool, optional): Only show discovered POIs (default: False)
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** List of POIs with coordinates and discovery status

#### `add_road`
Adds a road to a hex map.

**Parameters:**
- `path` (list[tuple[int, int]], required): List of (x, y) coordinates the road passes through, in order from start to end
- `road_type` (str, optional): Road quality - "highway", "road", "path", "trail" (default: "road")
- `condition` (str, optional): Road condition - "well-maintained", "fair", "poor", "overgrown" (default: "fair")
- `start_point` (str, optional): Where the road starts in the first hex: "center", "north", "northeast", "southeast", "south", "southwest", or "northwest" (default: "center")
- `end_point` (str, optional): Where the road ends in the last hex (default: "center")
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Success message with road details

**Example:**
```python
# Uses current map if party is at a location with a map
add_road(
    path=[(5, 3), (6, 3), (7, 4)],
    road_type="highway"
)

# Or specify a specific map
add_road(
    path=[(5, 3), (6, 3), (7, 4)],
    road_type="highway",
    map_name="Sword Coast"
)
```

#### `add_river`
Adds a river to a hex map.

**Parameters:**
- `path` (list[tuple[int, int]], required): List of (x, y) coordinates the river flows through, from source to mouth
- `width` (str, optional): River width category - "stream", "river", "wide river" (default: "river")
- `navigable` (bool, optional): Whether the river is navigable by boat (default: False)
- `start_point` (str, optional): Where the river starts in the first hex: "center" (spring/source) or a side (default: "center")
- `end_point` (str, optional): Where the river ends in the last hex: "center" (lake/ocean) or a side (default: "center")
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Success message with river details

**Example:**
```python
# River flowing through multiple hexes on current map
add_river(
    path=[(3, 2), (3, 3), (4, 3)],
    width="river",
    navigable=True
)
```

#### `get_neighboring_hexes`
Gets all hexes adjacent to a specific hex.

**Parameters:**
- `x` (int, required): X coordinate of center hex
- `y` (int, required): Y coordinate of center hex
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** List of neighboring hex coordinates (up to 6 neighbors)

**Note:** Hex maps use offset coordinate system. Neighbors depend on whether row is even or odd.

#### `render_hex_map`
Renders a hex map in the specified format for display or export.

**Parameters:**
- `render_mode` (Literal["json", "ascii", "emoji"], optional): Rendering mode (default: "emoji")
  - `json`: Returns structured JSON data suitable for external renderers
  - `ascii`: Returns text-based map using terrain code letters (same format as map creation)
  - `emoji`: Returns visually appealing ASCII art with emojis representing terrain
- `center_x` (int, optional): X coordinate to center the view (shows all if not provided)
- `center_y` (int, optional): Y coordinate to center the view (shows all if not provided)
- `radius` (int, optional): Radius in hexes around center point (only used with center_x/y)
- `map_name` (str, optional): Name of hex map to render (uses current map if not provided)

**Returns:** Rendered map in the specified format

**JSON Mode:**
Returns complete structured data including:
- Map metadata (name, description, hex size, default terrain)
- Bounds (min/max x/y coordinates)
- All hexes with coordinates, terrain, discovery status, elevation, POIs
- All roads with paths
- All rivers with segments

**ASCII Mode:**
Returns text-based map using single-letter terrain codes:
- **Grasslands:** G = grass, R = scrub, P = plains
- **Forests:** F = forest, L = light_forest, D = dense_forest, J = jungle
- **Wetlands:** A = marsh, S = swamp
- **Elevation:** H = hills, M = mountains
- **Arid:** E = desert, B = badlands, X = wasteland
- **Cold:** T = tundra, I = glacier
- **Special:** V = volcanic, C = coastal, W = water
- **Populated:** U = urban, N = farmland
- Hexes with POIs marked with `*`
- Includes terrain legend and POI list

**Emoji Mode (default):**
Returns rich-text visual display:
- **Grasslands:** 🟢 grass, 🌿 scrub, 🟢 plains
- **Forests:** 🌲 forest, 🌳 light_forest, 🌲 dense_forest, 🌴 jungle
- **Wetlands:** 🌿 marsh, 🌿 swamp
- **Elevation:** ⛰️ hills, 🏔️ mountains
- **Arid:** 🏜️ desert, 🪨 badlands, 💀 wasteland
- **Cold:** ❄️ tundra, 🧊 glacier
- **Special:** 🌋 volcanic, 🏖️ coastal, 🌊 water
- **Populated:** 🏙️ urban, 🌾 farmland
- POIs shown with 📍 or count (2📍) plus type-specific emojis (🏙️ city, 🏛️ temple, 🏰 castle, etc.)
- Includes terrain legend, POI list with coordinates
- Shows roads and rivers if present in view

**Example:**
```python
# Display current map with emojis (uses party's current location map)
render_hex_map()

# ASCII text version of current map
render_hex_map(render_mode="ascii")

# JSON for external renderer
render_hex_map(render_mode="json")

# View only 5-hex radius around a specific point on current map
render_hex_map(
    render_mode="emoji",
    center_x=12,
    center_y=8,
    radius=5
)

# Or specify a specific map explicitly
render_hex_map(map_name="Sword Coast", render_mode="emoji")
```

#### `calculate_distance`
Calculates the distance in hexes and kilometers between two points on a hex map.

**Parameters:**
- `from_x` (int, required): Starting X coordinate
- `from_y` (int, required): Starting Y coordinate
- `to_x` (int, required): Destination X coordinate
- `to_y` (int, required): Destination Y coordinate
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Distance in hexes and kilometers

**Example:**
```python
# Calculate distance on current map
calculate_distance(from_x=5, from_y=3, to_x=12, to_y=8)
# Returns: "Distance from [5,3] to [12,8]: 8 hexes (48.0 km)"
```

#### `describe_area`
Describes an area of the map centered on a specific hex, including terrain and POIs.

**Parameters:**
- `center_x` (int, required): X coordinate of center hex
- `center_y` (int, required): Y coordinate of center hex
- `radius` (int, optional): Radius in hexes (default: 1)
- `map_name` (str, optional): Name of hex map (uses current map if not provided)

**Returns:** Detailed description of the area including terrain, POIs, roads, and rivers

**Example:**
```python
# Describe 2-hex radius around a point on current map
describe_area(center_x=10, center_y=5, radius=2)
```

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
Records a player-game interaction in the transcript with a simple text response. Interactions are automatically added to the current context (adventure, combat, or transcript root).

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
- For interactions where the LLM made tool calls, use `record_interaction_with_tools` instead

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

#### `record_interaction_with_tools`
Records a player-game interaction that includes tool calls in the transcript. This function supports recording interactions where the LLM's response included both text and tool calls, preserving the complete context of how the game responded to the player.

**Parameters:**
- `player_entry` (str, required): Text input by the player
- `game_responses` (list[str | list[dict]], required): List of responses where each entry is either:
  - A string (text response)
  - A list of dicts (tool calls), where each dict has:
    - `tool_name` (str): Name of the tool called
    - `tool_id` (str): Unique ID for the tool call
    - `tool_parameters` (dict): Parameters passed to the tool
    - `tool_result` (str): Result returned by the tool
- `campaign_name` (str, optional): Campaign name (uses current if None)
- `session_number` (int, optional): Session number (uses latest if None, ≥1)

**Returns:** Success message with count of responses recorded

**Usage Notes:**
- Use this tool instead of `record_interaction` when the LLM's response included tool calls
- Supports mixed responses - text and tool calls can be interleaved
- Tool calls are recorded with their complete context (input parameters and results)
- Like `record_interaction`, interactions are nested in the current context (adventure/combat/root)
- This preserves the full interaction history including how tools were used

**Example:**
```python
# Record an interaction with tool calls
record_interaction_with_tools(
    player_entry="I attack the goblin with my sword",
    game_responses=[
        "Let me roll for your attack...",
        [
            {
                "tool_name": "roll_dice",
                "tool_id": "call_123",
                "tool_parameters": {"dice_notation": "1d20+5"},
                "tool_result": "🎲 1d20+5 [18] +5 = 23"
            }
        ],
        "You hit! Now rolling for damage...",
        [
            {
                "tool_name": "roll_dice",
                "tool_id": "call_124",
                "tool_parameters": {"dice_notation": "1d8+3"},
                "tool_result": "🎲 1d8+3 [6] +3 = 9"
            },
            {
                "tool_name": "update_character",
                "tool_id": "call_125",
                "tool_parameters": {"name_or_id": "Goblin", "hit_points_current": 0},
                "tool_result": "Updated Goblin: hit points current: 0"
            }
        ],
        "Your blade strikes true, dealing 9 damage! The goblin falls defeated."
    ]
)
# Result: "Recorded interaction with 4 response(s) to transcript"
```

**Comparison with `record_interaction`:**
- `record_interaction`: Simple text-only responses
  ```python
  record_interaction(
      player_entry="What do you see?",
      game_response="You see a large stone door"
  )
  ```
- `record_interaction_with_tools`: Complex responses with tool calls
  ```python
  record_interaction_with_tools(
      player_entry="I attack!",
      game_responses=[
          "Rolling attack...",
          [{"tool_name": "roll_dice", ...}],
          "You hit!"
      ]
  )
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