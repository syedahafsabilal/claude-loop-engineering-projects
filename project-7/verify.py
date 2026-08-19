import os
import re

LOG_FILE = "run.log"
PROGRESS_FILE = "progress.md"


def has_timestamp(line):
    return bool(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", line))


def main():
    checks = []

    log_ok = os.path.exists(LOG_FILE)
    checks.append(("run.log exists", log_ok))

    failure_with_ts = False
    if log_ok:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        for line in lines:
            if "FAILURE" in line and has_timestamp(line):
                failure_with_ts = True
    checks.append(("run.log has timestamped FAILURE line", failure_with_ts))

    progress_ok = os.path.exists(PROGRESS_FILE)
    checks.append(("progress.md exists", progress_ok))

    needs_human = False
    if progress_ok:
        with open(PROGRESS_FILE, "r") as f:
            text = f.read()
        needs_human = "NEEDS HUMAN" in text and "human" in text.lower()
    checks.append(("progress.md states NEEDS HUMAN", needs_human))

    monthly_cost = False
    if progress_ok:
        with open(PROGRESS_FILE, "r") as f:
            text = f.read()
        monthly_cost = "Estimated monthly cost" in text and "$" in text
    checks.append(("progress.md shows monthly cost estimate", monthly_cost))

    all_pass = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"[{status}] {name}")

    print()
    if all_pass:
        print("ALL CHECKS PASSED - failure is observable and diagnosed.")
    else:
        print("SOME CHECKS FAILED.")


if __name__ == "__main__":
    main()
