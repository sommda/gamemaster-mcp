"""
Data models for the D&D MCP Server.
"""

from datetime import datetime
from enum import Enum
from logging import Handler, LogRecord
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field
from shortuuid import random

from .logutils import logger
from .prompts import (
    combat_prompt,
    dungeon_prompt,
    outdoor_prompt,
    setup_prompt,
    town_prompt,
)

# Available game modes with descriptions
AVAILABLE_MODES = {
    "setup": "Mode used when you're setting up a campaign rather than actively playing it",
    "town": "Mode used when in town (typically bartering, gathering information, etc)",
    "outdoors": "Mode active when adventuring outdoors or traveling between locations by land",
    "dungeon": "Party is in a dungeon",
    "combat": "Party is in combat",
}

MODE_PROMPTS = {
    "setup": setup_prompt,
    "town": town_prompt,
    "outdoors": outdoor_prompt,
    "dungeon": dungeon_prompt,
    "combat": combat_prompt
}


class GameStats(BaseModel):
    """Statistics and metadata about the current campaign, and about the MCP server itself across all campaigns."""

    ctime: datetime = Field(default_factory=datetime.now)
    last_tool_call: datetime | None = None
    tool_calls: int = 0
    errors: int = 0
    campaigns_created: int = 0
    campaigns_loaded: int = 0
    campaign_updates: int = 0
    campaign_deletions: int = 0
    characters_created: int = 0
    character_updates: int = 0
    character_deletions: int = 0
    npcs_created: int = 0
    npc_updates: int = 0
    npc_deletions: int = 0
    locations_created: int = 0
    location_updates: int = 0
    location_deletions: int = 0
    quests_created: int = 0
    quest_updates: int = 0
    quest_deletions: int = 0
    encounters_created: int = 0
    encounters_completed: int = 0
    encounter_updates: int = 0
    encounter_deletions: int = 0
    sessions_created: int = 0
    session_updates: int = 0
    session_deletions: int = 0
    items_given: int = 0
    items_taken: int = 0
    item_updates: int = 0
    item_creations: int = 0
    item_deletions: int = 0
    spells_created: int = 0
    spell_updates: int = 0
    spell_deletions: int = 0
    spells_cast: int = 0
    die_rolls: int = 0
    roll_successes: int = 0
    roll_failures: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    death_saves_success: int = 0
    death_saves_failure: int = 0
    ingame_days: int = 0

    def _save_stats(self) -> None:
        # TODO: Implement me
        return None

    def _load_stats(self, stats: dict[str, Any]) -> None:
        # TODO: Implement me
        return None

    def inc(self, field: str, inc: int = 1) -> None:
        """Increment a counter.

        Args:
            field (str): The name of the counter to increment. Can be one of:

            inc (int = 1): The amount to increment the counter by. Defaults to 1.

        **Field** can be any of the following:
            tool_calls
            errors
            campaigns_created
            campaigns_loaded
            campaign_updates
            campaign_deletions
            characters_created
            character_updates
            character_deletions
            npcs_created
            npc_updates
            npc_deletions
            locations_created
            location_updates
            location_deletions
            quests_created
            quest_updates
            quest_deletions
            encounters_created
            encounters_completed
            encounter_updates
            encounter_deletions
            sessions_created
            session_updates
            session_deletions
            items_given
            items_taken
            item_updates
            item_creations
            item_deletions
            spells_created
            spell_updates
            spell_deletions
            spells_cast
            die_rolls
            roll_successes
            roll_failures
            damage_dealt
            damage_taken
            death_saves_success
            death_saves_failure
            ingame_days
        """
        try:
            setattr(self, field, getattr(self, field) + inc)
            self._save_stats()
        except Exception as e:
            logger.error(f"❌ Error incrementing {field} in GameStats: {e}")


class GameStatHandler(Handler):
    """Connects the logging module to the GameStats object."""

    def __init__(self, gamestats: GameStats, func=None) -> None:
        super().__init__()
        self.gamestats = gamestats
        self.func = func or self.inc_stat

    def emit(self, record):
        try:
            self.func(record)  # Execute the function with the log record
        except Exception:
            self.handleError(record)  # Handle errors gracefully

    def inc_stat(self, record: LogRecord):
        if "ERROR" in record.levelname:
            # Increment error count stat
            self.gamestats.inc("errors")


# Load GameStats object and attach logging handler
gamestats = GameStats()
logger.addHandler(GameStatHandler(gamestats))


class AbilityScore(BaseModel):
    """D&D ability score with modifiers."""

    score: int = Field(ge=1, le=30, description="Raw ability score")

    @property
    def mod(self) -> int:
        """Calculate ability modifier."""
        return (self.score - 10) // 2


class SavingThrowProficiency(str, Enum):
    """Proficiency level for saving throws."""
    NONE = "none"
    PROFICIENT = "proficient"


class SkillProficiency(str, Enum):
    """Proficiency level for skills."""
    NONE = "none"
    PROFICIENT = "proficient"
    EXPERTISE = "expertise"  # Double proficiency bonus


class SavingThrow(BaseModel):
    """Saving throw with proficiency tracking."""

    ability: str = Field(description="Base ability for this save (str, dex, con, int, wis, cha)")
    proficiency: SavingThrowProficiency = SavingThrowProficiency.NONE
    modifier: int = Field(default=0, description="Total saving throw modifier (ability mod + proficiency if applicable)")


class Skill(BaseModel):
    """Skill with proficiency tracking."""

    name: str = Field(description="Name of the skill")
    ability: str = Field(description="Base ability for this skill (str, dex, con, int, wis, cha)")
    proficiency: SkillProficiency = SkillProficiency.NONE
    modifier: int = Field(default=0, description="Total skill modifier (ability mod + proficiency if applicable)")


# Standard D&D 5e skills with their base abilities
STANDARD_SKILLS = {
    "acrobatics": "dexterity",
    "animal_handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}


# Standard D&D 5e saving throws
STANDARD_SAVING_THROWS = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]


class CharacterClass(BaseModel):
    """Character class information."""

    name: str
    level: int = Field(ge=1, le=20)
    hit_dice: Annotated[str, "The type of hit dice for this character. E.g.. '1d8'"] = (
        "1d4"  # e.g., "1d8"
    )
    subclass: Annotated[str | None, "The character's subclass."] = None


class Race(BaseModel):
    """Character race information."""

    name: str
    subrace: str | None = None
    traits: list[str] = Field(default_factory=list)


class Item(BaseModel):
    """Generic item model."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    description: str | None = None
    quantity: int = 1
    weight: float | None = None
    value: str | None = None  # e.g., "50 gp"
    item_type: str = "misc"  # weapon, armor, consumable, misc, etc.
    properties: dict[str, Any] = Field(default_factory=dict)


class Spell(BaseModel):
    """Spell information."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    level: int = Field(ge=0, le=9)
    school: str
    casting_time: str
    range: int = Field(default=5, description="The range of the spell, in feet")
    duration: str
    components: list[str]  # V, S, M
    description: str
    material_components: str | None = None
    prepared: bool = False


class SpecialAbility(BaseModel):
    """Special ability or feature for a character."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str = Field(description="Name of the special ability")
    description: str = Field(description="Description of the ability, including its effects")
    uses: str | None = Field(
        default=None,
        description="Description of usage limitations (e.g., '3/day', 'Recharges on short rest', 'Unlimited')"
    )
    uses_remaining: int | None = Field(
        default=None,
        ge=0,
        description="Number of uses remaining if the ability has limited uses"
    )


class Character(BaseModel):
    """Complete character sheet."""

    # Basic Info
    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    player_name: str | None = None
    character_class: CharacterClass
    race: Race
    background: str | None = None
    alignment: str | None = None
    description: str | None = (
        None  # A brief description of the character's appearance and demeanor.
    )
    bio: str | None = None  # The character's backstory, personality, and motivations.

    # Core Stats
    abilities: dict[str, AbilityScore] = Field(
        default_factory=lambda: {
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=10),
            "constitution": AbilityScore(score=10),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=10),
            "charisma": AbilityScore(score=10),
        }
    )

    # Combat Stats
    armor_class: int = 10
    hit_points_max: int = 1
    hit_points_current: int = 1
    temporary_hit_points: int = 0
    hit_dice_remaining: str = "1d8"
    death_saves_success: int = Field(ge=0, le=3, default=0)
    death_saves_failure: int = Field(ge=0, le=3, default=0)

    # Skills & Proficiencies
    proficiency_bonus: int = 2
    skills: dict[str, Skill] = Field(
        default_factory=lambda: {
            skill_name: Skill(name=skill_name, ability=ability, proficiency=SkillProficiency.NONE, modifier=0)
            for skill_name, ability in STANDARD_SKILLS.items()
        },
        description="Character's skills with proficiency tracking"
    )
    saving_throws: dict[str, SavingThrow] = Field(
        default_factory=lambda: {
            ability: SavingThrow(ability=ability, proficiency=SavingThrowProficiency.NONE, modifier=0)
            for ability in STANDARD_SAVING_THROWS
        },
        description="Character's saving throws with proficiency tracking"
    )

    # Deprecated fields for backward compatibility (will be migrated to new format)
    skill_proficiencies: list[str] | None = Field(
        default=None,
        exclude=True,
        description="DEPRECATED: Use 'skills' dict instead. Old format for skill proficiencies."
    )
    saving_throw_proficiencies: list[str] | None = Field(
        default=None,
        exclude=True,
        description="DEPRECATED: Use 'saving_throws' dict instead. Old format for saving throw proficiencies."
    )

    # Equipment
    inventory: list[Item] = Field(default_factory=list)
    equipment: dict[str, Item | None] = Field(
        default_factory=lambda: dict.fromkeys(["weapon_main", "weapon_off", "armor", "shield"])
    )

    # Spellcasting
    spellcasting_ability: str | None = None
    spell_slots: dict[int, int] = Field(default_factory=dict)  # level: max_slots
    spell_slots_used: dict[int, int] = Field(default_factory=dict)  # level: used_slots
    spells_known: list[Spell] = Field(default_factory=list)

    # Character Features
    features_and_traits: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    special_abilities: list[SpecialAbility] = Field(
        default_factory=list,
        description="Special abilities, racial features, class features, etc."
    )

    # Misc
    inspiration: bool = False
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NPC(BaseModel):
    """Non-player character."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    description: str | None = None
    bio: str | None = None  # The NPC's backstory, motivations, and secrets.
    race: str | None = None
    occupation: str | None = None
    location: str | None = None
    attitude: str | None = None  # friendly, neutral, hostile, etc.
    notes: str = ""
    stats: dict[str, Any] | None = None  # Combat stats if needed
    relationships: dict[str, str] = Field(default_factory=dict)  # character_name: relationship


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
    LIGHT_FOREST = "light_forest"
    FOREST = "forest"
    DENSE_FOREST = "dense_forest"
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
    """Geographic location or settlement."""

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

    # Map Integration (NEW)
    primary_map: Annotated[
        str | None,
        Field(description="Name of the HexMap this location appears on")
    ] = None

    hex_coordinate: Annotated[
        "HexCoordinate | None",
        Field(description="Position on the hex map")
    ] = None

    # Hierarchy (NEW)
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


class Quest(BaseModel):
    """Quest or mission."""

    id: str = Field(default_factory=lambda: random(length=8))
    title: str
    description: str
    giver: str | None = None  # NPC who gave the quest
    status: str = "active"  # active, completed, failed, on_hold
    objectives: list[str] = Field(default_factory=list)
    completed_objectives: list[str] = Field(default_factory=list)
    reward: str | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class CombatEncounter(BaseModel):
    """Combat encounter details."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    description: str
    enemies: list[str] = Field(default_factory=list)
    difficulty: str | None = None  # easy, medium, hard, deadly
    experience_value: int | None = None
    location: str | None = None
    status: str = "planned"  # planned, active, completed
    notes: str = ""


class SessionNote(BaseModel):
    """Session notes and summary."""

    id: str = Field(default_factory=lambda: random(length=8))
    session_number: int
    date: datetime = Field(default_factory=datetime.now)
    title: str | None = None
    summary: str
    events: list[str] = Field(default_factory=list)
    characters_present: list[str] = Field(default_factory=list)
    experience_gained: int | None = None
    treasure_found: list[str] = Field(default_factory=list)
    notes: str = ""


class Attack(BaseModel):
    """Details about a method of attack, including weapon type, to-hit modifiers, and damage"""

    weapon: Annotated[str, "name of the weapon or body part used to attack"]
    attack_roll_modifier: Annotated[int, "attack roll modifier to make it easier or harder to hit"]
    damage_roll: Annotated[str, "dice roll for damage, e.g. 2d4+2"]


class Monster(BaseModel):
    """Monster instance for combat encounters."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str = Field(description="Instance name for this specific monster")
    monster_type: str = Field(description="The type/species of monster (e.g., 'Goblin', 'Dragon')")
    size: str = "Medium"  # Tiny, Small, Medium, Large, Huge, Gargantuan
    creature_type: str = "humanoid"  # beast, fey, fiend, etc.
    alignment: str = "neutral"

    # Core Stats
    armor_class: int = 10
    hit_points_max: int = Field(ge=1, description="Maximum hit points")
    hit_points_current: int = Field(ge=0, description="Current hit points")
    hit_dice: str = "1d8"  # e.g., "2d8+2"
    speed: int = 30  # feet per round

    # Ability Scores
    abilities: dict[str, AbilityScore] = Field(
        default_factory=lambda: {
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=10),
            "constitution": AbilityScore(score=10),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=10),
            "charisma": AbilityScore(score=10),
        }
    )

    # Combat
    attacks: list[Attack] = Field(default_factory=list)
    damage_resistances: list[str] = Field(default_factory=list)
    damage_immunities: list[str] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)

    # Skills & Senses
    saving_throws: dict[str, int] = Field(
        default_factory=dict,
        description="Saving throw modifiers for abilities with proficiency. Key: ability name (e.g., 'dexterity'), Value: total modifier. Only include abilities with proficiency; others use base ability modifier."
    )
    skills: dict[str, int] = Field(
        default_factory=dict,
        description="Skill modifiers for skills with proficiency. Key: skill name (e.g., 'stealth'), Value: total modifier. Only include skills with proficiency; others use base ability modifier."
    )
    senses: list[str] = Field(
        default_factory=list,
        description="Special senses the monster has (e.g., 'darkvision 60 ft.', 'blindsight 30 ft.')"
    )
    languages: list[str] = Field(default_factory=list)

    # Special Abilities
    special_abilities: list[str] = Field(default_factory=list)
    legendary_actions: list[str] = Field(default_factory=list)
    legendary_actions_per_turn: int = 0

    # Challenge and Experience
    challenge_rating: str = "1/8"  # e.g., "1/4", "2", "15"
    experience_value: int = 25
    proficiency_bonus: int = 2

    # Metadata
    description: str | None = None
    notes: str = ""
    location: str | None = None  # Where this monster instance is located
    status: str = "alive"  # alive, dead, unconscious, etc.
    created_at: datetime = Field(default_factory=datetime.now)


class CombatParticipant(BaseModel):
    """Key stats for a participant in combat"""

    name: Annotated[str, "name of the character or monster"]
    initiative: Annotated[int, "initiave value, used to determine combat order"]
    hp: Annotated[int, "current hit points"]
    ac: Annotated[int, "current armor class based on currently equipped armor"]
    speed: Annotated[int, "feet this character may move per combat round"]
    attacks: list[Attack] = Field(default_factory=list)


class GameState(BaseModel):
    """Current state of the game."""

    campaign_name: str
    current_session: int = 1
    current_date_in_game: str | None = None
    current_location: str | None = None
    active_quests: list[str] = Field(default_factory=list)
    party_level: int = 1
    party_funds: str = "0 gp"
    initiative_order: list[CombatParticipant] = Field(default_factory=list)
    in_combat: bool = False
    current_turn: str | None = None
    monsters: list[Monster] = Field(
        default_factory=list, description="Monsters the party is currently facing or aware of"
    )
    modes: list[str] = Field(
        default_factory=lambda: ["setup"],
        description="Current active modes. First mode is primary. Combat should be listed first if active."
    )
    notes: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


class Campaign(BaseModel):
    """Main campaign container."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    description: str
    dm_name: str | None = None
    setting: str | Path | None = None
    characters: dict[str, Character] = Field(default_factory=dict)
    npcs: dict[str, NPC] = Field(default_factory=dict)
    locations: dict[str, Location] = Field(default_factory=dict)
    quests: dict[str, Quest] = Field(default_factory=dict)
    encounters: dict[str, CombatEncounter] = Field(default_factory=dict)
    sessions: list[SessionNote] = Field(default_factory=list)
    hex_maps: dict[str, "HexMap"] = Field(
        default_factory=dict,
        description="Hex maps for outdoor/wilderness areas, indexed by map name"
    )
    game_state: GameState
    world_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)

    # Location Hierarchy (NEW)
    root_location_id: Annotated[
        str | None,
        Field(description="ID of the root location representing the entire game world")
    ] = None

    def get_setting(self) -> str:
        """Return the setting details for the active campaign."""
        if isinstance(self.setting, str):
            return self.setting
        elif isinstance(self.setting, Path):
            setting_txt = self.setting.read_text()
            setting_txt += f"\n\n(From file: {str(self.setting)})"
            return setting_txt
        elif not self.setting:
            return "(⚠️ No setting details have been set for this campaign!)"
        else:
            e = TypeError(f"❌ Unknown setting type: {type(self.setting)}")
            raise e


# Event types for the adventure log
class EventType(str, Enum):
    COMBAT = "combat"
    ROLEPLAY = "roleplay"
    EXPLORATION = "exploration"
    QUEST = "quest"
    CHARACTER = "character"
    WORLD = "world"
    SESSION = "session"


# ========================================
# Hex Mapping Models
# ========================================

class TerrainType(str, Enum):
    """Terrain types for hexagonal map cells."""
    # Grasslands and vegetation
    GRASS = "grass"
    SCRUB = "scrub"
    PLAINS = "plains"

    # Forests
    FOREST = "forest"
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
    WASTELAND = "wasteland"

    # Cold
    TUNDRA = "tundra"
    GLACIER = "glacier"

    # Special
    VOLCANIC = "volcanic"
    COASTAL = "coastal"
    WATER = "water"

    # Populated
    URBAN = "urban"
    FARMLAND = "farmland"

class HexSide(str, Enum):
    """Sides of a hex for roads, rivers, and POI positioning."""
    NORTH = "north"
    NORTHEAST = "northeast"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    NORTHWEST = "northwest"
    CENTER = "center"


class POIType(str, Enum):
    """Types of points of interest."""
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    DUNGEON = "dungeon"
    RUINS = "ruins"
    CASTLE = "castle"
    TEMPLE = "temple"
    TOWER = "tower"
    CAVE = "cave"
    INN = "inn"
    CAMP = "camp"
    SHRINE = "shrine"
    LANDMARK = "landmark"


class HexCoordinate(BaseModel):
    """Offset coordinate system for hexagonal grids (odd-q offset)."""
    x: Annotated[int, Field(description="Column coordinate (0=leftmost, increases eastward)")]
    y: Annotated[int, Field(description="Row coordinate (0=topmost, increases southward)")]

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if not isinstance(other, HexCoordinate):
            return False
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
        str | None,
        Field(description="Description of where the river can be forded, if applicable")
    ] = None
    notes: str = ""


class PointOfInterest(BaseModel):
    """A point of interest within a hex."""

    id: str = Field(default_factory=lambda: random(length=8))
    name: str
    poi_type: POIType
    description: str
    location_id: Annotated[
        str | None,
        Field(description="ID of associated Location object if this POI has detailed data")
    ] = None
    discovered: Annotated[bool, Field(description="Whether the party has discovered this POI")] = False
    position: Annotated[
        HexSide,
        Field(description="Position within hex (CENTER or a specific side/edge)")
    ] = HexSide.CENTER
    notes: str = ""


class Hex(BaseModel):
    """A single hex on the map."""

    coordinate: HexCoordinate
    terrain: TerrainType
    roads: list[Road] = Field(default_factory=list)
    rivers: list[River] = Field(default_factory=list)
    pois: list[PointOfInterest] = Field(default_factory=list)
    elevation: Annotated[
        int | None,
        Field(description="Elevation in meters above sea level")
    ] = None
    explored: Annotated[bool, Field(description="Whether the party has explored this hex")] = False
    visibility: Annotated[
        str,
        Field(description="Visibility category (e.g., 'clear', 'obscured', 'hidden')")
    ] = "clear"
    notes: str = ""


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
        dict[str, int] | None,
        Field(description="Map bounds as {min_x, max_x, min_y, max_y}")
    ] = None
    notes: str = ""

    def _coord_key(self, coord: HexCoordinate) -> str:
        """Generate dictionary key from coordinate."""
        return f"{coord.x},{coord.y}"

    def get_hex(self, coord: HexCoordinate) -> Hex | None:
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

    def get_neighbors(self, coord: HexCoordinate) -> dict[HexSide, Hex | None]:
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


class AdventureEvent(BaseModel):
    """Individual event in the adventure log."""

    id: str = Field(default_factory=lambda: random(length=8))
    campaign: Annotated[str, "Name of the active campaign in which this event occurred"]
    event_type: EventType
    title: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.now)
    session_number: Annotated[int | None, "Active session number when this event occurred"] = None
    characters_involved: list[str] = Field(default_factory=list)
    location: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(ge=1, le=5, default=3)  # 1=minor, 5=major


class TranscriptEntry(BaseModel):
    """Individual entry in a transcript."""

    transcript_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    player_entry: str
    game_response: str


class Transcript(BaseModel):
    """Transcript of a session within a campaign (OLD FORMAT - kept for backward compatibility)"""

    id: str = Field(default_factory=lambda: random(length=8))
    campaign: Annotated[str, "Name of the campaign associated with this transcript"]
    session_number: Annotated[int, "Session number described by this transcript"]
    entries: list[TranscriptEntry]


# New tree-based transcript models

class TranscriptNode(BaseModel):
    """Base class for all transcript tree nodes."""

    id: str = Field(default_factory=lambda: random(length=8))
    node_type: str  # Will be overridden by subclasses with Literal

    # Optional metadata
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class ResponseText(BaseModel):
    """Text response from the LLM."""

    type: str = Field(default="text")
    content: str


class InteractionToolCall(BaseModel):
    """Details of a tool call made during interaction."""

    name: str
    id: str
    input: dict[str, Any]
    response: str


class ResponseTools(BaseModel):
    """Tool call response from the LLM."""

    type: str = Field(default="tools")
    calls: list[InteractionToolCall]


# Union type for responses
TranscriptInteractionResponse = ResponseText | ResponseTools


class TranscriptInteraction(TranscriptNode):
    """Leaf node representing single user-LLM exchange."""

    node_type: str = Field(default="interaction")
    user_text: str
    responses: list[TranscriptInteractionResponse]

    # Optional metadata
    character_speaking: str | None = None
    importance: int = Field(ge=1, le=5, default=3)


class TranscriptCombat(TranscriptNode):
    """Interior node representing a combat encounter."""

    node_type: str = Field(default="combat")

    # Combat summary
    participants: list[str]
    result: str
    summary: str

    # Detailed combat log
    actions: list[TranscriptInteraction] = Field(default_factory=list)

    # Combat metadata
    location: str | None = None
    rounds: int | None = None
    casualties: list[str] = Field(default_factory=list)


class TranscriptAdventure(TranscriptNode):
    """Interior node representing a story arc or quest."""

    node_type: str = Field(default="adventure")

    # Adventure summary
    title: str | None = None
    summary: str

    # Adventure contents - Forward reference for nested adventures
    actions: list["TranscriptInteraction | TranscriptCombat | TranscriptAdventure"] = Field(default_factory=list)

    # Adventure metadata
    quest_id: str | None = None
    locations: list[str] = Field(default_factory=list)
    npcs_met: list[str] = Field(default_factory=list)
    rewards: list[str] = Field(default_factory=list)


class TranscriptTree(TranscriptNode):
    """Root node of the transcript tree (NEW FORMAT)."""

    node_type: str = Field(default="transcript")

    campaign: str
    session_number: int

    # Children - can be any mix of interactions, combats, adventures
    children: list[TranscriptInteraction | TranscriptCombat | TranscriptAdventure] = Field(default_factory=list)

    # Current parent tracking
    current_parent_id: str | None = None

    # Metadata
    characters_present: list[str] = Field(default_factory=list)


__all__ = [
    "AbilityScore",
    "SavingThrowProficiency",
    "SkillProficiency",
    "SavingThrow",
    "Skill",
    "STANDARD_SKILLS",
    "STANDARD_SAVING_THROWS",
    "CharacterClass",
    "Race",
    "Item",
    "Spell",
    "Character",
    "NPC",
    "Monster",
    "Location",
    "LocationScale",
    "LocationType",
    "Quest",
    "CombatEncounter",
    "SessionNote",
    "GameState",
    "Campaign",
    "EventType",
    "AdventureEvent",
    "GameStats",
    "Attack",
    "CombatParticipant",
    "TranscriptEntry",
    "Transcript",
    # New tree-based transcript models
    "TranscriptNode",
    "ResponseText",
    "InteractionToolCall",
    "ResponseTools",
    "TranscriptInteractionResponse",
    "TranscriptInteraction",
    "TranscriptCombat",
    "TranscriptAdventure",
    "TranscriptTree",
    # Hex mapping models
    "TerrainType",
    "HexSide",
    "POIType",
    "HexCoordinate",
    "Road",
    "River",
    "PointOfInterest",
    "Hex",
    "HexMap",
]
