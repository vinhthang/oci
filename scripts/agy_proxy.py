#!/usr/bin/env python3
"""
Antigravity CLI (agy) to OpenAI-Compatible API Proxy Server
Exposes Antigravity CLI as an OpenAI-compatible /v1/chat/completions endpoint
for AnythingLLM, Open WebUI, and external AI clients.
"""

import sys
import json
import time
import uuid
import subprocess
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

app = FastAPI(title="Antigravity CLI OpenAI Proxy", version="1.0.0")

@app.get("/")
def root():
    return {"status": "ok", "service": "Antigravity CLI OpenAI Proxy", "backend": "agy v1.1.19"}

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "antigravity-agent",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "google-antigravity",
                "permission": [],
                "root": "antigravity-agent",
                "parent": None,
            },
            {
                "id": "gemini-pro",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "google-antigravity",
                "permission": [],
                "root": "gemini-pro",
                "parent": None,
            }
        ]
    }

def format_messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            prompt_parts.append(f"System Instructions: {content}\n")
        elif role == "user":
            prompt_parts.append(f"User: {content}\n")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}\n")
    return "\n".join(prompt_parts)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    stream = body.get("stream", False)
    prompt = format_messages_to_prompt(messages)
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_time = int(time.time())

    # Build agy command
    cmd = [
        "/home/opc/.local/bin/agy",
        "-p", prompt,
        "--dangerously-skip-permissions"
    ]

    if stream:
        async def stream_generator():
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Stream chunks
                for line in proc.stdout:
                    if line:
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": "antigravity-agent",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": line},
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                proc.wait()
                # End of stream
                end_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": "antigravity-agent",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(end_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": "antigravity-agent",
                    "choices": [{"index": 0, "delta": {"content": f"\nError: {str(e)}"}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    else:
        # Non-streaming execution
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            content = f"Error from Antigravity CLI: {res.stderr.strip()}"
        else:
            content = res.stdout.strip()

        return JSONResponse({
            "id": chat_id,
            "object": "chat.completion",
            "created": created_time,
            "model": "antigravity-agent",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split())
            }
        })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
