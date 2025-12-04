# Location System Improvement Specification

## Overview

This specification proposes enhancements to the Location system to better integrate with hex maps and establish location hierarchies. This is a simplified, focused approach that adds:
1. Basic hex map integration (single primary map per location)
2. Parent-child location hierarchies with scale levels

## Current State Analysis

### Current Location Model (`models.py:423-436`)

```python
class Location(BaseModel):
    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    location_type: str  # city, town, village, dungeon, forest, etc.
    description: str
    population: int | None = None
    government: str | None = None
    notable_features: list[str] = Field(default_factory=list)
    npcs: list[str] = Field(default_factory=list)  # NPC names
    connections: list[str] = Field(default_factory=list)  # Connected locations
    notes: str = ""
```

### Current Campaign Model (relevant parts)

```python
class Campaign(BaseModel):
    # ... existing fields ...
    locations: dict[str, Location] = Field(default_factory=dict)
    hex_maps: dict[str, HexMap] = Field(default_factory=dict)
```

### Current Limitations

1. **No Campaign Root Location**
   - Campaign has no single root location to anchor the hierarchy
   - No clear way to represent the entire game world as a location
   - Locations exist as a flat dictionary with no hierarchical organization

2. **No Map Integration**
   - Locations don't reference which hex map they're on
   - No coordinate information for placement on hex maps
   - POIs can reference Locations via `location_id`, but not bidirectional

3. **No Hierarchical Relationships**
   - A tavern in a city has no formal parent-child relationship
   - No concept of location containment or scale
   - Can't represent "The Prancing Pony is in Bree which is in the Bree-land region"

4. **Limited Scale Information**
   - All locations treated equally regardless of scale
   - No way to distinguish continent from village from room

## Proposed Improvements

### 1. Campaign Root Location

Add a root location concept to anchor the entire location hierarchy:

```python
class Campaign(BaseModel):
    # ... existing fields ...

    root_location_id: Annotated[
        str | None,
        Field(description="ID of the root location representing the entire game world")
    ] = None

    locations: dict[str, Location] = Field(default_factory=dict)
    hex_maps: dict[str, HexMap] = Field(default_factory=dict)
```

**Root Location Concept:**

The root location represents the entire game world for the campaign. It serves as the ultimate ancestor for all locations in the hierarchy.

**Examples:**
```python
# Campaign with world as root
root = Location(
    name="Faerûn",
    location_type=LocationType.CONTINENT,
    location_scale=LocationScale.CONTINENT,
    description="The main continent of the Forgotten Realms"
)

# All top-level locations are children of root
sword_coast = Location(
    name="The Sword Coast",
    location_type=LocationType.REGION,
    location_scale=LocationScale.REGION,
    parent_location_id=root.id,  # Parent is world root
    description="Coastal region along the western edge of Faerûn"
)
```

**Backward Compatibility:**

For existing campaigns without a root location:
- Any location with `parent_location_id = None` is implicitly considered a child of the root
- When `root_location_id` is set, hierarchy queries automatically include the root as the ultimate parent
- Storage layer handles both cases transparently

**Creation Strategy:**

Root location is created manually by user via client LLM:
1. User decides when to create root location (typically during campaign setup)
2. Uses `create_location` to create the root location
3. Uses `set_root_location` to designate it as the campaign root
4. Provides explicit control over root location properties (name, scale, description)

**Benefits:**
- Single source of truth for the world
- Clean hierarchical queries (all paths end at root)
- Root location can have a description and notes about the world
- Root location can reference a primary world map
- Can easily get "all top-level regions" by querying children of root

### 2. Map References and Coordinates

Add simple fields to link Locations to hex maps:

```python
class Location(BaseModel):
    # ... existing fields ...

    # Map Integration
    primary_map: Annotated[
        str | None,
        Field(description="Name of the HexMap this location appears on")
    ] = None

    hex_coordinate: Annotated[
        HexCoordinate | None,
        Field(description="Position on the hex map")
    ] = None
```

**Rationale:**
- `primary_map`: Links location to a hex map by name
- `hex_coordinate`: Precise (x, y) placement on that map
- Simple one-to-one relationship between location and map position

**Integration with Hex Map POIs:**

Currently POIs can reference Locations via `location_id` (one-way). We'll add bidirectional sync:
- When a POI is created with a `location_id`, update that Location's `primary_map` and `hex_coordinate`
- When a Location's `hex_coordinate` changes, update or create corresponding POI
- Add validation to prevent orphaned references

### 3. Location Hierarchy and Containment

Add hierarchical structure to support parent-child relationships:

```python
class Location(BaseModel):
    # ... existing fields ...

    # Hierarchy
    parent_location_id: Annotated[
        str | None,
        Field(description="ID of parent location (e.g., 'Bree' is parent of 'The Prancing Pony')")
    ] = None

    child_locations: Annotated[
        list[str],
        Field(description="IDs of locations contained within this one")
    ] = Field(default_factory=list)

    location_scale: Annotated[
        LocationScale,
        Field(description="Scale/scope of this location")
    ] = LocationScale.LOCAL
```

**Location Scale Enum:**

```python
class LocationScale(str, Enum):
    """Scale/scope of a location."""
    CONTINENT = "continent"        # Entire continent
    REGION = "region"              # Large region (e.g., "The North")
    KINGDOM = "kingdom"            # Kingdom or large territory
    PROVINCE = "province"          # Province or county
    AREA = "area"                  # General area (e.g., "Mirkwood Forest")
    SETTLEMENT = "settlement"      # City, town, village
    DISTRICT = "district"          # City district or neighborhood
    BUILDING = "building"          # Individual building or dungeon
    ROOM = "room"                  # Room within a building
    LOCAL = "local"                # Small local feature (default)
```

**Examples:**
```python
# Complete hierarchy with campaign root
Campaign root: "Forgotten Realms Campaign" (REGION)
  - "Faerûn" (CONTINENT, parent = root)
    - "The Sword Coast" (REGION, parent = Faerûn)
      - "Waterdeep" (SETTLEMENT, parent = Sword Coast)
        - "Castle Ward" (DISTRICT, parent = Waterdeep)
          - "Blackstaff Tower" (BUILDING, parent = Castle Ward)
            - "Tower Library" (ROOM, parent = Blackstaff Tower)

# Backward compatibility: orphaned locations
- "Neverwinter" (SETTLEMENT, parent = None)
  # Treated as child of campaign root for hierarchy queries
```

**Root Location Integration:**

Locations interact with the campaign root location as follows:

1. **Explicit Parent**: Location has `parent_location_id` set → uses that parent
2. **No Parent**: Location has `parent_location_id = None`:
   - If campaign has `root_location_id`, location is implicitly a child of root
   - If campaign has no `root_location_id`, location is a true orphan (top-level)
3. **Root Location**: The root location itself has `parent_location_id = None` (it's the top)

**Utility Methods:**

Add helper methods to Location for working with hierarchies:

```python
class Location(BaseModel):
    # ... fields ...

    def get_full_path(self, storage: DnDStorage) -> list[str]:
        """Get full hierarchical path from root to this location.

        Returns:
            List of location names from continent/region down to this location.
            Example: ["Faerûn", "Sword Coast", "Waterdeep", "Castle Ward", "Blackstaff Tower"]
        """
        pass

    def get_all_descendants(self, storage: DnDStorage) -> list[Location]:
        """Get all child locations recursively (DFS)."""
        pass

    def is_within(self, other_location_id: str, storage: DnDStorage) -> bool:
        """Check if this location is contained within another location (anywhere in hierarchy)."""
        pass
```

### 4. Structured Location Types

Replace free-form `location_type` string with enum for better categorization:

```python
class LocationType(str, Enum):
    """Structured location type classification."""

    # Settlements
    METROPOLIS = "metropolis"      # Huge city (100k+)
    CITY = "city"                  # Large city (10k-100k)
    TOWN = "town"                  # Town (1k-10k)
    VILLAGE = "village"            # Village (100-1k)
    HAMLET = "hamlet"              # Hamlet (<100)
    OUTPOST = "outpost"            # Military or trading outpost

    # Structures
    CASTLE = "castle"
    FORTRESS = "fortress"
    TOWER = "tower"
    TEMPLE = "temple"
    SHRINE = "shrine"
    RUINS = "ruins"
    DUNGEON = "dungeon"
    CAVE = "cave"
    MINE = "mine"

    # Buildings
    TAVERN = "tavern"
    INN = "inn"
    SHOP = "shop"
    GUILD_HALL = "guild_hall"
    LIBRARY = "library"
    MANOR = "manor"
    HOUSE = "house"

    # Natural
    FOREST = "forest"
    MOUNTAIN = "mountain"
    VALLEY = "valley"
    PLAINS = "plains"
    DESERT = "desert"
    SWAMP = "swamp"
    RIVER = "river"
    LAKE = "lake"
    COAST = "coast"
    ISLAND = "island"

    # Regions
    KINGDOM = "kingdom"
    PROVINCE = "province"
    TERRITORY = "territory"
    REGION = "region"
    DISTRICT = "district"

    # Special
    PLANAR = "planar"              # Outer planes location
    EXTRAPLANAR = "extraplanar"    # Demiplane, pocket dimension
    MAGICAL = "magical"            # Magically created/altered
    MOBILE = "mobile"              # Moving location (ship, wagon, etc.)

    # Other
    OTHER = "other"


class Location(BaseModel):
    # ... existing fields ...

    # CHANGE from:
    # location_type: str

    # TO:
    location_type: Annotated[
        LocationType,
        Field(description="Structured type classification")
    ]
```

### 5. Storage Layer Updates

Add to `DnDStorage` class:

```python
# Campaign Root Location
# NOTE: Root location is NOT auto-created. User creates via client LLM using
# create_location + set_root_location tools.

def get_root_location(self) -> Location | None:
    """Get the campaign's root location, or None if not set."""
    pass

def set_root_location(self, location_id: str) -> None:
    """Set a location as the campaign root.

    Args:
        location_id: ID of location to set as root

    Raises:
        ValueError: If location doesn't exist or already has a parent
    """
    pass

def get_orphaned_locations(self) -> list[Location]:
    """Get all locations with no parent (excluding root).

    Returns:
        List of locations that should be children of root but aren't explicitly set.

    Note:
        This differs from unmigrated locations. A location can be orphaned but
        still have children or map placement. Unmigrated locations are orphaned
        AND have no children AND no map (completely isolated).
    """
    pass

def get_unmigrated_locations(self) -> list[Location]:
    """Get all locations that are isolated (not integrated into hierarchy or maps).

    Returns:
        List of locations where:
        - parent_location_id is None (and not root)
        - child_locations is empty
        - primary_map is None

    These locations exist but aren't connected to anything.
    """
    pass

# Location Hierarchy
def set_parent_location(self, child_id: str, parent_id: str | None) -> None:
    """Set the parent location for a location (updates both child and parent).

    Note: Setting parent to None makes location a child of root (if root exists).
    """
    pass

def get_location_hierarchy(self, location_id: str) -> dict:
    """Get full hierarchy tree for a location (parents and children).

    Automatically includes root location in ancestry if applicable.
    """
    pass

def get_locations_by_scale(self, scale: LocationScale) -> list[Location]:
    """Get all locations at a specific scale level."""
    pass

def get_top_level_locations(self) -> list[Location]:
    """Get all top-level locations (children of root, or orphans if no root)."""
    pass

# Map Integration
def sync_location_with_poi(self, location_id: str, poi_id: str) -> None:
    """Synchronize a Location with its corresponding PointOfInterest."""
    pass

def get_locations_on_map(self, map_name: str) -> list[Location]:
    """Get all locations that appear on a specific map."""
    pass

def update_location_coordinate(
    self,
    location_id: str,
    map_name: str,
    coordinate: HexCoordinate
) -> None:
    """Update location's coordinate on a map (syncs with POI if exists)."""
    pass
```

### 6. MCP Tools Updates

**Modified Tools:**

No changes needed to `create_campaign` - root location is manually created by user via client LLM.

Update `create_location` to add hierarchy and map parameters:

```python
@mcp.tool
def create_location(
    name: str,
    location_type: LocationType,
    description: str,
    # ... existing parameters ...

    # NEW parameters:
    parent_location_id: str | None = None,
    location_scale: LocationScale = LocationScale.LOCAL,
    primary_map: str | None = None,
    hex_x: int | None = None,
    hex_y: int | None = None,
) -> str:
    """Create a new location with hierarchy and map integration."""
    pass
```

Update `get_location` to show hierarchy:

```python
@mcp.tool
def get_location(name: str) -> str:
    """Get location information including parent/children and map placement."""
    pass
```

Update `delete_location` to support recursive deletion:

```python
@mcp.tool
def delete_location(
    location_id: str,
    recursive: bool = False,
) -> str:
    """Delete a location from the campaign.

    Args:
        location_id: ID of location to delete
        recursive: If True, recursively delete all child locations (like rm -rf).
                   If False and location has children, deletion is prevented.

    Default behavior (recursive=False):
        - Prevents deletion if location has children
        - Safe by default

    Recursive deletion (recursive=True):
        - Deletes location and ALL descendants
        - Use with caution - cannot be undone
        - Children of children are also deleted (full tree removal)
    """
    pass
```

**New Tools:**

Root location management:

```python
@mcp.tool
def get_root_location() -> str:
    """Get information about the campaign's root location.

    Returns summary of root location including its direct children.
    """
    pass

@mcp.tool
def set_root_location(location_id: str) -> str:
    """Set an existing location as the campaign root.

    Args:
        location_id: ID of location to become root

    The location must not have a parent. All orphaned locations will
    become children of the new root.
    """
    pass

@mcp.tool
def get_top_level_locations() -> str:
    """List all top-level locations (direct children of root, or orphans if no root)."""
    pass
```

Location hierarchy management:

```python
@mcp.tool
def set_location_parent(
    child_location_id: str,
    parent_location_id: str | None,
) -> str:
    """Set or clear the parent location for a location.

    Setting parent to None makes the location a child of the campaign root.
    """
    pass

@mcp.tool
def get_location_hierarchy(
    location_id: str,
    include_children: bool = True,
    include_ancestors: bool = True,
) -> str:
    """Get the hierarchical context for a location."""
    pass

@mcp.tool
def list_child_locations(
    parent_location_id: str,
    recursive: bool = False,
) -> str:
    """List all child locations within a parent location."""
    pass
```

Map integration:

```python
@mcp.tool
def place_location_on_map(
    location_id: str,
    map_name: str,
    x: int,
    y: int,
    create_poi: bool = True,
) -> str:
    """Place a location on a hex map at specific coordinates.

    If create_poi is True, automatically creates a corresponding PointOfInterest.
    """
    pass

@mcp.tool
def list_locations_on_map(
    map_name: str,
    location_type: LocationType | None = None,
) -> str:
    """List all locations that appear on a specific map."""
    pass

@mcp.tool
def sync_location_and_poi(
    location_id: str,
    poi_id: str,
) -> str:
    """Synchronize a Location with its corresponding PointOfInterest."""
    pass
```

Migration and upgrade:

```python
@mcp.tool
def upgrade_location(
    location_id: str,
    location_type: LocationType | None = None,
    location_scale: LocationScale | None = None,
    parent_location_id: str | None = None,
    primary_map: str | None = None,
    hex_x: int | None = None,
    hex_y: int | None = None,
    infer_scale_from_type: bool = False,
) -> str:
    """Upgrade an existing location to use new hierarchy and map fields.

    This tool allows selective migration of locations from old format to new format.

    Args:
        location_id: ID of location to upgrade
        location_type: Set structured LocationType enum (if not already set)
        location_scale: Set scale level (if not already set)
        parent_location_id: Set parent in hierarchy (if not already set)
        primary_map: Set primary map reference (if not already set)
        hex_x, hex_y: Set map coordinates (if not already set)
        infer_scale_from_type: If True and location_type provided, automatically
                               set location_scale based on type. Default: False.

    Behavior:
        - Only updates fields that are currently None/empty
        - Minimal smart defaults: Only infers scale if explicitly requested
        - If location already has hierarchy/map data, reports current state
        - Returns summary of what was changed

    Scale Inference (when infer_scale_from_type=True):
        - CITY/TOWN/VILLAGE → SETTLEMENT
        - TAVERN/INN/SHOP → BUILDING
        - DUNGEON/CAVE → BUILDING or AREA
        - FOREST/MOUNTAIN/DESERT → AREA
        - KINGDOM/PROVINCE → KINGDOM/PROVINCE (1:1)

    Use Cases:
        - Gradually migrate existing locations as you work with them
        - Let LLM suggest appropriate hierarchy placement
        - Batch upgrade related locations (e.g., all locations in a city)
    """
    pass

@mcp.tool
def list_unmigrated_locations() -> str:
    """List locations that haven't been upgraded to new format.

    A location is considered unmigrated if it has:
    - No parent (parent_location_id is None, and it's not the root location)
    - No children (child_locations is empty)
    - No map placement (primary_map is None)
    - No connections to maps or other locations

    In other words, unmigrated locations are isolated - not integrated
    into the hierarchy or map systems.

    Useful for tracking migration progress and identifying locations
    that need organization.
    """
    pass
```

## Migration Strategy

### Backward Compatibility Approach

All new fields are optional with sensible defaults, ensuring existing campaigns work without modification:

**Reading Old Data:**
- Existing locations load successfully (all new fields default to None/empty)
- `location_type` remains as string (backward compatible)
- Locations without parents are implicitly children of root (if root exists)
- No validation errors for unmigrated data

**Selective Upgrade:**
- Use `upgrade_location` tool to migrate individual locations as needed
- LLM can assist in determining appropriate hierarchy placement
- No need to migrate all locations at once
- Track migration progress with `list_unmigrated_locations`

### Phase 1: Model Updates (Immediate)

1. Add `root_location_id` to Campaign model (optional)
2. Add new optional fields to `Location` model:
   - `primary_map: str | None`
   - `hex_coordinate: HexCoordinate | None`
   - `parent_location_id: str | None`
   - `child_locations: list[str]`
   - `location_scale: LocationScale` (default: LOCAL)
3. Add new enums: `LocationScale`, `LocationType`
4. Keep existing `location_type` as string for backward compatibility

### Phase 2: Storage Methods (Immediate)

1. Implement root location methods (with lazy creation)
2. Implement hierarchy storage methods (with root awareness)
3. Implement map integration methods
4. All methods handle both migrated and unmigrated locations transparently

### Phase 3: MCP Tools (Immediate)

1. Update `create_campaign` to auto-create root location
2. Update `create_location` and `get_location` tools
3. Add root location tools (3 tools)
4. Add hierarchy tools (3 tools)
5. Add map tools (3 tools)
6. Add migration tools: `upgrade_location`, `list_unmigrated_locations`

### Phase 4: Selective Migration (User-Driven, Ongoing)

1. Users identify locations to upgrade via `list_unmigrated_locations`
2. LLM analyzes location context and suggests hierarchy placement
3. User calls `upgrade_location` with LLM-suggested parameters
4. Process repeats for important locations over time
5. Unmigrated locations continue to work (just missing hierarchy/map features)

**Migration Workflow Example:**
```
User: "Let's organize the locations in my campaign"

LLM:
1. Calls list_unmigrated_locations()
2. Sees: "Waterdeep", "Neverwinter", "The Prancing Pony"
3. Suggests: "I notice you have unmigrated locations. Shall I help organize them?"

User: "Yes, start with Waterdeep"

LLM:
1. Calls get_location("Waterdeep")
2. Analyzes description, determines it's a city
3. Calls upgrade_location(
     location_id="...",
     location_type=LocationType.CITY,
     location_scale=LocationScale.SETTLEMENT,
     parent_location_id=<root_id>  # or finds appropriate region
   )

User: "Now do The Prancing Pony"

LLM:
1. Sees it's an inn based on description
2. Calls upgrade_location(
     location_id="...",
     location_type=LocationType.INN,
     location_scale=LocationScale.BUILDING,
     parent_location_id=<waterdeep_id>  # sets Waterdeep as parent
   )
```

## Implementation Priority

### Phase 1: Core Models (High Priority)

1. Add `root_location_id` field to Campaign model
2. Add `LocationScale` enum to models.py
3. Add `LocationType` enum to models.py
4. Add hierarchy fields to Location model:
   - `parent_location_id`
   - `child_locations`
   - `location_scale`
5. Add map integration fields to Location model:
   - `primary_map`
   - `hex_coordinate`

### Phase 2: Storage Layer (High Priority)

6. Implement root location methods:
   - `get_root_location()`
   - `set_root_location()`
   - `get_orphaned_locations()` (any location without parent)
   - `get_unmigrated_locations()` (isolated locations)
   - `get_top_level_locations()`
7. Implement hierarchy methods:
   - `set_parent_location()` (with root awareness)
   - `get_location_hierarchy()` (with root awareness)
   - `get_locations_by_scale()`
8. Implement map integration methods:
   - `sync_location_with_poi()`
   - `get_locations_on_map()`
   - `update_location_coordinate()`

### Phase 3: MCP Tools (High Priority)

9. Update `create_location` tool with hierarchy and map parameters
10. Update `get_location` tool to show hierarchy context
11. Update `delete_location` tool to add `recursive` parameter
12. Add root location tools:
    - `get_root_location`
    - `set_root_location`
    - `get_top_level_locations`
13. Add hierarchy tools:
    - `set_location_parent`
    - `get_location_hierarchy`
    - `list_child_locations`
14. Add map integration tools:
    - `place_location_on_map`
    - `list_locations_on_map`
    - `sync_location_and_poi`
15. Add migration tools:
    - `upgrade_location` (selective migration with minimal defaults)
    - `list_unmigrated_locations` (track progress)

### Phase 4: Utilities (Medium Priority)

16. Add Location helper methods (get_full_path, get_all_descendants, is_within)
17. Add bidirectional POI sync logic
18. Implement minimal smart defaults in `upgrade_location` (infer scale from type when requested)
19. Implement recursive deletion logic in storage layer (for `delete_location` tool)
20. Implement soft validation warnings for illogical hierarchies (e.g., CITY parent of BUILDING)

## Success Criteria

The location system improvements will be considered successful when:

1. Campaigns can have a root location (manually created via client LLM)
2. Orphaned locations (parent = None) are treated as children of root
3. Can query full hierarchical path ending at root (e.g., "Tower → District → City → Region → Root")
4. Locations can be placed on hex maps with precise coordinates (`primary_map` + `hex_coordinate`)
5. Bidirectional sync between Locations and POIs works correctly
6. Location hierarchy supports parent-child relationships
7. Can list all children of a location (with recursive option)
8. Can filter locations by scale level
9. Can get all top-level locations (direct children of root)
10. All existing location data works without migration (backward compatible)
11. `upgrade_location` tool successfully migrates individual locations
12. `list_unmigrated_locations` accurately identifies isolated locations (no parent, no children, no map)
13. LLM can assist users in upgrading locations with intelligent suggestions
14. Partially migrated campaigns work correctly (mixed old/new format)
15. Distinction between "orphaned" (no parent) and "unmigrated" (completely isolated) is clear
16. Location deletion is prevented if children exist (unless `recursive=True`)
17. Recursive deletion correctly removes entire subtree (location and all descendants)
18. Soft validation warnings alert users to illogical hierarchies without preventing them
19. New tools are tested via MCP Inspector
20. Integration with existing hex map POI system is seamless
21. `get_location` tool shows complete hierarchy context including path to root

## Design Decisions

All open questions have been resolved:

1. **Root Location Auto-Creation**: ✅ **Manual creation via tool**
   - Root location is NOT auto-created
   - User will create via client LLM using root location management tools
   - Provides explicit control over campaign structure
   - Root Name: Defaults to campaign name, with optional override parameter

2. **Root Location Mutability**: ✅ **Yes, can be changed**
   - Via `set_root_location()` tool
   - Changing root doesn't delete old root, just makes it a normal location
   - All orphans automatically become children of new root

3. **Coordinate Sync**: ✅ **Location is source of truth**
   - Location.hex_coordinate is source of truth
   - POI syncs to it automatically
   - No validation errors on mismatch - just sync

4. **Scale Enforcement**: ✅ **Soft validation with warnings**
   - Allow flexibility in parent-child relationships
   - Issue warnings for illogical hierarchies (e.g., CITY parent of BUILDING)
   - Don't prevent the relationship - let user decide

5. **Auto-Parent Updates**: ✅ **Manual parent assignment only**
   - No auto-suggestion when moving locations on map
   - User explicitly sets parent relationships
   - Keeps operations predictable and explicit

6. **Orphan Children**: ✅ **Prevent deletion by default, with recursive delete option**
   - **Default**: Prevent deletion if children exist (Option A)
   - **Override**: Add `recursive: bool = False` parameter to delete tool
   - When `recursive=True`, delete location and all descendants (like `rm -rf`)
   - Safety: Require explicit opt-in for recursive deletion

7. **Upgrade Location Defaults**: ✅ **Minimal smart defaults**
   - Only set scale if type is provided
   - Don't auto-assign parent or map coordinates
   - Keep `upgrade_location` simple and predictable
   - **Type-to-Scale Mapping**:
     - CITY/TOWN/VILLAGE → SETTLEMENT
     - TAVERN/INN/SHOP → BUILDING
     - DUNGEON/CAVE → BUILDING or AREA
     - FOREST/MOUNTAIN/DESERT → AREA
     - KINGDOM/PROVINCE → KINGDOM/PROVINCE (1:1)

8. **Migration Detection**: ✅ **Check critical fields only**
   - A location is unmigrated if it's **isolated**:
     - No parent (parent_location_id is None, and it's not the root)
     - No children (child_locations is empty)
     - No map placement (primary_map is None)
   - Rationale: Focus on integration into campaign structure
   - Partial migration is acceptable (e.g., has parent but no map)

## Document Metadata

**Version**: 2.3 (Final - All Decisions Resolved)
**Date**: 2025-11-29
**Status**: Design Specification - Ready for Implementation
**Author**: Claude (Sonnet 4.5)
**Related Specs**: HEX_MAPPING_SPEC.md, DATA_MODELS.md
**Scope**: Campaign root location, location hierarchy, basic hex map integration, and selective migration (connections deferred)

**Changes in v2.1**:
- Added campaign `root_location_id` field
- Root location anchors entire location hierarchy
- Orphaned locations (parent = None) implicitly become children of root
- Auto-creation strategy for root locations
- New root location management tools

**Changes in v2.2**:
- Added `upgrade_location` tool for selective migration
- Added `list_unmigrated_locations` tool for tracking progress
- Added `get_unmigrated_locations()` storage method
- Defined backward compatibility strategy (all new fields optional)
- LLM-assisted migration workflow example
- Smart defaults for type-to-scale inference
- Clarified "unmigrated" definition: isolated locations with no parent, no children, and no map placement

**Changes in v2.3**:
- ✅ All design decisions finalized (moved from "Open Questions" to "Design Decisions")
- Root location creation: Manual via client LLM (not auto-created)
- Root location mutability: Yes, can be changed
- Coordinate sync: Location is source of truth
- Scale enforcement: Soft validation with warnings
- Auto-parent updates: Manual assignment only
- Orphan children: Prevent deletion by default, add `recursive` parameter for tree deletion
- Upgrade defaults: Minimal (infer scale only when explicitly requested via `infer_scale_from_type`)
- Migration detection: Check critical fields (isolation criteria)
- Added `delete_location` tool with `recursive` parameter
- Removed `ensure_root_location()` method (root is manually created)
- Updated all tools and storage methods to reflect finalized decisions

## Key Concepts

### Orphaned vs Unmigrated Locations

**Orphaned Location:**
- Has `parent_location_id = None` (not the root)
- May still have children or be placed on a map
- Implicitly becomes child of campaign root
- Example: A top-level region with cities beneath it

**Unmigrated Location:**
- Orphaned (no parent) AND no children AND no map placement
- Completely isolated from campaign structure
- These are the locations `list_unmigrated_locations` identifies
- Example: An old location created before hierarchy system existed
