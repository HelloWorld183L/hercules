"""Module for building the Hercules agent."""

import os
from uuid import uuid4

import valkey
from dotenv import load_dotenv
from strands import Agent, AgentSkills
from strands.models.openai import OpenAIModel
from strands_tools import calculator, current_time, file_read, mem0_memory
from strands_tools.tavily import tavily_extract, tavily_search
from strands_valkey_session_manager import ValkeySessionManager

from hercules.tools import (
    create_moving_avg_graph,
    create_volume_graph,
    describe_excel_workbook,
    extract_workoutlog_stats,
    query_sheet,
    search_knowledgebase,
)


def build_agent() -> Agent:
    load_dotenv()

    strands_model_id = os.getenv("STRANDS_MODEL_ID")
    if not strands_model_id:
        raise RuntimeError("STRANDS_MODEL_ID environment variable not set")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    model = OpenAIModel(
        client_args={"api_key": openai_api_key}, model_id=strands_model_id
    )

    plugin = AgentSkills(skills=os.path.join(os.path.dirname(__file__), "skills"))

    # Load SOP
    with open(os.path.join(os.path.dirname(__file__), "sop.md"), "r") as f:
        system_prompt = f.read()

    # Valkey/Redis connection configured via environment so containers stay stateless
    valkey_host = os.getenv("VALKEY_HOST")
    valkey_port = int(os.getenv("VALKEY_PORT"))
    valkey_password = os.getenv("VALKEY_PASSWORD")

    if not valkey_host or not valkey_port:
        raise RuntimeError(
            "VALKEY_HOST and VALKEY_PORT environment variables must be set"
        )

    client = valkey.Valkey(
        host=valkey_host,
        port=valkey_port,
        password=valkey_password,
        decode_responses=True,
    )
    # Create a session manager with a unique session ID
    session_id = str(uuid4())
    session_manager = ValkeySessionManager(session_id=session_id, client=client)

    agent_id = str(uuid4())
    agent = Agent(
        agent_id=agent_id,
        model=model,
        tools=[
            calculator,
            current_time,
            mem0_memory,
            create_moving_avg_graph,
            describe_excel_workbook,
            query_sheet,
            create_volume_graph,
            extract_workoutlog_stats,
            tavily_search,
            tavily_extract,
            file_read,
            search_knowledgebase,
        ],
        plugins=[plugin],
        system_prompt=system_prompt,
        session_manager=session_manager,
    )

    return agent
