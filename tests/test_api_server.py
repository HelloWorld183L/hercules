import importlib
import sys
from types import ModuleType, SimpleNamespace

from fastapi.testclient import TestClient


class DummyAgent:
    def __init__(
        self,
        result_message,
        image_bytes: bytes | None = None,
        image_format: str = "png",
    ):
        self._result_message = result_message
        if image_bytes is not None:
            self.messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "content": [
                                    {
                                        "image": {
                                            "format": image_format,
                                            "source": {"bytes": image_bytes},
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                }
            ]
        else:
            self.messages = [{"role": "user", "content": [{"text": "user"}]}]

    async def invoke_async(self, ctx):
        return SimpleNamespace(message=self._result_message)


def _load_app_with_agent(agent_instance):
    # Insert a fake hercules.agent module so import builds our dummy agent
    fake_mod = ModuleType("hercules.agent")

    def build_agent():
        return agent_instance

    fake_mod.build_agent = build_agent
    sys.modules["hercules.agent"] = fake_mod

    # Import/reload the api_server module so it constructs the agent at import
    api_server = importlib.reload(importlib.import_module("hercules.api_server"))
    return api_server.app


def test_health_endpoint():
    """
    Test that the /health endpoint returns a 200 OK response with the expected JSON payload.
    This test sets up a DummyAgent to avoid invoking the real agent and verifies that the health endpoint responds correctly.
    """

    # Agent not used for health; provide a minimal stub
    agent = DummyAgent(result_message="ok")
    app = _load_app_with_agent(agent)
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_invoke_returns_plain_string_message():
    """
    Test that the /invoke endpoint correctly handles an agent that returns a plain string as its message.
    The test sets up a DummyAgent that returns a simple string message and verifies that the API
    response contains the expected text and does not include an image payload.
    """

    # Agent returns a plain string as message
    result_message = "plain reply"
    agent = DummyAgent(result_message=result_message, image_bytes=None)
    app = _load_app_with_agent(agent)
    client = TestClient(app)

    r = client.post("/invoke", data={"content": "hi", "user_id": "user2"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "plain reply"
    assert "image" not in body
