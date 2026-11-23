"""SFT of the agent brain on the traces of agent.generate_traces.

The brain is Qwen3-1.7B (brain thinking). The traces are what the big model did on the training
tasks: search the knowledge base, calculate with the tools, cite the passage, call final_answer.
Each model call of a trace is one training example: the prompt is the conversation the teacher
saw up to that point, the completion is what it wrote (reasoning and tool call), and the loss
covers the completion only.

The prompt is built with the chat template of the tokenizer and enable_thinking=True, which is
what the local brains do when the agent runs (ReActAgent.generate), and it is tokenized apart
from the completion, so the model learns to continue from exactly the tokens it will get at
inference. The completion ends with the end-of-turn token.

Run (on the DGX)::

    python -m agent.train_sft --traces agent/data/agent_traces.jsonl

The adapter is saved in rlm/weights/agent_sft_lora and a merged copy of the whole model in
rlm/weights/agent_sft_merged, so the agent can use it without peft::

    make bench FIX=sft LABEL=tasks BRAINS=thinking FEW_SHOT=False ARCA_THINKING_MODEL=rlm/weights/agent_sft_merged

What was decided, and why:

* LoRA r=16 on every linear layer, learning rate 1e-4. There are only a few hundred examples and
  the model already knows how to reason and to write a tool call: the SFT has to make the format
  and the habit (search, calculate with the tool, cite) reliable, not to teach new knowledge. The
  rate is half of the one of the first SFT (2e-4) because the model is bigger and the data
  smaller.
* The held-out examples are whole drugs, not whole tasks: the tasks of one drug differ only in
  the weight, so holding out a task and keeping its twin would make the evaluation loss look
  better than it is.
* Examples longer than max_length are dropped, never cut: a cut example loses its ending and
  would teach the model not to finish.
* The system prompt of the traces is the one the teacher got, with the worked examples (about 4400
  tokens). By default it is replaced by the prompt without examples (--system plain): the examples
  are what the training is meant to replace, the examples take half of every prompt, and the
  agent has to be run with the same prompt (evaluate.py --few-shot False). With --system keep the
  prompt of the traces stays and the agent runs with the default few-shot prompt.
* max_length 8192: a prompt with the search results takes 3800 tokens (median) and up to about
  6500 with the plain system prompt, and 2000 to 2500 more with the examples.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections.abc import Sequence
from pathlib import Path

END_OF_TURN = "<|im_end|>"


def read_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def group_of(trace: dict, evidence_by_id: dict[str, list[dict]]) -> str:
    """The drugs a trace is about (the files of the evidence of its task), as one key."""
    files = sorted({e["file"] for e in evidence_by_id.get(trace["id"], [])})
    return "+".join(files) if files else trace["id"]


def split_by_group(
    traces: list[dict], groups: list[str], eval_fraction: float, seed: int = 0
) -> tuple[list[dict], list[dict]]:
    """Hold out whole groups (drugs) until about eval_fraction of the traces are held out."""
    if eval_fraction <= 0:
        return traces, []
    names = sorted(set(groups))
    random.Random(seed).shuffle(names)
    target = eval_fraction * len(traces)
    held, count = set(), 0
    for name in names[:-1]:  # at least one group always stays in training
        if count >= target:
            break
        held.add(name)
        count += groups.count(name)
    train = [t for t, g in zip(traces, groups, strict=True) if g not in held]
    test = [t for t, g in zip(traces, groups, strict=True) if g in held]
    return train, test


def build_examples(trace: dict, tokenizer, system: str | None = None) -> list[dict]:
    """One example per model call of the trace: token ids and labels (-100 on the prompt)."""
    end_id = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    examples = []
    for turn in trace["turns"]:
        prompt = [dict(m) for m in turn["prompt"]]
        if system is not None:
            prompt[0] = {**prompt[0], "content": system}
        text = tokenizer.apply_chat_template(
            prompt, tokenize=False, add_generation_prompt=True, enable_thinking=True
        )
        prompt_ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        completion_ids = tokenizer(turn["completion"], add_special_tokens=False)["input_ids"] + [end_id]
        examples.append(
            {
                "task": trace["id"],
                "input_ids": prompt_ids + completion_ids,
                "labels": [-100] * len(prompt_ids) + completion_ids,
            }
        )
    return examples


def length_report(lengths: Sequence[int]) -> dict:
    """Median, 95th percentile and maximum of the example lengths, for the experiments log."""
    if not lengths:
        return {"n": 0, "p50": 0, "p95": 0, "max": 0}
    ordered = sorted(lengths)

    def at(q: float) -> int:
        return ordered[int(q * (len(ordered) - 1))]

    return {"n": len(ordered), "p50": at(0.5), "p95": at(0.95), "max": ordered[-1]}


def drop_overlong(examples: list[dict], max_length: int) -> tuple[list[dict], dict]:
    """Remove the examples longer than max_length tokens. Returns them and the length report."""
    report = length_report([len(e["input_ids"]) for e in examples])
    kept = [e for e in examples if len(e["input_ids"]) <= max_length]
    report["dropped"] = len(examples) - len(kept)
    return kept, report


def pad_batch(batch: list[dict], pad_id: int) -> dict[str, list[list[int]]]:
    """Pad to the longest example of the batch, on the right. The padding is not in the loss."""
    longest = max(len(e["input_ids"]) for e in batch)
    pad = [longest - len(e["input_ids"]) for e in batch]
    return {
        "input_ids": [e["input_ids"] + [pad_id] * n for e, n in zip(batch, pad, strict=True)],
        "attention_mask": [[1] * len(e["input_ids"]) + [0] * n for e, n in zip(batch, pad, strict=True)],
        "labels": [e["labels"] + [-100] * n for e, n in zip(batch, pad, strict=True)],
    }


def warmup_steps(n_examples: int, batch_size: int, grad_accum: int, epochs: float, fraction: float = 0.05) -> int:
    """Warm-up optimizer steps: 5 % of the run, at least one."""
    steps_per_epoch = math.ceil(n_examples / (batch_size * grad_accum))
    return max(1, round(fraction * steps_per_epoch * epochs))


def plain_system(max_steps: int = 10) -> str:
    """The system prompt of the agent without the worked examples."""
    from agent.react_agent import ReActAgent

    return ReActAgent.from_env(rag_mode="auto", few_shot=False).system_prompt(max_steps)


def train(args: argparse.Namespace) -> None:
    import torch
    from peft import LoraConfig, get_peft_model
    from torch.utils.data import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    traces = read_jsonl(args.traces)
    tasks = {t["id"]: t for t in read_jsonl(args.tasks)}
    groups = [group_of(t, {i: v["evidence"] for i, v in tasks.items()}) for t in traces]
    train_traces, eval_traces = split_by_group(traces, groups, args.eval_fraction, args.seed)
    print(f"{len(traces)} traces: {len(train_traces)} for training, {len(eval_traces)} held out (whole drugs)")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    system = plain_system() if args.system == "plain" else None

    def examples_of(items: list[dict]) -> tuple[list[dict], dict]:
        built = [e for t in items for e in build_examples(t, tokenizer, system)]
        return drop_overlong(built, args.max_length)

    train_set, report = examples_of(train_traces)
    print(f"train examples, length in tokens: {report}")
    eval_set, eval_report = examples_of(eval_traces)
    if eval_traces:
        print(f"eval examples, length in tokens: {eval_report}")
    has_eval = bool(eval_set)

    class Examples(Dataset):
        def __init__(self, items: list[dict]):
            self.items = items

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, i: int) -> dict:
            return self.items[i]

    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

    def collate(batch: list[dict]) -> dict:
        padded = pad_batch([{"input_ids": b["input_ids"], "labels": b["labels"]} for b in batch], pad_id)
        return {k: torch.tensor(v) for k, v in padded.items()}

    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32
    )
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(
        model,
        LoraConfig(
            r=args.lora_rank,
            lora_alpha=2 * args.lora_rank,
            lora_dropout=0.05,
            target_modules="all-linear",
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    config = TrainingArguments(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        lr_scheduler_type="cosine",
        warmup_steps=warmup_steps(len(train_set), args.batch_size, args.grad_accum, args.epochs),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        bf16=torch.cuda.is_available(),
        logging_steps=5,
        eval_strategy="epoch" if has_eval else "no",
        save_strategy="epoch",
        save_total_limit=3,
        load_best_model_at_end=has_eval,
        metric_for_best_model="eval_loss" if has_eval else None,
        seed=args.seed,
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=config,
        train_dataset=Examples(train_set),
        eval_dataset=Examples(eval_set) if has_eval else None,
        data_collator=collate,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(args.output)
    history = Path(args.output) / "log_history.json"
    history.write_text(json.dumps(trainer.state.log_history, indent=2), encoding="utf-8")
    print(f"adapter saved to {args.output} (training history in {history})")
    if not args.no_merge:
        merged = trainer.model.merge_and_unload()
        merged.save_pretrained(args.merged_output)
        tokenizer.save_pretrained(args.merged_output)
        print(f"merged model saved to {args.merged_output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--traces", default="agent/data/agent_traces.jsonl")
    parser.add_argument("--tasks", default="agent/bench/tasks_train.jsonl", help="to know the drugs of each trace")
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--output", default="rlm/weights/agent_sft_lora")
    parser.add_argument("--merged-output", default="rlm/weights/agent_sft_merged")
    parser.add_argument("--no-merge", action="store_true", help="save only the adapter")
    parser.add_argument("--system", choices=["keep", "plain"], default="plain",
                        help="keep the system prompt of the traces, or use the one without examples")
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--eval-fraction", type=float, default=0.15,
                        help="share of the traces held out, by drug, to pick the best epoch (0 disables)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resume-from-checkpoint", default=None, help="checkpoint-XXX folder")
    return parser


def main() -> None:
    train(build_parser().parse_args())


if __name__ == "__main__":
    main()
