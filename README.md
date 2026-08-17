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

### Step 5: Stop the /loop

When you see the success message or timeout message, manually stop the loop by typing:
```
/stop
```

Or use the Claude Code interface to stop the running loop.

## How the Safety Limit Works

The `/loop` command itself runs indefinitely until manually stopped. To add a safety limit, the `check_loop.sh` script tracks state:

1. **Counter file:** `check_count.txt` stores how many checks have been performed
2. **Increment on each check:** The script reads the counter, increments it, and saves it
3. **Limit enforcement:** After 15 checks, the script reports timeout and tells you to stop
4. **Manual stop required:** You must run `/stop` or stop the loop through the UI

This combines `/loop`'s recurring execution with a bounded monitoring pattern.

## Why We Use /loop for This Assignment

This course assignment specifically teaches you to use Claude Code's `/loop` feature because:

- **In-session monitoring:** The loop runs only while your Claude Code session is active
- **Recurring execution:** `/loop` automatically repeats the check every 60 seconds
- **Hands-off operation:** You don't need to manually trigger each check
- **Real-world pattern:** This mirrors how you'd monitor deployments, builds, or long-running tests

The combination of `/loop` (for the heartbeat) + `check_loop.sh` (for the bounded logic) demonstrates how to safely use recurring loops with automatic stop conditions.

## Key Commands Reference

| What You Want | Command to Type |
|---------------|----------------|
| Clean up previous run | `rm -f started.txt task_complete.txt check_count.txt` |
| Start the background task | `Start slow_task.sh in the background` |
| Start the monitoring loop | `/loop 60s bash check_loop.sh` |
| Stop the loop | `/stop` |
| Check if task started | `cat started.txt` |
| Check current status manually | `bash check_loop.sh` |

## Safety Limits

- **Maximum checks:** 15
- **Check interval:** 60 seconds  
- **Total timeout:** ~15 minutes (900 seconds)
- **Stop method:** Manual via `/stop` command or UI

The monitoring will not continue indefinitely. After 15 checks without finding the completion file, `check_loop.sh` reports a timeout and instructs you to stop the loop.

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
