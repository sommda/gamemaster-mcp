"""
D&D MCP Server
A comprehensive D&D campaign management server built with modern FastMCP framework.
"""

import argparse
import logging
import os
import random
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.prompts.prompt import Message
from pydantic import Field

from .models import (
    AVAILABLE_MODES,
    MODE_PROMPTS,
    NPC,
    AbilityScore,
    AdventureEvent,
    Campaign,
    Character,
    CharacterClass,
    CombatParticipant,
    EventType,
    Item,
    Location,
    Monster,
    Quest,
    Race,
    SessionNote,
    Transcript,
)

from .prompts import core_prompt, setup_prompt

from .storage import DnDStorage
from .tool_with_logging import tool_with_logging

logger = logging.getLogger("gamemaster-mcp")

logging.basicConfig(
    level=logging.INFO,
)

if not load_dotenv():
    logger.warning(
        "❌ .env file invalid or not found! Please see README.md for instructions. Using project root instead."
    )

data_path = Path(os.getenv("GAMEMASTER_STORAGE_DIR", "")).resolve()
logger.debug(f"📂 Data path: {data_path}")


# Initialize storage and FastMCP server
storage = DnDStorage(data_dir=data_path)
logger.debug("✅ Storage layer initialized")

mcp: FastMCP = FastMCP(name="D&D Campaign Manager")
logger.debug("✅ Server initialized, registering tools")


# Storage override for tests
def override_storage(ovr_storage: DnDStorage) -> None:
    global storage
    storage = ovr_storage


# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------


# Campaign management tools
@tool_with_logging(mcp, tags=["mode:setup"])
def create_campaign(
    name: Annotated[str, Field(description="Campaign name")],
    description: Annotated[
        str, Field(description="Brief decription of the campaign, or a tagline")
    ],
    dm_name: Annotated[str | None, Field(description="Dungeon Master name")] = None,
    setting: Annotated[
        str | Path | None,
        Field(
            description="""
        Campaign setting - a full description of the setting of the campaign in markdown format, or the path to a `.txt` or `.md` file containing the same.
        """
        ),
    ] = None,
) -> str:
    """Create a new D&D campaign."""
    campaign = storage.create_campaign(
        name=name, description=description, dm_name=dm_name, setting=setting
    )
    return f"🌟 Created campaign: '{campaign.name} and set as active 🌟'"


@tool_with_logging(mcp, tags=["mode:any"])
def get_campaign_info() -> str:
    """Get information about the current campaign."""
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    info = {
        "name": campaign.name,
        "description": campaign.description,
        "dm_name": campaign.dm_name,
        "setting": campaign.get_setting(),
        "character_count": len(campaign.characters),
        "npc_count": len(campaign.npcs),
        "location_count": len(campaign.locations),
        "quest_count": len(campaign.quests),
        "session_count": len(campaign.sessions),
        "current_session": campaign.game_state.current_session,
        "current_location": campaign.game_state.current_location,
        "party_level": campaign.game_state.party_level,
        "in_combat": campaign.game_state.in_combat,
    }

    return f"**Campaign: {campaign.name}**\n\n" + "\n".join(
        [f"**{k.replace('_', ' ').title()}:** {v}" for k, v in info.items()]
    )


@tool_with_logging(mcp, tags=["mode:setup"])
def list_campaigns() -> str:
    """List all available campaigns."""
    campaigns = storage.list_campaigns()
    if not campaigns:
        return f"❌ No campaigns found in {storage.data_dir}!"

    current = storage.get_current_campaign()
    current_name = current.name if current else None

    campaign_list = []
    for campaign in campaigns:
        marker = " (current)" if campaign == current_name else ""
        campaign_list.append(f"• {campaign}{marker}")

    return "**Available Campaigns:**\n" + "\n".join(campaign_list)


@tool_with_logging(mcp, tags=["mode:setup"])
def load_campaign(name: Annotated[str, Field(description="Campaign name to load")]) -> str:
    """Load a specific campaign."""
    campaign = storage.load_campaign(name)
    return f"📖 Loaded campaign: '{campaign.name}'. Campaign is now active!"


# Campaign resources
@mcp.resource("resource://campaigns/{campaign_name}")
def get_campaign(campaign_name: str) -> Campaign:
    return storage.get_campaign(campaign_name)


@mcp.resource("resource://campaigns")
def get_campaigns() -> list[str]:
    return storage.list_campaigns()


@mcp.resource("resource://current_campaign")
def get_current_campaign() -> str:
    return storage.get_current_campaign().name


# Character resources
@mcp.resource("resource://characters/{character_name}")
def get_character_resource(character_name: str) -> Character:
    character = storage.get_character(character_name)
    if not character:
        raise FileNotFoundError(f"Character '{character_name}' not found")
    return character


@mcp.resource("resource://campaigns/{campaign_name}/characters")
def get_campaign_characters(campaign_name: str) -> list[Character]:
    try:
        campaign = storage.get_campaign(campaign_name)
        return list(campaign.characters.values())
    except FileNotFoundError:
        raise FileNotFoundError(f"Campaign '{campaign_name}' not found")


@mcp.resource("resource://current_campaign/characters")
def get_current_campaign_characters() -> list[Character]:
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return []
    return list(current_campaign.characters.values())


# Character Management Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def create_character(
    name: Annotated[str, Field(description="Character name")],
    character_class: Annotated[str, Field(description="Character class")],
    class_level: Annotated[int, Field(description="Class level", ge=1, le=20)],
    race: Annotated[str, Field(description="Character race")],
    player_name: Annotated[
        str | None, Field(description="The name of the player in control of this character")
    ] = None,
    description: Annotated[
        str | None,
        Field(description="A brief description of the character's appearance and demeanor."),
    ] = None,
    bio: Annotated[
        str | None, Field(description="The character's backstory, personality, and motivations.")
    ] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
    dexterity: Annotated[int, Field(description="Dexterity score", ge=1, le=30)] = 10,
    constitution: Annotated[int, Field(description="Constitution score", ge=1, le=30)] = 10,
    intelligence: Annotated[int, Field(description="Intelligence score", ge=1, le=30)] = 10,
    wisdom: Annotated[int, Field(description="Wisdom score", ge=1, le=30)] = 10,
    charisma: Annotated[int, Field(description="Charisma score", ge=1, le=30)] = 10,
) -> str:
    """Create a new player character."""
    # Build ability scores
    abilities = {
        "strength": AbilityScore(score=strength),
        "dexterity": AbilityScore(score=dexterity),
        "constitution": AbilityScore(score=constitution),
        "intelligence": AbilityScore(score=intelligence),
        "wisdom": AbilityScore(score=wisdom),
        "charisma": AbilityScore(score=charisma),
    }

    character = Character(
        name=name,
        player_name=player_name,
        character_class=CharacterClass(name=character_class, level=class_level),
        race=Race(name=race),
        background=background,
        alignment=alignment,
        abilities=abilities,
        description=description,
        bio=bio,
    )

    storage.add_character(character)
    return f"Created character '{character.name}' (Level {character.character_class.level} {character.race.name} {character.character_class.name})"


@tool_with_logging(mcp)
def get_character(name_or_id: Annotated[str, Field(description="Character name or ID")]) -> str:
    """Get detailed character information."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    char_info = f"""**{character.name}** (`{character.id}`)
Level {character.character_class.level} {character.race.name} {character.character_class.name}
**Player:** {character.player_name or "N/A"}
**Background:** {character.background or "N/A"}
**Alignment:** {character.alignment or "N/A"}

**Description:** {character.description or "No description provided."}
**Bio:** {character.bio or "No bio provided."}

**Ability Scores:**
• STR: {character.abilities["strength"].score} ({character.abilities["strength"].mod:+d})
• DEX: {character.abilities["dexterity"].score} ({character.abilities["dexterity"].mod:+d})
• CON: {character.abilities["constitution"].score} ({character.abilities["constitution"].mod:+d})
• INT: {character.abilities["intelligence"].score} ({character.abilities["intelligence"].mod:+d})
• WIS: {character.abilities["wisdom"].score} ({character.abilities["wisdom"].mod:+d})
• CHA: {character.abilities["charisma"].score} ({character.abilities["charisma"].mod:+d})

**Combat Stats:**
• AC: {character.armor_class}
• HP: {character.hit_points_current}/{character.hit_points_max}
• Temp HP: {character.temporary_hit_points}

**Inventory:** {len(character.inventory)} items
"""

    return char_info


@tool_with_logging(mcp)
def update_character(
    name_or_id: Annotated[str, Field(description="The name or ID of the character to update.")],
    name: Annotated[
        str | None,
        Field(
            description="New character name. If you change this, you must use the character's ID to identify them."
        ),
    ] = None,
    player_name: Annotated[
        str | None, Field(description="The name of the player in control of this character")
    ] = None,
    description: Annotated[
        str | None,
        Field(description="A brief description of the character's appearance and demeanor."),
    ] = None,
    bio: Annotated[
        str | None, Field(description="The character's backstory, personality, and motivations.")
    ] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    hit_points_current: Annotated[int | None, Field(description="Current hit points", ge=0)] = None,
    hit_points_max: Annotated[int | None, Field(description="Maximum hit points", ge=1)] = None,
    temporary_hit_points: Annotated[
        int | None, Field(description="Temporary hit points", ge=0)
    ] = None,
    armor_class: Annotated[int | None, Field(description="Armor class")] = None,
    inspiration: Annotated[bool | None, Field(description="Inspiration status")] = None,
    notes: Annotated[str | None, Field(description="Additional notes about the character")] = None,
    strength: Annotated[int | None, Field(description="Strength score", ge=1, le=30)] = None,
    dexterity: Annotated[int | None, Field(description="Dexterity score", ge=1, le=30)] = None,
    constitution: Annotated[
        int | None, Field(description="Constitution score", ge=1, le=30)
    ] = None,
    intelligence: Annotated[
        int | None, Field(description="Intelligence score", ge=1, le=30)
    ] = None,
    wisdom: Annotated[int | None, Field(description="Wisdom score", ge=1, le=30)] = None,
    charisma: Annotated[int | None, Field(description="Charisma score", ge=1, le=30)] = None,
) -> str:
    """Update a character's properties."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    updates = {
        k: v for k, v in locals().items() if v is not None and k not in ["name_or_id", "character"]
    }
    updated_fields = [f"{key.replace('_', ' ')}: {value}" for key, value in updates.items()]

    if not updates:
        return f"No updates provided for {character.name}."

    storage.update_character(str(character.id), **updates)

    return f"Updated {character.name}'s properties: {'; '.join(updated_fields)}."


@tool_with_logging(mcp, tags=["mode:setup"])
def bulk_update_characters(
    names_or_ids: Annotated[
        list[str], Field(description="List of character names or IDs to update.")
    ],
    hp_change: Annotated[
        int | None, Field(description="Amount to change current HP by (positive or negative).")
    ] = None,
    temp_hp_change: Annotated[
        int | None, Field(description="Amount to change temporary HP by (positive or negative).")
    ] = None,
    strength_change: Annotated[
        int | None, Field(description="Amount to change strength by.")
    ] = None,
    dexterity_change: Annotated[
        int | None, Field(description="Amount to change dexterity by.")
    ] = None,
    constitution_change: Annotated[
        int | None, Field(description="Amount to change constitution by.")
    ] = None,
    intelligence_change: Annotated[
        int | None, Field(description="Amount to change intelligence by.")
    ] = None,
    wisdom_change: Annotated[int | None, Field(description="Amount to change wisdom by.")] = None,
    charisma_change: Annotated[
        int | None, Field(description="Amount to change charisma by.")
    ] = None,
) -> str:
    """Update properties for multiple characters at once by a given amount."""
    updates_log = []
    not_found_log = []

    changes = {
        "hp_change": hp_change,
        "temp_hp_change": temp_hp_change,
        "strength_change": strength_change,
        "dexterity_change": dexterity_change,
        "constitution_change": constitution_change,
        "intelligence_change": intelligence_change,
        "wisdom_change": wisdom_change,
        "charisma_change": charisma_change,
    }

    # Filter out None changes
    active_changes = {k: v for k, v in changes.items() if v is not None}
    if not active_changes:
        return "No changes specified."

    for name_or_id in names_or_ids:
        character = storage.get_character(name_or_id)
        if not character:
            not_found_log.append(name_or_id)
            continue

        char_updates = {}
        char_log = [f"{character.name}:"]

        if hp_change is not None:
            new_hp = character.hit_points_current + hp_change
            # Clamp HP between 0 and max HP
            new_hp = max(0, min(new_hp, character.hit_points_max))
            char_updates["hit_points_current"] = new_hp
            char_log.append(f"HP -> {new_hp}")

        if temp_hp_change is not None:
            new_temp_hp = character.temporary_hit_points + temp_hp_change
            # Temp HP cannot be negative
            new_temp_hp = max(0, new_temp_hp)
            char_updates["temporary_hit_points"] = new_temp_hp
            char_log.append(f"Temp HP -> {new_temp_hp}")

        ability_changes = {
            "strength": strength_change,
            "dexterity": dexterity_change,
            "constitution": constitution_change,
            "intelligence": intelligence_change,
            "wisdom": wisdom_change,
            "charisma": charisma_change,
        }
        abilities_modified = False
        for ability, change in ability_changes.items():
            if change is not None:
                new_score = character.abilities[ability].score + change
                new_score = max(1, min(new_score, 30))  # Clamp score
                character.abilities[ability].score = new_score
                char_log.append(f"{ability.capitalize()} -> {new_score}")
                abilities_modified = True

        if char_updates or abilities_modified:
            if char_updates:
                storage.update_character(str(character.id), **char_updates)
            elif abilities_modified:
                # Abilities are modified in place, just need to trigger a save
                storage._save_campaign()
            updates_log.append(" ".join(char_log))

    response_parts = []
    if updates_log:
        response_parts.append("Characters updated:\n" + "\n".join(updates_log))
    if not_found_log:
        response_parts.append(f"Characters not found: {', '.join(not_found_log)}")

    return "\n".join(response_parts) if response_parts else "No characters found to update."


@tool_with_logging(mcp, tags=["mode:any"])
def add_item_to_character(
    character_name_or_id: Annotated[
        str, Field(description="Name or ID of the character to receive the item.")
    ],
    item_name: Annotated[str, Field(description="Item name")],
    description: Annotated[str | None, Field(description="Item description")] = None,
    quantity: Annotated[int, Field(description="Quantity", ge=1)] = 1,
    item_type: Annotated[
        Literal["weapon", "armor", "consumable", "misc"], Field(description="Item type")
    ] = "misc",
    weight: Annotated[float | None, Field(description="Item weight", ge=0)] = None,
    value: Annotated[str | None, Field(description="Item value (e.g., '50 gp')")] = None,
) -> str:
    """Add an item to a character's inventory."""
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    item = Item(
        name=item_name,
        description=description,
        quantity=quantity,
        item_type=item_type,
        weight=weight,
        value=value,
    )

    character.inventory.append(item)
    storage.update_character(str(character.id), inventory=character.inventory)

    return f"Added {item.quantity}x {item.name} to {character.name}'s inventory"


@tool_with_logging(mcp, tags=["mode:any"])
def list_characters() -> str:
    """List all characters in the current campaign."""
    characters = storage.list_characters()
    if not characters:
        return "No characters in the current campaign."

    char_list = []
    for char_name in characters:
        char = storage.get_character(char_name)
        if char:
            char_list.append(
                f"• {char.name} (Level {char.character_class.level} {char.race.name} {char.character_class.name})"
            )

    return "**Characters:**\n" + "\n".join(char_list)


# NPC Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_npc(
    name: Annotated[str, Field(description="NPC name")],
    description: Annotated[
        str | None, Field(description="A brief, public description of the NPC.")
    ] = None,
    bio: Annotated[
        str | None, Field(description="A detailed, private bio for the NPC, including secrets.")
    ] = None,
    race: Annotated[str | None, Field(description="NPC race")] = None,
    occupation: Annotated[str | None, Field(description="NPC occupation")] = None,
    location: Annotated[str | None, Field(description="Current location")] = None,
    attitude: Annotated[
        Literal["friendly", "neutral", "hostile", "unknown"] | None,
        Field(description="Attitude towards party"),
    ] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new NPC."""
    npc = NPC(
        name=name,
        description=description,
        bio=bio,
        race=race,
        occupation=occupation,
        location=location,
        attitude=attitude,
        notes=notes,
    )

    storage.add_npc(npc)
    return f"Created NPC '{npc.name}'"


@tool_with_logging(mcp, tags=["mode:any"])
def get_npc(name: Annotated[str, Field(description="NPC name")]) -> str:
    """Get NPC information."""
    npc = storage.get_npc(name)
    if not npc:
        return f"NPC '{name}' not found."

    npc_info = f"""**{npc.name}** (`{npc.id}`)
**Race:** {npc.race or "Unknown"}
**Occupation:** {npc.occupation or "Unknown"}
**Location:** {npc.location or "Unknown"}
**Attitude:** {npc.attitude or "Neutral"}

**Description:** {npc.description or "No description available."}
**Bio:** {npc.bio or "No bio available."}

**Notes:** {npc.notes or "No additional notes."}
"""

    return npc_info


@tool_with_logging(mcp, tags=["mode:any"])
def list_npcs() -> str:
    """List all NPCs in the current campaign."""
    npcs = storage.list_npcs()
    if not npcs:
        return "No NPCs in the current campaign."

    npc_list = []
    for npc_name in npcs:
        npc = storage.get_npc(npc_name)
        if npc:
            location = f" ({npc.location})" if npc.location else ""
            npc_list.append(f"• {npc.name}{location}")

    return "**NPCs:**\n" + "\n".join(npc_list)


# Monster Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_monster(
    name: Annotated[str, Field(description="Instance name for this specific monster")],
    monster_type: Annotated[
        str, Field(description="The type/species of monster (e.g., 'Goblin', 'Dragon')")
    ],
    hit_points_max: Annotated[int, Field(description="Maximum hit points", ge=1)],
    hit_points_current: Annotated[int | None, Field(description="Current hit points")] = None,
    armor_class: Annotated[int, Field(description="Armor class", ge=1)] = 10,
    size: Annotated[str, Field(description="Monster size")] = "Medium",
    creature_type: Annotated[str, Field(description="Creature type")] = "humanoid",
    alignment: Annotated[str, Field(description="Monster alignment")] = "neutral",
    speed: Annotated[int, Field(description="Speed in feet per round")] = 30,
    challenge_rating: Annotated[
        str, Field(description="Challenge rating (e.g., '1/4', '2', '15')")
    ] = "1/8",
    experience_value: Annotated[int, Field(description="Experience points awarded", ge=0)] = 25,
    description: Annotated[str | None, Field(description="Monster description")] = None,
    location: Annotated[str | None, Field(description="Where this monster is located")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
    dexterity: Annotated[int, Field(description="Dexterity score", ge=1, le=30)] = 10,
    constitution: Annotated[int, Field(description="Constitution score", ge=1, le=30)] = 10,
    intelligence: Annotated[int, Field(description="Intelligence score", ge=1, le=30)] = 10,
    wisdom: Annotated[int, Field(description="Wisdom score", ge=1, le=30)] = 10,
    charisma: Annotated[int, Field(description="Charisma score", ge=1, le=30)] = 10,
) -> str:
    """Create a new monster and add it to the current game state."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return "No active campaign. Please create or load a campaign first."

    # Build ability scores
    abilities = {
        "strength": AbilityScore(score=strength),
        "dexterity": AbilityScore(score=dexterity),
        "constitution": AbilityScore(score=constitution),
        "intelligence": AbilityScore(score=intelligence),
        "wisdom": AbilityScore(score=wisdom),
        "charisma": AbilityScore(score=charisma),
    }

    # Set current HP to max if not provided
    if hit_points_current is None:
        hit_points_current = hit_points_max

    monster = Monster(
        name=name,
        monster_type=monster_type,
        hit_points_max=hit_points_max,
        hit_points_current=hit_points_current,
        armor_class=armor_class,
        size=size,
        creature_type=creature_type,
        alignment=alignment,
        speed=speed,
        challenge_rating=challenge_rating,
        experience_value=experience_value,
        description=description,
        location=location,
        abilities=abilities,
    )

    # Add monster to game state
    current_campaign.game_state.monsters.append(monster)
    storage._save_campaign()

    return f"Created monster '{monster.name}' ({monster.monster_type}) with {monster.hit_points_current}/{monster.hit_points_max} HP"


@tool_with_logging(mcp, tags=["mode:any"])
def get_monster(name: Annotated[str, Field(description="Monster name")]) -> str:
    """Get monster information."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return "No active campaign. Please create or load a campaign first."

    monster = None
    for m in current_campaign.game_state.monsters:
        if m.name.lower() == name.lower():
            monster = m
            break

    if not monster:
        return f"Monster '{name}' not found in current game state."

    # Format attacks
    attacks_info = ""
    if monster.attacks:
        attacks_list = []
        for attack in monster.attacks:
            attacks_list.append(
                f"  • {attack.weapon}: +{attack.attack_roll_modifier} to hit, {attack.damage_roll} damage"
            )
        attacks_info = "\n**Attacks:**\n" + "\n".join(attacks_list)

    # Format special abilities
    abilities_info = ""
    if monster.special_abilities:
        abilities_info = f"\n**Special Abilities:** {', '.join(monster.special_abilities)}"

    # Format resistances/immunities
    resist_info = ""
    if monster.damage_resistances:
        resist_info += f"\n**Damage Resistances:** {', '.join(monster.damage_resistances)}"
    if monster.damage_immunities:
        resist_info += f"\n**Damage Immunities:** {', '.join(monster.damage_immunities)}"
    if monster.condition_immunities:
        resist_info += f"\n**Condition Immunities:** {', '.join(monster.condition_immunities)}"

    monster_info = f"""**{monster.name}** ({monster.monster_type}) - `{monster.id}`
**Size/Type:** {monster.size} {monster.creature_type}
**Alignment:** {monster.alignment}
**AC:** {monster.armor_class} **HP:** {monster.hit_points_current}/{monster.hit_points_max}
**Speed:** {monster.speed} ft **Status:** {monster.status}
**Challenge Rating:** {monster.challenge_rating} ({monster.experience_value} XP)

**Ability Scores:**
STR {monster.abilities["strength"].score} ({monster.abilities["strength"].mod:+d})
DEX {monster.abilities["dexterity"].score} ({monster.abilities["dexterity"].mod:+d})
CON {monster.abilities["constitution"].score} ({monster.abilities["constitution"].mod:+d})
INT {monster.abilities["intelligence"].score} ({monster.abilities["intelligence"].mod:+d})
WIS {monster.abilities["wisdom"].score} ({monster.abilities["wisdom"].mod:+d})
CHA {monster.abilities["charisma"].score} ({monster.abilities["charisma"].mod:+d})
{attacks_info}{abilities_info}{resist_info}

**Location:** {monster.location or "Unknown"}
**Description:** {monster.description or "No description available."}
"""

    if monster.notes:
        monster_info += f"\n**Notes:** {monster.notes}"

    return monster_info


@tool_with_logging(mcp, tags=["mode:any"])
def list_monsters() -> str:
    """List all monsters in the current game state."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        return "No active campaign. Please create or load a campaign first."

    monsters = current_campaign.game_state.monsters
    if not monsters:
        return "No monsters in the current game state."

    monster_list = []
    for monster in monsters:
        status_info = f" [{monster.status}]" if monster.status != "alive" else ""
        hp_info = f" ({monster.hit_points_current}/{monster.hit_points_max} HP)"
        location_info = f" at {monster.location}" if monster.location else ""
        monster_list.append(
            f"• {monster.name} ({monster.monster_type}){status_info}{hp_info}{location_info}"
        )

    return "**Active Monsters:**\n" + "\n".join(monster_list)


# Location Management Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def create_location(
    name: Annotated[str, Field(description="Location name")],
    location_type: Annotated[
        str, Field(description="Type of location (city, town, village, dungeon, etc.)")
    ],
    description: Annotated[str, Field(description="Location description")],
    population: Annotated[int | None, Field(description="Population (if applicable)", ge=0)] = None,
    government: Annotated[str | None, Field(description="Government type")] = None,
    notable_features: Annotated[list[str] | None, Field(description="Notable features")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new location."""
    location = Location(
        name=name,
        location_type=location_type,
        description=description,
        population=population,
        government=government,
        notable_features=notable_features or [],
        notes=notes,
    )

    storage.add_location(location)
    return f"Created location '{location.name}' ({location.location_type})"


@tool_with_logging(mcp, tags=["mode:any"])
def get_location(name: Annotated[str, Field(description="Location name")]) -> str:
    """Get location information."""
    location = storage.get_location(name)
    if not location:
        return f"Location '{name}' not found."

    loc_info = f"""**{location.name}** ({location.location_type})

**Description:** {location.description}

**Population:** {location.population or "Unknown"}
**Government:** {location.government or "Unknown"}

**Notable Features:**
{chr(10).join(["• " + feature for feature in location.notable_features]) if location.notable_features else "None listed"}

**Notes:** {location.notes or "No additional notes."}
"""

    return loc_info


@tool_with_logging(mcp, tags=["mode:any"])
def list_locations() -> str:
    """List all locations in the current campaign."""
    locations = storage.list_locations()
    if not locations:
        return "No locations in the current campaign."

    loc_list = []
    for loc_name in locations:
        loc = storage.get_location(loc_name)
        if loc:
            loc_list.append(f"• {loc.name} ({loc.location_type})")

    return "**Locations:**\n" + "\n".join(loc_list)


# Quest Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def create_quest(
    title: Annotated[str, Field(description="Quest title")],
    description: Annotated[str, Field(description="Quest description")],
    giver: Annotated[str | None, Field(description="Quest giver (NPC name)")] = None,
    objectives: Annotated[list[str] | None, Field(description="Quest objectives")] = None,
    reward: Annotated[str | None, Field(description="Quest reward")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new quest."""
    quest = Quest(
        title=title,
        description=description,
        giver=giver,
        objectives=objectives or [],
        reward=reward,
        notes=notes,
    )

    storage.add_quest(quest)
    return f"Created quest '{quest.title}'"


@tool_with_logging(mcp, tags=["mode:any"])
def update_quest(
    title: Annotated[str, Field(description="Quest title")],
    status: Annotated[
        Literal["active", "completed", "failed", "on_hold"] | None,
        Field(description="New quest status"),
    ] = None,
    completed_objective: Annotated[
        str | None, Field(description="Objective to mark as completed")
    ] = None,
) -> str:
    """Update quest status or complete objectives."""
    quest = storage.get_quest(title)
    if not quest:
        return f"Quest '{title}' not found."

    if status:
        storage.update_quest_status(title, status)

    if completed_objective:
        if (
            completed_objective in quest.objectives
            and completed_objective not in quest.completed_objectives
        ):
            quest.completed_objectives.append(completed_objective)
            storage._save_campaign()  # Direct save since we modified the object

    return f"Updated quest '{title}'"


@tool_with_logging(mcp, tags=["mode:any"])
def list_quests(
    status: Annotated[
        Literal["active", "completed", "failed", "on_hold"] | None,
        Field(description="Filter by status"),
    ] = None,
) -> str:
    """List quests, optionally filtered by status."""
    quests = storage.list_quests(status)

    if not quests:
        filter_text = f" with status '{status}'" if status else ""
        return f"No quests found{filter_text}."

    quest_list = []
    for quest_title in quests:
        quest = storage.get_quest(quest_title)
        if quest:
            status_text = f" [{quest.status}]"
            quest_list.append(f"• {quest.title}{status_text}")

    return "**Quests:**\n" + "\n".join(quest_list)


# Game State Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def update_game_state(
    current_location: Annotated[str | None, Field(description="Current party location")] = None,
    current_session: Annotated[
        int | None, Field(description="Current session number", ge=1)
    ] = None,
    current_date_in_game: Annotated[str | None, Field(description="Current in-game date")] = None,
    party_level: Annotated[
        int | None, Field(description="Average party level", ge=1, le=20)
    ] = None,
    party_funds: Annotated[str | None, Field(description="Party treasure/funds")] = None,
    in_combat: Annotated[bool | None, Field(description="Whether party is in combat")] = None,
    notes: Annotated[str | None, Field(description="Current situation notes")] = None,
) -> str:
    """Update the current game state."""
    kwargs: dict[str, str | int | bool] = {}
    if current_location is not None:
        kwargs["current_location"] = current_location
    if current_session is not None:
        kwargs["current_session"] = current_session
    if current_date_in_game is not None:
        kwargs["current_date_in_game"] = current_date_in_game
    if party_level is not None:
        kwargs["party_level"] = party_level
    if party_funds is not None:
        kwargs["party_funds"] = party_funds
    if in_combat is not None:
        kwargs["in_combat"] = in_combat
    if notes is not None:
        kwargs["notes"] = notes

    storage.update_game_state(**kwargs)
    return "Updated game state"


@tool_with_logging(mcp, tags=["mode:any"])
def get_game_state() -> str:
    """Get the current game state."""
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    state_info = f"""**Game State**
**Campaign:** {game_state.campaign_name}
**Session:** {game_state.current_session}
**Location:** {game_state.current_location or "Unknown"}
**Date (In-Game):** {game_state.current_date_in_game or "Unknown"}
**Party Level:** {game_state.party_level}
**Party Funds:** {game_state.party_funds}
**In Combat:** {"Yes" if game_state.in_combat else "No"}

**Active Quests:** {len(game_state.active_quests)}

**Notes:** {game_state.notes or "No current notes."}
"""

    return state_info


# Mode Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def set_mode(
    modes: Annotated[list[str] | str, Field(description="Mode(s) to set. Can be a single mode string or list of modes")],
) -> str:
    """Set the current game mode(s). Replaces existing modes.

    Available modes: setup, town, outdoors, dungeon, combat
    Combat should be listed first if active.
    """
    # Convert single mode to list
    if isinstance(modes, str):
        modes = [modes]

    # Validate modes
    invalid_modes = [mode for mode in modes if mode not in AVAILABLE_MODES]
    if invalid_modes:
        return f"Invalid modes: {', '.join(invalid_modes)}. Available modes: {', '.join(AVAILABLE_MODES.keys())}"

    # Ensure combat is first if present
    if "combat" in modes and modes[0] != "combat":
        modes = ["combat"] + [mode for mode in modes if mode != "combat"]

    # Update game state
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    game_state.modes = modes
    storage.update_game_state(modes=modes)

    primary_mode = modes[0] if modes else "none"
    modes_str = ", ".join(modes)
    return f"Set modes to: [{modes_str}]. Primary mode: {primary_mode}"


@tool_with_logging(mcp, tags=["mode:any"])
def get_mode() -> str:
    """Get the current game mode(s)."""
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    modes = game_state.modes
    if not modes:
        return "No modes set."

    primary_mode = modes[0]
    modes_str = ", ".join(modes)
    return f"Current modes: [{modes_str}]. Primary mode: {primary_mode}"


# Combat Management Tools
@tool_with_logging(mcp, tags=["mode:town", "mode:dunegon", "mode:outdoors"])
def start_combat(
    participants: Annotated[
        list[CombatParticipant], Field(description="Combat participants with initiative order")
    ],
) -> str:
    """Start a combat encounter."""
    # Sort by initiative (highest first)
    initiative_order = sorted(participants, key=lambda x: x.initiative, reverse=True)

    storage.update_game_state(
        in_combat=True,
        initiative_order=initiative_order,
        current_turn=initiative_order[0].name if initiative_order else None,
    )

    order_text = "\n".join(
        [f"{i + 1}. {p.name} (Initiative: {p.initiative})" for i, p in enumerate(initiative_order)]
    )

    return f"**Combat Started!**\n\n**Initiative Order:**\n{order_text}\n\n**Current Turn:** {initiative_order[0].name if initiative_order else 'None'}"


@tool_with_logging(mcp, tags=["mode:combat"])
def end_combat(
    result: Annotated[str, Field(description="Combat result (e.g., 'victory', 'defeat', 'fled')")],
    summary: Annotated[str, Field(description="Brief summary of how the combat ended")],
    casualties: Annotated[
        list[str] | None, Field(description="List of participants who died or were defeated")
    ] = None,
) -> str:
    """End the current combat encounter and record it in the transcript."""
    # Update game state
    storage.update_game_state(in_combat=False, initiative_order=[], current_turn=None)

    # End combat in transcript
    try:
        storage.end_transcript_combat(
            result=result,
            summary=summary,
            casualties=casualties
        )
        return f"Combat ended with result: {result}. Recorded in transcript."
    except Exception as e:
        # If transcript combat doesn't exist, just end combat in game state
        return f"Combat ended. (Note: {str(e)})"


# Adventure Management Tools
@tool_with_logging(mcp, tags=["mode:any"])
def start_adventure(
    title: Annotated[str, Field(description="Adventure title (e.g., 'The Temple of Doom')")],
    quest_id: Annotated[str | None, Field(description="Associated quest ID, if any")] = None,
) -> str:
    """Start an adventure and begin recording interactions in the transcript as part of this adventure."""
    adventure = storage.start_transcript_adventure(title=title, quest_id=quest_id)
    return f"📖 Started adventure: '{adventure.title}'. All interactions will be recorded as part of this adventure."


@tool_with_logging(mcp, tags=["mode:any"])
def end_adventure(
    summary: Annotated[str, Field(description="Summary of what happened during the adventure")],
    rewards: Annotated[
        list[str] | None, Field(description="List of rewards obtained (items, XP, etc.)")
    ] = None,
) -> str:
    """End the current adventure and record the summary in the transcript."""
    try:
        adventure_node = storage.end_transcript_adventure(summary=summary, rewards=rewards)
        return f"✅ Ended adventure: '{adventure_node.title}'. Summary recorded in transcript."
    except Exception as e:
        return f"❌ Error ending adventure: {str(e)}"


@tool_with_logging(mcp, tags=["mode:combat"])
def next_turn() -> str:
    """Advance to the next turn in combat."""
    game_state = storage.get_game_state()
    if not game_state or not game_state.in_combat:
        return "Not currently in combat."

    if not game_state.initiative_order:
        return "No initiative order set."

    # Find current turn index and advance
    current_index = 0
    if game_state.current_turn:
        for i, participant in enumerate(game_state.initiative_order):
            if participant.name == game_state.current_turn:
                current_index = i
                break

    next_index = (current_index + 1) % len(game_state.initiative_order)
    next_participant = game_state.initiative_order[next_index]

    storage.update_game_state(current_turn=next_participant.name)

    return f"**Next Turn:** {next_participant.name}"


# Session Management Tools
@tool_with_logging(mcp, tags=["mode:setup"])
def add_session_note(
    session_number: Annotated[int, Field(description="Session number", ge=1)],
    summary: Annotated[str, Field(description="Session summary")],
    title: Annotated[str | None, Field(description="Session title")] = None,
    events: Annotated[list[str] | None, Field(description="Key events that occurred")] = None,
    characters_present: Annotated[
        list[str] | None, Field(description="Characters present in session")
    ] = None,
    experience_gained: Annotated[
        int | None, Field(description="Experience points gained", ge=0)
    ] = None,
    treasure_found: Annotated[
        list[str] | None, Field(description="Treasure or items found")
    ] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Add notes for a game session."""
    session_note = SessionNote(
        session_number=session_number,
        title=title,
        summary=summary,
        events=events or [],
        characters_present=characters_present or [],
        experience_gained=experience_gained,
        treasure_found=treasure_found or [],
        notes=notes,
    )

    storage.add_session_note(session_note)
    return f"Added session note for Session {session_note.session_number}"


@tool_with_logging(mcp, tags=["mode:setup"])
def get_sessions() -> str:
    """Get all session notes."""
    sessions = storage.get_sessions()
    if not sessions:
        return "No session notes recorded."

    session_list = []
    for session in sorted(sessions, key=lambda s: s.session_number):
        title = session.title or "No title"
        date = session.date.strftime("%Y-%m-%d")
        session_list.append(f"**Session {session.session_number}** ({date}): {title}")
        session_list.append(
            f"  {session.summary[:100]}{'...' if len(session.summary) > 100 else ''}"
        )
        session_list.append("")

    return "**Session Notes:**\n\n" + "\n".join(session_list)


# Adventure Log Tools
@tool_with_logging(mcp, tags=["mode:any"])
def add_event(
    event_type: Annotated[
        Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"],
        Field(description="Type of event"),
    ],
    title: Annotated[str, Field(description="Event title")],
    description: Annotated[str, Field(description="Event description")],
    session_number: Annotated[int | None, Field(description="Session number", ge=1)] = None,
    characters_involved: Annotated[
        list[str] | None, Field(description="Characters involved in the event")
    ] = None,
    location: Annotated[str | None, Field(description="Location where event occurred")] = None,
    importance: Annotated[int, Field(description="Event importance (1-5)", ge=1, le=5)] = 3,
    tags: Annotated[list[str] | None, Field(description="Tags for categorizing the event")] = None,
    campaign_name: Annotated[
        str | None, Field(description="Campaign name (uses current campaign if None)")
    ] = None,
) -> str:
    """Add an event to the adventure log."""
    if campaign_name is None:
        campaign = storage.get_current_campaign()
        if not campaign:
            raise ValueError("No active campaign. Please create or load a campaign first.")
        campaign_name = campaign.name
    else:
        # Validate that the specified campaign exists
        try:
            storage.get_campaign(campaign_name)
        except FileNotFoundError:
            raise ValueError(f"Campaign '{campaign_name}' not found.")

    event = AdventureEvent(
        campaign=campaign_name,
        event_type=EventType(event_type),
        title=title,
        description=description,
        session_number=session_number,
        characters_involved=characters_involved or [],
        location=location,
        importance=importance,
        tags=tags or [],
    )

    storage.add_event(event)
    return f"Added {event_type.lower()} event: '{event.title}'"


@tool_with_logging(mcp, tags=["mode:any"])
def get_events(
    limit: Annotated[
        int | None, Field(description="Maximum number of events to return", ge=1)
    ] = None,
    campaign: Annotated[str | None, "Get events by campaign name"] = None,
    event_type: Annotated[
        Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"]
        | None,
        Field(description="Filter by event type"),
    ] = None,
    search: Annotated[str | None, Field(description="Search events by title/description")] = None,
) -> str:
    """Get events from the adventure log."""
    if search:
        events = storage.search_events(search)
    else:
        events = storage.get_events(limit=limit, event_type=event_type, campaign=campaign)

    if not events:
        return "No events found."

    event_list = []
    for event in events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M")
        session_text = f" (Session {event.session_number})" if event.session_number else ""
        importance_stars = "★" * event.importance

        event_list.append(f"**{event.title}** [{event.event_type}] {importance_stars}")
        event_list.append(f"  {timestamp}{session_text}")
        event_list.append(
            f"  {event.description[:150]}{'...' if len(event.description) > 150 else ''}"
        )
        if event.location:
            event_list.append(f"  📍 {event.location}")
        event_list.append("")

    return "**Adventure Log:**\n\n" + "\n".join(event_list)


# Utility Tools
@tool_with_logging(mcp, tags=["mode:any"])
def roll_dice(
    dice_notation: Annotated[str, Field(description="Dice notation (e.g., '1d20', '3d6+2')")],
    advantage: Annotated[bool, Field(description="Roll with advantage")] = False,
    disadvantage: Annotated[bool, Field(description="Roll with disadvantage")] = False,
) -> str:
    """Roll dice with D&D notation."""
    dice_notation = dice_notation.lower().strip()

    # Parse dice notation (e.g., "1d20", "3d6+2", "2d8-1")
    pattern = r"(\d+)d(\d+)([+-]\d+)?"
    match = re.match(pattern, dice_notation)

    if not match:
        return f"Invalid dice notation: {dice_notation}"

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    # Roll dice
    if advantage or disadvantage:
        if num_dice != 1 or die_size != 20:
            return "Advantage/disadvantage only applies to single d20 rolls"

        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)

        if advantage:
            result = max(roll1, roll2)
            roll_text = f"Advantage: {roll1}, {roll2} (taking {result})"
        else:
            result = min(roll1, roll2)
            roll_text = f"Disadvantage: {roll1}, {roll2} (taking {result})"

        total = result + modifier
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** {roll_text}{modifier_text} = **{total}**"
    else:
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        roll_sum = sum(rolls)
        total = roll_sum + modifier

        rolls_text = ", ".join(map(str, rolls)) if num_dice > 1 else str(rolls[0])
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** [{rolls_text}]{modifier_text} = **{total}**"


@tool_with_logging(mcp)
def calculate_experience(
    party_size: Annotated[int, Field(description="Number of party members", ge=1)],
    party_level: Annotated[int, Field(description="Average party level", ge=1, le=20)],
    encounter_xp: Annotated[int, Field(description="Total encounter XP value", ge=0)],
) -> str:
    """Calculate experience points for an encounter."""
    # D&D 5e encounter multipliers based on party size
    if party_size < 3:
        multiplier = 1.5
    elif party_size > 5:
        multiplier = 0.5
    else:
        multiplier = 1.0

    adjusted_xp = int(encounter_xp * multiplier)
    xp_per_player = adjusted_xp // party_size

    return f"""**Experience Calculation:**
Base Encounter XP: {encounter_xp}
Party Size Multiplier: {multiplier}x
Adjusted XP: {adjusted_xp}
**XP per Player: {xp_per_player}**"""


# Transcript tools and resources
@tool_with_logging(mcp)
def record_interaction(
    player_entry: Annotated[str, "Text input by the player"],
    game_response: Annotated[str, "Response send by the game"],
    campaign_name: Annotated[
        str | None,
        "Name of campaign to which this interaction applies, or none to use the current campaign",
    ] = None,
    session_number: Annotated[
        int | None,
        "Session number to which this interaction applies, or none to use the latest session",
        Field(description="Session number", ge=1),
    ] = None,
):
    storage.add_transcript_entry(player_entry, game_response, campaign_name, session_number)


@mcp.resource("resource://transcripts/{campaign_name}/{session_number}")
def get_transcript(campaign_name: str, session_number: int) -> Transcript:
    return storage.get_transcript(campaign_name, session_number)


@mcp.resource("resource://current_transcript")
def get_current_transcript() -> Transcript:
    return storage.get_transcript(None, None)


# Game state resources
@mcp.resource("resource://current_campaign/game_state")
def get_current_campaign_game_state():
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        raise FileNotFoundError("No current campaign")
    return current_campaign.game_state


@mcp.resource("resource://campaigns/{campaign_name}/game_state")
def get_campaign_game_state(campaign_name: str):
    try:
        campaign = storage.get_campaign(campaign_name)
        return campaign.game_state
    except FileNotFoundError:
        raise FileNotFoundError(f"Campaign '{campaign_name}' not found")


# Mode resources
@mcp.resource("resource://current_campaign/mode")
def get_current_campaign_mode() -> dict[str, Any]:
    """Get current campaign mode(s)."""
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        raise FileNotFoundError("No current campaign")
    return {
        "modes": current_campaign.game_state.modes,
        "primary_mode": current_campaign.game_state.modes[0] if current_campaign.game_state.modes else None
    }


@mcp.resource("resource://modes")
def get_available_modes() -> list[dict[str, str]]:
    """Get all available modes with descriptions."""
    return [
        {"mode": mode, "description": description}
        for mode, description in AVAILABLE_MODES.items()
    ]


@mcp.prompt
def current_prompt() -> str:
    """Generates the most appropriate prompt for the current game state."""
    prompt = core_prompt
    current_campaign = storage.get_current_campaign()
    if not current_campaign:
        prompt += setup_prompt
    else:
        for mode in current_campaign.game_state.modes:
            if MODE_PROMPTS.get(mode):
                prompt += MODE_PROMPTS.get(mode)

    return Message(prompt)


logger.debug("✅ All tools successfully registered. Gamemaster-MCP server running! 🎲")


def main() -> None:
    """Main entry point for the D&D MCP Server."""
    parser = argparse.ArgumentParser(description="Server configuration")

    parser.add_argument(
        "--transport", type=str, help="Transport type to use with the server (optional)"
    )

    parser.add_argument(
        "--port", type=int, default=8000, help="Port number to run the server on (default: 8000)"
    )

    args = parser.parse_args()

    if args.transport is not None:
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
