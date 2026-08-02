import logging
import re

from openpyxl import load_workbook
from strands.types.tools import ToolResult, ToolUse

logger = logging.getLogger("hercules")

# Regex to extract http(s) URLs from text
URL_RE = re.compile(r"https?://[^\s,;\)\]\}'\"]+")
MAX_URLS_PER_SHEET = 50

TOOL_SPEC = {
    "name": "describe_excel_workbook",
    "description": "Describe the structure of an Excel workbook. These are usually workout programs where workout structure, progression methods, etc. are described. This is used to understand the layout and content of the workout program without reading the entire file contents. Returns workbook structure, sheet names, columns, row counts.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "workbook_file_path": {
                    "type": "string",
                    "description": "File path for the temporary Excel workbook. It must include the file extension.",
                }
            },
            "required": ["workbook_file_path"],
        }
    },
}


def describe_excel_workbook(tool: ToolUse, **kwargs) -> ToolResult:
    """
    Describe the structure of an Excel workbook (`.xlsx` file format).
    These are usually workout programs where workout structure, progression methods, etc. are described.
    This is used to understand the layout and content of the workout program without reading the entire file contents.
    Returns workbook structure, sheet names, columns, row counts.
    """
    try:
        tool_use_id = tool["toolUseId"]
        tool_input = tool["input"]
        workbook_file_path = tool_input["workbook_file_path"]

        logger.info(f"Received request to describe workbook at {workbook_file_path}")

        if not workbook_file_path:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [{"text": "No workbook data has been provided."}],
            }

        sample_max_rows = 10
        sample_max_cols = 20

        workbook = load_workbook(filename=workbook_file_path, read_only=True)
        logger.info(f"Workbook loaded successfully from {workbook_file_path}")

        workbook_sheet_names = workbook.sheetnames
        sheet_details = {}
        aggregated_urls = []
        aggregated_seen = set()
        for sheet_name in workbook_sheet_names:
            sheet = workbook[sheet_name]
            sample_rows = [
                row
                for row in sheet.iter_rows(
                    max_row=sample_max_rows, max_col=sample_max_cols, values_only=True
                )
            ]

            # Extract URLs from sample rows
            urls = []
            seen = set()
            for row in sample_rows:
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

            # Add found URLs to aggregated list (deduplicated globally)
            for u in urls:
                if u not in aggregated_seen:
                    aggregated_seen.add(u)
                    aggregated_urls.append(u)

            sheet_details[sheet_name] = {
                "row_count": sheet.max_row,
                "column_count": sheet.max_column,
                # Sample the sheet to get an idea as to what is in it
                "sample_rows": sample_rows,
                "urls": urls,
            }

        logger.info(
            f"Workbook description generated successfully for {workbook_file_path}"
        )

        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {
                    "text": f"{workbook_file_path} workbook structure has been analysed successfully. Contents have been sampled with a maximum of {sample_max_rows} rows and {sample_max_cols} columns."
                },
                {"json": {"sheets": sheet_details, "urls": aggregated_urls}},
            ],
        }
    except Exception as e:
        logger.exception(f"Error analysing workbook structure: {e}")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Failed to analyse workbook structure: {e!s}"}],
        }
