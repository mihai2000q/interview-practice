# Prompt benchmark

The experiment behind [`docs/prompt-benchmark.md`](../docs/prompt-benchmark.md): the app's own
prompts, run against real models on hand-written test cases.

- `fixtures.py`: the test cases and their gold labels (synthetic).
- `tasks.py`: builds each prompt with the app's real `build_messages` and scores the replies.
- `harness.py`: the model calls: cached, parallel, with a hard spend cap.
- `run.py`: the stages (`e1` few-shot, `e2` scratchpad, `e3` temperature, `e4` every task on every
  model, `judge` the independent ratings).
- `analyze.py`: turns `results/*.jsonl` into `results/tables.md` (calls no model).
- `results/`: every raw reply with its cost, latency and tokens.

From `interview-practice.server`, with `OPENROUTER_API_KEY` set in the shell:

```bash
uv run python ../experiments/run.py e1 e2 e3 e4 judge   # resumable; stops at BENCH_BUDGET_USD
uv run python ../experiments/analyze.py                  # free
```
