# Project 7 - Observable Scheduled Loop (Fails Safe, Needs Human)

This project demonstrates a **scheduled loop** that:
- runs on a defined cadence,
- is **observable** (every beat is logged with a timestamp),
- **measures tokens + cost** per beat and projects an **estimated monthly cost**,
- has a **hard safety limit** (max attempts) so it cannot loop forever,
- and is **deliberately sabotaged** so it fails loudly and leaves clear evidence
  in `run.log` and `progress.md`.

The final state is **NEEDS HUMAN**. The sabotage is intentional and is NOT fixed.

## 1. The loop and its cadence

`loop.py` is a Python script (no external dependencies) that runs a beat
every `cadence_seconds` (default **3 seconds**). Each beat:
1. tries to read its task prompt from a file,
2. would "process" it and write output (counting input/output tokens),
3. records the beat cost and logs the result.

Because the loop is sabotaged, the prompt file does not exist, so every beat
fails before doing any work.

## 2. Safety limit

`max_attempts` (default **3**) is a hard cap. The loop will stop after this
many failed beats instead of running forever. This is the "fail safe" guard.

## 3. Observability / logging

Every event is appended to `run.log` as a single line with this shape:

```
2026-08-19T12:00:00 | FAILURE | attempt 1 | task file missing: nonexistent_prompt.txt | reason: ...
```

Each log line contains at minimum:
- **timestamp** (ISO-8601),
- **FAILURE** marker,
- **useful reason/context** (what broke and why).

The failure is therefore **never silent**.

## 4. Token + cost measurement and monthly estimate

Even though real beats fail (0 tokens used), the loop uses a configured
"expected" beat size to show the cost model:

- `expected_input_tokens`  = 200
- `expected_output_tokens` = 150
- `price_per_input_token`  = $0.00001  ($10 / 1M tokens)
- `price_per_output_token` = $0.00003  ($30 / 1M tokens)

Per beat cost = input_tokens * price_in + output_tokens * price_out.

Beats per month = (30 days * 24h * 3600s) / cadence_seconds.

Estimated monthly cost = per-beat cost * beats per month.

This projection is printed at startup and written into `progress.md`, so a
human can see the cost impact of the current cadence without replaying a run.

## 5. The deliberate sabotage

In `loop.py` the prompt source is set to a file that does not exist:

```python
"prompt_file": "nonexistent_prompt.txt",
```

(Alternative sabotage, left commented in the code: a success condition that
can never be met.) The loop is intentionally NOT fixed.

## 6. How to run

```bash
cd project-7
python loop.py
```

The script prints a final `LOOP FAILED - NEEDS HUMAN INTERVENTION` message,
updates `progress.md`, and writes evidence to `run.log`.

## 7. How to verify the failure

```bash
python verify.py
```

`verify.py` checks that:
- `run.log` exists and contains a timestamped `FAILURE` line,
- `progress.md` contains a clear `NEEDS HUMAN` note,
- the monthly cost estimate is present.

## 8. How to diagnose the failure (using only the log + progress.md)

You do **not** need to replay the run.

- **WHAT failed:** `run.log` shows `task file missing: nonexistent_prompt.txt`
  and `reason: the loop's prompt source does not exist`. `progress.md` states
  the loop exhausted all attempts and a human must restore the prompt source.
- **WHEN it failed:** every `run.log` line starts with an ISO-8601 timestamp,
  including the final `LOOP EXHAUSTED` line.

## 9. Current status

See `progress.md`: **NEEDS HUMAN**.
