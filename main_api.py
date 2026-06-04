"""Run the Hercules FastAPI ASGI app with Uvicorn."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("hercules.api_server:app", host="0.0.0.0", port=8000, reload=False)
