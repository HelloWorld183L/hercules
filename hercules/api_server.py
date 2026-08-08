import base64
import hashlib
import logging
import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from strands.types.content import Message

from hercules.agent import build_agent
from hercules.mime_types import MIME_TYPES

logger = logging.getLogger("hercules.api")

app = FastAPI(title="Hercules Agent API", version="0.1.0")

# Agent instance created at startup
agent = build_agent()


@app.get("/health")
def health():
    return {"status": "ok"}


def _store_upload(upload: UploadFile) -> str | None:
    if not upload:
        return None
    content_type = upload.content_type
    if content_type and ";" in content_type:
        content_type = content_type.split(";")[0].strip()

    file_extension = MIME_TYPES.get(content_type, "ignore")
    if file_extension == "ignore":
        return None

    data = upload.file.read()
    time_of_upload = hashlib.sha256(data).hexdigest()[:12]
    fname = f"{time_of_upload}_upload.{file_extension}"
    dest = os.path.join(tempfile.gettempdir(), fname)
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def _build_context_input(
    user_id: str | None, content: str, file_path: str | None
) -> str:
    """Build the context input string for the agent."""
    hashed_user_id = (
        hashlib.sha256(user_id.encode()).hexdigest() if user_id else "unknown"
    )
    context_input = f"[user_id: {hashed_user_id}], [user_input: {content}]"
    if file_path:
        stored_path = _store_upload(file_path)
        if stored_path:
            _, ext = os.path.splitext(stored_path)
            ext = ext.lstrip(".")
            context_input += f", [file_extension: {ext}], [file_path: {stored_path}]"

    return context_input


def _create_image_payload(message: Message) -> dict | None:
    """
    Create an image payload from the agent's messages if an image is present.
    The payload includes the image format and base64-encoded data.
    """

    img_details = (
        message["content"][0].get("toolResult", {}).get("content", [{}])[0].get("image")
    )
    if not img_details:
        return None

    image_payload = {
        "format": img_details.get("format"),
        "data": base64.b64encode(
            img_details.get("source", {}).get("bytes", b"\x00")
        ).decode("ascii"),
    }
    return image_payload


@app.post("/invoke")
async def invoke(
    content: str = Form(...),
    user_id: str | None = Form(None),
    file: UploadFile | None = File(None),  # noqa: B008
):
    """
    Invoke the Strands Agent.

    Accepts `content` (the user text) and optional `file` upload.
    Returns JSON with the agent response; image/file payloads are base64-encoded.
    """
    try:
        context_input = _build_context_input(user_id, content, file)
        result = await agent.invoke_async(context_input)

        if isinstance(result.message, dict) and "content" in result.message:
            response_text = result.message["content"][0]["text"]
            # Create image payload if the agent returned an image in its messages
            image_payload = _create_image_payload(result.message)
        else:
            response_text = str(result.message)
            # No image payload if the message is just a plain text response
            image_payload = None

        payload = {"text": response_text}
        if image_payload:
            payload["image"] = image_payload

        return JSONResponse(content=payload)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
