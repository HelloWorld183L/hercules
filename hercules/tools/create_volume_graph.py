import logging

from matplotlib import pyplot as plt
import io

from strands.types.tools import ToolUse, ToolResult

logger = logging.getLogger("hercules")

TOOL_SPEC = {
    "name": "create_volume_graph",
    "description": "Create a volume graph from the provided muscle group and volume data.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "muscle_groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of muscle groups for which to display volume.",
                },
                "volume_per_muscle_group": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of volume values as strings that can be converted to floats. This represents the sets for a muscle group and MUST NOT be a range. If it is a range, round up to the nearest whole number.",
                },
                "workout_program_name": {
                    "type": "string",
                    "description": "Name of the workout program for which the volume graph is being created. This is used for titling the graph.",
                },
            },
            "required": ["muscle_groups", "volume_per_muscle_group"],
        }
    },
}


def create_volume_graph(tool: ToolUse, **kwargs) -> ToolResult:
    """
    Creates a volume graph from the provided data and returns it as a BytesIO object containing the PNG image data.

    This function expects the tool input to contain two lists: 'muscle_groups' and 'volume_per_muscle_group'. The 'muscle_groups' list should contain muscle group names, and the 'volume_per_muscle_group' list should contain numeric values as strings. The function will convert the volume values to floats and generate a bar graph showing the volume for each muscle group. The resulting graph is returned as a PNG image in a BytesIO object.

    The tool is expected to be used for visualizing trends in user metrics over time, such as tracking progress towards fitness goals. The graph can help users understand how their metrics are changing and identify any patterns or trends.
    """
    try:
        tool_use_id = tool["toolUseId"]
        tool_input = tool["input"]
        muscle_groups = tool_input["muscle_groups"]
        volume = tool_input["volume_per_muscle_group"]
        workout_program_name = tool_input.get("workout_program_name")

        if not muscle_groups:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {"text": "No muscle groups were provided for volume graph."}
                ],
            }
        if not volume:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {
                        "text": "No volume values per muscle group were provided for volume graph."
                    }
                ],
            }

        try:
            volume_numbers = [float(x.strip()) for x in volume]
        except ValueError:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [
                    {
                        "text": "Invalid volume values provided. All values must be convertible to floats. DO NOT provide volume ranges. Round up if needed."
                    }
                ],
            }

        plt.figure(figsize=(12, 5))
        plt.bar(muscle_groups, volume_numbers, label="Volume")

        plt.xlabel("Muscle Groups")
        plt.ylabel("Volume (sets per muscle group per week)")
        if workout_program_name:
            plt.title(f"Volume Graph of muscle groups in {workout_program_name}")
        else:
            plt.title("Volume Graph of muscle groups in workout program")
        plt.tight_layout()

        graph_bytes = io.BytesIO()
        plt.savefig(graph_bytes, format="png")
        graph_bytes.seek(0)
        plt.close()

        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {
                    "image": {
                        "format": "png",
                        "source": {"bytes": graph_bytes.getvalue()},
                    }
                }
            ],
        }
    except Exception as e:
        logger.exception(f"Error creating volume graph: {e}")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Failed to create volume graph: {str(e)}"}],
        }
