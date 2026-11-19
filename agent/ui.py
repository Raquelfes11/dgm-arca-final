"""Chat UI for the ARCA agent: speech bubbles, scrollable history, collapsible reasoning.

Plain FastAPI + one HTML page (agent/static/chat.html): no Gradio, no CDN, works offline.

    uv run python -m agent.ui            # expects the API at http://localhost:8000

Your messages go on the right, the agent's answers on the left. Under each question the
agent's ReAct trace (thought / action / observation) is available in a collapsed block, so
the chat stays readable but nothing is hidden (it is still your debugging tool and demo).

The API is stateless (one task per call), so to hold a conversation the UI sends the last
few turns as context together with the new question.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

API_URL = os.environ.get("ARCA_API_URL", "http://localhost:8000")
HISTORY_TURNS = 3  # previous exchanges sent as context
HISTORY_CHARS = 700  # each previous message is cut to this length

def _mask_side_effects(text: str) -> str:
    """Hide earlier requests for side-effect tools so history never re-triggers them.

    The agent only runs tools with side effects (e.g. creating a PDF) if the task asks for
    them; the context we prepend must not count as a new request.
    """
    try:
        from agent.react_agent import NEGATED_REQUEST, REQUEST_PATTERNS
    except Exception:  # noqa: BLE001 - UI must work even if the agent deps are missing
        return text
    for pattern in [*REQUEST_PATTERNS.values(), NEGATED_REQUEST]:
        text = pattern.sub("[...]", text)
    return text


def build_task(message: str, history: list[dict]) -> str:
    """The new question, preceded by a compact transcript of the latest turns."""
    turns = history[-HISTORY_TURNS:]
    if not turns:
        return message
    context = "\n".join(
        f"Usuario: {_mask_side_effects(t['q'])[:HISTORY_CHARS]}\n"
        f"Asistente: {_mask_side_effects(t['a'])[:HISTORY_CHARS]}"
        for t in turns
    )
    return (
        f"Conversación previa (solo como contexto):\n{context}\n\n"
        f"Pregunta actual del usuario:\n{message}"
    )


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    brain: str = "rlm"
    max_steps: int = 10


app = FastAPI(title="ARCA chat UI")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(
        Path(__file__).parent / "static" / "chat.html",
        headers={"Cache-Control": "no-store"},  # the page and /chat must stay in sync
    )


def _call_agent(req: ChatRequest) -> tuple[int, dict]:
    """Forward the question to the agent API; return (status, json) with a readable error."""
    task = build_task(req.message.strip(), req.history)
    try:
        reply = httpx.post(
            f"{API_URL}/agent",
            json={"task": task, "brain": req.brain, "max_steps": req.max_steps},
            timeout=None,  # a slow brain can take many minutes
        )
    except httpx.ConnectError:
        return 502, {"error": f"No consigo conectar con la API en {API_URL}. ¿Está arrancada?"}
    except httpx.HTTPError as exc:
        return 502, {"error": f"Error de red: {exc}"}
    if reply.status_code != 200:
        try:
            detail = reply.json().get("detail", reply.text)
        except ValueError:
            detail = reply.text
        msg = detail.get("message", detail) if isinstance(detail, dict) else detail
        return 502, {"error": f"La API respondió {reply.status_code}: {msg}"}
    return 200, reply.json()


# Jobs run in the background so no single HTTP request lasts longer than a tunnel
# (ngrok, proxy) tolerates: the browser starts a job and polls until it finishes.
JOBS: dict[str, dict] = {}


def _run_job(job_id: str, req: ChatRequest) -> None:
    status, payload = _call_agent(req)
    JOBS[job_id] = {"state": "done", "status": status, "payload": payload}


@app.post("/chat")
def chat(req: ChatRequest):
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"state": "running"}
    threading.Thread(target=_run_job, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/chat/{job_id}")
def chat_result(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        return JSONResponse({"error": "Trabajo desconocido (¿se reinició la UI?)"}, status_code=404)
    if job["state"] == "running":
        return {"state": "running"}
    JOBS.pop(job_id, None)
    return JSONResponse(job["payload"], status_code=job["status"])


def main() -> None:
    port = int(os.environ.get("ARCA_UI_PORT", "7860"))
    host = os.environ.get("ARCA_UI_HOST", "127.0.0.1")
    print(f"ARCA chat en http://{host}:{port}  (API: {API_URL})")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
