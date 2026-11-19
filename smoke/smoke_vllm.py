"""Prueba rápida del servicio de inferencia vLLM de la DGX.

vLLM expone una API compatible con OpenAI, así que el formato es el de siempre:
  - GET  {base}/v1/models            -> lista los modelos servidos (sirve para comprobar la clave)
  - POST {base}/v1/chat/completions  -> {"model": ..., "messages": [{"role", "content"}, ...]}
  - Cabecera de autenticación:        Authorization: Bearer <API_KEY>

Variables de entorno (en el .env, que se carga con load_dotenv):
  VLLM_API_KEY    clave que nos han dado (obligatoria)
  VLLM_BASE_URL   por defecto http://0.0.0.0:8001/v1
  VLLM_MODEL      opcional; si no está, se usa el primer modelo que devuelva /v1/models

Uso:
  uv run python smoke/smoke_vllm.py
  uv run python smoke/smoke_vllm.py "¿Cuál es la dosis máxima diaria de paracetamol en adultos?"
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("VLLM_BASE_URL", "http://0.0.0.0:8001/v1").rstrip("/")
API_KEY = os.getenv("VLLM_API_KEY")
DEFAULT_QUESTION = "¿Para qué sirve el paracetamol? Responde en dos frases."


def main() -> int:
    if not API_KEY:
        print("Falta VLLM_API_KEY en el .env", file=sys.stderr)
        return 1

    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    headers = {"Authorization": f"Bearer {API_KEY}"}

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=120) as client:
        # 1. Modelos disponibles (también valida la URL y la clave).
        r = client.get("/models")
        if r.status_code == 401:
            print("401: la API key no es válida.", file=sys.stderr)
            return 1
        r.raise_for_status()
        models = [m["id"] for m in r.json()["data"]]
        print(f"Modelos servidos: {models}")
        model = os.getenv("VLLM_MODEL") or models[0]

        # 2. Pregunta en formato chat.
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Eres un asistente de enfermería. Responde en español."},
                {"role": "user", "content": question},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        r = client.post("/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()

    print(f"\nPregunta: {question}\n")
    print(f"Respuesta ({model}):\n{data['choices'][0]['message']['content']}")
    print(f"\nTokens: {data.get('usage')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
