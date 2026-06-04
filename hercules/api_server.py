from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import tempfile
import hashlib
import logging
import base64
from typing import Optional
from hercules.agent import build_agent
from hercules.mime_types import MIME_TYPES

logger = logging.getLogger("hercules.api")


app = FastAPI(title="Hercules Agent API", version="0.1.0")

# Agent instance created at startup
agent = build_agent()


@app.get("/health")
def health():
    return {"status": "ok"}


def _store_upload(upload: UploadFile) -> Optional[str]:
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


@app.post("/invoke")
async def invoke(
    content: str = Form(...),
    user_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Invoke the Strands Agent.

    Accepts `content` (the user text) and optional `file` upload.
    Returns JSON with the agent response; image/file payloads are base64-encoded.
    """
    try:
        hashed_user_id = (
            hashlib.sha256(user_id.encode()).hexdigest() if user_id else "anonymous"
        )

        context_input = f"[user_id: {hashed_user_id}], [user_input: {content}]"

        stored_path = None
        if file:
            stored_path = _store_upload(file)
            if stored_path:
                _, ext = os.path.splitext(stored_path)
                ext = ext.lstrip(".")
                context_input += (
                    f", [file_extension: {ext}], [file_path: {stored_path}]"
                )

        result = await agent.invoke_async(context_input)

        if isinstance(result.message, dict) and "content" in result.message:
            response_text = result.message["content"][0]["text"]
        else:
            response_text = str(result.message)

        # Try to detect image/tool results in messages
        image_payload = None
        try:
            img_response = [msg for msg in agent.messages if msg["role"] == "user"][-1]
            img_details = (
                img_response["content"][0]
                .get("toolResult", {})
                .get("content", [{}])[0]
                .get("image")
            )
            if img_details:
                image_payload = {
                    "format": img_details.get("format"),
                    "data": base64.b64encode(
                        img_details.get("source", {}).get("bytes", b"\x00")
                    ).decode("ascii"),
                }
        except Exception:
            image_payload = None

        payload = {"text": response_text}
        if image_payload:
            payload["image"] = image_payload

        return JSONResponse(content=payload)

    except Exception as e:
        logger.exception("Error invoking agent")
        raise HTTPException(status_code=500, detail=str(e))
