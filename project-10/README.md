# Project 10 — Secret Discovery (RUN 1)

A minimal exercise showing that a gitignored local `.env` file is NOT available
to a fresh Git/cloud clone.

## Setup

1. The secret `DEMO_TOKEN` lives ONLY in the local, gitignored `.env` file:

   ```
   DEMO_TOKEN=project10-demo-token
   ```

   `.env` is listed in `.gitignore`, so it is never committed or pushed.

2. `main.py` does NOT read `.env`. It reads `DEMO_TOKEN` ONLY from the process
   environment via `os.environ.get("DEMO_TOKEN")`. This is deliberate: the
   program never loads, parses, or references `.env`, and never hardcodes the
   token.

## Run / Verify

Run with the token exported into the environment:

```
DEMO_TOKEN="$(grep DEMO_TOKEN .env | cut -d= -f2)" python main.py
```

The program reports:

- `[OK] DEMO_TOKEN found in environment ...` — the token was supplied to the
  process environment before launch.
- `[FAIL] DEMO_TOKEN NOT present in the process environment.` — the token was
  absent.

## Notes (RUN 1)

- The secret exists locally in the gitignored `.env`, but the program itself
  does NOT read `.env`.
- A fresh Git clone or cloud environment will NOT contain `.env`, so unless the
  secret is injected into the environment by some other means, `main.py` fails
  clearly there.
- The token is never hardcoded in source (`main.py`) and never committed to a
  tracked file (`.env` is gitignored).

This establishes the RUN 1 baseline: local secret present, program relying
solely on the environment. Subsequent runs can explore what happens when the
environment is empty (e.g. on a fresh clone/cloud host).
