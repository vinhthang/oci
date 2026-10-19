#!/usr/bin/env python3
"""
Antigravity CLI (agy) to OpenAI-Compatible API Proxy Server
Exposes Antigravity CLI as an OpenAI-compatible /v1/chat/completions endpoint
with a persistent stream-json supervisor for low-latency turns, SSE token streaming,
and structured /v1/review endpoint for AnythingLLM, Open WebUI, and external review tools.
"""

import os
import sys
import json
import time
import uuid
import re
import sqlite3
import logging
import asyncio
import subprocess
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, Union, AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [agy_proxy] %(message)s"
)
logger = logging.getLogger("agy_proxy")

AGY_BIN = os.environ.get("AGY_BIN", "/home/opc/.local/bin/agy")
DEFAULT_TIMEOUT_SECONDS = 600
MAX_TURNS_PER_WORKER = 30

# Dynamically discover CLI version at startup
try:
    v = subprocess.run([AGY_BIN, "--version"], capture_output=True, text=True, timeout=5)
    CLI_VERSION = v.stdout.strip() if v.returncode == 0 else "unknown"
except Exception:
    CLI_VERSION = "unknown"

# Model passthrough allowlist: honor real agy model IDs
AGY_MODEL_IDS = {
    "gemini-3.8-flash-high",
    "gemini-3.8-flash-medium",
    "gemini-3.8-flash-low",
    "claude-sonnet-4-6",
    "claude-opus-4-6-thinking",
    "gpt-oss-120b-medium",
}

AGY_EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}

# Conversation resume helper functions
_CONV_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,63}$")
_SUMMARIES_DB = os.path.expanduser("~/.gemini/antigravity-cli/conversation_summaries.db")

def _valid_conversation_id(v: Any) -> Optional[str]:
    return v.strip() if isinstance(v, str) and _CONV_ID_RE.match(v.strip()) else None

def _latest_conversation_id() -> Optional[str]:
    try:
        con = sqlite3.connect(f"file:{_SUMMARIES_DB}?mode=ro", uri=True, timeout=2)
        row = con.execute(
            "SELECT conversation_id FROM conversation_summaries ORDER BY last_modified_time DESC LIMIT 1"
        ).fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None

def _discover_conversation_id(pre_id: Optional[str]) -> Optional[str]:
    return _latest_conversation_id()

def format_messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    if len(messages) == 1 and messages[0].get("role") == "user":
        return messages[0].get("content", "")
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


class AgySupervisor:
    """
    Persistent Stream-JSON Supervisor Daemon managing a warm 'agy' worker process.
    Keeps stdin/stdout open to execute turns with minimal latency (~2-4s)
    and stream tokens as SSE chunks.
    """
    def __init__(self, agy_bin: str = AGY_BIN, max_turns: int = MAX_TURNS_PER_WORKER):
        self.agy_bin = agy_bin
        self.max_turns = max_turns
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.pid: Optional[int] = None
        self.status: str = "stopped"  # "stopped", "starting", "warm", "restarting", "error"
        self.completed_turns: int = 0
        self.conversation_id: Optional[str] = None
        self.lock = asyncio.Lock()
        self._stopping: bool = False
        self._stdout_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._active_turn_queue: Optional[asyncio.Queue] = None
        self._init_event = asyncio.Event()

    async def start(self):
        """Starts the persistent supervisor worker process."""
        async with self.lock:
            await self._start_locked()

    async def _start_locked(self):
        if self.proc and self.proc.returncode is None:
            return

        self.status = "starting"
        self._stopping = False
        self.completed_turns = 0
        self.conversation_id = None
        self._init_event.clear()

        cmd = [
            self.agy_bin,
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--dangerously-skip-permissions"
        ]

        logger.info(f"Spawning agy stream-json supervisor: {' '.join(cmd)}")
        try:
            self.proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self.pid = self.proc.pid
            self._stdout_task = asyncio.create_task(self._stdout_reader())
            self._stderr_task = asyncio.create_task(self._stderr_reader())

            # Wait for the worker to emit the 'init' event
            try:
                await asyncio.wait_for(self._init_event.wait(), timeout=30.0)
                self.status = "warm"
                logger.info(f"AgySupervisor worker is warm (PID: {self.pid}, conv: {self.conversation_id})")
            except asyncio.TimeoutError:
                if self.proc.returncode is not None:
                    self.status = "error"
                    raise RuntimeError(f"agy process exited with code {self.proc.returncode} before init")
                logger.warning("Init event timed out after 30s, proceeding as warm")
                self.status = "warm"

        except Exception as e:
            self.status = "error"
            logger.error(f"Failed to start agy supervisor: {e}")
            await self._cleanup_proc()
            raise

    async def _stdout_reader(self):
        try:
            while self.proc and self.proc.stdout:
                line = await self.proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("event")
                if event_type == "init":
                    self.conversation_id = data.get("conversation_id")
                    self._init_event.set()
                elif event_type == "result":
                    cid = (data.get("result") or {}).get("conversation_id")
                    if cid:
                        self.conversation_id = cid

                if self._active_turn_queue is not None:
                    await self._active_turn_queue.put(data)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in _stdout_reader: {e}")
        finally:
            if self._active_turn_queue is not None:
                await self._active_turn_queue.put({
                    "event": "error",
                    "error": "Worker process exited or stdout closed unexpectedly"
                })
            if not self._stopping:
                self.status = "stopped"
                logger.warning(f"Worker PID {self.pid} terminated unexpectedly")
                if self._active_turn_queue is None:
                    asyncio.create_task(self._auto_restart())

    async def _stderr_reader(self):
        try:
            while self.proc and self.proc.stderr:
                line = await self.proc.stderr.readline()
                if not line:
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _auto_restart(self):
        try:
            async with self.lock:
                if not self._stopping and (self.proc is None or self.proc.returncode is not None):
                    logger.info("Auto-restarting worker in background...")
                    await self._start_locked()
        except Exception as e:
            logger.error(f"Failed to auto-restart worker: {e}")

    async def _cleanup_proc(self):
        if self._stdout_task and not self._stdout_task.done():
            self._stdout_task.cancel()
            try:
                await self._stdout_task
            except asyncio.CancelledError:
                pass
        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        if self.proc:
            try:
                if self.proc.returncode is None:
                    self.proc.terminate()
                    try:
                        await asyncio.wait_for(self.proc.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        self.proc.kill()
                        await self.proc.wait()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning(f"Error terminating proc: {e}")

        self.proc = None
        self.pid = None

    async def stop(self):
        """Gracefully stops the supervisor worker."""
        self._stopping = True
        async with self.lock:
            self.status = "stopping"
            await self._cleanup_proc()
            self.status = "stopped"
            logger.info("AgySupervisor stopped")

    async def restart(self):
        """Restarts the supervisor on demand, interrupting any active hung process."""
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.kill()
            except Exception:
                pass
        async with self.lock:
            await self._restart_locked()

    async def _restart_locked(self):
        self.status = "restarting"
        await self._cleanup_proc()
        await self._start_locked()

    async def ensure_started(self):
        """Ensures worker is active and warm while lock is already held."""
        if self.proc is None or self.proc.returncode is not None or self.status != "warm":
            await self._start_locked()

    async def execute_turn(self, prompt: str) -> Dict[str, Any]:
        """
        Executes a single conversational turn through the persistent worker.
        Serializes requests via asyncio.Lock and enforces 600s timeout.
        """
        async with self.lock:
            await self.ensure_started()
            turn_queue = asyncio.Queue()
            self._active_turn_queue = turn_queue

            try:
                payload = json.dumps({"event": "user", "message": {"content": prompt}}) + "\n"
                if not self.proc or not self.proc.stdin:
                    raise RuntimeError("Supervisor worker stdin is unavailable")
                self.proc.stdin.write(payload.encode("utf-8"))
                await self.proc.stdin.drain()

                full_text: List[str] = []
                result_obj: Optional[Dict[str, Any]] = None

                async def _collect():
                    nonlocal result_obj
                    while True:
                        event = await turn_queue.get()
                        event_type = event.get("event")
                        if event_type == "error":
                            raise RuntimeError(event.get("error", "Unknown worker error"))
                        elif event_type == "step_update":
                            su = event.get("step_update", {})
                            delta = su.get("text_delta")
                            if delta:
                                full_text.append(delta)
                        elif event_type == "result":
                            result_obj = event.get("result", {})
                            break

                await asyncio.wait_for(_collect(), timeout=DEFAULT_TIMEOUT_SECONDS)

                self.completed_turns += 1
                if self.completed_turns >= self.max_turns:
                    logger.info(f"Worker reached {self.completed_turns} turns, auto-recycling...")
                    await self._restart_locked()

                response_content = ""
                if result_obj and "response" in result_obj:
                    response_content = str(result_obj["response"]).strip()
                elif full_text:
                    response_content = "".join(full_text).strip()

                return {
                    "response": response_content,
                    "usage": (result_obj or {}).get("usage", {}),
                    "duration_seconds": (result_obj or {}).get("duration_seconds", 0.0),
                    "conversation_id": self.conversation_id,
                }

            except asyncio.TimeoutError:
                logger.error(f"Turn timed out after {DEFAULT_TIMEOUT_SECONDS}s, recycling worker")
                await self._restart_locked()
                raise HTTPException(
                    status_code=504,
                    detail=f"Antigravity CLI execution timed out after {DEFAULT_TIMEOUT_SECONDS}s"
                )
            except asyncio.CancelledError:
                logger.warning("Turn cancelled by caller, recycling worker")
                await self._restart_locked()
                raise
            except Exception as e:
                logger.error(f"Turn error: {e}, recycling worker")
                await self._restart_locked()
                raise
            finally:
                self._active_turn_queue = None

    async def stream_turn(
        self, prompt: str, chat_id: str, created_time: int, model_id: Optional[str]
    ) -> AsyncGenerator[str, None]:
        """
        Streams token chunks from step_update as SSE chunks until result event.
        Serializes requests via asyncio.Lock and enforces 600s timeout.
        """
        async with self.lock:
            await self.ensure_started()
            turn_queue = asyncio.Queue()
            self._active_turn_queue = turn_queue

            try:
                payload = json.dumps({"event": "user", "message": {"content": prompt}}) + "\n"
                if not self.proc or not self.proc.stdin:
                    raise RuntimeError("Supervisor worker stdin is unavailable")
                self.proc.stdin.write(payload.encode("utf-8"))
                await self.proc.stdin.drain()

                start_t = time.time()
                done = False

                while not done:
                    remaining = DEFAULT_TIMEOUT_SECONDS - (time.time() - start_t)
                    if remaining <= 0:
                        raise asyncio.TimeoutError()

                    event = await asyncio.wait_for(turn_queue.get(), timeout=remaining)
                    event_type = event.get("event")

                    if event_type == "error":
                        raise RuntimeError(event.get("error", "Unknown worker error"))
                    elif event_type == "step_update":
                        su = event.get("step_update", {})
                        delta = su.get("text_delta")
                        if delta:
                            chunk = {
                                "id": chat_id,
                                "object": "chat.completion.chunk",
                                "created": created_time,
                                "model": model_id or "antigravity-agent",
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": delta},
                                        "finish_reason": None
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                    elif event_type == "result":
                        done = True
                        end_chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model_id or "antigravity-agent",
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

                self.completed_turns += 1
                if self.completed_turns >= self.max_turns:
                    logger.info(f"Worker reached {self.completed_turns} turns, auto-recycling...")
                    await self._restart_locked()

            except asyncio.TimeoutError:
                logger.error(f"Stream turn timed out after {DEFAULT_TIMEOUT_SECONDS}s, recycling worker")
                await self._restart_locked()
                err_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id or "antigravity-agent",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"\nError: Execution timed out after {DEFAULT_TIMEOUT_SECONDS}s"},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            except asyncio.CancelledError:
                logger.warning("Stream turn cancelled by client, recycling worker")
                await self._restart_locked()
                raise

            except Exception as e:
                logger.error(f"Stream turn error: {e}, recycling worker")
                await self._restart_locked()
                err_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id or "antigravity-agent",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"\nError: {str(e)}"},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            finally:
                self._active_turn_queue = None


supervisor = AgySupervisor(agy_bin=AGY_BIN, max_turns=MAX_TURNS_PER_WORKER)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifespan: starts supervisor so it is warm immediately
    logger.info("Initializing AgySupervisor on application startup...")
    try:
        await supervisor.start()
        logger.info(f"AgySupervisor warm (PID: {supervisor.pid})")
    except Exception as e:
        logger.error(f"Failed to start AgySupervisor on startup: {e}")
    yield
    # Shutdown lifespan: gracefully stops supervisor
    logger.info("Stopping AgySupervisor on application shutdown...")
    await supervisor.stop()

app = FastAPI(
    title="Antigravity CLI OpenAI Proxy",
    version="1.4.2",
    lifespan=lifespan
)

@app.get("/")
def root():
    backend_str = f"agy v{CLI_VERSION}" if CLI_VERSION != "unknown" else "agy"
    return {
        "status": "ok",
        "service": "Antigravity CLI OpenAI Proxy",
        "backend": backend_str,
        "supervisor_status": supervisor.status,
        "pid": supervisor.pid,
        "completed_turns": supervisor.completed_turns,
        "supervisor": {
            "status": supervisor.status,
            "pid": supervisor.pid,
            "completed_turns": supervisor.completed_turns,
            "max_turns": supervisor.max_turns,
        }
    }

@app.get("/v1/models")
def list_models():
    models_data = [
        {
            "id": "antigravity-agent",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "google-antigravity",
            "permission": [],
            "root": "antigravity-agent",
            "parent": None,
        }
    ]
    for mid in sorted(AGY_MODEL_IDS):
        models_data.append({
            "id": mid,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "google-antigravity",
            "permission": [],
            "root": mid,
            "parent": None,
        })
    return {
        "object": "list",
        "data": models_data,
    }

@app.post("/v1/supervisor/restart")
async def restart_supervisor():
    """Restarts the persistent supervisor on demand."""
    await supervisor.restart()
    return {
        "status": "restarted",
        "supervisor_status": supervisor.status,
        "pid": supervisor.pid,
        "completed_turns": supervisor.completed_turns,
    }

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
    req_model = str(body.get("model") or "").strip()
    conversation_id = _valid_conversation_id(body.get("conversation_id"))

    # Determine if request can run on warm supervisor
    # Default models: "", "default", "antigravity-agent"
    is_default_model = req_model in ["", "default", "antigravity-agent"]

    # If caller specifically requested to resume an existing past conversation
    # that differs from the supervisor's active conversation, fall back to one-shot
    if conversation_id and supervisor.conversation_id and conversation_id != supervisor.conversation_id:
        is_default_model = False

    prompt = format_messages_to_prompt(messages)
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_time = int(time.time())

    # --- Mode 1: Warm Supervisor Execution ---
    if is_default_model:
        if stream:
            return StreamingResponse(
                supervisor.stream_turn(prompt, chat_id, created_time, req_model or "antigravity-agent"),
                media_type="text/event-stream"
            )
        else:
            res = await supervisor.execute_turn(prompt)
            resp_content = res["response"]
            usage = res.get("usage", {})
            prompt_tok = usage.get("input_tokens", len(prompt.split()))
            comp_tok = usage.get("output_tokens", len(resp_content.split()))
            tot_tok = usage.get("total_tokens", prompt_tok + comp_tok)

            return JSONResponse({
                "id": chat_id,
                "conversation_id": res.get("conversation_id"),
                "object": "chat.completion",
                "created": created_time,
                "model": req_model or "antigravity-agent",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": resp_content
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tok,
                    "completion_tokens": comp_tok,
                    "total_tokens": tot_tok
                }
            })

    # --- Mode 2: One-Shot Fallback for Non-Default Models or Explicit Historical Conversations ---
    model_id = req_model if req_model in AGY_MODEL_IDS else None
    cmd = [
        AGY_BIN,
        "-p", prompt,
        "--dangerously-skip-permissions"
    ]
    if model_id:
        cmd += ["--model", model_id]
    elif req_model:
        cmd += ["--model", req_model]

    if conversation_id:
        cmd += ["--conversation", conversation_id]

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
                start_stream_time = time.time()
                for line in proc.stdout:
                    if time.time() - start_stream_time > DEFAULT_TIMEOUT_SECONDS:
                        proc.kill()
                        raise TimeoutError(f"Subprocess exceeded {DEFAULT_TIMEOUT_SECONDS}s timeout")
                    if line:
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model_id or req_model or "antigravity-agent",
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
                end_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id or req_model or "antigravity-agent",
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
                    "model": model_id or req_model or "antigravity-agent",
                    "choices": [{"index": 0, "delta": {"content": f"\nError: {str(e)}"}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    else:
        # Non-streaming execution with server-side timeout
        pre_conv_id = None if conversation_id else _latest_conversation_id()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=504,
                detail=f"Antigravity CLI execution timed out after {DEFAULT_TIMEOUT_SECONDS}s"
            )

        used_conversation_id = conversation_id or _discover_conversation_id(pre_conv_id)
        if res.returncode != 0:
            content = f"Error from Antigravity CLI: {res.stderr.strip()}"
        else:
            content = res.stdout.strip()

        return JSONResponse({
            "id": chat_id,
            "conversation_id": used_conversation_id,
            "object": "chat.completion",
            "created": created_time,
            "model": model_id or req_model or "antigravity-agent",
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

@app.post("/v1/review")
async def review_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 1. Validate prompt/messages
    messages = body.get("messages", [])
    prompt_raw = body.get("prompt")
    if messages:
        prompt = format_messages_to_prompt(messages)
    elif prompt_raw:
        prompt = str(prompt_raw)
    else:
        raise HTTPException(status_code=400, detail="Either 'messages' or 'prompt' must be provided")

    # 2. Validate json_schema
    json_schema = body.get("json_schema")
    if not json_schema:
        raise HTTPException(status_code=400, detail="'json_schema' is required for structured review")
    if isinstance(json_schema, dict):
        json_schema_str = json.dumps(json_schema)
    elif isinstance(json_schema, str):
        try:
            json.loads(json_schema)
            json_schema_str = json_schema
        except Exception:
            raise HTTPException(status_code=400, detail="'json_schema' string is not valid JSON")
    else:
        raise HTTPException(status_code=400, detail="'json_schema' must be a JSON object or string")

    # 3. Model passthrough
    req_model = str(body.get("model") or "").strip()
    model_id = req_model if req_model in AGY_MODEL_IDS else None

    # 4. Effort level
    req_effort = str(body.get("effort") or "").strip().lower()
    effort_level = req_effort if req_effort in AGY_EFFORT_LEVELS else None

    # 5. Build agy command
    cmd = [
        AGY_BIN,
        "-p", prompt,
        "--dangerously-skip-permissions",
        "--output-format", "json",
        "--json-schema", json_schema_str,
    ]
    if model_id:
        cmd += ["--model", model_id]
    if effort_level:
        cmd += ["--effort", effort_level]

    conversation_id = _valid_conversation_id(body.get("conversation_id"))
    if conversation_id:
        cmd += ["--conversation", conversation_id]

    start_time = time.time()
    pre_conv_id = None if conversation_id else _latest_conversation_id()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"Antigravity CLI review execution timed out after {DEFAULT_TIMEOUT_SECONDS}s"
        )

    duration_ms = int((time.time() - start_time) * 1000)

    if res.returncode != 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Antigravity CLI execution failed",
                "returncode": res.returncode,
                "stderr": res.stderr.strip(),
                "stdout": res.stdout.strip(),
                "duration_ms": duration_ms
            }
        )

    # 6. Parse structured result
    try:
        agy_output = json.loads(res.stdout)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to decode JSON output from Antigravity CLI",
                "raw_output": res.stdout.strip(),
                "duration_ms": duration_ms
            }
        )

    # agy's --json-schema places the parsed structured result in 'structured_output'
    if "structured_output" in agy_output:
        result_data = agy_output["structured_output"]
    elif "response" in agy_output:
        try:
            result_data = json.loads(agy_output["response"])
        except Exception:
            result_data = agy_output["response"]
    else:
        result_data = agy_output

    used_conversation_id = conversation_id
    if not used_conversation_id and isinstance(agy_output, dict):
        for _k, _v in agy_output.items():
            if "conversation" in str(_k).lower() and isinstance(_v, str) and _v:
                used_conversation_id = _v
                break
    if not used_conversation_id:
        used_conversation_id = _discover_conversation_id(pre_conv_id)

    return {
        "model": model_id or "default",
        "effort": effort_level or "default",
        "result": result_data,
        "duration_ms": duration_ms,
        "usage": agy_output.get("usage", {}),
        "conversation_id": used_conversation_id
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
