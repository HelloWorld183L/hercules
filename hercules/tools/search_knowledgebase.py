"""
Module for the search_knowledgebase tool, which allows the agent to search for relevant documents
in the knowledge base using semantic similarity. This tool uses the vector_client to query the Qdrant
vector database and retrieve relevant documents based on the input query. The results include the text,
source, and relevance score of each document found in the knowledge base.
"""

import logging
from typing import Any

from dotenv import load_dotenv
from qdrant_client.http.models import ScoredPoint
from strands.types.tools import ToolResult, ToolUse

from hercules.vector_client import get_vector_client

logger = logging.getLogger("hercules")

load_dotenv()

DEFAULT_LIMIT_RESULTS = 5

TOOL_SPEC = {
    "name": "search_knowledgebase",
    "description": "Search for relevant documents (via semantic similarity) in the knowledge base that contain information about good training practices, nutrition, and recovery. Use this to inform your responses to the user, but do not return the results directly to the user. Instead, use the information from the search results to generate a helpful and accurate response to the user's query.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for finding relevant documents.",
                },
                "limit_results": {
                    "type": "string",
                    "description": "The maximum number of results to return.",
                },
            },
            "required": ["query"],
        }
    },
}


def search_knowledgebase(tool: ToolUse, **kwargs) -> ToolResult:
    """
    Search for relevant documents in the knowledge base.
    Returns the relevant documents from the knowledge base based on the query.
    """
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]
    query = tool_input["query"]
    limit_results = tool_input.get("limit_results", DEFAULT_LIMIT_RESULTS)

    if not query:
        logger.error("No query provided for knowledge base search.")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": "No query provided for knowledge base search."}],
        }

    # Search for relevant documents
    vector_client = get_vector_client()
    search_result = vector_client.search(query=query, limit=limit_results)

    no_relevant_docs_found = not search_result or len(search_result.points) == 0
    if no_relevant_docs_found:
        logger.info(
            f"No relevant documents found in the knowledge base. Search result: {search_result}"
        )
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": "No relevant documents found in the knowledge base."}],
        }

    logger.info(f"Knowledge base search successful. Search result: {search_result}")

    formatted_results = _format_search_results(search_result.points)
    logger.info(f"Knowledge base search results: {formatted_results}")
    return {
        "toolUseId": tool_use_id,
        "status": "success",
        "content": formatted_results,
    }


def _format_search_results(
    search_result_points: list[ScoredPoint],
) -> list[dict[str, Any]]:
    """
    Helper function to format the search results from the knowledge base.
    Returns a list of dictionaries containing the text, source, and score of each document.
    """
    formatted_results = []
    for result in search_result_points:
        payload = {}
        score = None

        # If result is a tuple/list, try to find payload dict and numeric score inside it
        if isinstance(result, (tuple, list)):
            for item in result:
                if isinstance(item, dict):
                    payload = item
                elif isinstance(item, (int, float)):
                    score = item

            # Fallback: common tuple shapes -> (id, payload, score) or (payload, score)
            if not payload:
                if len(result) >= 2 and isinstance(result[1], dict):
                    payload = result[1]
                elif len(result) >= 1 and isinstance(result[0], dict):
                    payload = result[0]
            if score is None:
                # try last element as score
                try:
                    last = result[-1]
                    if isinstance(last, (int, float)):
                        score = float(last)
                except (KeyError, IndexError, TypeError, ValueError):
                    score = None
        else:
            # ScoredPoint-like object
            payload = getattr(result, "payload", {}) or {}
            score = getattr(result, "score", None)

        formatted_results.append(
            {
                "text": payload.get("text", ""),
                "source": payload.get("source", ""),
                "score": score,
            }
        )

    return formatted_results
