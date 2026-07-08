import json
import os
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from expense_agent.agent import root_agent


def generate_traces():
    dataset_path = "tests/eval/datasets/basic-dataset.json"
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return

    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    eval_cases = dataset.get("eval_cases", [])
    output_cases = []

    agents_map = {
        "expense_processor": {
            "agent_id": "expense_processor",
            "agent_type": "Workflow",
        },
        "review_agent": {
            "agent_id": "review_agent",
            "agent_type": "LlmAgent",
            "instruction": "You are an expense review agent. Analyze the expense and check for risk factors...",
        },
    }

    print(f"Generating traces for {len(eval_cases)} evaluation cases...")

    for case in eval_cases:
        case_id = case["eval_case_id"]
        prompt_text = case["prompt"]["parts"][0]["text"]
        print(f"\nProcessing case: {case_id}")

        session_service = InMemorySessionService()
        user_id = f"eval-user-{case_id}"
        session_id = f"eval-session-{uuid.uuid4()}"

        session = session_service.create_session_sync(
            user_id=user_id, app_name="expense_agent", session_id=session_id
        )
        runner = Runner(
            agent=root_agent, session_service=session_service, app_name="expense_agent"
        )

        message = types.Content(
            role="user", parts=[types.Part.from_text(text=prompt_text)]
        )

        events = list(
            runner.run(new_message=message, user_id=user_id, session_id=session.id)
        )

        has_request_input = False
        is_injection = False

        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if (
                        part.function_call
                        and part.function_call.name == "adk_request_input"
                    ):
                        has_request_input = True
                        args = part.function_call.args or {}
                        message_text = args.get("message", "")
                        if "SECURITY WARNING" in message_text:
                            is_injection = True
                        break

        if has_request_input:
            decision_text = "reject" if is_injection else "approve"
            print(
                f" -> Paused for HITL. Automating decision: '{decision_text}' (is_injection={is_injection})"
            )

            resume_message = types.Content(
                role="user", parts=[types.Part.from_text(text=decision_text)]
            )

            resume_events = list(
                runner.run(
                    new_message=resume_message, user_id=user_id, session_id=session.id
                )
            )
            events.extend(resume_events)

        session_data = session_service.get_session_sync(
            user_id=user_id, app_name="expense_agent", session_id=session.id
        )

        turns = []
        current_turn = None
        for ev in session_data.events:
            if ev.author == "user":
                if current_turn is not None:
                    turns.append(current_turn)
                current_turn = {"turn_index": len(turns), "events": []}

            if ev.content:
                content_dict = ev.content.model_dump(exclude_none=True)
                agent_event = {
                    "author": ev.author or "expense_processor",
                    "content": content_dict,
                }
                if current_turn is not None:
                    current_turn["events"].append(agent_event)

        if current_turn is not None:
            turns.append(current_turn)

        output_cases.append(
            {
                "eval_case_id": case_id,
                "agent_data": {"agents": agents_map, "turns": turns},
            }
        )

    output_dir = "artifacts/traces"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "generated_traces.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"eval_cases": output_cases}, f, indent=2)

    print(f"\nSaved generated traces to {output_path}")


if __name__ == "__main__":
    generate_traces()
