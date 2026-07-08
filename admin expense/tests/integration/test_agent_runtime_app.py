import json
import logging

import pytest
from google.adk.events.event import Event

from expense_agent.agent_runtime_app import AgentEngineApp


@pytest.fixture
def agent_app(monkeypatch: pytest.MonkeyPatch) -> AgentEngineApp:
    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")

    from expense_agent.agent_runtime_app import agent_runtime

    agent_runtime.set_up()
    return agent_runtime


@pytest.mark.asyncio
async def test_agent_stream_query(agent_app: AgentEngineApp) -> None:
    expense_event = {
        "data": {
            "amount": 45.00,
            "currency": "USD",
            "submitter": "bob@company.com",
            "category": "meals",
            "description": "Team lunch",
            "date": "2026-04-12",
        }
    }
    message = json.dumps(expense_event)
    events = []
    async for event in agent_app.async_stream_query(message=message, user_id="test"):
        events.append(event)
    assert len(events) > 0, "Expected at least one chunk in response"

    has_text_content = False
    for event in events:
        validated_event = Event.model_validate(event)
        content = validated_event.content
        if (
            content is not None
            and content.parts
            and any(part.text for part in content.parts)
        ):
            has_text_content = True
            break

    assert has_text_content, "Expected at least one event with text content"


def test_agent_feedback(agent_app: AgentEngineApp) -> None:
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "user_id": "test-user-456",
        "session_id": "test-session-456",
    }

    agent_app.register_feedback(feedback_data)

    with pytest.raises(ValueError):
        invalid_feedback = {
            "score": "invalid",
            "text": "Bad feedback",
            "user_id": "test-user-789",
            "session_id": "test-session-789",
        }
        agent_app.register_feedback(invalid_feedback)

    logging.info("All assertions passed for agent feedback test")
