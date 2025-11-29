# Hex Mapping System Specification

## Overview

This specification describes a hex-based outdoor mapping system for the D&D Gamemaster MCP server. The system supports kingdom-scale maps with 10km (6 mile) diameter hexes, terrain types, roads, rivers, and points of interest.

## 1. Data Models

### 1.1 Core Enumerations

#### TerrainType
```python
class TerrainType(str, Enum):
    # Grasslands and vegetation
    GRASS = "grass"
    SCRUB = "scrub"
    PLAINS = "plains"
    FARMLAND = "farmland"

    # Forests
    LIGHT_FOREST = "light_forest"
    DENSE_FOREST = "dense_forest"
    JUNGLE = "jungle"

    # Wetlands
    MARSH = "marsh"
    SWAMP = "swamp"

    # Elevation
    HILLS = "hills"
    MOUNTAINS = "mountains"

    # Arid
    DESERT = "desert"
    BADLANDS = "badlands"

    # Cold
    TUNDRA = "tundra"
    GLACIER = "glacier"

    # Special
    VOLCANIC = "volcanic"
    COAST = "coast"
    WATER = "water"
```

#### HexSide
```python
class HexSide(str, Enum):
    NORTH = "north"
    NORTHEAST = "northeast"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    NORTHWEST = "northwest"
    CENTER = "center"
```

#### POIType
```python
class POIType(str, Enum):
    TOWN = "town"
    DUNGEON = "dungeon"
    CASTLE = "castle"
    TOWER = "tower"
    VILLAGE = "village"
    RUINS = "ruins"
    CAMP = "camp"
    SHRINE = "shrine"
    LANDMARK = "landmark"
```

### 1.2 Coordinate System

**Choice: Offset Coordinates (x, y)**

Using a simple offset coordinate system where hexes form columns and rows:
- `x` (column): 0 = leftmost column, increases eastward (to the right)
- `y` (row): 0 = topmost row, increases southward (downward)
- Odd columns (x=1, 3, 5...) are offset down by half a hex
- Example: hex [1,0] touches hexes [0,0] and [0,1]

This is known as "odd-q offset" in hex grid terminology.

```python
class HexCoordinate(BaseModel):
    """Offset coordinate system for hexagonal grids (odd-q offset)."""
    x: Annotated[int, Field(description="Column coordinate (0=leftmost, increases eastward)")]
    y: Annotated[int, Field(description="Row coordinate (0=topmost, increases southward)")]

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def to_cube(self) -> tuple[int, int, int]:
        """Convert offset coordinates to cube coordinates (q, r, s) for distance calculations.

        Cube coordinates satisfy: q + r + s = 0
        This conversion uses the odd-q offset formula.
        """
        q = self.x
        r = self.y - (self.x - (self.x & 1)) // 2
        s = -q - r
        return (q, r, s)

    def distance_to(self, other: "HexCoordinate") -> int:
        """Calculate distance in hexes using cube coordinates."""
        q1, r1, s1 = self.to_cube()
        q2, r2, s2 = other.to_cube()
        return (abs(q1 - q2) + abs(r1 - r2) + abs(s1 - s2)) // 2
```

### 1.3 Map Features

#### Road
```python
class Road(BaseModel):
    """A road passing through a hex."""

    id: str = Field(default_factory=lambda: random(length=8))
    start_point: Annotated[
        HexSide | None,
        Field(description="Where the road enters: a hex side or CENTER. None if road originates at center of this hex")
    ] = None
    end_point: Annotated[
        HexSide | None,
        Field(description="Where the road exits: a hex side or CENTER. None if road terminates at center of this hex")
    ] = None
    road_type: Annotated[
        str,
        Field(description="Type of road (e.g., 'highway', 'path', 'trail')")
    ] = "road"
    condition: Annotated[
        str,
        Field(description="Condition of the road (e.g., 'well-maintained', 'overgrown', 'ruined')")
    ] = "fair"
    notes: str = ""
```

#### River
```python
class River(BaseModel):
    """A river passing through a hex."""

    id: str = Field(default_factory=lambda: random(length=8))
    start_point: Annotated[
        HexSide | None,
        Field(description="Where river enters: a hex side or CENTER. None if river originates at center (source)")
    ] = None
    end_point: Annotated[
        HexSide | None,
        Field(description="Where river exits: a hex side or CENTER. None if river terminates at center (lake/ocean)")
    ] = None
    width: Annotated[
        str,
        Field(description="Width category (e.g., 'stream', 'river', 'wide river')")
    ] = "river"
    navigable: Annotated[bool, Field(description="Whether the river is navigable by boat")] = False
    ford_location: Annotated[
        Optional[str],
        Field(description="Description of where the river can be forded, if applicable")
    ] = None
    notes: str = ""
```

#### PointOfInterest
```python
class PointOfInterest(BaseModel):
    """A point of interest within a hex."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    poi_type: POIType
    description: str
    location_id: Annotated[
        Optional[str],
        Field(description="ID of associated Location object if this POI has detailed data")
    ] = None
    discovered: Annotated[bool, Field(description="Whether the party has discovered this POI")] = False
    position: Annotated[
        HexSide,
        Field(description="Position within hex (CENTER or a specific side/edge)")
    ] = HexSide.CENTER
    notes: str = ""
```

### 1.4 Hex Model

```python
class Hex(BaseModel):
    """A single hex on the map."""

    coordinate: HexCoordinate
    terrain: TerrainType
    roads: list[Road] = Field(default_factory=list)
    rivers: list[River] = Field(default_factory=list)
    pois: list[PointOfInterest] = Field(default_factory=list)
    elevation: Annotated[
        Optional[int],
        Field(description="Elevation in meters above sea level")
    ] = None
    explored: Annotated[bool, Field(description="Whether the party has explored this hex")] = False
    visibility: Annotated[
        str,
        Field(description="Visibility category (e.g., 'clear', 'obscured', 'hidden')")
    ] = "clear"
    notes: str = ""

    def get_description(self) -> str:
        """Generate a natural language description of the hex using LLM sampling.

        This method will use MCP sampling to have an LLM generate a natural language
        description based on the hex's complete JSON data (terrain, roads, rivers, POIs, etc.).

        The implementation will serialize this Hex object to JSON and pass it to the LLM
        with a prompt requesting a descriptive paragraph suitable for a D&D game.

        Returns:
            A natural language description of the hex and its features.
        """
        # Implementation will use mcp.sample() or similar to generate description
        pass
```

### 1.5 HexMap Model

```python
class HexMap(BaseModel):
    """A complete hex map representing a kingdom or region."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    description: str
    hex_diameter_km: Annotated[float, Field(description="Diameter of each hex in kilometers")] = 10.0
    hexes: Annotated[
        dict[str, Hex],
        Field(description="Hexes indexed by 'x,y' coordinate string")
    ] = Field(default_factory=dict)
    default_terrain: TerrainType = TerrainType.GRASS
    bounds: Annotated[
        Optional[dict[str, int]],
        Field(description="Map bounds as {min_x, max_x, min_y, max_y}")
    ] = None
    notes: str = ""

    def _coord_key(self, coord: HexCoordinate) -> str:
        """Generate dictionary key from coordinate."""
        return f"{coord.x},{coord.y}"

    def get_hex(self, coord: HexCoordinate) -> Optional[Hex]:
        """Get a hex at the given coordinate."""
        return self.hexes.get(self._coord_key(coord))

    def set_hex(self, hex: Hex) -> None:
        """Add or update a hex in the map."""
        self.hexes[self._coord_key(hex.coordinate)] = hex
        self._update_bounds(hex.coordinate)

    def _update_bounds(self, coord: HexCoordinate) -> None:
        """Update map bounds to include the given coordinate."""
        if self.bounds is None:
            self.bounds = {
                "min_x": coord.x,
                "max_x": coord.x,
                "min_y": coord.y,
                "max_y": coord.y
            }
        else:
            self.bounds["min_x"] = min(self.bounds["min_x"], coord.x)
            self.bounds["max_x"] = max(self.bounds["max_x"], coord.x)
            self.bounds["min_y"] = min(self.bounds["min_y"], coord.y)
            self.bounds["max_y"] = max(self.bounds["max_y"], coord.y)

    def get_neighbors(self, coord: HexCoordinate) -> dict[HexSide, Optional[Hex]]:
        """Get all neighboring hexes with their directions.

        Uses odd-q offset coordinates where odd columns are shifted down.
        """
        # Neighbor offsets depend on whether column is even or odd
        if coord.x % 2 == 0:
            # Even column offsets
            offsets = {
                HexSide.NORTH: (0, -1),
                HexSide.NORTHEAST: (1, -1),
                HexSide.SOUTHEAST: (1, 0),
                HexSide.SOUTH: (0, 1),
                HexSide.SOUTHWEST: (-1, 0),
                HexSide.NORTHWEST: (-1, -1)
            }
        else:
            # Odd column offsets (shifted down)
            offsets = {
                HexSide.NORTH: (0, -1),
                HexSide.NORTHEAST: (1, 0),
                HexSide.SOUTHEAST: (1, 1),
                HexSide.SOUTH: (0, 1),
                HexSide.SOUTHWEST: (-1, 1),
                HexSide.NORTHWEST: (-1, 0)
            }

        neighbors = {}
        for direction, (dx, dy) in offsets.items():
            neighbor_coord = HexCoordinate(x=coord.x + dx, y=coord.y + dy)
            neighbors[direction] = self.get_hex(neighbor_coord)

        return neighbors
```

## 2. Storage Design

### 2.1 Integration with Campaign Model

Add to the `Campaign` model in `models.py`:

```python
class Campaign(BaseModel):
    # ... existing fields ...

    hex_maps: dict[str, HexMap] = Field(
        default_factory=dict,
        description="Hex maps for outdoor/wilderness areas, indexed by map name"
    )
```

### 2.2 Storage Layer Updates

Add to `DnDStorage` class in `storage.py`:

```python
# HexMap Management
def add_hex_map(self, hex_map: HexMap) -> None:
    """Add a hex map to the current campaign."""
    if not self._current_campaign:
        raise ValueError("No current campaign")

    self._current_campaign.hex_maps[hex_map.name] = hex_map
    self._current_campaign.updated_at = datetime.now()
    self._save_campaign()

def get_hex_map(self, name: str) -> HexMap | None:
    """Get a hex map by name."""
    if not self._current_campaign:
        raise ValueError("No current campaign")
    return self._current_campaign.hex_maps.get(name)

def list_hex_maps(self) -> list[str]:
    """List all hex map names."""
    if not self._current_campaign:
        raise ValueError("No current campaign")
    return list(self._current_campaign.hex_maps.keys())
```

### 2.3 File Storage Considerations

For very large maps (10,000+ hexes), consider:
- Lazy loading of hex data
- Separate JSON file per map: `{campaign_name}_map_{map_name}.json`
- Only load hexes in active region into memory
- For initial implementation, store everything in campaign JSON (simpler)

## 3. MCP Tools

### 3.1 Map Management Tools

#### create_hex_map
```python
@mcp.tool
def create_hex_map(
    name: Annotated[str, Field(description="Name of the hex map")],
    description: Annotated[str, Field(description="Description of the region this map represents")],
    hex_diameter_km: Annotated[float, Field(description="Diameter of each hex in km")] = 10.0,
    default_terrain: Annotated[TerrainType, Field(description="Default terrain type")] = TerrainType.GRASS,
) -> str:
    """Create a new hex map for outdoor wilderness areas."""
```

#### generate_map_for_location
```python
@mcp.tool
def generate_map_for_location(
    location_id: Annotated[str, Field(description="ID of the existing outdoor Location to add a map to")],
    map_description: Annotated[str, Field(description="Description of the terrain and features to generate (e.g., 'a forested valley with a river running north to south and mountains on the eastern edge')")],
    width: Annotated[int, Field(description="Width of the map in hexes", ge=5, le=50)] = 20,
    height: Annotated[int, Field(description="Height of the map in hexes", ge=5, le=50)] = 20,
    hex_scale_km: Annotated[float, Field(description="Size of each hex in kilometers")] = 10.0,
) -> str:
    """Generate a hex map for an existing outdoor location using LLM sampling.

    This tool uses MCP sampling to ask an LLM to generate a hex map in ASCII format
    based on the provided description. The LLM will create terrain appropriate to the
    description, which is then automatically parsed and converted into a HexMap object
    associated with the specified Location.

    Workflow:
    1. Retrieve the Location object by ID
    2. Construct a detailed prompt for the LLM including:
       - The map description
       - Available terrain types and their ASCII codes
       - The requested dimensions (width x height)
       - ASCII format requirements (odd rows indented)
       - Example of proper formatting
    3. Use mcp.sample() to have the LLM generate the ASCII map
    4. Parse the ASCII response using import_terrain_from_ascii logic
    5. Create a new HexMap with name based on location name
    6. Store the map and link it to the Location
    7. Return success message with map details

    Example:
        location_id = "abc12345"  # An outdoor Location called "Silverwood Vale"
        map_description = "A valley with dense forest in the center, light forest around the edges,
                          hills to the north, and a small river flowing from northeast to southwest"

        Result: Creates a 20x20 hex map with terrain matching the description
    """
```

#### delete_hex_map
```python
@mcp.tool
def delete_hex_map(
    map_name: Annotated[str, Field(description="Name of the map to delete")],
) -> str:
    """Delete a hex map from the campaign."""
```

#### list_hex_maps
```python
@mcp.tool
def list_hex_maps() -> str:
    """List all hex maps in the current campaign."""
```

### 3.2 Hex Manipulation Tools

#### add_or_update_hex
```python
@mcp.tool
def add_or_update_hex(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    x: Annotated[int, Field(description="X coordinate (column, 0=leftmost)")],
    y: Annotated[int, Field(description="Y coordinate (row, 0=topmost)")],
    terrain: Annotated[TerrainType, Field(description="Terrain type for this hex")],
    explored: Annotated[bool, Field(description="Whether party has explored this hex")] = False,
    elevation: Annotated[Optional[int], Field(description="Elevation in meters")] = None,
    notes: Annotated[Optional[str], Field(description="Notes about this hex")] = None,
) -> str:
    """Add or update a hex on the map."""
```

#### get_hex_info
```python
@mcp.tool
def get_hex_info(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    x: Annotated[int, Field(description="X coordinate (column)")],
    y: Annotated[int, Field(description="Y coordinate (row)")],
) -> str:
    """Get detailed information about a specific hex."""
```

#### mark_hex_explored
```python
@mcp.tool
def mark_hex_explored(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    x: Annotated[int, Field(description="X coordinate (column)")],
    y: Annotated[int, Field(description="Y coordinate (row)")],
) -> str:
    """Mark a hex as explored by the party."""
```

### 3.3 Road and River Tools

#### add_road
```python
@mcp.tool
def add_road(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    path: Annotated[list[tuple[int, int]], Field(description="List of (x, y) coordinates the road passes through, in order from start to end")],
    road_type: Annotated[str, Field(description="Type of road (e.g., 'highway', 'road', 'path', 'trail')")] = "road",
    condition: Annotated[str, Field(description="Road condition (e.g., 'well-maintained', 'fair', 'poor', 'overgrown')")] = "fair",
    name: Annotated[Optional[str], Field(description="Optional name for this road (e.g., 'King's Highway', 'Old Forest Road')")] = None,
    start_point: Annotated[str, Field(description="Where the road starts in the first hex: 'center', 'north', 'northeast', 'southeast', 'south', 'southwest', or 'northwest'")] = "center",
    end_point: Annotated[str, Field(description="Where the road ends in the last hex: 'center', 'north', 'northeast', 'southeast', 'south', 'southwest', or 'northwest'")] = "center",
) -> str:
    """Add a road that follows a path through multiple hexes.

    The tool automatically calculates which sides the road enters and exits for each hex
    based on the sequence of coordinates. Each consecutive pair of hexes must be adjacent.

    The start_point defines where the road begins in the first hex (defaults to 'center',
    e.g., a town). The end_point defines where the road ends in the last hex.

    Examples:
        # Road from town center to castle center
        path = [(0, 0), (1, 0), (2, 1)]
        start_point = "center", end_point = "center"

        # Road entering from north side of first hex, ending at town center in last hex
        path = [(5, 5), (5, 6)]
        start_point = "north", end_point = "center"
    """
```

#### add_river
```python
@mcp.tool
def add_river(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    path: Annotated[list[tuple[int, int]], Field(description="List of (x, y) coordinates the river flows through, from source to mouth")],
    width: Annotated[str, Field(description="River width category (e.g., 'stream', 'river', 'wide river')")] = "river",
    navigable: Annotated[bool, Field(description="Whether the river is navigable by boat")] = False,
    name: Annotated[Optional[str], Field(description="Optional name for this river (e.g., 'Misty River', 'Dragon Brook')")] = None,
    start_point: Annotated[str, Field(description="Where the river starts in the first hex: 'center' (spring/source) or a side (entering from another region)")] = "center",
    end_point: Annotated[str, Field(description="Where the river ends in the last hex: 'center' (lake/ocean) or a side (exiting to another region)")] = "center",
) -> str:
    """Add a river that follows a path through multiple hexes.

    The tool automatically calculates which sides the river enters and exits for each hex
    based on the sequence of coordinates. Each consecutive pair of hexes must be adjacent.

    The start_point defines where the river begins (defaults to 'center' for a spring/source).
    The end_point defines where it ends (defaults to 'center' for emptying into a lake/ocean).

    Examples:
        # River from mountain spring to ocean
        path = [(5, 2), (4, 3), (4, 4), (3, 5)]
        start_point = "center", end_point = "center"

        # River entering from north, exiting south into another map region
        path = [(10, 0), (10, 1), (10, 2)]
        start_point = "north", end_point = "south"
    """
```

#### remove_road
```python
@mcp.tool
def remove_road(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    path: Annotated[list[tuple[int, int]], Field(description="List of (x, y) coordinates where the road should be removed")],
) -> str:
    """Remove a road from the specified hexes.

    Removes road segments from each hex in the path. Useful for modifying roads or
    removing abandoned routes.
    """
```

#### remove_river
```python
@mcp.tool
def remove_river(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    path: Annotated[list[tuple[int, int]], Field(description="List of (x, y) coordinates where the river should be removed")],
) -> str:
    """Remove a river from the specified hexes.

    Removes river segments from each hex in the path.
    """
```

### 3.4 Point of Interest Tools

#### add_poi_to_hex
```python
@mcp.tool
def add_poi_to_hex(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    x: Annotated[int, Field(description="X coordinate (column)")],
    y: Annotated[int, Field(description="Y coordinate (row)")],
    name: Annotated[str, Field(description="Name of the point of interest")],
    poi_type: Annotated[POIType, Field(description="Type of POI")],
    description: Annotated[str, Field(description="Description of the POI")],
    location_id: Annotated[Optional[str], Field(description="ID of associated Location object")] = None,
    discovered: Annotated[bool, Field(description="Has the party discovered this?")] = False,
    position: Annotated[str, Field(description="Position within hex: 'center', 'north', 'northeast', 'southeast', 'south', 'southwest', 'northwest'")] = "center",
) -> str:
    """Add a point of interest to a hex.

    The position indicates where in the hex the POI is located. Use 'center' for most
    POIs (towns, dungeons at hex center), or a specific side for POIs at hex edges
    (e.g., a tower on the northern edge).
    """
```

#### remove_poi_from_hex
```python
@mcp.tool
def remove_poi_from_hex(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    poi_id: Annotated[str, Field(description="ID of the POI to remove")],
) -> str:
    """Remove a point of interest from the map."""
```

#### mark_poi_discovered
```python
@mcp.tool
def mark_poi_discovered(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    poi_id: Annotated[str, Field(description="ID of the POI")],
) -> str:
    """Mark a POI as discovered by the party."""
```

#### list_pois_on_map
```python
@mcp.tool
def list_pois_on_map(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    discovered_only: Annotated[bool, Field(description="Only show discovered POIs")] = False,
    poi_type: Annotated[Optional[POIType], Field(description="Filter by POI type")] = None,
) -> str:
    """List all points of interest on a map."""
```

### 3.5 Navigation and Exploration Tools

#### get_neighboring_hexes
```python
@mcp.tool
def get_neighboring_hexes(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    x: Annotated[int, Field(description="X coordinate of center hex (column)")],
    y: Annotated[int, Field(description="Y coordinate of center hex (row)")],
) -> str:
    """Get information about all hexes adjacent to the specified hex."""
```

#### describe_area
```python
@mcp.tool
def describe_area(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    center_x: Annotated[int, Field(description="X coordinate of center (column)")],
    center_y: Annotated[int, Field(description="Y coordinate of center (row)")],
    radius: Annotated[int, Field(description="Radius in hexes")] = 1,
) -> str:
    """Describe an area of the map centered on a specific hex."""
```

#### calculate_distance
```python
@mcp.tool
def calculate_distance(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    from_x: Annotated[int, Field(description="Starting X coordinate (column)")],
    from_y: Annotated[int, Field(description="Starting Y coordinate (row)")],
    to_x: Annotated[int, Field(description="Destination X coordinate (column)")],
    to_y: Annotated[int, Field(description="Destination Y coordinate (row)")],
) -> str:
    """Calculate the distance in hexes and kilometers between two points."""
```

#### find_path
```python
@mcp.tool
def find_path(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    from_x: Annotated[int, Field(description="Starting X coordinate (column)")],
    from_y: Annotated[int, Field(description="Starting Y coordinate (row)")],
    to_x: Annotated[int, Field(description="Destination X coordinate (column)")],
    to_y: Annotated[int, Field(description="Destination Y coordinate (row)")],
    prefer_roads: Annotated[bool, Field(description="Prefer hexes with roads")] = True,
    avoid_terrain: Annotated[Optional[list[TerrainType]], Field(description="Terrain types to avoid")] = None,
) -> str:
    """Find an optimal path between two hexes on the map."""
```

### 3.6 Bulk Operations

#### import_terrain_from_ascii
```python
@mcp.tool
def import_terrain_from_ascii(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    ascii_map: Annotated[str, Field(description="ASCII representation of the map. Each character represents one hex. Odd columns (x=1,3,5...) should be indented with a leading space to show the offset.")],
    legend: Annotated[dict[str, str], Field(description="Mapping of ASCII characters to terrain type names. Example: {'G': 'grass', 'F': 'light_forest', 'M': 'mountains'}")],
    start_x: Annotated[int, Field(description="X coordinate for the top-left hex")] = 0,
    start_y: Annotated[int, Field(description="Y coordinate for the top-left hex")] = 0,
) -> str:
    """Import terrain from an ASCII map representation.

    This is the most efficient way to create large maps. Each character in the ASCII map
    represents one hex's terrain type. Rows are separated by newlines. Odd-numbered columns
    should be indented with a space to represent the hex offset.

    Example:
        ascii_map = '''
        G G F F M
         G F F H M
        G F F H H
         W G F H M
        '''
        legend = {
            'G': 'grass',
            'F': 'light_forest',
            'M': 'mountains',
            'H': 'hills',
            'W': 'water'
        }
    """
```

#### fill_rectangular_region
```python
@mcp.tool
def fill_rectangular_region(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    min_x: Annotated[int, Field(description="Minimum X coordinate (inclusive)")],
    min_y: Annotated[int, Field(description="Minimum Y coordinate (inclusive)")],
    max_x: Annotated[int, Field(description="Maximum X coordinate (inclusive)")],
    max_y: Annotated[int, Field(description="Maximum Y coordinate (inclusive)")],
    terrain: Annotated[TerrainType, Field(description="Terrain type to fill")],
) -> str:
    """Fill a rectangular region with a specific terrain type.

    Useful for quickly initializing a map with a base terrain or making large-scale changes.
    Creates hexes at all coordinates within the specified bounds.
    """
```

#### generate_terrain_region
```python
@mcp.tool
def generate_terrain_region(
    map_name: Annotated[str, Field(description="Name of the hex map")],
    center_x: Annotated[int, Field(description="Center X coordinate (column)")],
    center_y: Annotated[int, Field(description="Center Y coordinate (row)")],
    radius: Annotated[int, Field(description="Radius of the region in hexes")],
    terrain: Annotated[TerrainType, Field(description="Terrain type to fill")],
) -> str:
    """Fill a circular region with a specific terrain type.

    Useful for creating natural features like forests, hills, or lakes. Uses hex distance
    calculation to create a circular pattern.
    """
```

## 4. Technical Implementation Details

### 4.1 LLM-Generated Map Creation

The `generate_map_for_location` tool uses MCP sampling to generate maps. Here's the implementation design:

#### LLM Prompt Construction

```python
def build_map_generation_prompt(description: str, width: int, height: int) -> str:
    """Build the prompt for LLM map generation."""

    terrain_codes = {
        'G': 'grass',
        'P': 'plains',
        'F': 'farmland',
        'L': 'light_forest',
        'D': 'dense_forest',
        'J': 'jungle',
        'M': 'marsh',
        'S': 'swamp',
        'H': 'hills',
        'N': 'mountains',
        'E': 'desert',
        'B': 'badlands',
        'T': 'tundra',
        'I': 'glacier',
        'V': 'volcanic',
        'C': 'coast',
        'W': 'water',
        'R': 'scrub'
    }

    prompt = f"""Generate a hex map in ASCII format with the following characteristics:

DESCRIPTION: {description}

MAP SIZE: {width} hexes wide by {height} hexes tall

TERRAIN CODES (use single letters):
"""

    for code, terrain in terrain_codes.items():
        prompt += f"  {code} = {terrain}\n"

    prompt += f"""
FORMAT REQUIREMENTS:
1. Each character represents one hex's terrain type
2. Separate hexes with a single space
3. Each row is on its own line
4. ODD-numbered rows (rows 1, 3, 5...) must start with a space to show hex offset
5. EVEN-numbered rows (rows 0, 2, 4...) start directly with a terrain code
6. Create exactly {height} rows

EXAMPLE (5x3 map):
G G L L M
 L L D D H
G L D H H

This creates:
- Row 0 (even): hexes at columns 0,2,4,6,8
- Row 1 (odd, indented): hexes at columns 1,3,5,7,9
- Row 2 (even): hexes at columns 0,2,4,6,8

Now generate a {width}x{height} hex map matching the description. Output ONLY the ASCII map, no explanations.
"""

    return prompt
```

#### Sampling and Parsing Workflow

```python
async def generate_map_for_location_impl(
    location_id: str,
    map_description: str,
    width: int,
    height: int,
    hex_scale_km: float,
    storage: DnDStorage,
    mcp_server
) -> str:
    """Implementation of generate_map_for_location tool."""

    # 1. Get the location
    location = storage.get_location(location_id)
    if not location:
        raise ValueError(f"Location with ID {location_id} not found")

    # 2. Build the prompt
    prompt = build_map_generation_prompt(map_description, width, height)

    # 3. Sample from LLM
    response = await mcp_server.sample(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,  # Enough for a 50x50 map
        temperature=0.7  # Some creativity, not too random
    )

    ascii_map = response.content.strip()

    # 4. Build legend from terrain codes
    legend = {
        'G': 'grass', 'P': 'plains', 'F': 'farmland',
        'L': 'light_forest', 'D': 'dense_forest', 'J': 'jungle',
        'M': 'marsh', 'S': 'swamp', 'H': 'hills', 'N': 'mountains',
        'E': 'desert', 'B': 'badlands', 'T': 'tundra', 'I': 'glacier',
        'V': 'volcanic', 'C': 'coast', 'W': 'water', 'R': 'scrub'
    }

    # 5. Parse the ASCII map
    hexes = parse_ascii_map(ascii_map, legend, start_x=0, start_y=0)

    # 6. Create HexMap object
    map_name = f"{location.name} Map"
    hex_map = HexMap(
        name=map_name,
        description=map_description,
        hex_diameter_km=hex_scale_km
    )

    # 7. Add all hexes to the map
    for x, y, terrain in hexes:
        coord = HexCoordinate(x=x, y=y)
        hex_obj = Hex(
            coordinate=coord,
            terrain=TerrainType(terrain)
        )
        hex_map.set_hex(hex_obj)

    # 8. Store the map
    storage.add_hex_map(hex_map)

    # 9. Link to location (optional - could add map_name field to Location)
    # location.map_name = map_name
    # storage.update_location(location)

    return f"Generated {width}x{height} hex map '{map_name}' for {location.name}. " \
           f"Total hexes: {len(hexes)}. Scale: {hex_scale_km}km per hex."
```

#### Error Handling

The implementation should handle:
- **Invalid location ID**: Clear error message
- **Malformed LLM output**: Retry with clarified prompt or fallback to manual creation
- **Invalid terrain codes**: Skip unknown codes or map to default terrain
- **Incorrect dimensions**: Validate parsed map matches requested size

#### Integration with Location Model

To fully integrate, the `Location` model could be extended:

```python
class Location(BaseModel):
    # ... existing fields ...
    map_name: Optional[str] = None  # Name of associated HexMap
```

This allows tools to query "What map is associated with this location?" and vice versa.

### 4.2 ASCII Map Parsing

The `import_terrain_from_ascii` tool parses ASCII maps where:
- Each non-whitespace character represents a hex
- Spaces are used to separate hexes within a row
- Leading spaces on a line indicate odd-column offset
- Newlines separate rows

**Parsing Algorithm:**

```python
def parse_ascii_map(ascii_map: str, legend: dict[str, str], start_x: int = 0, start_y: int = 0) -> list[tuple[int, int, str]]:
    """Parse ASCII map into list of (x, y, terrain) tuples.

    Returns:
        List of (x, y, terrain_type) tuples
    """
    hexes = []
    lines = ascii_map.strip().split('\n')

    for row_idx, line in enumerate(lines):
        y = start_y + row_idx

        # Check if this is an odd column row (starts with space)
        is_offset_row = line.startswith(' ')
        if is_offset_row:
            line = line[1:]  # Remove leading space

        # Split by spaces to get individual hex characters
        chars = line.split()

        for col_idx, char in enumerate(chars):
            if char in legend:
                # Calculate x coordinate
                # If offset row, odd columns (1, 3, 5...)
                # If not offset row, even columns (0, 2, 4...)
                x = start_x + (col_idx * 2) + (1 if is_offset_row else 0)
                terrain = legend[char]
                hexes.append((x, y, terrain))

    return hexes
```

**Example:**
```
Input ASCII:
G G F
 F F M
G F H

Parsed as:
(0,0,grass) (2,0,light_forest)        # Row 0, even columns
(1,1,light_forest) (3,1,mountains)    # Row 1, odd columns (offset)
(0,2,grass) (2,2,light_forest) (4,2,hills)  # Row 2, even columns
```

### 4.2 Road and River Path Processing

When adding roads or rivers via paths, the system must:

1. **Validate adjacency**: Ensure each consecutive pair of hexes is adjacent
2. **Calculate sides**: Determine which side the path enters/exits each hex
3. **Create segments**: Add Road/River objects to each hex along the path

**Side Calculation Algorithm:**

```python
def calculate_path_sides(
    path: list[tuple[int, int]],
    start_point: str = "center",
    end_point: str = "center"
) -> list[tuple[int, int, HexSide | None, HexSide | None]]:
    """Calculate entry/exit points for each hex in a path.

    Args:
        path: List of (x, y) coordinates
        start_point: Where path starts in first hex (HexSide value, "center", or side name)
        end_point: Where path ends in last hex (HexSide value, "center", or side name)

    Returns:
        List of (x, y, entry_point, exit_point) tuples.
        Points can be HexSide enum values or None.
        None means the road/river terminates at the center of the hex.
    """
    result = []

    for i, (x, y) in enumerate(path):
        coord = HexCoordinate(x=x, y=y)
        entry_point = None
        exit_point = None

        # First hex
        if i == 0:
            # If start is center, entry is None; otherwise use the side
            entry_point = None if start_point == "center" else HexSide(start_point)
            if len(path) > 1:
                next_coord = HexCoordinate(x=path[1][0], y=path[1][1])
                exit_point = get_direction_from_to(coord, next_coord)
            else:
                # Single hex path
                exit_point = None if end_point == "center" else HexSide(end_point)

        # Last hex (not first)
        elif i == len(path) - 1:
            prev_coord = HexCoordinate(x=path[i-1][0], y=path[i-1][1])
            entry_point = get_direction_from_to(prev_coord, coord)
            exit_point = None if end_point == "center" else HexSide(end_point)

        # Middle hexes
        else:
            prev_coord = HexCoordinate(x=path[i-1][0], y=path[i-1][1])
            entry_point = get_direction_from_to(prev_coord, coord)
            next_coord = HexCoordinate(x=path[i+1][0], y=path[i+1][1])
            exit_point = get_direction_from_to(coord, next_coord)

        result.append((x, y, entry_point, exit_point))

    return result


def get_direction_from_to(from_coord: HexCoordinate, to_coord: HexCoordinate) -> HexSide:
    """Determine which direction to travel from one hex to reach an adjacent hex.

    Raises ValueError if hexes are not adjacent.
    """
    # Get the offset based on whether from_coord is even or odd column
    if from_coord.x % 2 == 0:
        directions = EVEN_COL_DIRECTIONS
    else:
        directions = ODD_COL_DIRECTIONS

    dx = to_coord.x - from_coord.x
    dy = to_coord.y - from_coord.y

    # Find which direction matches this offset
    for direction, (offset_x, offset_y) in directions.items():
        if dx == offset_x and dy == offset_y:
            return direction

    raise ValueError(f"Hexes at {from_coord} and {to_coord} are not adjacent")
```

**Examples:**

```python
# Road from town center through hexes to castle center
path = [(0, 0), (1, 0), (2, 1)]
start_point = "center"
end_point = "center"

# Results in:
# Hex [0,0]: entry=None (starts at center), exit=NORTHEAST (to [1,0])
# Hex [1,0]: entry=SOUTHWEST (from [0,0]), exit=SOUTHEAST (to [2,1])
# Hex [2,1]: entry=NORTHWEST (from [1,0]), exit=None (ends at center)

# Road entering from north, exiting to south
path = [(5, 5), (5, 6), (5, 7)]
start_point = "north"
end_point = "south"

# Results in:
# Hex [5,5]: entry=NORTH (from outside map), exit=SOUTH (to [5,6])
# Hex [5,6]: entry=NORTH (from [5,5]), exit=SOUTH (to [5,7])
# Hex [5,7]: entry=NORTH (from [5,6]), exit=SOUTH (to outside map)
```

### 4.3 Coordinate System Utilities

```python
# Neighbor calculation for odd-q offset coordinates
# Different offsets for even vs odd columns due to hex staggering

# Even columns (x % 2 == 0)
EVEN_COL_DIRECTIONS = {
    HexSide.NORTH: (0, -1),
    HexSide.NORTHEAST: (1, -1),
    HexSide.SOUTHEAST: (1, 0),
    HexSide.SOUTH: (0, 1),
    HexSide.SOUTHWEST: (-1, 0),
    HexSide.NORTHWEST: (-1, -1)
}

# Odd columns (x % 2 == 1) - shifted down by half a hex
ODD_COL_DIRECTIONS = {
    HexSide.NORTH: (0, -1),
    HexSide.NORTHEAST: (1, 0),
    HexSide.SOUTHEAST: (1, 1),
    HexSide.SOUTH: (0, 1),
    HexSide.SOUTHWEST: (-1, 1),
    HexSide.NORTHWEST: (-1, 0)
}

def get_neighbor_coordinate(coord: HexCoordinate, direction: HexSide) -> HexCoordinate:
    """Get the coordinate of a neighboring hex.

    Uses different offsets for even/odd columns due to hex staggering.
    """
    if coord.x % 2 == 0:
        dx, dy = EVEN_COL_DIRECTIONS[direction]
    else:
        dx, dy = ODD_COL_DIRECTIONS[direction]

    return HexCoordinate(x=coord.x + dx, y=coord.y + dy)

def get_hexes_in_range(center: HexCoordinate, radius: int) -> list[HexCoordinate]:
    """Get all hex coordinates within a given radius.

    Uses cube coordinate distance for accurate circular range.
    """
    results = []
    # Search in a rectangular area and filter by distance
    for x in range(center.x - radius, center.x + radius + 1):
        for y in range(center.y - radius, center.y + radius + 1):
            coord = HexCoordinate(x=x, y=y)
            if center.distance_to(coord) <= radius:
                results.append(coord)
    return results
```

### 4.4 Pathfinding Algorithm

Use **A\* algorithm** with terrain-based movement costs:

```python
TERRAIN_COSTS = {
    # Easy terrain
    TerrainType.GRASS: 1.0,
    TerrainType.PLAINS: 1.0,
    TerrainType.FARMLAND: 0.9,  # Well-maintained paths
    TerrainType.COAST: 1.1,

    # Moderate terrain
    TerrainType.SCRUB: 1.2,
    TerrainType.LIGHT_FOREST: 1.5,
    TerrainType.HILLS: 1.5,
    TerrainType.TUNDRA: 1.5,
    TerrainType.DESERT: 1.8,

    # Difficult terrain
    TerrainType.DENSE_FOREST: 2.0,
    TerrainType.MARSH: 2.0,
    TerrainType.BADLANDS: 2.2,

    # Very difficult terrain
    TerrainType.JUNGLE: 2.5,
    TerrainType.SWAMP: 2.5,
    TerrainType.VOLCANIC: 2.5,
    TerrainType.GLACIER: 2.8,
    TerrainType.MOUNTAINS: 3.0,

    # Impassable (without special means)
    TerrainType.WATER: float('inf')  # Impassable without boats
}

def terrain_cost(hex: Hex, has_road: bool = False) -> float:
    """Calculate movement cost for a hex."""
    base_cost = TERRAIN_COSTS.get(hex.terrain, 1.0)

    # Roads reduce cost significantly
    if has_road:
        return min(base_cost, 0.5)

    return base_cost
```

### 4.5 Movement and Travel Time

```python
# Movement rates (km per day)
TRAVEL_RATES = {
    "fast": 40.0,      # Forced march
    "normal": 30.0,    # Standard travel pace
    "slow": 20.0,      # Careful exploration
}

def calculate_travel_time(
    path: list[Hex],
    hex_diameter_km: float,
    pace: str = "normal"
) -> float:
    """Calculate travel time in days for a given path."""
    total_km = len(path) * hex_diameter_km
    km_per_day = TRAVEL_RATES.get(pace, 30.0)
    return total_km / km_per_day
```

### 4.6 Map Rendering Considerations

For future ASCII/text-based map rendering:

```
    ___     ___     ___
   / G \___/ F \___/ H \
   \___/ F \___/ T \___/
   / F \___/ F \___/ M \
   \___/ R \___/ H \___/
   / W \___/ G \___/ G \
   \___/   \___/   \___/

Legend:
G = Grass, F = Forest, H = Hills
M = Mountains, W = Water, T = Town
R = Road
```

## 5. Integration with Existing Systems

### 5.1 Location Integration

When a POI references a `Location` object:
1. Store the `Location.id` in `PointOfInterest.location_id`
2. When entering a POI, update `GameState.current_location` to the location name
3. Tools can query both hex coordinates and location details

### 5.2 Quest Integration

Quests can reference hex coordinates:
```python
class Quest(BaseModel):
    # ... existing fields ...
    map_name: Optional[str] = None
    target_hex_x: Optional[int] = None
    target_hex_y: Optional[int] = None
```

### 5.3 Game State Updates

Add to `GameState`:
```python
class GameState(BaseModel):
    # ... existing fields ...
    current_map: Optional[str] = None
    current_hex_x: Optional[int] = None
    current_hex_y: Optional[int] = None
```

### 5.4 Adventure Event Logging

Log exploration events:
```python
# When entering a new hex
event = AdventureEvent(
    campaign=campaign_name,
    event_type=EventType.EXPLORATION,
    title=f"Explored {terrain.value} terrain",
    description=hex.get_description(),
    location=f"{map_name} ({x},{y})"
)
```

## 6. Future Enhancements

### 6.1 Multi-Scale Maps

Support multiple map scales:
- **Kingdom**: 10km hexes (current spec)
- **Regional**: 2km hexes (detailed exploration)
- **Local**: 100m hexes (tactical outdoor combat)

### 6.2 Weather and Seasons

```python
class Hex(BaseModel):
    # ... existing fields ...
    climate_zone: Optional[str] = None  # "temperate", "arctic", "tropical"
    seasonal_modifiers: dict[str, dict] = Field(default_factory=dict)
```

### 6.3 Visibility and Fog of War

```python
class Hex(BaseModel):
    # ... existing fields ...
    visibility_level: str = "hidden"  # "hidden", "spotted", "explored", "detailed"
```

### 6.4 Political Boundaries

```python
class Territory(BaseModel):
    """A political territory on the map."""
    name: str
    ruler: Optional[str] = None
    hexes: list[HexCoordinate] = Field(default_factory=list)
    color: str = "#CCCCCC"  # For rendering
    allies: list[str] = Field(default_factory=list)
    enemies: list[str] = Field(default_factory=list)
```

## 7. Implementation Priority

### Phase 1: Core Models and Storage (Priority: High)
1. Add enums (TerrainType, HexSide, POIType)
2. Implement HexCoordinate with distance calculation
3. Create Hex, Road, River, PointOfInterest models
4. Create HexMap model with basic methods
5. Update Campaign model to include hex_maps
6. Add storage methods for hex map CRUD

### Phase 2: Basic Tools (Priority: High)
1. create_hex_map
2. import_terrain_from_ascii ⭐ (primary authoring tool)
3. generate_map_for_location ⭐ (LLM-assisted map generation)
4. fill_rectangular_region
5. add_or_update_hex
6. get_hex_info
7. list_hex_maps

### Phase 3: Navigation and Features (Priority: Medium)
1. generate_terrain_region (circular fill)
2. get_neighboring_hexes
3. calculate_distance
4. describe_area
5. mark_hex_explored
6. add_poi_to_hex
7. POI discovery tools

### Phase 4: Roads and Rivers (Priority: Medium)
1. add_road (path-based, auto-calculates sides)
2. add_river (path-based, auto-calculates sides)
3. remove_road
4. remove_river

### Phase 5: Advanced Features (Priority: Low)
1. find_path (A* pathfinding)
2. Travel time calculations
3. Integration with quest system

## 8. Testing Strategy

### 8.1 Unit Tests
- HexCoordinate distance calculations
- Neighbor calculations
- Path finding correctness
- Terrain cost calculations

### 8.2 Integration Tests
- Create map and add hexes via ASCII import
- Add roads following paths (validate adjacency checking)
- Add rivers from source to mouth
- Verify correct side calculations for roads/rivers
- POI discovery workflow
- Navigation between locations using roads

### 8.3 Inspector Testing
Use `npx @mcpjam/inspector` to test:
1. Creating a new hex map
2. Importing terrain from ASCII (10x10 grid with varied terrain)
3. Filling a rectangular region
4. Adding circular terrain features
5. Adding individual hexes
6. Creating a road network
7. Adding a river system
8. Placing POIs
9. Testing navigation queries
10. Querying hex information

## 9. Documentation Updates Needed

1. Update README.md with hex mapping features
2. Add examples of map creation workflows
3. Document coordinate system for users
4. Create a tutorial for building a starter region
5. Add prompts for outdoor/exploration mode

## 10. Success Criteria

The hex mapping system will be considered complete when:

1. DMs can create kingdom-scale maps with varied terrain
2. Roads and rivers can be added to connect locations
3. Points of interest can be placed and discovered
4. Party can track their position on the map
5. Basic distance and neighbor queries work correctly
6. Maps persist across sessions
7. Integration with existing Location system functions properly
8. All tools are tested via MCP Inspector

---

**Document Version**: 1.11
**Date**: 2025-11-29
**Status**: Design Specification - Ready for Review
**Changelog**:
- v1.11: Added generate_map_for_location tool for LLM-assisted map generation from descriptions
- v1.10: Changed Hex.get_description() to use LLM sampling instead of templated text generation
- v1.9: Changed PointOfInterest.position to use HexSide enum instead of free-form string
- v1.8: Expanded TerrainType enum from 9 to 18 types (added desert, tundra, glacier, volcanic, plains, farmland, badlands, coast, marsh)
- v1.7: Added CENTER to HexSide enum, removed separate HexPoint type for simplicity
- v1.6: Added optional start_point and end_point parameters to add_road/add_river (defaults to "center")
- v1.5: Changed roads/rivers to path-based tools (single tool call for entire route with auto-calculated sides)
- v1.4: Added ASCII map import tool and rectangular fill for efficient bulk terrain authoring
- v1.3: Removed random encounters feature (will be added later)
- v1.2: Removed created_at and updated_at timestamp fields
- v1.1: Changed from axial (q,r) to offset (x,y) coordinate system per user request
- v1.0: Initial specification
