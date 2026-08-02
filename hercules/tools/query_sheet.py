import base64
import datetime as _dt
import logging
import re

from openpyxl import load_workbook
from strands.types.tools import ToolResult, ToolUse

logger = logging.getLogger("hercules")

# Regex to extract http(s) URLs from text
URL_RE = re.compile(r"https?://[^\s,;\)\]\}'\"]+")
MAX_URLS_PER_SHEET = 50

TOOL_SPEC = {
    "name": "query_sheet",
    "description": "Get the relevant rows and columns from a worksheet to understand a workout program.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "workbook_file_path": {
                    "type": "string",
                    "description": "File path for the temporary Excel workbook. It must include the file extension.",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Sheet name of interest within the Excel workbook.",
                },
            },
            "required": ["workbook_file_path", "sheet_name"],
        }
    },
}


def query_sheet(tool: ToolUse, **kwargs) -> ToolResult:
    """
    Get the relevant rows and columns from a worksheet to understand a workout program.
    Returns the relevant rows and columns from a worksheet to understand a workout program.
    """
    try:
        tool_use_id = tool["toolUseId"]
        tool_input = tool["input"]
        workbook_file_path = tool_input["workbook_file_path"]
        workbook_sheet_name = tool_input["sheet_name"]

        if not workbook_file_path:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [{"text": "No workbook data has been provided."}],
            }

        workbook = load_workbook(filename=workbook_file_path, read_only=True)
        if workbook_sheet_name not in workbook.sheetnames:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": f"Sheet name {workbook_sheet_name} not found in workbook."}
                ],
            }

        # We set this in order to not overwhelm the context window with too much data
        # TODO: Look into context offloading via retrieval to be able to retrieve more data without overwhelming the context window
        max_rows = 500
        max_cols = 50
        sheet = workbook[workbook_sheet_name]
        sheet_rows = [
            row
            for row in sheet.iter_rows(
                max_row=max_rows, max_col=max_cols, values_only=True
            )
        ]

        # Serialize cell values so the result is JSON-safe (datetimes -> ISO, bytes -> base64)
        # Convert to a sparse representation: keep only non-null cells as {col, value} entries
        serialized_rows = [
            [
                {"col": i + 1, "value": _serialize_cell(c)}
                for i, c in enumerate(row)
                if c is not None
            ]
            for row in sheet_rows
        ]
        logger.info(f"Serialized rows: {serialized_rows}")
        # Extract URLs from the retrieved rows so the agent can decide to fetch them
        urls = []
        seen = set()
        for row in sheet_rows:
            for cell in row:
                if isinstance(cell, str):
                    for m in URL_RE.findall(cell):
                        if m not in seen:
                            seen.add(m)
                            urls.append(m)
                            if len(urls) >= MAX_URLS_PER_SHEET:
                                break
                if len(urls) >= MAX_URLS_PER_SHEET:
                    break
            if len(urls) >= MAX_URLS_PER_SHEET:
                break

        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {
                    "text": f"Workbook has been analysed successfully. The first {len(sheet_rows)} rows and up to {max_cols} columns have been retrieved. Only non-empty cells are returned."
                },
                {"json": {"rows": serialized_rows, "urls": urls}},
            ],
        }
    except Exception as e:
        logger.exception(f"Error analysing workbook structure: {e}")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Failed to analyse workbook structure: {e!s}"}],
        }


def _serialize_cell(cell):
    """
    Serialize Excel cell values to be JSON-safe.

    :param cell: The cell value to serialize.
    :returns: A JSON-safe representation of the cell value.

    """
    if isinstance(cell, (_dt.datetime, _dt.date, _dt.time)):
        try:
            return cell.isoformat()
        except Exception:
            return str(cell)
    if isinstance(cell, (bytes, bytearray)):
        return base64.b64encode(cell).decode("ascii")
    return cell
