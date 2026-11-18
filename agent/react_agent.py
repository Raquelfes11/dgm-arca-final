"""The ReAct agent: Thought -> Action -> Observation, in a loop, with every tool you built.

This is where phases 1 to 3 meet. The brain is a model (``brain="base"``, your phase-1
RLM with ``brain="rlm"``, or a thinking model with ``brain="thinking"``); the hands are the
phase-2 registry plus ``search_knowledge_base`` from phase 3; the loop is yours to write.

``ReActAgent.run`` is what ``POST /agent`` calls. Until it is implemented the endpoint
answers 501. Reuse what you already have: ``tool_use.parser.parse_tool_calls`` to read
the model's output, ``ToolRegistry.call`` to execute, ``ConversationMemory`` to keep the
history within budget.
"""

from __future__ import annotations

import json
import os
import threading
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import re

from dotenv import load_dotenv

from agent.memory import ConversationMemory
from agent.prompts import (
    REACT_SYSTEM_PROMPT,
    REACT_SYSTEM_PROMPT_FEWSHOT,
    SHEET_RULES,
    SUMMARY_PROMPT,
)
from api.schemas import AgentAction, AgentResponse, AgentStep, ToolCallRecord
from tool_use.registry import ToolRegistry, tool
from tool_use.tools import default_registry
from tool_use.parser import THINK_PATTERN, ToolCall, parse_tool_calls
from rag.retriever import build_retrievers

# The model ids and the adapter live in each teammate's .env. Loading it here means any script
# that uses the agent finds them, without exporting them by hand. Variables already exported win.
load_dotenv()

RETRIEVER = "hybrid"
LAMBDA_BM25 = 0.4  # best MRR in the λ sweep with recursive chunking (EXPERIMENTS.md)
MAX_NEW_TOKENS = 1024
# Per tool call. Measured in reports/agent_tool_latency.json (see EXPERIMENTS.md, 2026-11-03):
# normal calls take at most ~1.1 s, the first search (builds the retriever) ~12 s, and CIMA
# gives up by itself after 15 s. 30 s leaves ~2.5x margin over the slowest of those.
TOOL_TIMEOUT_S = 30
SUMMARY_FALLBACK_CHARS = 1000  # used when the model gives no summary
MAX_REPEATED_CALLS = 3  # the same call (name + arguments) this many times stops the run
RAG_MODES = ("auto", "tool", "off")  # how the knowledge base reaches the model, see from_env
AUTO_SEARCH_TOP_K = 5  # passages of the automatic search made before the first step
MIN_TOP_K = 3  # small models ask for top_k=1 and the passage they need is not the first one

def _not_done_message(name: str, reason: str) -> str:
    """Observation for a tool that did not produce its result. It says in capitals that
    nothing was done, because a small model reads a plain error as a pending step and then
    claims the result anyway (t23: the model said the sheet was generated)."""
    return (
        f"HERRAMIENTA NO EJECUTADA: '{name}' {reason}. "
        f"NO se ha generado ningún resultado ni archivo con '{name}'. "
        "En tu respuesta final di claramente que esa acción NO se ha realizado y no la "
        "presentes como hecha. Entrega solo lo que sí has calculado o consultado."
    )


# A tool with side effects only runs if the user's task asks for its result ("genera la hoja de
# preparación"). If the model calls it on its own, it is blocked (see ReActAgent._call_tool).
REQUEST_PATTERNS: dict[str, re.Pattern] = {
    "create_preparation_sheet": re.compile(
        r"(?:gener|cre[ae]|elabor|haz\b|hac[eé]\b|prepar|sac[ae]|imprim|export|dame|dam[eé]\b|"
        r"necesit|quier|adjunt|incluy|con\b)\w*\b[^.?!\n]{0,40}?"
        r"(?:hoja|ficha)\s+de\s+preparaci|(?:\bpdf\b)",
        re.IGNORECASE,
    ),
}
# "sin la hoja", "no quiero la hoja", "no generes el PDF": the user rules it out
NEGATED_REQUEST = re.compile(
    r"\bsin\b[^.?!\n]{0,25}(?:hoja|ficha|pdf)|\bno\b[^.?!\n]{0,30}(?:hoja|ficha|pdf)",
    re.IGNORECASE,
)


def requested_tools(task: str) -> set[str]:
    """Tools with side effects that the task explicitly asks for."""
    if NEGATED_REQUEST.search(task):
        return set()
    return {name for name, pattern in REQUEST_PATTERNS.items() if pattern.search(task)}


# Tools that create a file: the observation tells the model to quote the real path, and the code
# checks the final answer does (name -> what it creates).
FILE_TOOLS = {"create_preparation_sheet": "Hoja de preparación"}

# Tools whose result a final answer can claim. name -> (pattern that shows the answer talks about
# that result, how to call it in the warning). The pattern is narrow on purpose: a bare "ficha"
# would also match "ficha técnica" in RAG answers. Generous enough to catch "hoja", "PDF".
CLAIM_PATTERNS: dict[str, tuple[re.Pattern, str]] = {
    "create_preparation_sheet": (
        re.compile(r"hoja de preparaci|ficha de preparaci|\bPDF\b|\bla hoja\b", re.IGNORECASE),
        "la hoja de preparación",
    ),
}
# The answer already says the action did not happen (blocked, could not, needs confirmation).
ACKNOWLEDGES_PATTERN = re.compile(
    r"\bno\s+(?:se\s+)?(?:ha\s+|he\s+|han\s+|hemos\s+)?(?:podido|pudo|puedo|puede|es\s+posible|"
    r"generad|cread|realizad|ejecutad|disponible)"
    r"|\bno\s+(?:genero|creo|genera|crea)\b|bloquead|requiere\s+confirmaci|sin\s+confirmaci"
    r"|necesita\s+confirmaci|pendiente\s+de\s+confirmaci",
    re.IGNORECASE,
)


def check_claimed_actions(answer: str, done_tools: set[str]) -> tuple[str, list[str]]:
    """Flag a final answer that presents a tool result as done when the tool did not succeed.

    Returns the answer (with a warning line in front if it needed one) and the warnings.
    In a clinical setting a claimed preparation sheet that does not exist is a safety error,
    so the text itself is corrected and not only the metadata (nobody may read the metadata).
    """
    if ACKNOWLEDGES_PATTERN.search(answer):
        return answer, []  # it says it did not happen: that is the honest answer
    warnings_found: list[str] = []
    labels: list[str] = []
    for tool_name, (pattern, label) in CLAIM_PATTERNS.items():
        if tool_name in done_tools or not pattern.search(answer):
            continue
        warnings_found.append(
            f"La respuesta menciona {label}, pero '{tool_name}' no se ejecutó con éxito."
        )
        labels.append(label)
    if labels:
        answer = f"AVISO: {' y '.join(labels)} NO se ha generado: la herramienta no se ejecutó con éxito (estaba bloqueada, falló o no se llegó a llamar). " + answer
    return answer, warnings_found


ACTION_PATTERN = re.compile(r"Action:\s*`?(?P<name>[A-Za-z_]\w*)`?")
ACTION_JSON_PATTERN = re.compile(r"Action:\s*(?=\{)")  # Action: {"name": ..., "arguments": {...}}

_retriever = None


def _json_object_at(text: str) -> dict | None:
    """The JSON object that starts at the beginning of text, or None if there is none."""
    if not text.startswith("{"):
        return None
    try:
        payload, _ = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _answer_text(arguments: dict) -> str:
    """The answer of a final_answer call as text. Missing or null is an empty string."""
    answer = arguments.get("answer")
    return "" if answer is None else str(answer)


def _action_line_fallback(raw: str, known_tools) -> ToolCall | None:
    """Read an Action line written without a <tool_call> block. Small models do this a lot
    (phase 4: about half of the steps without a valid call). Two shapes are accepted:
    Action: tool_name, optionally followed by the arguments as a JSON object, and
    Action: {"name": "tool_name", "arguments": {...}}, which is what Qwen3-1.7B wrote in
    t04, t09 and t20. Only names that exist in the registry count, and only text outside
    the think block.
    """
    visible = THINK_PATTERN.sub("", raw)
    visible = visible.rsplit("<think>", 1)[0] if "<think>" in visible else visible
    found: list[tuple[int, ToolCall]] = []  # (position in the text, call)
    for match in ACTION_PATTERN.finditer(visible):
        if match.group("name") not in known_tools:
            continue
        payload = _json_object_at(visible[match.end():].lstrip())
        arguments: dict = {}
        if payload is not None:
            arguments = payload.get("arguments", payload) if "name" in payload else payload
            if not isinstance(arguments, dict):
                arguments = {}
        found.append((match.start(), ToolCall(name=match.group("name"), arguments=arguments)))
    for match in ACTION_JSON_PATTERN.finditer(visible):
        payload = _json_object_at(visible[match.end():])
        name = payload.get("name") if payload is not None else None
        if not isinstance(name, str) or name not in known_tools:
            continue
        arguments = payload.get("arguments", payload.get("parameters", {}))
        if not isinstance(arguments, dict):
            arguments = {}
        found.append((match.start(), ToolCall(name=name, arguments=arguments)))
    if not found:
        return None
    return max(found, key=lambda item: item[0])[1]  # the last Action is the final decision


def _get_retriever():
    """Ingest -> chunk -> build_retrievers, one single time. Returns the chosen retriever."""
    global _retriever
    if _retriever is None:
        from rag.chunking import recursive_chunks
        from rag.embed import Embedder
        from rag.generate import CORPUS_DIR, INDEX_DIR
        from rag.ingest import load_corpus

        chunks = recursive_chunks(load_corpus(CORPUS_DIR)) # decided in EXPERIMENTS.md. Works better than semantic
        retrievers = build_retrievers(
            chunks,
            Embedder(),
            persist_dir=INDEX_DIR / "recursive", # same index as rag/
            weight_bm25=LAMBDA_BM25
        )
        _retriever = retrievers[RETRIEVER]
        if os.environ.get("ARCA_DRUG_FILTER", "1").lower() not in ("0", "false", "off"):
            from rag.drugs import DrugAwareRetriever

            _retriever = DrugAwareRetriever(_retriever, chunks)  # ARCA_DRUG_FILTER=0 turns it off

    return _retriever

@tool
def final_answer(answer: str) -> str:
    """Return the final answer to the user and stop the loop.

    Args:
        answer: The complete answer to the task.
    """
    return answer


@tool
def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """Search the domain knowledge base and return the most relevant passages with their ids.

    Args:
        query: What to look for, phrased as a question.
        top_k: How many passages to return.
    """
    # Call your phase-3 retriever and render hits as "[id] (source)\\ntext".
    hits = _get_retriever().search(query, max(top_k, MIN_TOP_K))
    if not hits:
        return "No se han encontrado pasajes relevantes."
    return "\n\n".join(f"[{h.chunk.id}] ({h.chunk.source})\n{h.chunk.text}" for h in hits)


BRAINS = {
    "base": lambda: os.environ.get("ARCA_RLM_BASE_MODEL", "Qwen/Qwen3-0.6B"),
    "rlm": lambda: os.environ.get("ARCA_RLM_ADAPTER", ""),
    "thinking": lambda: os.environ.get("ARCA_THINKING_MODEL", "Qwen/Qwen3-1.7B"),
}


def _resolve_adapter() -> str:
    """Folder of the trained LoRA adapter (brain="rlm"), downloaded from the Hub if missing.

    Same rule as ``rlm/inference.py``: ``ARCA_RLM_ADAPTER`` is the local folder and
    ``ARCA_RLM_ADAPTER_REPO`` the Hub repo it is downloaded from when the folder does not exist.
    """
    adapter = BRAINS["rlm"]()
    if not adapter:
        raise ValueError("brain='rlm' needs ARCA_RLM_ADAPTER to be set.")
    if not Path(adapter).exists():
        repo = os.environ.get("ARCA_RLM_ADAPTER_REPO")
        if not repo:
            raise FileNotFoundError(
                f"ARCA_RLM_ADAPTER points to a missing folder: {adapter} "
                "(define ARCA_RLM_ADAPTER_REPO to download it from the Hub)"
            )
        from huggingface_hub import snapshot_download

        snapshot_download(repo, local_dir=adapter)
    return adapter


@dataclass
class ReActAgent:
    registry: ToolRegistry = field(default_factory=default_registry)
    token_budget: int = 6000
    steps: list[AgentStep] = field(default_factory=list)
    _models: dict = field(default_factory=dict) # brain -> (tokenizer, model)
    rag_mode: str = "tool"  # "tool": the model decides to search, "auto": also before step 1
    few_shot: bool = False
    _tokens_used: int = field(default=0, init=False, repr=False)  # of the run in progress
    _requested: set = field(default_factory=set, init=False, repr=False)  # side-effect tools the task asks for
    # The agent keeps the trace and the token count of the run in progress, and FastAPI serves
    # requests from several threads: runs go one at a time (one GPU anyway) so they cannot mix.
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.rag_mode not in RAG_MODES:
            raise ValueError(f"rag_mode must be one of {list(RAG_MODES)}, got {self.rag_mode!r}")

    @classmethod
    def from_env(cls, rag_mode: str = "auto", use_tools: bool = True, few_shot: bool = False) -> ReActAgent:
        """The agent the API and the evaluation use, with two switches for the ablations.

        rag_mode "auto": the code searches with the task text before the first step, and the
        model can still search (the default, it was the best arm in EXPERIMENTS.md, #04).
        rag_mode "tool": the model decides whether to search the knowledge base.
        rag_mode "off": there is no knowledge base at all.
        use_tools False leaves out CIMA, convert_units, dose_calculator and the sheet tool.
        final_answer is always available.
        """
        agent = cls(rag_mode=rag_mode, few_shot=few_shot)
        if not use_tools:
            agent.registry = ToolRegistry()
        agent.registry.register(final_answer)
        if rag_mode != "off":
            agent.registry.register(search_knowledge_base)
        agent.load()
        return agent

    def load(self) -> None:
        """Load the model(s) behind BRAINS. Loading lazily per brain is fine.
        Nothing to load at startup. Each brain is loaded on first use, in _get_brain()."""
        
    def _get_brain(self, brain: str):
        if brain not in BRAINS:
            raise ValueError(f"brain must be one of {sorted(BRAINS)}, got {brain!r}")
        if brain not in self._models:
            adapter = _resolve_adapter() if brain == "rlm" else None  # fail before loading anything
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.bfloat16 if device == "cuda" else torch.float32

            model_id = BRAINS["thinking"]() if brain == "thinking" else BRAINS["base"]()
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype).to(device)

            if adapter:
                from peft import PeftConfig, PeftModel

                trained_on = PeftConfig.from_pretrained(adapter).base_model_name_or_path
                if trained_on and trained_on != model_id:
                    warnings.warn(
                        f"adapter trained on {trained_on}, but the loaded model is {model_id}.",
                        stacklevel=2,
                    )
                model = PeftModel.from_pretrained(model, adapter)

            self._models[brain] = (tokenizer, model.eval())

        return self._models[brain]

    def system_prompt(self, max_steps: int, sheet: bool = False) -> str:
        """``sheet`` adds the rules for the preparation sheet: only a run whose task asks for it."""
        template = REACT_SYSTEM_PROMPT_FEWSHOT if self.few_shot else REACT_SYSTEM_PROMPT
        if sheet:
            template = template.replace("- You have at most", SHEET_RULES + "- You have at most", 1)
        return template.format(
            max_steps=max_steps, tools_description=self.registry.render_for_prompt()
        )

    def generate(self, messages: list[dict], brain: str, thinking: bool | None = None) -> str:
        """One generation with the chosen brain.

        ``thinking`` forces the chat template flag; by default only ``base`` does not think.
        """
        import torch

        tokenizer, model = self._get_brain(brain)
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=(brain != "base") if thinking is None else thinking,
        )
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                # stop as soon as the first tool call is closed: the model must not go on to
                # write the "Observation:" itself (it makes up tool results)
                stop_strings=["</tool_call>"],
                tokenizer=tokenizer,
            )
        self._tokens_used += int(out.shape[1])  # prompt + generated tokens of this call
        return tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    def _call_tool(self, name: str, arguments: dict) -> ToolCallRecord:
        """Run one tool call with a time limit. Never raises: a failure comes back as a record.

        Tools marked ``requires_confirmation`` (side effects) only run if the user's task asked
        for them (``self._requested``). Otherwise they are blocked and the model is told.
        """
        spec = self.registry.tools.get(name)
        if spec is not None and spec.requires_confirmation and name not in self._requested:
            return ToolCallRecord(
                name=name,
                arguments=arguments,
                ok=False,
                error=_not_done_message(
                    name, "está BLOQUEADA: el usuario no ha pedido esta acción en su mensaje, así que no se ejecuta"
                ),
                requires_confirmation=True,
            )
        box: list[ToolCallRecord] = []
        worker = threading.Thread(
            target=lambda: box.append(self.registry.call(name, arguments)), daemon=True
        )
        worker.start()
        worker.join(TOOL_TIMEOUT_S)
        if worker.is_alive():  # a thread cannot be killed: it is abandoned (daemon) and we move on
            return ToolCallRecord(
                name=name,
                arguments=arguments,
                ok=False,
                error=_not_done_message(name, f"ha superado el tiempo límite ({TOOL_TIMEOUT_S}s)"),
                latency_ms=1000 * TOOL_TIMEOUT_S,
            )
        return box[0]

    def summarize(self, messages: list[dict], brain: str) -> str:
        """Summarise old messages with the brain itself, for ``ConversationMemory.compress``.

        Thinking is off: a summary does not need a reasoning block and it would eat tokens.
        If the model returns nothing usable (for example a ``<think>`` cut by the token limit),
        we fall back to the start of the history rather than lose it all.
        """
        history = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        raw = self.generate(
            [{"role": "user", "content": SUMMARY_PROMPT.format(history=history)}],
            brain,
            thinking=False,
        )
        summary = raw.rsplit("</think>", 1)[-1].strip()
        if not summary or summary.startswith("<think>"):
            summary = history[:SUMMARY_FALLBACK_CHARS]
        return summary

    def _model_label(self, brain: str) -> str:
        """Which model answered, written like ``/rag`` does: base model (+ adapter)."""
        if brain == "thinking":
            return BRAINS["thinking"]()
        if brain == "rlm":
            return f"{BRAINS['base']()} + {BRAINS['rlm']()}"
        return BRAINS["base"]()

    def run(self, task: str, max_steps: int = 10, brain: str = "rlm") -> AgentResponse:
        """What ``POST /agent`` calls: runs the loop and fills in ``model`` and ``tokens_used``."""
        with self._lock:
            self._tokens_used = 0
            self._requested = requested_tools(task)
            response = self._run_loop(task, max_steps, brain)
            response.model = self._model_label(brain)
            response.tokens_used = self._tokens_used
            return response

    def _auto_search(self, task: str, memory: ConversationMemory) -> None:
        """Search the knowledge base with the task text before the first model step.

        The result goes into the conversation as if the model had asked for it, so it has the
        format the model already knows, and into self.steps marked as automatic, so the reports
        can tell it apart from a search the model chose. It does not use up one of the max_steps.
        """
        if "search_knowledge_base" not in self.registry.tools:
            raise ValueError("rag_mode='auto' needs search_knowledge_base in the registry")
        arguments = {"query": task, "top_k": AUTO_SEARCH_TOP_K}
        record = self._call_tool("search_knowledge_base", arguments)
        observation = str(record.result if record.ok else record.error)
        call = json.dumps({"name": "search_knowledge_base", "arguments": arguments},
                          ensure_ascii=False)
        self.steps.append(
            AgentStep(
                thought="Búsqueda automática en la base de conocimiento con el enunciado.",
                action=AgentAction(name="search_knowledge_base", arguments=arguments),
                observation=observation,
                automatic=True,
            )
        )
        memory.add("assistant", f"<tool_call>\n{call}\n</tool_call>")
        memory.add("tool", observation, name="search_knowledge_base")

    def _run_loop(self, task: str, max_steps: int, brain: str) -> AgentResponse:
        """The ReAct loop.
        """
        self.steps = []
        tokenizer, _ = self._get_brain(brain)

        def count_tokens(text: str) -> int:
            return len(tokenizer.encode(text))

        memory = ConversationMemory(
            self.system_prompt(max_steps, sheet="create_preparation_sheet" in self._requested),
            count_tokens,
            self.token_budget,
            pin_first=True,
        )
        memory.add("user", task)
        if self.rag_mode == "auto":
            self._auto_search(task, memory)
        nudged = False  # True after we already asked the model once to fix its format
        seen: dict[tuple[str, str], int] = {}  # (tool, arguments) -> times called
        done_tools: set[str] = set()  # tools that returned ok=True: only these results are real
        outputs: list[str] = []  # paths of the files the tools created
        reminded = False  # True after we told the model once that the task asks for a tool it did not call
        for step in range(max_steps):
            raw = self.generate(memory.render(), brain)
            if raw.count("<tool_call>") > raw.count("</tool_call>"):
                raw += "\n</tool_call>"  # small models sometimes stop before closing the tag
            parsed = parse_tool_calls(raw)
            route = "tag"  # how the call was read, kept in the step to measure the format
            if not parsed.has_tool_calls:
                fallback = _action_line_fallback(raw, self.registry.tools)
                if fallback is not None:
                    parsed.tool_calls = [fallback]
                    route = "fallback"
            thought = parsed.thinking or parsed.text
            problem = None  # why this step cannot be run, if it cannot
            if parsed.has_tool_calls:
                first = next(c for c in parsed.tool_calls if c.error is None)
                if first.name == "final_answer" and not _answer_text(first.arguments).strip():
                    problem = (
                        "final_answer was called without an answer. Call it again with the "
                        'complete answer: <tool_call>{"name": "final_answer", "arguments": '
                        '{"answer": "..."}}</tool_call>'
                    )
            if (not parsed.has_tool_calls or problem) and not nudged:
                # first format failure: tell the model what went wrong and let it try again
                nudged = True
                errors = [c.error for c in parsed.tool_calls if c.error]
                message = problem or (
                    (f"Invalid tool call: {errors[0]}. " if errors else "No tool call found. ")
                    + "Do not write 'Action: name'. Reply with one "
                    '<tool_call>{"name": "...", "arguments": {...}}</tool_call> block, '
                    "or call final_answer."
                )
                self.steps.append(AgentStep(thought=thought, observation=message))
                memory.add("assistant", raw)
                memory.add("user", message)
                continue
            if not parsed.has_tool_calls or problem:
                # second failure in a row: accept what the model wrote, but flag it
                self.steps.append(AgentStep(thought=thought, observation="(no tool call)"))
                return AgentResponse(
                    final_answer="" if problem else (parsed.text or thought),  # an empty final_answer is not an answer
                    steps = self.steps,
                    n_steps=step+1,
                    succeeded=False
                )
            nudged = False  # a valid call resets the counter
            call = parsed.tool_calls[0]
            action = AgentAction(name=call.name, arguments=call.arguments)
            if call.name == "final_answer":
                self.steps.append(AgentStep(thought=thought, action=action, call_route=route))
                missing = sorted(self._requested - done_tools)
                if missing and not reminded and step + 1 < max_steps:
                    # the task asks for a tool and the model wants to finish without calling it:
                    # say so once instead of letting it claim a result that does not exist
                    reminded = True
                    message = (
                        f"La tarea pide explícitamente el resultado de {missing} y todavía NO has "
                        "llamado a esa herramienta con éxito, así que no puedes darlo por hecho. "
                        "Calcula lo que falte con dose_calculator, llama a la herramienta y después "
                        "usa final_answer."
                    )
                    self.steps[-1].observation = message
                    memory.add("assistant", raw)
                    memory.add("user", message)
                    continue
                answer, flags = check_claimed_actions(_answer_text(call.arguments), done_tools)
                for path in outputs:  # the model must name the real file: if not, the code does
                    if Path(path).name not in answer:
                        answer += f"\n\nRuta real del archivo generado: {path}"
                return AgentResponse(
                    final_answer=answer,
                    steps=self.steps,
                    n_steps=step + 1,
                    warnings=flags,
                )
            key = (call.name, json.dumps(call.arguments, sort_keys=True, default=str))
            seen[key] = seen.get(key, 0) + 1
            if seen[key] >= MAX_REPEATED_CALLS:
                # the model keeps asking for the same thing: stop instead of burning all the steps
                message = f"Loop detected: '{call.name}' was called {seen[key]} times with the same arguments."
                self.steps.append(
                    AgentStep(thought=thought, action=action, observation=message, call_route=route)
                )
                return AgentResponse(final_answer="", steps=self.steps, n_steps=step + 1, succeeded=False)
            record = self._call_tool(call.name, call.arguments)
            if record.ok:
                done_tools.add(call.name)
            observation =str(record.result if record.ok else record.error)
            if record.ok and call.name in FILE_TOOLS:
                outputs.append(observation)
                observation = (
                    f"{FILE_TOOLS[call.name]} generada correctamente. Ruta del archivo: {observation}. "
                    "En tu respuesta final incluye el resultado del cálculo (dosis y volumen o "
                    "velocidad) y esta ruta exacta; no inventes otro nombre ni enlace."
                )
            if seen[key] == 2:  # second identical call: run it, but warn the model
                observation += (
                    "\n[Warning: you already made this exact call and the result will not "
                    "change. Try different arguments or another tool, or call final_answer.]"
                )
            step_record = AgentStep(
                thought=thought, 
                action=AgentAction(
                    name=call.name, arguments=call.arguments
                ), 
                observation=observation,
                call_route=route)
            self.steps.append(step_record)
            memory.add("assistant", raw); memory.add("tool", observation, name=call.name)
            memory.compress(lambda old: self.summarize(old, brain))
        return AgentResponse(final_answer="", steps=self.steps, n_steps=max_steps,
                                succeeded=False)
