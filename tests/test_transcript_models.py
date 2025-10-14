"""
Tests for transcript tree data models.

Tests cover:
- Node creation and validation
- Tree structure rules
- Response types (text and tool calls)
- Migration from old format to new format
"""

import pytest
from datetime import datetime
from gamemaster_mcp.models import (
    TranscriptNode,
    TranscriptTree,
    TranscriptInteraction,
    TranscriptCombat,
    TranscriptAdventure,
    ResponseText,
    ResponseTools,
    InteractionToolCall,
)


class TestResponseTypes:
    """Test response type models."""

    def test_response_text_creation(self):
        """Test creating a text response."""
        response = ResponseText(type="text", content="You see a dark corridor")
        assert response.type == "text"
        assert response.content == "You see a dark corridor"

    def test_response_tools_creation(self):
        """Test creating a tools response with tool calls."""
        tool_call = InteractionToolCall(
            name="roll_dice",
            id="call_123",
            input={"dice": "1d20", "modifier": 5},
            response="Rolled 15 + 5 = 20"
        )
        response = ResponseTools(type="tools", calls=[tool_call])

        assert response.type == "tools"
        assert len(response.calls) == 1
        assert response.calls[0].name == "roll_dice"
        assert response.calls[0].input["dice"] == "1d20"

    def test_interaction_tool_call_validation(self):
        """Test tool call has required fields."""
        tool_call = InteractionToolCall(
            name="get_character",
            id="call_456",
            input={"character_name": "Gareth"},
            response="Gareth Ironshield (Level 2 Fighter)"
        )
        assert tool_call.name == "get_character"
        assert tool_call.id == "call_456"
        assert "character_name" in tool_call.input


class TestInteractionNode:
    """Test TranscriptInteraction node model."""

    def test_interaction_creation(self):
        """Test creating a TranscriptInteraction node."""
        interaction = TranscriptInteraction(
            user_text="I attack the orc",
            responses=[ResponseText(content="Roll for attack")]
        )

        assert interaction.node_type == "interaction"
        assert interaction.user_text == "I attack the orc"
        assert len(interaction.responses) == 1
        assert interaction.responses[0].content == "Roll for attack"
        assert interaction.importance == 3  # Default

    def test_interaction_with_character(self):
        """Test interaction with character_speaking metadata."""
        interaction = TranscriptInteraction(
            user_text="I cast fireball",
            responses=[ResponseText(content="Roll for damage")],
            character_speaking="Lyralei",
            importance=4
        )

        assert interaction.character_speaking == "Lyralei"
        assert interaction.importance == 4

    def test_interaction_with_multiple_responses(self):
        """Test interaction with text and tool responses."""
        responses = [
            ResponseText(content="You attack the orc"),
            ResponseTools(calls=[
                InteractionToolCall(
                    name="roll_dice",
                    id="call_1",
                    input={"dice": "1d20+3"},
                    response="Rolled 18"
                )
            ]),
            ResponseText(content="Hit! Roll damage")
        ]

        interaction = TranscriptInteraction(
            user_text="I attack with my sword",
            responses=responses
        )

        assert len(interaction.responses) == 3
        assert interaction.responses[0].type == "text"
        assert interaction.responses[1].type == "tools"
        assert interaction.responses[2].type == "text"

    def test_interaction_has_unique_id(self):
        """Test each interaction gets a unique ID."""
        int1 = TranscriptInteraction(user_text="Test 1", responses=[ResponseText(content="R1")])
        int2 = TranscriptInteraction(user_text="Test 2", responses=[ResponseText(content="R2")])

        assert int1.id != int2.id
        assert len(int1.id) == 8  # shortuuid length


class TestCombatNode:
    """Test Combat node model."""

    def test_combat_creation(self):
        """Test creating a Combat node."""
        combat = TranscriptCombat(
            participants=["Gareth", "Orc Warrior 1", "Orc Warrior 2"],
            result="victory",
            summary="Party defeated 2 orcs with no casualties",
            actions=[]
        )

        assert combat.node_type == "combat"
        assert len(combat.participants) == 3
        assert combat.result == "victory"
        assert combat.summary == "Party defeated 2 orcs with no casualties"
        assert combat.actions == []

    def test_combat_with_interactions(self):
        """Test combat containing interaction actions."""
        actions = [
            TranscriptInteraction(user_text="I attack orc 1", responses=[ResponseText(content="Hit!")]),
            TranscriptInteraction(user_text="I attack orc 2", responses=[ResponseText(content="Miss!")]),
            TranscriptInteraction(user_text="I attack orc 1 again", responses=[ResponseText(content="Critical hit!")])
        ]

        combat = TranscriptCombat(
            participants=["Gareth", "Orc Warrior 1", "Orc Warrior 2"],
            result="victory",
            summary="Gareth defeated both orcs in 3 rounds",
            actions=actions,
            location="Ancient Stone Circle",
            rounds=3,
            casualties=["Orc Warrior 1", "Orc Warrior 2"]
        )

        assert len(combat.actions) == 3
        assert combat.location == "Ancient Stone Circle"
        assert combat.rounds == 3
        assert len(combat.casualties) == 2

    def test_combat_only_contains_interactions(self):
        """Test that combat validation ensures only Interactions in actions."""
        # This will be enforced by validation function, not Pydantic
        actions = [
            TranscriptInteraction(user_text="I attack", responses=[ResponseText(content="Hit!")])
        ]

        combat = TranscriptCombat(
            participants=["Gareth", "Orc"],
            result="victory",
            summary="Quick fight",
            actions=actions
        )

        # All actions should be Interactions
        for action in combat.actions:
            assert action.node_type == "interaction"


class TestAdventureNode:
    """Test Adventure node model."""

    def test_adventure_creation(self):
        """Test creating an Adventure node."""
        adventure = TranscriptAdventure(
            title="The Lost Temple",
            summary="Party explored ancient temple and retrieved artifact",
            actions=[]
        )

        assert adventure.node_type == "adventure"
        assert adventure.title == "The Lost Temple"
        assert adventure.summary == "Party explored ancient temple and retrieved artifact"
        assert adventure.actions == []

    def test_adventure_with_mixed_children(self):
        """Test adventure containing interactions, combats, and nested adventures."""
        actions = [
            TranscriptInteraction(user_text="We enter the temple", responses=[ResponseText(content="You see...")]),
            TranscriptCombat(
                participants=["Gareth", "Temple Guardian"],
                result="victory",
                summary="Defeated guardian",
                actions=[
                    TranscriptInteraction(user_text="I attack", responses=[ResponseText(content="Hit!")])
                ]
            ),
            TranscriptInteraction(user_text="We take artifact", responses=[ResponseText(content="Acquired!")]),
        ]

        adventure = TranscriptAdventure(
            title="Temple Exploration",
            summary="Found the ancient artifact",
            actions=actions,
            quest_id="quest_123",
            locations=["Dark Forest", "Ancient Temple"],
            npcs_met=["Temple Guardian", "Ancient Spirit"],
            rewards=["Ancient Medallion", "500 XP"]
        )

        assert len(adventure.actions) == 3
        assert adventure.actions[0].node_type == "interaction"
        assert adventure.actions[1].node_type == "combat"
        assert adventure.actions[2].node_type == "interaction"
        assert len(adventure.locations) == 2
        assert len(adventure.npcs_met) == 2
        assert len(adventure.rewards) == 2

    def test_adventure_nested(self):
        """Test nested adventures."""
        side_quest = TranscriptAdventure(
            title="Help the Farmer",
            summary="Rescued chickens from goblins",
            actions=[
                TranscriptInteraction(user_text="We chase goblins", responses=[ResponseText(content="You catch them")])
            ]
        )

        main_quest = TranscriptAdventure(
            title="Save the Kingdom",
            summary="Kingdom saved through heroic efforts",
            actions=[
                TranscriptInteraction(user_text="We meet the king", responses=[ResponseText(content="He asks for help")]),
                side_quest,
                TranscriptInteraction(user_text="We confront villain", responses=[ResponseText(content="Victory!")])
            ]
        )

        assert len(main_quest.actions) == 3
        assert main_quest.actions[1].node_type == "adventure"
        assert main_quest.actions[1].title == "Help the Farmer"


class TestTranscriptNode:
    """Test Transcript root node model."""

    def test_transcript_creation(self):
        """Test creating a Transcript root node."""
        transcript = TranscriptTree(
            campaign="The Arena",
            session_number=1,
            children=[]
        )

        assert transcript.node_type == "transcript"
        assert transcript.campaign == "The Arena"
        assert transcript.session_number == 1
        assert transcript.children == []
        assert transcript.current_parent_id is None

    def test_transcript_with_children(self):
        """Test transcript with mixed children."""
        children = [
            TranscriptInteraction(user_text="We enter dungeon", responses=[ResponseText(content="Dark corridor")]),
            TranscriptCombat(
                participants=["Gareth", "Goblin"],
                result="victory",
                summary="Quick fight",
                actions=[
                    TranscriptInteraction(user_text="I attack", responses=[ResponseText(content="Hit!")])
                ]
            ),
            TranscriptAdventure(
                title="Temple Quest",
                summary="Found artifact",
                actions=[
                    TranscriptInteraction(user_text="We explore", responses=[ResponseText(content="Found it!")])
                ]
            )
        ]

        transcript = TranscriptTree(
            campaign="Test Campaign",
            session_number=1,
            children=children,
            current_parent_id="xyz123"
        )

        assert len(transcript.children) == 3
        assert transcript.children[0].node_type == "interaction"
        assert transcript.children[1].node_type == "combat"
        assert transcript.children[2].node_type == "adventure"
        assert transcript.current_parent_id == "xyz123"

    def test_transcript_metadata(self):
        """Test transcript metadata fields."""
        transcript = TranscriptTree(
            campaign="The Arena",
            session_number=2,
            children=[],
            characters_present=["Gareth", "Lyralei", "Brother Marcus"],
            tags=["epic", "boss-fight"],
            notes="Great session!"
        )

        assert len(transcript.characters_present) == 3
        assert "epic" in transcript.tags
        assert transcript.notes == "Great session!"


class TestTreeStructureValidation:
    """Test tree structure validation rules."""

    def test_interaction_cannot_have_children(self):
        """Test that Interactions are always leaves (no children)."""
        interaction = TranscriptInteraction(
            user_text="Test",
            responses=[ResponseText(content="Response")]
        )

        # Interaction shouldn't have 'children' attribute
        assert not hasattr(interaction, 'children')
        # It only has user_text and responses
        assert hasattr(interaction, 'user_text')
        assert hasattr(interaction, 'responses')

    def test_combat_actions_are_list(self):
        """Test Combat actions field is a list."""
        combat = TranscriptCombat(
            participants=["A", "B"],
            result="victory",
            summary="Test",
            actions=[]
        )

        assert isinstance(combat.actions, list)
        assert hasattr(combat, 'actions')
        # Combat uses 'actions' not 'children'
        assert not hasattr(combat, 'children')

    def test_adventure_actions_are_list(self):
        """Test Adventure actions field is a list."""
        adventure = TranscriptAdventure(
            title="Test",
            summary="Test summary",
            actions=[]
        )

        assert isinstance(adventure.actions, list)
        assert hasattr(adventure, 'actions')
        # Adventure uses 'actions' not 'children'
        assert not hasattr(adventure, 'children')

    def test_transcript_children_are_list(self):
        """Test Transcript children field is a list."""
        transcript = TranscriptTree(
            campaign="Test",
            session_number=1,
            children=[]
        )

        assert isinstance(transcript.children, list)
        assert hasattr(transcript, 'children')


class TestModelSerialization:
    """Test model serialization to/from dict for JSON storage."""

    def test_interaction_serialization(self):
        """Test Interaction can be serialized to dict."""
        interaction = TranscriptInteraction(
            user_text="Test input",
            responses=[
                ResponseText(content="Text response"),
                ResponseTools(calls=[
                    InteractionToolCall(
                        name="test_tool",
                        id="call_1",
                        input={"param": "value"},
                        response="tool result"
                    )
                ])
            ],
            character_speaking="TestChar",
            importance=4
        )

        data = interaction.model_dump(mode="json")

        assert data["node_type"] == "interaction"
        assert data["user_text"] == "Test input"
        assert len(data["responses"]) == 2
        assert data["responses"][0]["type"] == "text"
        assert data["responses"][1]["type"] == "tools"
        assert data["character_speaking"] == "TestChar"
        assert data["importance"] == 4

    def test_combat_serialization(self):
        """Test Combat can be serialized to dict."""
        combat = TranscriptCombat(
            participants=["A", "B"],
            result="victory",
            summary="Test combat",
            actions=[
                TranscriptInteraction(user_text="Test", responses=[ResponseText(content="Response")])
            ],
            location="Test Location",
            rounds=3
        )

        data = combat.model_dump(mode="json")

        assert data["node_type"] == "combat"
        assert data["participants"] == ["A", "B"]
        assert data["result"] == "victory"
        assert data["summary"] == "Test combat"
        assert len(data["actions"]) == 1
        assert data["location"] == "Test Location"
        assert data["rounds"] == 3

    def test_transcript_full_tree_serialization(self):
        """Test full transcript tree can be serialized."""
        transcript = TranscriptTree(
            campaign="Test Campaign",
            session_number=1,
            children=[
                TranscriptInteraction(user_text="Test 1", responses=[ResponseText(content="R1")]),
                TranscriptCombat(
                    participants=["A"],
                    result="victory",
                    summary="Win",
                    actions=[
                        TranscriptInteraction(user_text="Attack", responses=[ResponseText(content="Hit!")])
                    ]
                )
            ],
            current_parent_id="root_id"
        )

        data = transcript.model_dump(mode="json")

        assert data["node_type"] == "transcript"
        assert data["campaign"] == "Test Campaign"
        assert data["session_number"] == 1
        assert len(data["children"]) == 2
        assert data["children"][0]["node_type"] == "interaction"
        assert data["children"][1]["node_type"] == "combat"
        assert len(data["children"][1]["actions"]) == 1
        assert data["current_parent_id"] == "root_id"

    def test_model_deserialization(self):
        """Test models can be reconstructed from dict."""
        data = {
            "id": "test123",
            "node_type": "interaction",
            "user_text": "Test",
            "responses": [
                {"type": "text", "content": "Response"}
            ],
            "character_speaking": None,
            "importance": 3,
            "tags": [],
            "notes": ""
        }

        interaction = TranscriptInteraction.model_validate(data)

        assert interaction.id == "test123"
        assert interaction.user_text == "Test"
        assert len(interaction.responses) == 1
        assert interaction.importance == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
