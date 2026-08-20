import os


def main() -> int:
    token = os.environ.get("DEMO_TOKEN")
    if token:
        print(f"[OK] DEMO_TOKEN found in environment (length={len(token)}).")
        return 0
    print("[FAIL] DEMO_TOKEN NOT present in the process environment.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
