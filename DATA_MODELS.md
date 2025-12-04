# Data Models Reference

This document provides comprehensive documentation for all data models used in the Gamemaster MCP Server. All models are implemented using [Pydantic](https://docs.pydantic.dev/) and provide full type validation and serialization.

## Table of Contents

1. [Core Campaign Models](#core-campaign-models)
   - [Campaign](#campaign)
   - [GameState](#gamestate)
2. [Character Models](#character-models)
   - [Character](#character)
   - [AbilityScore](#abilityscore)
   - [CharacterClass](#characterclass)
   - [Race](#race)
3. [World Building Models](#world-building-models)
   - [NPC](#npc)
   - [Monster](#monster)
   - [Location](#location)
   - [Quest](#quest)
4. [Hex Map Models](#hex-map-models)
   - [HexMap](#hexmap)
   - [Hex](#hex)
   - [HexCoordinate](#hexcoordinate)
   - [PointOfInterest](#pointofinterest)
   - [Road](#road)
   - [River](#river)
   - [TerrainType](#terraintype)
   - [HexSide](#hexside)
   - [POIType](#poitype)
5. [Equipment and Items](#equipment-and-items)
   - [Item](#item)
   - [Spell](#spell)
6. [Combat Models](#combat-models)
   - [CombatParticipant](#combatparticipant)
   - [Attack](#attack)
   - [CombatEncounter](#combatencounter)
7. [Session Management](#session-management)
   - [SessionNote](#sessionnote)
   - [AdventureEvent](#adventureevent)
   - [EventType](#eventtype)
8. [Transcript Models](#transcript-models)
   - [Transcript (Legacy)](#transcript-legacy)
   - [TranscriptEntry (Legacy)](#transcriptentry-legacy)
   - [TranscriptTree](#transcripttree)
   - [TranscriptInteraction](#transcriptinteraction)
   - [TranscriptCombat](#transcriptcombat)
   - [TranscriptAdventure](#transcriptadventure)
   - [Response Types](#response-types)
9. [System Models](#system-models)
   - [GameStats](#gamestats)

---

## Core Campaign Models

### Campaign

The main container model that holds all campaign data.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): Campaign name
- `description` (str): Campaign description
- `dm_name` (str | None): Dungeon Master name
- `setting` (str | Path | None): Campaign setting description or path to file
- `characters` (dict[str, Character]): All player characters indexed by name
- `npcs` (dict[str, NPC]): All NPCs indexed by name
- `locations` (dict[str, Location]): All locations indexed by name
- `quests` (dict[str, Quest]): All quests indexed by title
- `encounters` (dict[str, CombatEncounter]): Combat encounters indexed by name
- `sessions` (list[SessionNote]): List of session notes
- `hex_maps` (dict[str, HexMap]): Hex maps for outdoor/wilderness areas, indexed by map name
- `game_state` (GameState): Current game state
- `world_notes` (str): Additional world-building notes
- `root_location_id` (str | None): ID of the root location representing the entire game world
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime | None): Last update timestamp

**Methods:**
- `get_setting() -> str`: Returns the setting text, handling both string and file paths

**Example:**
```json
{
  "id": "ABC12345",
  "name": "Rise of the Dragon Lords",
  "description": "Epic campaign against ancient dragons",
  "dm_name": "John Smith",
  "setting": "A world where dragons have returned...",
  "characters": {...},
  "npcs": {...},
  "locations": {...},
  "game_state": {...},
  "created_at": "2024-01-15T10:30:00"
}
```

### GameState

Tracks the current state of the campaign session.

**Fields:**
- `campaign_name` (str): Name of the associated campaign
- `current_session` (int): Current session number (default: 1)
- `current_date_in_game` (str | None): In-game date
- `current_location` (str | None): Current party location
- `active_quests` (list[str]): List of active quest titles
- `party_level` (int): Average party level (default: 1)
- `party_funds` (str): Party treasure/funds (default: "0 gp")
- `initiative_order` (list[CombatParticipant]): Combat initiative order
- `in_combat` (bool): Whether party is currently in combat
- `current_turn` (str | None): Whose turn it is in combat
- `monsters` (list[Monster]): Monsters the party is currently facing or aware of
- `modes` (list[str]): Current active game modes (default: ["setup"])
- `notes` (str): Current situation notes
- `updated_at` (datetime): Last update timestamp

**Available Modes:**
- `setup`: Mode used when setting up a campaign rather than actively playing it
- `town`: Mode used when in town (bartering, gathering information, etc)
- `outdoors`: Mode active when adventuring outdoors or traveling between locations
- `dungeon`: Party is in a dungeon
- `combat`: Party is in combat

**Mode Behavior:**
- Multiple modes can be active simultaneously (e.g., ["combat", "dungeon"] for dungeon combat)
- The first mode in the list is the "primary mode" and has priority for client displays
- Combat mode is automatically moved to first position when present
- Modes enable contextual tool filtering and add mode-specific rules to prompts

**Example:**
```json
{
  "campaign_name": "Rise of the Dragon Lords",
  "current_session": 5,
  "current_location": "Dragon's Lair",
  "party_level": 8,
  "party_funds": "2500 gp",
  "in_combat": true,
  "current_turn": "Aragorn",
  "monsters": [
    {
      "name": "Ancient Red Dragon",
      "monster_type": "Dragon",
      "hit_points_current": 350,
      "hit_points_max": 546
    }
  ],
  "notes": "Party is low on spell slots"
}
```

---

## Character Models

### Character

Complete D&D 5e character sheet model.

**Basic Information:**
- `id` (str): Unique 8-character identifier
- `name` (str): Character name
- `player_name` (str | None): Name of controlling player
- `character_class` (CharacterClass): Class and level information
- `race` (Race): Race and subrace information
- `background` (str | None): Character background
- `alignment` (str | None): Character alignment
- `description` (str | None): Appearance and demeanor
- `bio` (str | None): Backstory, personality, and motivations

**Core Stats:**
- `abilities` (dict[str, AbilityScore]): Six D&D ability scores
  - Keys: "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
  - Values: AbilityScore objects with score and computed modifier

**Combat Stats:**
- `armor_class` (int): Armor class (default: 10)
- `hit_points_max` (int): Maximum hit points (default: 1)
- `hit_points_current` (int): Current hit points (default: 1)
- `temporary_hit_points` (int): Temporary hit points (default: 0)
- `hit_dice_remaining` (str): Remaining hit dice (default: "1d8")
- `death_saves_success` (int): Successful death saves (0-3)
- `death_saves_failure` (int): Failed death saves (0-3)

**Skills & Proficiencies:**
- `proficiency_bonus` (int): Proficiency bonus (default: 2)
- `skill_proficiencies` (list[str]): List of skill proficiencies
- `saving_throw_proficiencies` (list[str]): List of saving throw proficiencies

**Equipment:**
- `inventory` (list[Item]): Character's inventory
- `equipment` (dict[str, Item | None]): Currently equipped items
  - Keys: "weapon_main", "weapon_off", "armor", "shield"

**Spellcasting:**
- `spellcasting_ability` (str | None): Primary spellcasting ability
- `spell_slots` (dict[int, int]): Maximum spell slots by level
- `spell_slots_used` (dict[int, int]): Used spell slots by level
- `spells_known` (list[Spell]): Known spells

**Character Features:**
- `features_and_traits` (list[str]): Class features and racial traits
- `languages` (list[str]): Known languages

**Miscellaneous:**
- `inspiration` (bool): Whether character has inspiration
- `notes` (str): Additional character notes
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp

### AbilityScore

D&D ability score with automatic modifier calculation.

**Fields:**
- `score` (int): Raw ability score (1-30)

**Properties:**
- `mod` (int): Calculated modifier: `(score - 10) // 2`

**Example:**
```json
{
  "score": 16,
  "mod": 3
}
```

### CharacterClass

Character class information.

**Fields:**
- `name` (str): Class name (e.g., "Fighter", "Wizard")
- `level` (int): Character level (1-20)
- `hit_dice` (str): Hit dice type (default: "1d4")
- `subclass` (str | None): Subclass name

**Example:**
```json
{
  "name": "Fighter",
  "level": 5,
  "hit_dice": "1d10",
  "subclass": "Champion"
}
```

### Race

Character race information.

**Fields:**
- `name` (str): Race name (e.g., "Human", "Elf")
- `subrace` (str | None): Subrace name (e.g., "High Elf")
- `traits` (list[str]): Racial traits

**Example:**
```json
{
  "name": "Elf",
  "subrace": "High Elf",
  "traits": ["Darkvision", "Keen Senses", "Fey Ancestry"]
}
```

---

## World Building Models

### NPC

Non-player character model.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): NPC name
- `description` (str | None): Public description
- `bio` (str | None): Detailed backstory, motivations, and secrets
- `race` (str | None): NPC race
- `occupation` (str | None): NPC occupation
- `location` (str | None): Current location
- `attitude` (str | None): Attitude towards party ("friendly", "neutral", "hostile", etc.)
- `notes` (str): Additional notes
- `stats` (dict[str, Any] | None): Combat stats if needed
- `relationships` (dict[str, str]): Character relationships (character_name: relationship)

**Example:**
```json
{
  "id": "NPC12345",
  "name": "Elara the Wise",
  "description": "An elderly sage with silver hair",
  "bio": "Former court wizard seeking redemption",
  "race": "Human",
  "occupation": "Sage",
  "location": "Tower of Knowledge",
  "attitude": "friendly",
  "relationships": {
    "Gandalf": "Mentor",
    "Aragorn": "Ally"
  }
}
```

### Monster

Monster instance for combat encounters and active threats.

**Basic Information:**
- `id` (str): Unique 8-character identifier
- `name` (str): Instance name for this specific monster
- `monster_type` (str): The type/species of monster (e.g., "Goblin", "Dragon")
- `size` (str): Monster size ("Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan")
- `creature_type` (str): D&D creature type (default: "humanoid")
- `alignment` (str): Monster alignment (default: "neutral")
- `description` (str | None): Monster appearance and behavior
- `location` (str | None): Where this monster instance is located
- `status` (str): Current status ("alive", "dead", "unconscious", etc.)

**Core Stats:**
- `armor_class` (int): Armor class (default: 10)
- `hit_points_max` (int): Maximum hit points (≥1)
- `hit_points_current` (int): Current hit points (≥0)
- `hit_dice` (str): Hit dice notation (default: "1d8")
- `speed` (int): Movement speed in feet per round (default: 30)

**Ability Scores:**
- `abilities` (dict[str, AbilityScore]): Six D&D ability scores with automatic modifiers
  - Keys: "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
  - All default to AbilityScore(score=10) for +0 modifier

**Combat Systems:**
- `attacks` (list[Attack]): Available attacks with modifiers and damage
- `damage_resistances` (list[str]): Damage types monster resists
- `damage_immunities` (list[str]): Damage types monster is immune to
- `condition_immunities` (list[str]): Conditions monster is immune to

**Skills & Senses:**
- `saving_throws` (dict[str, int]): Saving throw bonuses by ability
- `skills` (dict[str, int]): Skill bonuses by skill name
- `senses` (list[str]): Special senses (e.g., "darkvision 60 ft")
- `languages` (list[str]): Known languages

**Special Abilities:**
- `special_abilities` (list[str]): Special abilities and traits
- `legendary_actions` (list[str]): Available legendary actions
- `legendary_actions_per_turn` (int): Number of legendary actions per turn (default: 0)

**Challenge and Experience:**
- `challenge_rating` (str): Challenge rating (e.g., "1/8", "2", "15")
- `experience_value` (int): Experience points awarded for defeating this monster
- `proficiency_bonus` (int): Proficiency bonus based on CR (default: 2)

**Metadata:**
- `notes` (str): Additional notes about this monster instance
- `created_at` (datetime): Creation timestamp

**Example:**
```json
{
  "id": "MON12345",
  "name": "Goblin Scout",
  "monster_type": "Goblin",
  "size": "Small",
  "creature_type": "humanoid",
  "alignment": "neutral evil",
  "armor_class": 14,
  "hit_points_max": 8,
  "hit_points_current": 5,
  "speed": 30,
  "abilities": {
    "strength": {"score": 8, "mod": -1},
    "dexterity": {"score": 14, "mod": 2},
    "constitution": {"score": 10, "mod": 0}
  },
  "attacks": [
    {
      "weapon": "Scimitar",
      "attack_roll_modifier": 4,
      "damage_roll": "1d6+2"
    }
  ],
  "skills": {"stealth": 6},
  "senses": ["darkvision 60 ft"],
  "languages": ["Common", "Goblin"],
  "special_abilities": ["Nimble Escape"],
  "challenge_rating": "1/4",
  "experience_value": 50,
  "location": "Forest Clearing",
  "status": "injured"
}
```

**Note:** Monsters are stored in the `GameState.monsters` list and represent active threats that the party is currently facing or aware of, unlike NPCs which are stored at the campaign level and represent persistent world characters.

### Location

Geographic location or settlement with hierarchical organization and hex map integration.

**Basic Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): Location name
- `location_type` (str): Type (city, town, village, dungeon, forest, etc.)
- `description` (str): Location description
- `population` (int | None): Population if applicable
- `government` (str | None): Government type
- `notable_features` (list[str]): Notable features
- `npcs` (list[str]): NPC names present at this location
- `connections` (list[str]): Connected location names
- `notes` (str): Additional notes

**Hierarchy Fields (NEW):**
- `parent_location_id` (str | None): ID of parent location in hierarchy (e.g., 'Bree' is parent of 'The Prancing Pony')
- `child_locations` (list[str]): IDs of locations contained within this one
- `location_scale` (LocationScale): Scale/scope of this location (default: LOCAL)

**Map Integration Fields (NEW):**
- `primary_map` (str | None): Name of the HexMap this location appears on
- `hex_coordinate` (HexCoordinate | None): Position on the hex map (x, y coordinates)

**LocationScale Enum:**
- `CONTINENT`: Entire continent
- `REGION`: Large region (e.g., "The North")
- `KINGDOM`: Kingdom or large territory
- `PROVINCE`: Province or county
- `AREA`: General area (e.g., "Mirkwood Forest")
- `SETTLEMENT`: City, town, village
- `DISTRICT`: City district or neighborhood
- `BUILDING`: Individual building or dungeon
- `ROOM`: Room within a building
- `LOCAL`: Small local feature (default)

**LocationType Enum (40+ structured types):**
- Settlements: METROPOLIS, CITY, TOWN, VILLAGE, HAMLET, OUTPOST
- Structures: CASTLE, FORTRESS, TOWER, TEMPLE, SHRINE, RUINS, DUNGEON, CAVE, MINE
- Buildings: TAVERN, INN, SHOP, GUILD_HALL, LIBRARY, MANOR, HOUSE
- Natural: FOREST, MOUNTAIN, VALLEY, PLAINS, DESERT, SWAMP, RIVER, LAKE, COAST, ISLAND
- Regions: KINGDOM, PROVINCE, TERRITORY, REGION, DISTRICT
- Special: PLANAR, EXTRAPLANAR, MAGICAL, MOBILE
- Other: OTHER

**Example (with hierarchy and map integration):**
```json
{
  "id": "LOC12345",
  "name": "Waterdeep",
  "location_type": "city",
  "description": "The City of Splendors",
  "population": 130000,
  "government": "Council of Lords",
  "notable_features": ["Castle Ward", "Dock Ward", "Undermountain"],
  "npcs": ["Lord Piergeiron", "Durnan"],
  "connections": ["Neverwinter", "Baldur's Gate"],
  "parent_location_id": "REG56789",
  "child_locations": ["DIST001", "DIST002", "DIST003"],
  "location_scale": "settlement",
  "primary_map": "Sword Coast",
  "hex_coordinate": {
    "x": 12,
    "y": 8
  }
}
```

**Backward Compatibility:**
- All new fields are optional with sensible defaults
- Existing locations without hierarchy work as top-level orphans
- Orphaned locations (parent_location_id = None) are implicitly children of the campaign root if one is set

### Quest

Quest or mission model.

**Fields:**
- `id` (str): Unique 8-character identifier
- `title` (str): Quest title
- `description` (str): Quest description
- `giver` (str | None): NPC who gave the quest
- `status` (str): Quest status ("active", "completed", "failed", "on_hold")
- `objectives` (list[str]): Quest objectives
- `completed_objectives` (list[str]): Completed objectives
- `reward` (str | None): Quest reward
- `notes` (str): Additional notes
- `created_at` (datetime): Creation timestamp

**Example:**
```json
{
  "id": "QST12345",
  "title": "The Lost Crown",
  "description": "Retrieve the ancient crown from the cursed tomb",
  "giver": "King Aldric",
  "status": "active",
  "objectives": [
    "Find the tomb entrance",
    "Defeat the tomb guardians",
    "Retrieve the crown"
  ],
  "completed_objectives": ["Find the tomb entrance"],
  "reward": "1000 gold pieces and royal favor"
}
```

---

## Hex Map Models

The hex map system provides wilderness exploration, travel, and outdoor adventure tracking using a hexagonal grid system. Maps integrate with Locations and support Points of Interest, terrain types, roads, and rivers.

**Current Map Concept:**
The server automatically determines the "current map" based on the current location in the campaign's game state. When a location has a `primary_map` field, that map becomes the current map. If the current location has no map, the system recursively searches up the location hierarchy (checking parent locations) until a map is found. This allows hex map tools to omit the `map_name` parameter and automatically use the contextually appropriate map based on where the party is located.

### HexMap

Top-level container for a hex-based wilderness map.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): Map name (e.g., "Sword Coast", "Barovia")
- `description` (str | None): Map description
- `hex_size_miles` (int): Miles per hex side (default: 6 miles, representing ~31 sq mi per hex)
- `default_terrain` (TerrainType): Default terrain for unspecified hexes
- `hexes` (dict[str, Hex]): All hexes indexed by coordinate key "x,y"
- `roads` (list[Road]): All roads on this map
- `rivers` (list[River]): All rivers on this map
- `notes` (str): Additional map notes

**Methods:**
- `_hex_key(coord: HexCoordinate) -> str`: Generate coordinate key
- `get_hex(coord: HexCoordinate) -> Hex | None`: Get hex at coordinate
- `set_hex(hex: Hex) -> None`: Set hex at its coordinate
- `get_neighbors(coord: HexCoordinate) -> list[HexCoordinate]`: Get adjacent hex coordinates

**Example:**
```json
{
  "id": "MAP12345",
  "name": "Sword Coast",
  "description": "The northwestern coast of Faerûn",
  "hex_size_miles": 6,
  "default_terrain": "plains",
  "hexes": {
    "12,8": {
      "coordinate": {"x": 12, "y": 8},
      "terrain": "urban",
      "pois": [
        {
          "name": "Waterdeep",
          "poi_type": "city",
          "description": "The City of Splendors"
        }
      ]
    }
  },
  "roads": [...],
  "rivers": [...]
}
```

### Hex

Individual hex cell on a hex map.

**Fields:**
- `coordinate` (HexCoordinate): Position on the map
- `terrain` (TerrainType): Primary terrain type
- `pois` (list[PointOfInterest]): Points of interest in this hex
- `explored` (bool): Whether party has explored this hex
- `visibility` (str): Visibility category (e.g., 'clear', 'obscured', 'hidden')
- `notes` (str): Additional hex notes
- `elevation` (int | None): Elevation in meters above sea level
- `roads` (list[Road]): Roads passing through this hex
- `rivers` (list[River]): Rivers flowing through this hex

**Example:**
```json
{
  "coordinate": {"x": 5, "y": 3},
  "terrain": "forest",
  "pois": [
    {
      "name": "Abandoned Tower",
      "poi_type": "ruins",
      "discovered": false
    }
  ],
  "explored": true,
  "visibility": "clear",
  "notes": "Dense pine forest",
  "elevation": 120,
  "roads": [],
  "rivers": []
}
```

### HexCoordinate

Offset coordinate system for hexagonal grids.

**Fields:**
- `x` (int): X coordinate (column)
- `y` (int): Y coordinate (row)

**Example:**
```json
{
  "x": 12,
  "y": 8
}
```

### PointOfInterest

Notable feature or location within a hex.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): POI name
- `poi_type` (POIType): Type of point of interest
- `description` (str | None): POI description
- `location_id` (str | None): Associated Location ID for bidirectional linking
- `discovered` (bool): Whether party has discovered this POI
- `notes` (str): Additional POI notes

**Example:**
```json
{
  "id": "POI12345",
  "name": "The Prancing Pony",
  "poi_type": "inn",
  "description": "A cozy inn in Bree",
  "location_id": "LOC67890",
  "discovered": true,
  "notes": "Party's favorite rest stop"
}
```

### Road

Road connecting hexes on the map.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str | None): Road name (e.g., "King's Road")
- `path` (list[HexCoordinate]): Hexes the road passes through
- `road_type` (str): Road quality ("highway", "road", "trail")
- `notes` (str): Additional road notes

**Example:**
```json
{
  "id": "ROAD123",
  "name": "King's Road",
  "path": [
    {"x": 5, "y": 3},
    {"x": 6, "y": 3},
    {"x": 7, "y": 4}
  ],
  "road_type": "highway",
  "notes": "Well-maintained royal highway"
}
```

### River

River or waterway on the map.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str | None): River name
- `path` (list[dict]): River segments with hex coordinates and entry/exit sides
  - Each segment: `{"hex": HexCoordinate, "entry_side": HexSide, "exit_side": HexSide}`
- `river_width` (str): River width category ("stream", "river", "wide_river")
- `notes` (str): Additional river notes

**Example:**
```json
{
  "id": "RIV12345",
  "name": "Dessarin River",
  "path": [
    {
      "hex": {"x": 3, "y": 2},
      "entry_side": "N",
      "exit_side": "SE"
    },
    {
      "hex": {"x": 3, "y": 3},
      "entry_side": "NW",
      "exit_side": "S"
    }
  ],
  "river_width": "river",
  "notes": "Flows from the Dessarin Hills"
}
```

### TerrainType

Enumeration of terrain types for hexes (24 types total).

**Grasslands and Vegetation:**
- `GRASS`: Open grassland
- `SCRUB`: Scrubland with sparse vegetation
- `PLAINS`: Open plains

**Forests:**
- `FOREST`: Standard wooded area
- `LIGHT_FOREST`: Lightly wooded area
- `DENSE_FOREST`: Heavily wooded, difficult terrain
- `JUNGLE`: Dense tropical forest

**Wetlands:**
- `MARSH`: Marshy wetland
- `SWAMP`: Swampy wetlands

**Elevation:**
- `HILLS`: Rolling hills
- `MOUNTAINS`: Mountainous terrain

**Arid:**
- `DESERT`: Arid wasteland
- `BADLANDS`: Rocky, eroded terrain
- `WASTELAND`: Blasted or cursed land

**Cold:**
- `TUNDRA`: Frozen plains
- `GLACIER`: Ice and glacial terrain

**Special:**
- `VOLCANIC`: Volcanic terrain
- `COASTAL`: Coastline
- `WATER`: Lakes, seas, oceans

**Populated:**
- `URBAN`: Cities and settlements
- `FARMLAND`: Agricultural land

### HexSide

Enumeration of hex sides for rivers and borders.

**Values:**
- `N`: North
- `NE`: Northeast
- `SE`: Southeast
- `S`: South
- `SW`: Southwest
- `NW`: Northwest

### POIType

Enumeration of point of interest types (13 types total).

**Settlements:**
- `CITY`: Major city
- `TOWN`: Town
- `VILLAGE`: Small village
- `INN`: Inn or tavern

**Structures:**
- `CASTLE`: Castle or fortress
- `TEMPLE`: Temple or religious site
- `TOWER`: Wizard tower or watchtower
- `SHRINE`: Small shrine

**Exploration:**
- `DUNGEON`: Dungeon entrance
- `RUINS`: Ancient ruins
- `CAVE`: Cave entrance
- `CAMP`: Encampment
- `LANDMARK`: Notable landmark

**Location and POI Integration:**
- POIs can reference Location objects via `location_id`
- Locations can reference their primary hex map via `primary_map` and `hex_coordinate`
- Use `sync_location_and_poi` tool to keep them synchronized
- This allows seamless integration between narrative locations and wilderness exploration

---

## Equipment and Items

### Item

Generic item model for equipment and inventory.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): Item name
- `description` (str | None): Item description
- `quantity` (int): Item quantity (default: 1)
- `weight` (float | None): Item weight
- `value` (str | None): Item value (e.g., "50 gp")
- `item_type` (str): Item type ("weapon", "armor", "consumable", "misc")
- `properties` (dict[str, Any]): Additional item properties

**Example:**
```json
{
  "id": "ITM12345",
  "name": "Longsword +1",
  "description": "A finely crafted sword with magical enhancement",
  "quantity": 1,
  "weight": 3.0,
  "value": "500 gp",
  "item_type": "weapon",
  "properties": {
    "damage": "1d8+1",
    "damage_type": "slashing",
    "magic": true
  }
}
```

### Spell

Spell information model.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): Spell name
- `level` (int): Spell level (0-9)
- `school` (str): School of magic
- `casting_time` (str): Casting time
- `range` (int): Spell range in feet (default: 5)
- `duration` (str): Spell duration
- `components` (list[str]): Spell components (V, S, M)
- `description` (str): Spell description
- `material_components` (str | None): Material component description
- `prepared` (bool): Whether spell is prepared

**Example:**
```json
{
  "id": "SPL12345",
  "name": "Fireball",
  "level": 3,
  "school": "Evocation",
  "casting_time": "1 action",
  "range": 150,
  "duration": "Instantaneous",
  "components": ["V", "S", "M"],
  "description": "A bright streak flashes from your pointing finger...",
  "material_components": "A tiny ball of bat guano and sulfur",
  "prepared": true
}
```

---

## Combat Models

### CombatParticipant

Key combat statistics for initiative tracking.

**Fields:**
- `name` (str): Character or monster name
- `initiative` (int): Initiative value for combat order
- `hp` (int): Current hit points
- `ac` (int): Current armor class
- `speed` (int): Movement speed in feet per round
- `attacks` (list[Attack]): Available attacks

**Example:**
```json
{
  "name": "Aragorn",
  "initiative": 15,
  "hp": 45,
  "ac": 18,
  "speed": 30,
  "attacks": [
    {
      "weapon": "Longsword",
      "attack_roll_modifier": 7,
      "damage_roll": "1d8+4"
    }
  ]
}
```

### Attack

Attack details including weapon and modifiers.

**Fields:**
- `weapon` (str): Weapon or body part used to attack
- `attack_roll_modifier` (int): Attack roll modifier
- `damage_roll` (str): Damage dice notation (e.g., "2d4+2")

### CombatEncounter

Pre-planned combat encounter.

**Fields:**
- `id` (str): Unique 8-character identifier
- `name` (str): Encounter name
- `description` (str): Encounter description
- `enemies` (list[str]): List of enemy names
- `difficulty` (str | None): Encounter difficulty ("easy", "medium", "hard", "deadly")
- `experience_value` (int | None): Total XP value
- `location` (str | None): Encounter location
- `status` (str): Encounter status ("planned", "active", "completed")
- `notes` (str): Additional notes

---

## Session Management

### SessionNote

Comprehensive session documentation.

**Fields:**
- `id` (str): Unique 8-character identifier
- `session_number` (int): Session number
- `date` (datetime): Session date
- `title` (str | None): Session title
- `summary` (str): Session summary
- `events` (list[str]): Key events that occurred
- `characters_present` (list[str]): Characters present in session
- `experience_gained` (int | None): Experience points gained
- `treasure_found` (list[str]): Treasure or items found
- `notes` (str): Additional notes

**Example:**
```json
{
  "id": "SES12345",
  "session_number": 5,
  "date": "2024-01-15T19:00:00",
  "title": "The Dragon's Lair",
  "summary": "The party finally confronted the ancient red dragon",
  "events": [
    "Entered the volcanic lair",
    "Defeated dragon minions",
    "Epic battle with Smagoroth"
  ],
  "characters_present": ["Aragorn", "Legolas", "Gimli"],
  "experience_gained": 2500,
  "treasure_found": ["Dragon Hoard: 10000 gp", "Ring of Fire Resistance"]
}
```

### AdventureEvent

Individual logged event for campaign history.

**Fields:**
- `id` (str): Unique 8-character identifier
- `campaign` (str): Campaign name where event occurred
- `event_type` (EventType): Type of event
- `title` (str): Event title
- `description` (str): Event description
- `timestamp` (datetime): When event occurred
- `session_number` (int | None): Session number when event occurred
- `characters_involved` (list[str]): Characters involved in event
- `location` (str | None): Where event occurred
- `tags` (list[str]): Event tags for categorization
- `importance` (int): Event importance rating (1-5, where 5 is most important)

### EventType

Enumeration of event types for the adventure log.

**Values:**
- `COMBAT`: Combat encounters
- `ROLEPLAY`: Social interactions and roleplay moments
- `EXPLORATION`: Discovery and exploration events
- `QUEST`: Quest-related events
- `CHARACTER`: Character development moments
- `WORLD`: World-building and lore events
- `SESSION`: Session-level events

---

## Transcript Models

The transcript system uses a **hierarchical tree structure** to organize gameplay interactions, allowing for nested story arcs, combat encounters, and adventures. This replaces the older flat transcript format.

### Transcript (Legacy)

**Note:** This is the old flat format, kept for backward compatibility. New transcripts use the [TranscriptTree](#transcripttree) format.

Complete transcript of player-game interactions for a session.

**Fields:**
- `id` (str): Unique 8-character identifier
- `campaign` (str): Associated campaign name
- `session_number` (int): Session number
- `entries` (list[TranscriptEntry]): All interaction entries

### TranscriptEntry (Legacy)

**Note:** This is the old flat format, kept for backward compatibility. New transcripts use [TranscriptInteraction](#transcriptinteraction).

Individual player-game interaction entry.

**Fields:**
- `transcript_id` (str): Associated transcript ID
- `timestamp` (datetime): When interaction occurred
- `player_entry` (str): Text input by the player
- `game_response` (str): Response from the game/DM

---

### TranscriptTree

**New tree-based format:** Root node of the transcript tree representing a complete session.

**Fields:**
- `id` (str): Unique 8-character identifier
- `node_type` (str): Always "transcript"
- `campaign` (str): Associated campaign name
- `session_number` (int): Session number
- `children` (list[TranscriptInteraction | TranscriptCombat | TranscriptAdventure]): Top-level nodes in the session
- `current_parent_id` (str | None): ID of the node where new interactions are currently being added
- `characters_present` (list[str]): Characters present in this session
- `tags` (list[str]): Optional tags for categorization
- `notes` (str): Optional notes about the session

**Structure:**
```
TranscriptTree (root)
├── TranscriptInteraction (leaf)
├── TranscriptCombat (interior node)
│   ├── TranscriptInteraction (leaf)
│   └── TranscriptInteraction (leaf)
├── TranscriptAdventure (interior node)
│   ├── TranscriptInteraction (leaf)
│   ├── TranscriptCombat (interior node)
│   │   └── TranscriptInteraction (leaf)
│   └── TranscriptInteraction (leaf)
└── TranscriptInteraction (leaf)
```

**Example:**
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
      "responses": [{"type": "text", "content": "You see..."}]
    },
    {
      "node_type": "combat",
      "participants": ["Party", "Dragon"],
      "result": "victory",
      "summary": "Epic battle",
      "actions": [...]
    }
  ],
  "current_parent_id": "TRS12345",
  "characters_present": ["Aragorn", "Legolas"]
}
```

### TranscriptInteraction

**Leaf node:** Represents a single user-LLM exchange (a conversation turn).

**Fields:**
- `id` (str): Unique 8-character identifier
- `node_type` (str): Always "interaction"
- `user_text` (str): Text input by the user/player
- `responses` (list[ResponseText | ResponseTools]): LLM responses (text or tool calls)
- `character_speaking` (str | None): Which character is speaking (if applicable)
- `importance` (int): Importance rating 1-5 (default: 3)
- `tags` (list[str]): Optional tags for categorization
- `notes` (str): Optional notes about this interaction

**Example:**
```json
{
  "id": "INT12345",
  "node_type": "interaction",
  "user_text": "I want to investigate the ancient altar",
  "responses": [
    {
      "type": "text",
      "content": "As you approach the altar, you notice strange runes glowing faintly..."
    }
  ],
  "character_speaking": "Gandalf",
  "importance": 4,
  "tags": ["discovery", "magic"],
  "notes": "This triggered the main quest"
}
```

### TranscriptCombat

**Interior node:** Represents a combat encounter with nested interaction actions.

**Fields:**
- `id` (str): Unique 8-character identifier
- `node_type` (str): Always "combat"
- `participants` (list[str]): Names of all combatants
- `result` (str): Combat outcome (e.g., "victory", "defeat", "fled")
- `summary` (str): Brief summary of how the combat ended
- `actions` (list[TranscriptInteraction]): Detailed turn-by-turn combat interactions
- `location` (str | None): Where combat took place
- `rounds` (int | None): Number of combat rounds
- `casualties` (list[str]): Participants who died or were defeated
- `tags` (list[str]): Optional tags for categorization
- `notes` (str): Optional notes about this combat

**Example:**
```json
{
  "id": "CMB12345",
  "node_type": "combat",
  "participants": ["Aragorn", "Legolas", "Orc Chieftain", "Goblin x3"],
  "result": "victory",
  "summary": "The heroes defeated the orc raiding party after 3 rounds",
  "actions": [
    {
      "node_type": "interaction",
      "user_text": "Aragorn attacks the chieftain",
      "responses": [{"type": "text", "content": "Roll for attack: 18! Hit! Roll damage..."}]
    },
    {
      "node_type": "interaction",
      "user_text": "Legolas shoots two arrows",
      "responses": [{"type": "text", "content": "Both arrows find their mark..."}]
    }
  ],
  "location": "Mountain Pass",
  "rounds": 3,
  "casualties": ["Orc Chieftain", "Goblin x3"],
  "tags": ["combat", "encounter"],
  "notes": "Party was ambushed while traveling"
}
```

### TranscriptAdventure

**Interior node:** Represents a story arc or quest with nested actions (interactions, combats, or sub-adventures).

**Fields:**
- `id` (str): Unique 8-character identifier
- `node_type` (str): Always "adventure"
- `title` (str | None): Adventure title (e.g., "The Temple of Doom")
- `summary` (str): Summary of what happened during the adventure
- `actions` (list[TranscriptInteraction | TranscriptCombat | TranscriptAdventure]): Nested story elements
- `quest_id` (str | None): Associated quest ID if this adventure is part of a quest
- `locations` (list[str]): Locations visited during this adventure
- `npcs_met` (list[str]): NPCs encountered during this adventure
- `rewards` (list[str]): Rewards obtained (items, XP, etc.)
- `tags` (list[str]): Optional tags for categorization
- `notes` (str): Optional notes about this adventure

**Example:**
```json
{
  "id": "ADV12345",
  "node_type": "adventure",
  "title": "The Lost Temple",
  "summary": "The party explored an ancient temple and retrieved the Sacred Crown",
  "actions": [
    {
      "node_type": "interaction",
      "user_text": "We search for the temple entrance",
      "responses": [{"type": "text", "content": "You find hidden stairs..."}]
    },
    {
      "node_type": "combat",
      "participants": ["Party", "Temple Guardian"],
      "result": "victory",
      "summary": "Defeated the guardian",
      "actions": [...]
    },
    {
      "node_type": "interaction",
      "user_text": "We take the crown from the altar",
      "responses": [{"type": "text", "content": "As you lift the crown..."}]
    }
  ],
  "quest_id": "QST67890",
  "locations": ["Ancient Temple", "Temple Inner Chamber"],
  "npcs_met": ["Temple Guardian Spirit"],
  "rewards": ["Sacred Crown", "500 XP"],
  "tags": ["main quest", "exploration"],
  "notes": "This completed the first major quest arc"
}
```

### Response Types

Interactions can have different types of responses from the LLM:

#### ResponseText

Standard text response from the LLM.

**Fields:**
- `type` (str): Always "text"
- `content` (str): The response text

**Example:**
```json
{
  "type": "text",
  "content": "You find a hidden door behind the bookshelf"
}
```

#### ResponseTools

Tool call response when the LLM used tools.

**Fields:**
- `type` (str): Always "tools"
- `calls` (list[InteractionToolCall]): List of tool calls made

#### InteractionToolCall

Details of a single tool call.

**Fields:**
- `name` (str): Tool name that was called
- `id` (str): Unique call ID
- `input` (dict): Tool input parameters
- `response` (str): Tool response/output

**Example:**
```json
{
  "type": "tools",
  "calls": [
    {
      "name": "roll_dice",
      "id": "call_123",
      "input": {"dice_notation": "1d20+5"},
      "response": "🎲 1d20+5 [18] +5 = 23"
    }
  ]
}
```

---

**Migration Note:** Old transcripts using the flat `Transcript` and `TranscriptEntry` format are automatically migrated to the new `TranscriptTree` format when loaded. A backup of the original file is created with a `.old` extension.

---

## System Models

### GameStats

Server statistics and metadata tracking.

**Core Counters:**
- `ctime` (datetime): Server creation time
- `last_tool_call` (datetime | None): Last tool invocation
- `tool_calls` (int): Total tool calls
- `errors` (int): Total errors

**Campaign Tracking:**
- `campaigns_created`, `campaigns_loaded`, `campaign_updates`, `campaign_deletions`

**Entity Tracking:**
- Characters: `characters_created`, `character_updates`, `character_deletions`
- NPCs: `npcs_created`, `npc_updates`, `npc_deletions`
- Locations: `locations_created`, `location_updates`, `location_deletions`
- Quests: `quests_created`, `quest_updates`, `quest_deletions`
- Encounters: `encounters_created`, `encounters_completed`, `encounter_updates`, `encounter_deletions`
- Sessions: `sessions_created`, `session_updates`, `session_deletions`

**Item and Spell Tracking:**
- Items: `items_given`, `items_taken`, `item_updates`, `item_creations`, `item_deletions`
- Spells: `spells_created`, `spell_updates`, `spell_deletions`, `spells_cast`

**Game Mechanics:**
- `die_rolls`, `roll_successes`, `roll_failures`
- `damage_dealt`, `damage_taken`
- `death_saves_success`, `death_saves_failure`
- `ingame_days`

**Methods:**
- `inc(field: str, inc: int = 1)`: Increment a counter field
- `_save_stats()`: Save statistics (TODO: implementation needed)
- `_load_stats(stats: dict)`: Load statistics (TODO: implementation needed)

---

## Field Validation

All models use Pydantic validation with the following common patterns:

### ID Fields
- 8-character random strings generated using `shortuuid`
- Example: `"ABC12345"`

### Numeric Constraints
- Ability scores: 1-30 range
- Character levels: 1-20 range
- Spell levels: 0-9 range
- Death saves: 0-3 range
- Event importance: 1-5 range

### Timestamps
- Automatic generation using `datetime.now()` for creation
- Manual updates for modification tracking

### Default Factories
- Empty lists and dictionaries use `Field(default_factory=list)` or `Field(default_factory=dict)`
- Complex defaults use lambda functions for proper initialization

This comprehensive data model structure ensures type safety, validation, and consistent data handling throughout the Gamemaster MCP Server.