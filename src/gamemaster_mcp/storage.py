"""
Storage layer for the D&D MCP Server.
Handles persistence of campaign data to JSON files.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import shortuuid

from .models import (
    NPC,
    AdventureEvent,
    Campaign,
    Character,
    GameState,
    HexCoordinate,
    HexMap,
    Location,
    LocationScale,
    Quest,
    ResponseText,
    ResponseTools,
    SessionNote,
    TranscriptAdventure,
    TranscriptCombat,
    TranscriptInteraction,
    # New transcript tree models
    TranscriptTree,
)

logger = logging.getLogger("gamemaster-mcp")

logging.basicConfig(
    level=logging.DEBUG,
)


# UUID Helper function
def new_uuid() -> str:
    """Generate a new random 8-character UUID."""
    return shortuuid.random(length=8)


class DnDStorage:
    """Handles storage and retrieval of D&D campaign data."""

    def __init__(self, data_dir: str | Path = "dnd_data"):
        self.data_dir = Path(data_dir)
        logger.debug(f"📂 Initializing DnDStorage with data_dir: {self.data_dir.resolve()}")
        self.data_dir.mkdir(exist_ok=True)

        # Create subdirectories if necessary
        (self.data_dir / "campaigns").mkdir(exist_ok=True)
        (self.data_dir / "events").mkdir(exist_ok=True)
        (self.data_dir / "transcripts").mkdir(exist_ok=True)
        logger.debug("📂 Storage subdirectories ensured.")

        self._current_campaign: Campaign | None = None
        self._events: list[AdventureEvent] = []

        # Track current parent node for transcript tree manipulation
        self._transcript_current_parent: dict[str, str] = {}  # campaign -> parent_node_id
        # Track parent stack for nested structures (combat within adventure, etc.)
        self._parent_stack: dict[str, list[str]] = {}  # campaign -> list of parent IDs

        # Load existing data
        logger.debug("📂 Loading initial data...")
        self._load_current_campaign()
        self._load_events()
        logger.debug("✅ Initial data loaded.")

    def _get_campaign_file(self, campaign_name: str | None = None) -> Path:
        """Get the file path for a campaign."""
        if campaign_name is None and self._current_campaign:
            campaign_name = self._current_campaign.name
        if campaign_name is None:
            raise ValueError("No campaign name provided and no current campaign")

        safe_name = "".join(
            c for c in campaign_name if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        return self.data_dir / "campaigns" / f"{safe_name}.json"

    def _get_events_file(self) -> Path:
        """Get the file path for adventure events."""
        return self.data_dir / "events" / "adventure_log.json"

    def _get_transcript_dir(self, campaign_name: str) -> Path:
        return self.data_dir / "transcripts" / campaign_name

    def _get_transcript_file(self, campaign_name: str, session_number: int) -> Path:
        return self.data_dir / "transcripts" / campaign_name / f"session_{session_number}.json"

    def _save_campaign(self) -> None:
        """Save the current campaign to disk."""
        if not self._current_campaign:
            logger.debug("❌ No current campaign to save.")
            return

        campaign_file = self._get_campaign_file()
        logger.debug(f"💾 Saving campaign '{self._current_campaign.name}' to {campaign_file}")
        logger.info(f"💾 Autosaving '{self._current_campaign.name}'")
        campaign_data = self._current_campaign.model_dump(mode="json")

        with open(campaign_file, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f, default=str)
        logger.debug(f"✅ Campaign '{self._current_campaign.name}' saved successfully.")

    def _load_current_campaign(self):
        """Load the most recently used campaign."""
        logger.debug("📂 Attempting to load the most recent campaign...")
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            logger.debug("❌ Campaigns directory does not exist. No campaign loaded.")
            return

        # Find the most recent campaign file
        campaign_files = list(campaigns_dir.glob("*.json"))
        if not campaign_files:
            logger.debug("❌ No campaign files found.")
            return

        # Sort by modification time and load the most recent
        latest_file = max(campaign_files, key=lambda f: f.stat().st_mtime)
        logger.debug(f"📂 Most recent campaign file is '{latest_file.name}'.")

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._current_campaign = Campaign.model_validate(data)
            logger.info(f"✅ Successfully loaded campaign: {self._current_campaign.name}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading campaign from {latest_file}: {e}")

    def _save_events(self) -> None:
        """Save adventure events to disk."""
        events_file = self._get_events_file()
        logger.debug(f"💾 Saving {len(self._events)} events to {events_file}...")
        events_data = [event.model_dump(mode="json") for event in self._events]

        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, default=str)
        logger.debug("✅ Events saved successfully.")

    def _load_events(self) -> None:
        """Load adventure events from disk."""
        logger.debug("📂 Attempting to load adventure events...")
        events_file = self._get_events_file()
        if not events_file.exists():
            logger.debug("❌ Adventure log file does not exist. No events loaded.")
            return

        try:
            with open(events_file, "r", encoding="utf-8") as f:
                events_data = json.load(f)
            self._events = [AdventureEvent.model_validate(event) for event in events_data]
            logger.info(f"✅ Successfully loaded {len(self._events)} events.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading events: {e}")

    def _load_transcript(self, campaign_name: str, session_number: int) -> TranscriptTree | None:
        """Load a transcript, migrating from old format if necessary."""
        transcript_file = self._get_transcript_file(campaign_name, session_number)
        if not transcript_file.exists():
            return None

        try:
            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)

            # Detect format: old format has 'entries', new format has 'children'
            if "entries" in transcript_data:
                logger.info("🔄 Migrating old transcript format to new tree format...")

                # Create backup
                backup_file = transcript_file.with_suffix(".json.old")
                import shutil
                shutil.copy2(transcript_file, backup_file)
                logger.info(f"💾 Created backup at {backup_file}")

                # Migrate: convert each old entry to TranscriptInteraction
                children = []
                for entry in transcript_data.get("entries", []):
                    interaction = TranscriptInteraction(
                        user_text=entry.get("player_entry", ""),
                        responses=[ResponseText(content=entry.get("game_response", ""))]
                    )
                    children.append(interaction)

                # Create new TranscriptTree
                transcript = TranscriptTree(
                    campaign=transcript_data["campaign"],
                    session_number=transcript_data["session_number"],
                    children=children,
                    current_parent_id=None
                )

                # Save in new format
                self._save_transcript(transcript)
                logger.info("✅ Migration complete. Transcript now uses tree format.")
                return transcript

            else:
                # New format - load as TranscriptTree
                transcript = TranscriptTree.model_validate(transcript_data)
                logger.info(
                    f"✅ Successfully loaded transcript for {campaign_name}, session {session_number}"
                )

                # Restore current parent from transcript metadata
                if transcript.current_parent_id:
                    self._transcript_current_parent[campaign_name] = transcript.current_parent_id
                else:
                    # Default to transcript root
                    self._transcript_current_parent[campaign_name] = transcript.id

                return transcript

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading transcript: {e}")
            return None

    def _save_transcript(self, transcript: TranscriptTree) -> None:
        """Save a transcript tree to disk."""
        transcript_dir = self._get_transcript_dir(transcript.campaign)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = self._get_transcript_file(transcript.campaign, transcript.session_number)

        # Update current_parent_id in transcript before saving
        current_parent = self._transcript_current_parent.get(transcript.campaign)
        if current_parent:
            transcript.current_parent_id = current_parent

        # Write transcript to the file
        transcript_data = transcript.model_dump(mode="json")
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, default=str, indent=4)
        logger.debug("✅ Transcript saved successfully.")

    # Current Parent Tracking
    def get_current_parent_id(self, campaign_name: str) -> str | None:
        """Get the current parent node ID for a campaign."""
        return self._transcript_current_parent.get(campaign_name)

    def set_current_parent_id(self, campaign_name: str, node_id: str) -> None:
        """Set the current parent node ID for a campaign."""
        self._transcript_current_parent[campaign_name] = node_id
        logger.debug(f"📍 Set current parent for '{campaign_name}' to node {node_id}")

    def _find_node_in_tree(
        self, node: TranscriptTree | TranscriptCombat | TranscriptAdventure, target_id: str
    ) -> TranscriptTree | TranscriptCombat | TranscriptAdventure | None:
        """Recursively find a node by ID in the tree."""
        if node.id == target_id:
            return node

        # Check children/actions depending on node type
        children = []
        if isinstance(node, TranscriptTree):
            children = node.children
        elif isinstance(node, (TranscriptCombat, TranscriptAdventure)):
            children = node.actions

        for child in children:
            if child.id == target_id:
                return child
            # Recursively search in combat and adventure nodes
            if isinstance(child, (TranscriptCombat, TranscriptAdventure)):
                result = self._find_node_in_tree(child, target_id)
                if result:
                    return result

        return None

    # Transcript Tree Manipulation
    def add_transcript_interaction(
        self,
        user_text: str,
        responses: list[dict],
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptInteraction:
        """Add an interaction to the current parent node."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            transcript = TranscriptTree(
                campaign=campaign_name,
                session_number=session_number,
                children=[]
            )
            # Set transcript root as current parent
            self.set_current_parent_id(campaign_name, transcript.id)

        # Convert response dicts to proper response objects
        response_objects = []
        for resp in responses:
            if resp["type"] == "text":
                response_objects.append(ResponseText(content=resp["content"]))
            elif resp["type"] == "tools":
                # Convert tool calls
                from .models import InteractionToolCall
                tool_calls = []
                for call in resp.get("calls", []):
                    tool_calls.append(InteractionToolCall(
                        name=call["name"],
                        id=call["id"],
                        input=call["input"],
                        response=call.get("response", "")
                    ))
                response_objects.append(ResponseTools(calls=tool_calls))

        # Create interaction
        interaction = TranscriptInteraction(
            user_text=user_text,
            responses=response_objects
        )

        # Find current parent and add interaction
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id or current_parent_id == transcript.id:
            # Add to transcript root
            transcript.children.append(interaction)
        else:
            # Find parent node and add to its actions
            parent_node = self._find_node_in_tree(transcript, current_parent_id)
            if parent_node and isinstance(parent_node, (TranscriptCombat, TranscriptAdventure)):
                parent_node.actions.append(interaction)
            else:
                # Fallback to root if parent not found
                logger.warning(f"⚠️ Parent node {current_parent_id} not found, adding to root")
                transcript.children.append(interaction)

        self._save_transcript(transcript)
        logger.info("✅ Added interaction to transcript")
        return interaction

    def start_transcript_combat(
        self,
        participants: list[str],
        location: str | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptCombat:
        """Start a combat encounter, creating a Combat node and setting it as current parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            transcript = TranscriptTree(
                campaign=campaign_name,
                session_number=session_number,
                children=[]
            )
            self.set_current_parent_id(campaign_name, transcript.id)

        # Create combat node (summary and result will be set when ending combat)
        combat = TranscriptCombat(
            participants=participants,
            result="",  # Will be set when ending
            summary="",  # Will be set when ending
            actions=[],
            location=location
        )

        # Add combat to current parent
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id or current_parent_id == transcript.id:
            # Add to transcript root
            transcript.children.append(combat)
        else:
            # Find parent node and add to its actions
            parent_node = self._find_node_in_tree(transcript, current_parent_id)
            if parent_node and isinstance(parent_node, TranscriptAdventure):
                parent_node.actions.append(combat)
            else:
                # Fallback to root
                logger.warning(f"⚠️ Parent node {current_parent_id} not found, adding to root")
                transcript.children.append(combat)

        # Push current parent onto stack and set combat as new current parent
        if campaign_name not in self._parent_stack:
            self._parent_stack[campaign_name] = []
        self._parent_stack[campaign_name].append(current_parent_id)
        self.set_current_parent_id(campaign_name, combat.id)

        self._save_transcript(transcript)
        logger.info(f"✅ Started combat with participants: {participants}")
        return combat

    def end_transcript_combat(
        self,
        result: str,
        summary: str,
        casualties: list[str] | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptCombat:
        """End a combat encounter, setting result/summary and restoring previous parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            raise ValueError("No transcript found")

        # Find combat node
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id:
            raise ValueError("No current parent set")

        combat_node = self._find_node_in_tree(transcript, current_parent_id)
        if not combat_node or not isinstance(combat_node, TranscriptCombat):
            raise ValueError("Current parent is not a combat node")

        # Update combat with results
        combat_node.result = result
        combat_node.summary = summary
        if casualties:
            combat_node.casualties = casualties
        combat_node.rounds = len([a for a in combat_node.actions if isinstance(a, TranscriptInteraction)])

        # Pop previous parent from stack and restore
        if campaign_name in self._parent_stack and self._parent_stack[campaign_name]:
            previous_parent = self._parent_stack[campaign_name].pop()
        else:
            previous_parent = transcript.id
        self.set_current_parent_id(campaign_name, previous_parent)

        self._save_transcript(transcript)
        logger.info(f"✅ Ended combat with result: {result}")
        return combat_node

    def start_transcript_adventure(
        self,
        title: str,
        quest_id: str | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptAdventure:
        """Start an adventure, creating an Adventure node and setting it as current parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            transcript = TranscriptTree(
                campaign=campaign_name,
                session_number=session_number,
                children=[]
            )
            self.set_current_parent_id(campaign_name, transcript.id)

        # Create adventure node (summary will be set when ending)
        adventure = TranscriptAdventure(
            title=title,
            summary="",  # Will be set when ending
            actions=[],
            quest_id=quest_id
        )

        # Add adventure to current parent
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id or current_parent_id == transcript.id:
            # Add to transcript root
            transcript.children.append(adventure)
        else:
            # Find parent node and add to its actions
            parent_node = self._find_node_in_tree(transcript, current_parent_id)
            if parent_node and isinstance(parent_node, TranscriptAdventure):
                parent_node.actions.append(adventure)
            else:
                # Fallback to root
                logger.warning(f"⚠️ Parent node {current_parent_id} not found, adding to root")
                transcript.children.append(adventure)

        # Push current parent onto stack and set adventure as new current parent
        if campaign_name not in self._parent_stack:
            self._parent_stack[campaign_name] = []
        self._parent_stack[campaign_name].append(current_parent_id)
        self.set_current_parent_id(campaign_name, adventure.id)

        self._save_transcript(transcript)
        logger.info(f"✅ Started adventure: {title}")
        return adventure

    def end_transcript_adventure(
        self,
        summary: str,
        rewards: list[str] | None = None,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptAdventure:
        """End an adventure, setting summary and restoring previous parent."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            raise ValueError("No transcript found")

        # Find adventure node
        current_parent_id = self.get_current_parent_id(campaign_name)
        if not current_parent_id:
            raise ValueError("No current parent set")

        adventure_node = self._find_node_in_tree(transcript, current_parent_id)
        if not adventure_node or not isinstance(adventure_node, TranscriptAdventure):
            raise ValueError("Current parent is not an adventure node")

        # Update adventure with summary
        adventure_node.summary = summary
        if rewards:
            adventure_node.rewards = rewards

        # Pop previous parent from stack and restore
        if campaign_name in self._parent_stack and self._parent_stack[campaign_name]:
            previous_parent = self._parent_stack[campaign_name].pop()
        else:
            previous_parent = transcript.id
        self.set_current_parent_id(campaign_name, previous_parent)

        self._save_transcript(transcript)
        logger.info(f"✅ Ended adventure: {adventure_node.title}")
        return adventure_node

    def get_ungrouped_transcript_nodes(
        self,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> list[TranscriptInteraction | TranscriptCombat | TranscriptAdventure]:
        """Get all transcript nodes that haven't been grouped into an adventure yet.

        Returns all nodes after the last TranscriptAdventure in the transcript's children.
        """
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            return []

        # Find the index of the last TranscriptAdventure in children
        last_adventure_index = -1
        for i, child in enumerate(transcript.children):
            if isinstance(child, TranscriptAdventure):
                last_adventure_index = i

        # Get all nodes after the last adventure (or all nodes if no adventure exists)
        return transcript.children[last_adventure_index + 1:]

    def complete_transcript_adventure(
        self,
        title: str,
        summary: str,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptAdventure:
        """Complete an adventure by grouping all interactions since the last adventure.

        Takes all nodes that have been added to the transcript root since the last
        TranscriptAdventure node (or since the start) and groups them into a new
        TranscriptAdventure node at the same level.
        """
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name

        if session_number is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            session_number = campaign.game_state.current_session

        # Load or create transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            # No transcript exists, nothing to complete
            raise ValueError("No transcript found for this session")

        # Find the index of the last TranscriptAdventure in children
        last_adventure_index = -1
        for i, child in enumerate(transcript.children):
            if isinstance(child, TranscriptAdventure):
                last_adventure_index = i

        # Get all nodes after the last adventure (or all nodes if no adventure exists)
        nodes_to_group = transcript.children[last_adventure_index + 1:]

        if not nodes_to_group:
            raise ValueError("No interactions to group into an adventure")

        # Create new adventure node with these interactions
        adventure = TranscriptAdventure(
            title=title,
            summary=summary,
            actions=nodes_to_group,
        )

        # Replace the grouped nodes with the single adventure node
        transcript.children = transcript.children[:last_adventure_index + 1] + [adventure]

        # Save transcript
        self._save_transcript(transcript)
        logger.info(f"✅ Completed adventure: '{title}' with {len(nodes_to_group)} node(s)")
        return adventure

    # Campaign Management
    def create_campaign(
        self,
        name: str,
        description: str,
        dm_name: str | None = None,
        setting: str | Path | None = None,
    ) -> Campaign:
        """Create a new campaign."""
        logger.info(f"✨ Creating new campaign: '{name}'")
        game_state = GameState(campaign_name=name)

        campaign = Campaign(
            name=name,
            description=description,
            dm_name=dm_name,
            setting=setting,
            game_state=game_state,
        )

        self._current_campaign = campaign
        self._save_campaign()
        logger.info(f"✅ Campaign '{name}' created and set as active.")
        return campaign

    def get_current_campaign(self) -> Campaign | None:
        """Get the current campaign."""
        return self._current_campaign

    def list_campaigns(self) -> list[str]:
        """List all available campaigns."""
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            return []

        return [f.stem for f in campaigns_dir.glob("*.json")]

    def get_campaign(self, name: str) -> Campaign:
        logger.info(f"📂 Attempting to load campaign: '{name}'")
        campaign_file = self._get_campaign_file(name)
        logger.debug(f"📂 Campaign file path: {campaign_file}")

        if not campaign_file.exists():
            logger.error(f"❌ Campaign file not found for '{name}'")
            raise FileNotFoundError(f"Campaign '{name}' not found")

        with open(campaign_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Campaign.model_validate(data)

    def load_campaign(self, name: str) -> Campaign:
        self._current_campaign = self.get_campaign(name)
        logger.info(f"✅ Successfully loaded campaign '{name}'.")
        return self._current_campaign

    def update_campaign(self, **kwargs):
        """Update campaign metadata."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"📝 Updating campaign '{self._current_campaign.name}' with data: {kwargs}")
        for key, value in kwargs.items():
            if hasattr(self._current_campaign, key):
                logger.debug(f"📝 Updating {key} to {value}")
                setattr(self._current_campaign, key, value)

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Campaign '{self._current_campaign.name}' updated.")

    # Character Management
    def add_character(self, character: Character) -> None:
        """Add a character to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(
            f"➕ Adding character '{character.name}' to campaign '{self._current_campaign.name}'."
        )
        self._current_campaign.characters[character.name] = character
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.debug(
            f"✅ Character '{character.name}' added to campaign: '{self._current_campaign.name}'."
        )

    def _find_character(self, name_or_id: str) -> Character | None:
        """Find a character by name or ID."""
        if not self._current_campaign:
            e = ValueError("No current campaign")
            logger.error(e)
            raise e

        character: Character | None = None
        logger.info(f"_find_character: current campaign: {self._current_campaign.name}")
        logger.info(
            f"_find_character: current campaign characters: {self._current_campaign.characters}"
        )

        # Try searching by ID first if appropriate
        if len(name_or_id) == 8:
            try:
                char_id = name_or_id
                for char in self._current_campaign.characters.values():
                    if char.id == char_id:
                        character = char
            except (ValueError, TypeError):
                # Not a UUID, so it's a name
                logger.warning(f"⚠️ Character not found by ID: {name_or_id}, trying name")
                pass

        # Search by name
        if not character:
            try:
                character = self._current_campaign.characters.get(name_or_id)
            except (ValueError, TypeError) as e:
                logger.error(e)
                return None

        return character

    def get_character(self, name_or_id: str) -> Character | None:
        """Get a character by name or ID."""
        if not name_or_id:
            raise ValueError("Empty character name or id")

        char = self._find_character(name_or_id)
        if not char:
            logger.error(f"❌ Character '{name_or_id}' not found!")
            return None
        logger.debug(f"✅ Found character '{char.name}'")
        return char

    def update_character(
        self,
        name_or_id: str,
        name: str | None = None,
        player_name: str | None = None,
        description: str | None = None,
        bio: str | None = None,
        background: str | None = None,
        alignment: str | None = None,
        hit_points_current: int | None = None,
        hit_points_max: int | None = None,
        temporary_hit_points: int | None = None,
        armor_class: int | None = None,
        inspiration: bool | None = None,
        notes: str | None = None,
        strength: int | None = None,
        dexterity: int | None = None,
        constitution: int | None = None,
        intelligence: int | None = None,
        wisdom: int | None = None,
        charisma: int | None = None,
        level: int | None = None,
        # Spell-related fields for internal use by spell/inventory management tools
        inventory: list | None = None,
        spell_slots: dict | None = None,
        spell_slots_used: dict | None = None,
        spells_known: list | None = None,
        # Skills and saving throws for internal use by proficiency management tools
        skills: dict | None = None,
        saving_throws: dict | None = None,
        # Special abilities for internal use by ability management tools
        special_abilities: list | None = None,
    ) -> None:
        """Update a character's data."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"📝 Attempting to update character '{name_or_id}'")
        character = self._find_character(name_or_id)
        if not character:
            e = ValueError(f"❌ Character '{name_or_id}' not found!")
            logger.error(e)
            raise e

        original_name = character.name

        # Update basic fields
        if name is not None:
            character.name = name
        if player_name is not None:
            character.player_name = player_name
        if description is not None:
            character.description = description
        if bio is not None:
            character.bio = bio
        if background is not None:
            character.background = background
        if alignment is not None:
            character.alignment = alignment
        if notes is not None:
            character.notes = notes

        # Update combat stats
        if hit_points_current is not None:
            character.hit_points_current = hit_points_current
        if hit_points_max is not None:
            character.hit_points_max = hit_points_max
        if temporary_hit_points is not None:
            character.temporary_hit_points = temporary_hit_points
        if armor_class is not None:
            character.armor_class = armor_class
        if inspiration is not None:
            character.inspiration = inspiration

        # Update ability scores
        if strength is not None:
            character.abilities["strength"].score = strength
        if dexterity is not None:
            character.abilities["dexterity"].score = dexterity
        if constitution is not None:
            character.abilities["constitution"].score = constitution
        if intelligence is not None:
            character.abilities["intelligence"].score = intelligence
        if wisdom is not None:
            character.abilities["wisdom"].score = wisdom
        if charisma is not None:
            character.abilities["charisma"].score = charisma

        # Update level (special handling for character class)
        if level is not None:
            character.character_class.level = level

        # Update equipment and spells (used by dedicated tools)
        if inventory is not None:
            character.inventory = inventory
        if spell_slots is not None:
            character.spell_slots = spell_slots
        if spell_slots_used is not None:
            character.spell_slots_used = spell_slots_used
        if spells_known is not None:
            character.spells_known = spells_known

        # Update skills and saving throws (used by proficiency management tools)
        if skills is not None:
            character.skills = skills
        if saving_throws is not None:
            character.saving_throws = saving_throws

        # Update special abilities (used by ability management tools)
        if special_abilities is not None:
            character.special_abilities = special_abilities

        character.updated_at = datetime.now()

        # Handle name change
        if name is not None and name != original_name:
            logger.debug(
                f"🏷️ Character name changed from '{original_name}' to '{name}'. Updating dictionary key."
            )
            self._current_campaign.characters[name] = self._current_campaign.characters.pop(
                original_name
            )

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Character '{character.name}' updated successfully.")

    def remove_character(self, name_or_id: str) -> None:
        """Remove a character from the campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.debug(f"🗑️ Attempting to remove character '{name_or_id}'.")
        character_to_remove = self._find_character(name_or_id)
        if character_to_remove:
            char_name = character_to_remove.name
            logger.debug(f"🗑️ Found character '{char_name}' to remove.")
            # We need the name to delete from the dict
            del self._current_campaign.characters[char_name]
            self._current_campaign.updated_at = datetime.now()
            self._save_campaign()
            logger.info(f"✅ Character '{char_name}' removed successfully.")
        else:
            logger.warning(f"⚠️ Character '{name_or_id}' not found for removal.")

    def list_characters(self) -> list[str]:
        """List all character names in the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.characters.keys())

    # NPC Management
    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.npcs[npc.name] = npc
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_npc(self, name: str) -> NPC | None:
        """Get an NPC by name."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not name:
            raise ValueError("Empty npc name")
        return self._current_campaign.npcs.get(name)

    def list_npcs(self) -> list[str]:
        """List all NPC names."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.npcs.keys())

    # Location Management
    def add_location(self, location: Location) -> None:
        """Add a location to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.locations[location.name] = location
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_location(self, name: str) -> Location | None:
        """Get a location by name."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not name:
            raise ValueError("Empty location name")
        return self._current_campaign.locations.get(name)

    def list_locations(self) -> list[str]:
        """List all location names."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.locations.keys())

    # Root Location Management
    def get_root_location(self) -> Location | None:
        """Get the campaign's root location, or None if not set."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        if not self._current_campaign.root_location_id:
            return None

        # Find location by ID
        for location in self._current_campaign.locations.values():
            if location.id == self._current_campaign.root_location_id:
                return location

        return None

    def set_root_location(self, location_id: str) -> None:
        """Set a location as the campaign root.

        Args:
            location_id: ID of location to set as root

        Raises:
            ValueError: If location doesn't exist or already has a parent
        """
        if not self._current_campaign:
            raise ValueError("No current campaign")

        # Find location by ID
        location = None
        for loc in self._current_campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        if not location:
            raise ValueError(f"Location with ID '{location_id}' not found")

        if location.parent_location_id is not None:
            raise ValueError(
                f"Location '{location.name}' already has a parent and cannot be set as root"
            )

        self._current_campaign.root_location_id = location_id
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Set '{location.name}' as campaign root location")

    def get_orphaned_locations(self) -> list[Location]:
        """Get all locations with no parent (excluding root).

        Returns:
            List of locations that should be children of root but aren't explicitly set.
        """
        if not self._current_campaign:
            raise ValueError("No current campaign")

        root_id = self._current_campaign.root_location_id
        orphans = []

        for location in self._current_campaign.locations.values():
            # Skip root location itself
            if root_id and location.id == root_id:
                continue
            # Include if no parent
            if location.parent_location_id is None:
                orphans.append(location)

        return orphans

    def get_unmigrated_locations(self) -> list[Location]:
        """Get all locations that are isolated (not integrated into hierarchy or maps).

        Returns:
            List of locations where:
            - parent_location_id is None (and not root)
            - child_locations is empty
            - primary_map is None
        """
        if not self._current_campaign:
            raise ValueError("No current campaign")

        root_id = self._current_campaign.root_location_id
        unmigrated = []

        for location in self._current_campaign.locations.values():
            # Skip root location itself
            if root_id and location.id == root_id:
                continue

            # Check if location is completely isolated
            is_unmigrated = (
                location.parent_location_id is None
                and len(location.child_locations) == 0
                and location.primary_map is None
            )

            if is_unmigrated:
                unmigrated.append(location)

        return unmigrated

    def get_top_level_locations(self) -> list[Location]:
        """Get all top-level locations (children of root, or orphans if no root)."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        root_id = self._current_campaign.root_location_id

        if root_id:
            # Get all locations with no parent (excluding root itself)
            top_level = []
            for location in self._current_campaign.locations.values():
                if location.id != root_id and location.parent_location_id is None:
                    top_level.append(location)
            return top_level
        else:
            # No root, return all orphans
            return self.get_orphaned_locations()

    # Location Hierarchy Management
    def set_parent_location(self, child_id: str, parent_id: str | None) -> None:
        """Set the parent location for a location (updates both child and parent).

        Args:
            child_id: ID of child location
            parent_id: ID of parent location, or None to make child a top-level location
        """
        if not self._current_campaign:
            raise ValueError("No current campaign")

        # Find child location
        child = None
        for loc in self._current_campaign.locations.values():
            if loc.id == child_id:
                child = loc
                break

        if not child:
            raise ValueError(f"Child location with ID '{child_id}' not found")

        # Remove child from old parent's child_locations
        if child.parent_location_id:
            old_parent = None
            for loc in self._current_campaign.locations.values():
                if loc.id == child.parent_location_id:
                    old_parent = loc
                    break
            if old_parent and child_id in old_parent.child_locations:
                old_parent.child_locations.remove(child_id)

        # Set new parent
        child.parent_location_id = parent_id

        # Add child to new parent's child_locations
        if parent_id:
            parent = None
            for loc in self._current_campaign.locations.values():
                if loc.id == parent_id:
                    parent = loc
                    break

            if not parent:
                raise ValueError(f"Parent location with ID '{parent_id}' not found")

            if child_id not in parent.child_locations:
                parent.child_locations.append(child_id)

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Set parent of '{child.name}' to {parent.name if parent_id and parent else 'None'}")

    def get_location_hierarchy(self, location_id: str) -> dict:
        """Get full hierarchy tree for a location (parents and children).

        Returns dict with 'ancestors' (list from root down) and 'descendants' (nested dict).
        """
        if not self._current_campaign:
            raise ValueError("No current campaign")

        # Find location
        location = None
        for loc in self._current_campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        if not location:
            raise ValueError(f"Location with ID '{location_id}' not found")

        # Build ancestor list
        ancestors = []
        current = location
        visited = set()  # Prevent infinite loops

        while current.parent_location_id and current.id not in visited:
            visited.add(current.id)
            parent = None
            for loc in self._current_campaign.locations.values():
                if loc.id == current.parent_location_id:
                    parent = loc
                    break
            if parent:
                ancestors.insert(0, {"id": parent.id, "name": parent.name, "scale": parent.location_scale})
                current = parent
            else:
                break

        # Add root if exists and not already in ancestors
        root = self.get_root_location()
        if root and (not ancestors or ancestors[0]["id"] != root.id):
            # Check if location is actually descended from root
            if location.parent_location_id is None and location.id != root.id:
                # Orphaned location - implicitly child of root
                ancestors.insert(0, {"id": root.id, "name": root.name, "scale": root.location_scale})

        # Build descendants tree
        def build_descendants_tree(loc_id: str) -> dict:
            loc = None
            for location_obj in self._current_campaign.locations.values():
                if location_obj.id == loc_id:
                    loc = location_obj
                    break

            if not loc:
                return {}

            children = []
            for child_id in loc.child_locations:
                child_tree = build_descendants_tree(child_id)
                if child_tree:
                    children.append(child_tree)

            return {
                "id": loc.id,
                "name": loc.name,
                "scale": loc.location_scale,
                "children": children
            }

        descendants = build_descendants_tree(location_id)

        return {
            "ancestors": ancestors,
            "current": {"id": location.id, "name": location.name, "scale": location.location_scale},
            "descendants": descendants.get("children", [])
        }

    def get_locations_by_scale(self, scale: LocationScale) -> list[Location]:
        """Get all locations at a specific scale level."""

        if not self._current_campaign:
            raise ValueError("No current campaign")

        return [
            loc for loc in self._current_campaign.locations.values()
            if loc.location_scale == scale
        ]

    def get_current_map_name(self) -> str | None:
        """Get the name of the current hex map based on current location.

        Returns the primary_map from:
        1. The current location (if it has one)
        2. The current location's parent (recursively up the hierarchy)
        3. None if no map found
        """
        if not self._current_campaign:
            return None

        # Get current location name from game state
        current_loc_name = self._current_campaign.game_state.current_location
        if not current_loc_name:
            return None

        # Find the current location object
        current_location = self.get_location(current_loc_name)
        if not current_location:
            return None

        # Check if current location has a map
        if current_location.primary_map:
            return current_location.primary_map

        # Recursively check parent locations
        visited = set()  # Prevent infinite loops
        current = current_location

        while current.parent_location_id and current.id not in visited:
            visited.add(current.id)

            # Find parent location by ID
            parent = None
            for loc in self._current_campaign.locations.values():
                if loc.id == current.parent_location_id:
                    parent = loc
                    break

            if not parent:
                break

            if parent.primary_map:
                return parent.primary_map

            current = parent

        return None

    # Map Integration
    def sync_location_with_poi(self, location_id: str, poi_id: str) -> None:
        """Synchronize a Location with its corresponding PointOfInterest."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        # Find location
        location = None
        for loc in self._current_campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        if not location:
            raise ValueError(f"Location with ID '{location_id}' not found")

        # Find POI in any hex map
        poi = None
        map_name = None
        for hex_map in self._current_campaign.hex_maps.values():
            for hex_obj in hex_map.hexes.values():
                for p in hex_obj.pois:
                    if p.id == poi_id:
                        poi = p
                        map_name = hex_map.name
                        break
                if poi:
                    break
            if poi:
                break

        if not poi:
            raise ValueError(f"POI with ID '{poi_id}' not found in any hex map")

        # Sync: set location's primary_map and hex_coordinate from POI
        from .models import HexCoordinate

        location.primary_map = map_name

        # Find the hex containing this POI
        for hex_map in self._current_campaign.hex_maps.values():
            if hex_map.name == map_name:
                for hex_obj in hex_map.hexes.values():
                    if any(p.id == poi_id for p in hex_obj.pois):
                        location.hex_coordinate = HexCoordinate(
                            x=hex_obj.coordinate.x,
                            y=hex_obj.coordinate.y
                        )
                        break

        # Sync POI's location_id
        poi.location_id = location_id

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Synced location '{location.name}' with POI '{poi.name}'")

    def get_locations_on_map(self, map_name: str) -> list[Location]:
        """Get all locations that appear on a specific map."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        return [
            loc for loc in self._current_campaign.locations.values()
            if loc.primary_map == map_name
        ]

    def update_location_coordinate(
        self,
        location_id: str,
        map_name: str,
        coordinate: HexCoordinate
    ) -> None:
        """Update location's coordinate on a map (syncs with POI if exists)."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        # Find location
        location = None
        for loc in self._current_campaign.locations.values():
            if loc.id == location_id:
                location = loc
                break

        if not location:
            raise ValueError(f"Location with ID '{location_id}' not found")

        # Update location
        location.primary_map = map_name
        location.hex_coordinate = coordinate

        # Find and update POI if it exists
        for hex_map in self._current_campaign.hex_maps.values():
            for hex_obj in hex_map.hexes.values():
                for poi in hex_obj.pois:
                    if poi.location_id == location_id:
                        # Move POI to new hex if needed
                        if hex_obj.coordinate.x != coordinate.x or hex_obj.coordinate.y != coordinate.y:
                            # Remove from old hex
                            hex_obj.pois = [p for p in hex_obj.pois if p.id != poi.id]

                            # Add to new hex
                            target_hex = hex_map.get_hex(coordinate)
                            if target_hex:
                                target_hex.pois.append(poi)
                            else:
                                # Create new hex if it doesn't exist
                                from .models import Hex
                                new_hex = Hex(
                                    coordinate=coordinate,
                                    terrain=hex_map.default_terrain
                                )
                                new_hex.pois.append(poi)
                                hex_map.set_hex(new_hex)

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Updated coordinate for '{location.name}' on map '{map_name}'")

    # Quest Management
    def add_quest(self, quest: Quest) -> None:
        """Add a quest to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.quests[quest.title] = quest
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_quest(self, title: str) -> Quest | None:
        """Get a quest by title."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not title:
            raise ValueError("Empty quest title")
        return self._current_campaign.quests.get(title)

    def update_quest_status(self, title: str, status: str) -> None:
        """Update a quest's status."""
        quest = self.get_quest(title)
        if quest:
            quest.status = status
            self._current_campaign.updated_at = datetime.now()  # type: ignore
            self._save_campaign()
        else:
            raise ValueError(f"No such quest {title}")

    def list_quests(self, status: str | None = None) -> list[str]:
        """List quest titles, optionally filtered by status."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        quests = self._current_campaign.quests
        if status:
            return [title for title, quest in quests.items() if quest.status == status]
        return list(quests.keys())

    # Game State Management
    def update_game_state(self, **kwargs) -> None:
        """Update the game state."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        game_state = self._current_campaign.game_state
        for key, value in kwargs.items():
            if hasattr(game_state, key):
                setattr(game_state, key, value)

        game_state.updated_at = datetime.now()
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_game_state(self) -> GameState | None:
        """Get the current game state."""
        if not self._current_campaign:
            return None
        return self._current_campaign.game_state

    # Session Management
    def add_session_note(self, session_note: SessionNote) -> None:
        """Add a session note."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.sessions.append(session_note)
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_sessions(self) -> list[SessionNote]:
        """Get all session notes."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return self._current_campaign.sessions

    # Adventure Log / Events
    def add_event(self, event: AdventureEvent) -> None:
        """Add an event to the adventure log."""
        logger.info(f"➕ Adding event: '{event.title}' ({event.event_type})")
        self._events.append(event)
        self._save_events()
        logger.debug("✅ Event added and log saved.")

    def get_events(
        self, limit: int | None = None, event_type: str | None = None, campaign: str | None = None
    ) -> list[AdventureEvent]:
        """Get adventure events, optionally filtered."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if campaign:
            events = [e for e in events if e.campaign == campaign]

        # Sort by timestamp (newest first)
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        if limit:
            events = events[:limit]

        return events

    def search_events(self, query: str) -> list[AdventureEvent]:
        """Search events by title or description."""
        query_lower = query.lower()
        return [
            event
            for event in self._events
            if query_lower in event.title.lower() or query_lower in event.description.lower()
        ]

    # Transcripts (backward compatibility methods)
    def get_transcript(
        self, campaign_name: str | None = None, session_number: int | None = None
    ) -> TranscriptTree | None:
        """Get a transcript tree. Now returns TranscriptTree (new format)."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
        else:
            campaign = self.get_campaign(campaign_name)

        if session_number is None:
            session_number = campaign.game_state.current_session if campaign and campaign.game_state else 1

        return self._load_transcript(campaign.name, session_number)

    def add_transcript_entry(
        self,
        player_entry: str,
        game_response: str,
        campaign_name: str | None = None,
        session_number: int | None = None,
    ) -> TranscriptTree:
        """Add a transcript entry. Now uses new TranscriptTree format internally."""
        if campaign_name is None:
            campaign = self.get_current_campaign()
            if not campaign:
                raise ValueError("No current campaign")
            campaign_name = campaign.name
        else:
            campaign = self.get_campaign(campaign_name)
            campaign_name = campaign.name

        if session_number is None:
            campaign_obj = self.get_current_campaign()
            session_number = campaign_obj.game_state.current_session if campaign_obj else 0

        # Add the interaction using new API
        self.add_transcript_interaction(
            user_text=player_entry,
            responses=[{"type": "text", "content": game_response}],
            campaign_name=campaign_name,
            session_number=session_number
        )

        # Return the updated transcript
        transcript = self._load_transcript(campaign_name, session_number)
        if transcript is None:
            raise ValueError("Failed to load transcript after adding entry")
        return transcript

    # HexMap Management
    def add_hex_map(self, hex_map: HexMap) -> None:
        """Add a hex map to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"➕ Adding hex map '{hex_map.name}' to campaign '{self._current_campaign.name}'.")
        self._current_campaign.hex_maps[hex_map.name] = hex_map
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.debug(f"✅ Hex map '{hex_map.name}' added successfully.")

    def get_hex_map(self, name: str) -> HexMap | None:
        """Get a hex map by name."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        if not name:
            raise ValueError("Empty hex map name")
        return self._current_campaign.hex_maps.get(name)

    def delete_hex_map(self, name: str) -> None:
        """Delete a hex map from the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        if name in self._current_campaign.hex_maps:
            logger.info(f"🗑️ Deleting hex map '{name}' from campaign '{self._current_campaign.name}'.")
            del self._current_campaign.hex_maps[name]
            self._current_campaign.updated_at = datetime.now()
            self._save_campaign()
            logger.debug(f"✅ Hex map '{name}' deleted successfully.")
        else:
            logger.warning(f"⚠️ Hex map '{name}' not found for deletion.")

    def list_hex_maps(self) -> list[str]:
        """List all hex map names in the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")
        return list(self._current_campaign.hex_maps.keys())
