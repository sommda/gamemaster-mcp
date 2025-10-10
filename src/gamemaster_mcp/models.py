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

from .prompts import (
    core_prompt,
    setup_prompt,
    outdoor_prompt,
    dungeon_prompt,
    town_prompt,
    combat_prompt
)

from .logutils import logger

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
    skill_proficiencies: list[str] = Field(default_factory=list)
    saving_throw_proficiencies: list[str] = Field(default_factory=list)

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
    saving_throws: dict[str, int] = Field(default_factory=dict)  # ability: modifier
    skills: dict[str, int] = Field(default_factory=dict)  # skill: modifier
    senses: list[str] = Field(default_factory=list)  # darkvision, blindsight, etc.
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
    game_state: GameState
    world_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)

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


class TranscriptTool(BaseModel):
    """Tool call entry in a transcript."""

    transcript_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_name: Annotated[str, "Name of the tool that was called"]
    tool_params: Annotated[dict[str, Any], "Parameters passed to the tool"]
    tool_response: Annotated[str, "Response returned by the tool"]


class Transcript(BaseModel):
    """Transcript of a session within a campaign"""

    id: str = Field(default_factory=lambda: random(length=8))
    campaign: Annotated[str, "Name of the campaign associated with this transcript"]
    session_number: Annotated[int, "Session number described by this transcript"]
    entries: list[TranscriptEntry | TranscriptTool]


__all__ = [
    "AbilityScore",
    "CharacterClass",
    "Race",
    "Item",
    "Spell",
    "Character",
    "NPC",
    "Monster",
    "Location",
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
    "TranscriptTool",
    "Transcript",
]
