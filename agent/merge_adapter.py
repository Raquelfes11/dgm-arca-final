"""Merge a LoRA adapter into its base model and save the whole model.

The agent loads the brain with plain transformers, so an adapter has to be merged first. The
training script does it at the end for the last epoch; this one does it for any adapter or
checkpoint folder, for example to compare the model after epoch 1 or 2 with the final one.

The base model is read from the adapter config unless --base is given.

Run (on the DGX)::

    python -m agent.merge_adapter rlm/weights/agent_sft_lora/checkpoint-22 rlm/weights/agent_sft_e1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def base_model_of(adapter: str | Path) -> str:
    """The base model named in the adapter config."""
    config = json.loads((Path(adapter) / "adapter_config.json").read_text(encoding="utf-8"))
    return config["base_model_name_or_path"]


def merge(adapter: str, output: str, base: str | None = None) -> None:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base = base or base_model_of(adapter)
    model = AutoModelForCausalLM.from_pretrained(
        base, dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32
    )
    merged = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    merged.save_pretrained(output)
    AutoTokenizer.from_pretrained(base).save_pretrained(output)
    print(f"merged {adapter} into {base}, saved in {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("adapter", help="adapter folder or checkpoint-XXX folder")
    parser.add_argument("output", help="folder for the merged model")
    parser.add_argument("--base", default=None, help="base model (default: the one in the adapter config)")
    args = parser.parse_args()
    merge(args.adapter, args.output, args.base)


if __name__ == "__main__":
    main()
