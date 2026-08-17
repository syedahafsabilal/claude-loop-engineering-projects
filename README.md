# Claude Loop Practice

**Course Assignment:** Project 1 - In-Session Loop Monitoring (Concept 4)

A hands-on project to practice using Claude Code's `/loop` feature for autonomous background task monitoring.

## What This Project Demonstrates

This project teaches you how to use Claude Code's `/loop` command to monitor a long-running task. You'll learn how four components work together:

1. **Long-running background task** (`slow_task.sh`) - simulates a 3-minute process
2. **Claude Code's `/loop`** - provides the recurring heartbeat that checks every 60 seconds
3. **Completion condition** - detects when `task_complete.txt` appears
4. **Safety limit** - automatically stops after 15 checks (~15 minutes) if the task never completes

## Files

### Background Task
- **`slow_task.sh`** - The simulated long-running task
  - Writes `started.txt` immediately on launch (diagnostic marker)
  - Waits 3 minutes using `sleep 180`
  - Writes `task_complete.txt` with timestamp when done

### Monitoring Scripts
- **`check_loop.sh`** - The monitoring script called by `/loop`
  - Tracks how many checks have been performed using `check_count.txt`
  - Checks for `task_complete.txt` on each run
  - Reports success when file is found
  - Reports timeout after 15 checks
  - Tells you when to stop the loop

### Legacy Files (for reference)
- `slow_task.bat` - Windows batch version (doesn't work reliably in this environment)
- `check_task.bat` - Windows batch monitoring script (replaced by check_loop.sh)

## How to Run This Project

Follow these exact steps to demonstrate Project 1:

### Step 1: Clean Up from Previous Runs

In Claude Code chat, type:
```
rm -f started.txt task_complete.txt check_count.txt
```

### Step 2: Start the Long-Running Background Task

In Claude Code chat, type:
```
Start slow_task.sh in the background
```

Claude will launch it using the Bash tool with `run_in_background: true`.

Verify it started by typing:
```
cat started.txt
```

You should see a timestamp showing when the task started.

### Step 3: Start the /loop Monitoring

In Claude Code chat, type this **exact command**:
```
/loop 60s bash check_loop.sh
```

This tells Claude Code to:
- Run `bash check_loop.sh` every 60 seconds
- Keep running until you manually stop it or the script indicates completion

### Step 4: Watch the Monitoring

Claude Code will now check every 60 seconds. You'll see output like:
```
Check 1/15: Looking for task_complete.txt...
Not found yet. Waiting for next check (60s)...
```

After ~3 minutes (around check 3 or 4), you'll see:
```
Check 4/15: Looking for task_complete.txt...

=== SUCCESS: File found! Contents: ===
done at [timestamp]

✓ Loop completed successfully. STOP THE LOOP NOW.
```

### Step 5: Loop Termination (Hybrid Approach)

When monitoring completes (either success or timeout), the loop stops through a **hybrid mechanism**:

1. **State file:** `check_loop.sh` writes `monitoring_done.txt` when complete, making all subsequent cron fires harmless no-ops
2. **Claude actively watches:** If Claude is actively engaged in the session and sees the completion message, Claude will immediately call `CronDelete` to stop the cron job
3. **Manual fallback:** If Claude doesn't catch it (e.g., you ran the check manually outside cron context), you can manually run `CronDelete <job-id>` or use `/stop`

**In an active demonstration**, Claude should notice completion and cancel the job automatically. **In unattended monitoring**, the state file prevents repeated outputs but the cron continues firing until manually stopped.

## How the Safety Limit Works

The `/loop` command itself runs indefinitely until manually stopped. The `check_loop.sh` script implements bounded monitoring through state tracking:

1. **Counter file:** `check_count.txt` stores how many checks have been performed
2. **State file:** `monitoring_done.txt` marks when monitoring is complete (success or timeout)
3. **Increment on each check:** The script reads the counter, increments it, and saves it
4. **Completion detection:** When `task_complete.txt` appears, the script writes the state file and reports success
5. **Limit enforcement:** After 15 checks without finding the file, the script writes the state file and reports timeout
6. **No-op on repeat:** Once the state file exists, subsequent cron fires exit immediately as harmless no-ops

**Key limitation:** The bash script cannot directly call `CronDelete` to terminate its own cron job. It can only mark itself complete and become a no-op. Actual cron termination requires either Claude (watching actively) or manual user intervention with `CronDelete`.

## Why We Use /loop for This Assignment

This course assignment specifically teaches you to use Claude Code's `/loop` feature because:

- **Persistent scheduling:** The cron job persists independently of the session for up to 7 days (auto-expires) unless manually cancelled
- **Recurring execution:** `/loop` automatically repeats the check every 60 seconds
- **Hands-off operation:** You don't need to manually trigger each check
- **Real-world pattern:** This mirrors how you'd monitor deployments, builds, or long-running tests

The combination of `/loop` (for the heartbeat) + `check_loop.sh` (for the bounded logic) demonstrates how to safely use recurring loops with automatic stop conditions.

## Key Commands Reference

| What You Want | Command to Type |
|---------------|----------------|
| Clean up previous run | `rm -f started.txt task_complete.txt check_count.txt monitoring_done.txt` |
| Start the background task | `Start slow_task.sh in the background` |
| Start the monitoring loop | `/loop 60s bash check_loop.sh` |
| Stop the loop manually | `CronDelete <job-id>` |
| Check if task started | `cat started.txt` |
| Check current status manually | `bash check_loop.sh` |
| List active cron jobs | `List all active cron jobs` |

## Safety Limits

- **Maximum checks:** 15
- **Check interval:** 60 seconds  
- **Total timeout:** ~15 minutes (900 seconds)
- **Stop method:** `CronDelete <job-id>` (manual) or Claude automatically cancels when watching actively
- **State protection:** After completion/timeout, `monitoring_done.txt` makes subsequent cron fires harmless no-ops

The monitoring will not continue indefinitely. After 15 checks without finding the completion file, `check_loop.sh` reports a timeout, writes the state file, and Claude (if watching) will cancel the cron job.

## Technical Notes: Background Task Launch

### The Challenge

In a Windows environment with Git Bash, launching Windows batch files as detached background processes is unreliable. Several approaches failed:

1. `cmd.exe /c "start ..."` - doesn't detach properly through bash bridge
2. `powershell Start-Process` - PowerShell runtime errors
3. `cmd.exe /c batch.bat &` - cmd starts but batch internals don't execute

### The Solution

Use a bash script (`slow_task.sh`) and launch it with Claude Code's Bash tool using `run_in_background: true`. This works because:
- The bash script runs natively in the bash environment
- Background execution is handled by the Claude Code harness, not Windows process management
- File I/O works without command bridge translation issues

### Verification

The `started.txt` marker confirms the task launched successfully. If it doesn't appear within a few seconds, the launch failed.

## Expected Results

**Successful run example:**
- Task launched: `Tue, Aug 18, 2026 12:09:52 AM`
- Loop checks: 1, 2, 3, 4...
- Detection: Check 4 (~3 minutes)
- Completion: `Tue, Aug 18, 2026 12:12:53 AM`
- Status: ✓ Success

## Learning Outcomes

By completing this project, you'll understand:
- How to use `/loop` for recurring in-session tasks
- How to monitor long-running background processes
- How to implement safety limits in loops
- How to combine recurring execution with bounded monitoring
- How to handle background task launch in hybrid Windows/bash environments

---

**Next Steps:** Try modifying the check interval (30s, 2m) or the safety limit (10 checks, 20 checks) to see how the system behaves!
