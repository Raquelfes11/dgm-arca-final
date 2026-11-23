"""agent.train_sft without torch: the examples, the split and the padding."""

import pytest

from agent.train_sft import (
    END_OF_TURN,
    build_examples,
    drop_overlong,
    group_of,
    length_report,
    pad_batch,
    split_by_group,
    tail_loss,
    warmup_steps,
)


class FakeTokenizer:
    """One token per character; the end-of-turn token is id 1000."""

    def convert_tokens_to_ids(self, token):
        assert token == END_OF_TURN
        return 1000

    def apply_chat_template(self, messages, tokenize, add_generation_prompt, enable_thinking):
        assert not tokenize and add_generation_prompt and enable_thinking
        return "".join(f"[{m['role']}]{m['content']}" for m in messages) + "[assistant]"

    def __call__(self, text, add_special_tokens):
        assert not add_special_tokens
        return {"input_ids": [ord(c) for c in text]}


def trace(task_id="x001"):
    system = {"role": "system", "content": "SYS"}
    user = {"role": "user", "content": "Q"}
    first = {"role": "assistant", "content": "<think>a</think><tool_call>1</tool_call>"}
    tool = {"role": "tool", "content": "R", "name": "dose_calculator"}
    return {
        "id": task_id,
        "turns": [
            {"prompt": [system, user], "completion": first["content"]},
            {"prompt": [system, user, first, tool], "completion": "<think>b</think><tool_call>2</tool_call>"},
        ],
    }


def test_each_model_call_is_one_example_with_the_loss_on_the_completion_only():
    examples = build_examples(trace(), FakeTokenizer())
    assert len(examples) == 2
    first = examples[0]
    prompt = "[system]SYS[user]Q[assistant]"
    completion = "<think>a</think><tool_call>1</tool_call>"
    assert first["input_ids"] == [ord(c) for c in prompt + completion] + [1000]
    assert first["labels"][: len(prompt)] == [-100] * len(prompt)
    assert first["labels"][len(prompt):] == [ord(c) for c in completion] + [1000]
    assert len(first["labels"]) == len(first["input_ids"])
    assert examples[1]["input_ids"][: len(prompt)] == first["input_ids"][: len(prompt)]  # same start
    assert len(examples[1]["input_ids"]) > len(first["input_ids"])  # the second call has seen more


def test_the_system_prompt_can_be_replaced():
    plain = build_examples(trace(), FakeTokenizer(), system="S")
    text = "".join(chr(i) for i in plain[0]["input_ids"][:-1])
    assert text.startswith("[system]S[user]Q") and "SYS" not in text


def test_split_holds_out_whole_groups_and_keeps_some_for_training():
    traces = [trace(f"x{i:03d}") for i in range(10)]
    groups = ["a", "a", "b", "b", "c", "c", "d", "d", "e", "e"]
    train, held = split_by_group(traces, groups, 0.3, seed=1)
    assert train and held and len(train) + len(held) == 10
    train_groups = {g for t, g in zip(traces, groups) if t in train}
    held_groups = {g for t, g in zip(traces, groups) if t in held}
    assert not train_groups & held_groups  # no drug on both sides
    assert split_by_group(traces, groups, 0)[1] == []


def test_group_is_the_set_of_files_of_the_evidence():
    evidence = {"x001": [{"file": "b.md"}, {"file": "a.md"}, {"file": "a.md"}]}
    assert group_of({"id": "x001"}, evidence) == "a.md+b.md"
    assert group_of({"id": "x999"}, evidence) == "x999"


def test_overlong_examples_are_dropped_not_cut():
    examples = [{"input_ids": [0] * n, "labels": [0] * n} for n in (5, 10, 20)]
    kept, report = drop_overlong(examples, 10)
    assert [len(e["input_ids"]) for e in kept] == [5, 10]
    assert report["dropped"] == 1 and report["max"] == 20
    assert length_report([])["n"] == 0


def test_padding_goes_on_the_right_and_is_out_of_the_loss():
    batch = [{"input_ids": [1, 2, 3], "labels": [-100, 2, 3]}, {"input_ids": [4], "labels": [4]}]
    padded = pad_batch(batch, pad_id=9)
    assert padded["input_ids"] == [[1, 2, 3], [4, 9, 9]]
    assert padded["attention_mask"] == [[1, 1, 1], [1, 0, 0]]
    assert padded["labels"] == [[-100, 2, 3], [4, -100, -100]]


def test_warmup_is_five_percent_with_a_minimum_of_one():
    assert warmup_steps(230, 1, 8, 3.0) == 4  # 29 steps per epoch, 87 in total
    assert warmup_steps(4, 1, 8, 1.0) == 1


def test_tail_loss_equals_the_loss_over_the_whole_sequence_with_the_prompt_masked():
    torch = pytest.importorskip("torch")
    torch.manual_seed(0)
    vocab, length, n = 11, 9, 3
    table = torch.randn(vocab, vocab)  # next-token logits depend on the current token
    input_ids = torch.randint(0, vocab, (1, length))
    labels = input_ids.clone()
    labels[:, : length - n] = -100
    kept = {}

    def model(input_ids, attention_mask, logits_to_keep):
        kept["n"] = logits_to_keep
        full = table[input_ids]  # (1, length, vocab)
        return type("Out", (), {"logits": full[:, -logits_to_keep:]})()

    inputs = {"input_ids": input_ids, "attention_mask": torch.ones_like(input_ids), "labels": labels}
    loss, _ = tail_loss(model, inputs)
    full = table[input_ids]
    expected = torch.nn.functional.cross_entropy(full[0, :-1], labels[0, 1:], ignore_index=-100)
    assert kept["n"] == n + 1  # only the completion and the position before it
    assert torch.allclose(loss, expected, atol=1e-6)
    summed, _ = tail_loss(model, inputs, num_items_in_batch=n * 4)  # four accumulated micro-batches
    assert torch.allclose(summed, expected * n / (n * 4), atol=1e-6)
