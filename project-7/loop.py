import os
import time
from datetime import datetime

CONFIG = {
    "cadence_seconds": 3,
    "max_attempts": 3,
    "prompt_file": "nonexistent_prompt.txt",
    "expected_input_tokens": 200,
    "expected_output_tokens": 150,
    "price_per_input_token": 0.00001,
    "price_per_output_token": 0.00003,
}

LOG_FILE = "run.log"
PROGRESS_FILE = "progress.md"


def now():
    return datetime.now().isoformat(timespec="seconds")


def append_log(line):
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def cost_for_beat(input_tokens, output_tokens):
    return (input_tokens * CONFIG["price_per_input_token"]
            + output_tokens * CONFIG["price_per_output_token"])


def beats_per_month():
    seconds_per_month = 30 * 24 * 3600
    return seconds_per_month / CONFIG["cadence_seconds"]


def estimated_monthly_cost():
    return cost_for_beat(CONFIG["expected_input_tokens"],
                         CONFIG["expected_output_tokens"]) * beats_per_month()


def run_beat(attempt):
    ts = now()
    try:
        with open(CONFIG["prompt_file"], "r") as f:
            prompt = f.read()
        input_tokens = int(len(prompt.split()) / 0.75)
        output_tokens = int(input_tokens * 0.75)
        cost = cost_for_beat(input_tokens, output_tokens)
        append_log(f"{ts} | SUCCESS | attempt {attempt} | input_tokens={input_tokens} "
                   f"output_tokens={output_tokens} cost=${cost:.6f}")
        return True
    except FileNotFoundError:
        append_log(f"{ts} | FAILURE | attempt {attempt} | task file missing: "
                   f"{CONFIG['prompt_file']} | reason: the loop's prompt source does "
                   f"not exist, so no work could be performed | input_tokens=0 "
                   f"output_tokens=0 cost=$0.000000")
        return False


def write_progress(status, detail):
    content = f"""# Project 7 Progress

Status: **{status}**

{detail}

## Loop Configuration
- Cadence: every {CONFIG['cadence_seconds']} seconds
- Max attempts (hard limit): {CONFIG['max_attempts']}
- Prompt file: {CONFIG['prompt_file']}

## Token + Cost Model
- Expected input tokens / beat: {CONFIG['expected_input_tokens']}
- Expected output tokens / beat: {CONFIG['expected_output_tokens']}
- Price per input token: ${CONFIG['price_per_input_token']:.5f}
- Price per output token: ${CONFIG['price_per_output_token']:.5f}
- Cost per beat: ${cost_for_beat(CONFIG['expected_input_tokens'], CONFIG['expected_output_tokens']):.6f}
- Beats per month: {beats_per_month():.0f}
- Estimated monthly cost: ${estimated_monthly_cost():.2f}

## Last Events
See `run.log` for the full timestamped event stream.

Last updated: {now()}
"""
    with open(PROGRESS_FILE, "w") as f:
        f.write(content)


def main():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    append_log(f"{now()} | INFO | loop start | cadence={CONFIG['cadence_seconds']}s "
               f"max_attempts={CONFIG['max_attempts']} prompt_file={CONFIG['prompt_file']}")
    append_log(f"{now()} | INFO | estimated monthly cost = "
               f"${estimated_monthly_cost():.2f} (based on expected usage at current cadence)")

    attempts = 0
    while attempts < CONFIG["max_attempts"]:
        attempts += 1
        if run_beat(attempts):
            write_progress("RUNNING", "Loop completed a beat successfully.")
            print("LOOP OK")
            return
        if attempts < CONFIG["max_attempts"]:
            time.sleep(CONFIG["cadence_seconds"])

    failure_msg = (f"{now()} | FAILURE | loop exhausted {CONFIG['max_attempts']} attempts "
                   f"without success | reason: required prompt file "
                   f"'{CONFIG['prompt_file']}' is missing (deliberate sabotage) | "
                   f"human intervention required")
    append_log(failure_msg)
    write_progress(
        "NEEDS HUMAN",
        "The scheduled loop FAILED after exhausting all "
        f"{CONFIG['max_attempts']} attempts. The required prompt file "
        f"'{CONFIG['prompt_file']}' does not exist (this is a deliberate sabotage "
        "for the demo). A human MUST create or restore the prompt source and then "
        "re-run the loop. Diagnosis: read `run.log` for timestamps and full failure "
        "context; the missing file is the root cause."
    )
    print("LOOP FAILED - NEEDS HUMAN INTERVENTION. See run.log and progress.md.")


if __name__ == "__main__":
    main()
