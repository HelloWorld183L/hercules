import base64
import logging

from matplotlib import pyplot as plt
import io

from strands.types.tools import ToolUse, ToolResult

logger = logging.getLogger("hercules")

TOOL_SPEC = {
    "name": "create_moving_avg_graph",
    "description": "Creates a moving average graph from the provided metrics.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "dates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of dates corresponding to the metric values."
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of metric values as strings that can be converted to floats."
                }
            },
            "required": ["dates", "metrics"]
        }
    }
}


def create_moving_avg_graph(tool: ToolUse, **kwargs) -> ToolResult:
    """
    Creates a moving average graph from the provided metrics and returns it as a BytesIO object containing the PNG image data.

    This function expects the tool input to contain two lists: 'dates' and 'metrics'. The 'dates' list should contain date strings, and the 'metrics' list should contain numeric values as strings. The function will convert the metric values to floats, calculate a 7-day moving average, and generate a line graph with both the original metrics and the moving average. The resulting graph is returned as a PNG image in a BytesIO object.

    The tool is expected to be used for visualizing trends in user metrics over time, such as tracking progress towards fitness goals. The graph can help users understand how their metrics are changing and identify any patterns or trends.
    """
    try:
        tool_use_id = tool['toolUseId']
        tool_input = tool["input"]
        dates = tool_input["dates"]
        metrics = tool_input["metrics"]

        if not dates:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [{"text": "No dates provided for graph."}]
            }
        if not metrics:
            return {
                "toolUseId": tool_use_id,
                "status": "error",
                "content": [{"text": "No metrics provided for graph."}]
            }
        

        metric_numbers = [float(x.strip()) for x in metrics]
        rolling_avg_metrics = _rolling_average(metric_numbers)

        plt.figure(figsize=(12, 5))
        plt.plot(dates, metric_numbers, label='Daily metric value')
        plt.plot(dates, rolling_avg_metrics, label='7-day moving average')

        plt.xlabel('Date')
        plt.ylabel('Metric value')
        plt.title('Moving Average Graph of metric value over time')
        plt.tight_layout()

        graph_bytes = io.BytesIO()
        plt.savefig(graph_bytes, format='png')
        graph_bytes.seek(0)
        plt.close()

        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"image": {"format": "png", "source": {"bytes": graph_bytes.getvalue()}}}]
        }
    except Exception as e:
        logger.exception(f"Error creating moving average graph: {e}")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Failed to create graph: {str(e)}"}]
        }

def _rolling_average(data, window_size=7) -> list:
    if window_size <= 0:
        raise ValueError("Window size must be greater than 0")

    result = []
    for i in range(len(data)):
        # Use minimum of window_size or remaining data points
        window = min(window_size, i + 1)
        result.append(sum(data[max(0, i - window + 1):i + 1]) / window)
    
    return result