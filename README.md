# Claude Loop Practice

A demonstration of autonomous background task monitoring in a Windows/bash hybrid environment. This project shows how to launch a long-running task in the background and poll for its completion without blocking the current session.

## What It Does

This project simulates a common automation pattern: start a slow background task (e.g., a build, deployment, or long computation), then periodically check whether it's finished. Instead of blocking for 3 minutes or requiring manual checking, an automated monitoring loop polls every 60 seconds and reports success when the task completes.

## Files

### Task Files

- **`slow_task.bat`** - Windows batch version of the slow task
  - Writes `started.txt` marker immediately on launch
  - Waits 3 minutes using `ping 127.0.0.1 -n 181` (non-interactive delay)
  - Writes `task_complete.txt` with timestamp when done
  - *Note:* Uses `ping` instead of `timeout /nobreak` because timeout requires console interaction

- **`slow_task.sh`** - Bash version of the slow task (working implementation)
  - Same behavior as batch version but works reliably in this environment
  - Uses `sleep 180` for the 3-minute delay
  - Successfully creates marker files when launched via Bash tool's `run_in_background` flag

### Monitoring

- **`check_task.bat`** - Windows batch monitoring script
  - Loops up to 15 times, checking for `task_complete.txt` every 60 seconds
  - Prints file contents and exits successfully when found
  - Reports timeout if 15 checks complete without finding the file

- **Inline bash monitoring loop** - The working implementation
  - Same logic as check_task.bat but executed directly in bash
  - Successfully detected completion on check 4 (~3 minutes)

## How to Run

### Working Method (Bash Script)

1. Clean up any previous runs:
   ```bash
   rm -f started.txt task_complete.txt
   ```

2. Launch the background task using the Bash tool's background execution:
   ```bash
   ./slow_task.sh &
   # (or use Bash tool with run_in_background=true)
   ```

3. Verify it started:
   ```bash
   cat started.txt
   ```

4. Run the monitoring loop:
   ```bash
   max_checks=15
   check_count=0
   
   while [ $check_count -lt $max_checks ]; do
       check_count=$((check_count + 1))
       echo "Check $check_count/$max_checks: Looking for task_complete.txt..."
       
       if [ -f task_complete.txt ]; then
           echo ""
           echo "=== File found! Contents: ==="
           cat task_complete.txt
           echo ""
           echo "Loop completed successfully."
           exit 0
       fi
       
       echo "Not found yet. Waiting 60 seconds..."
       sleep 60
   done
   
   echo "=== LIMIT HIT: Checked $max_checks times, file never appeared ==="
   ```

## Safety Limits

- **Maximum checks:** 15
- **Check interval:** 60 seconds
- **Total timeout:** ~15 minutes (900 seconds)

The monitoring loop will not run indefinitely. After 15 checks without finding the completion file, it reports a timeout and exits with an error code.

## Why This Uses an Inline Bash Loop (Not /loop)

This project implements an **in-session bounded monitoring loop** using inline bash code. While Claude Code offers a `/loop` command for recurring tasks, it's not the right tool for this use case.

### What /loop Is For

The `/loop` command is designed for **recurring, indefinite tasks** that run on a schedule:
- Checking deployment status every hour
- Running health checks every 30 minutes
- Periodic standup reports
- Tasks that repeat until manually stopped

By default, `/loop` tasks are session-only (they stop when you close Claude Code), but they can also be made durable to survive across sessions.

### Why /loop Doesn't Fit Bounded Monitoring

This project needs **bounded monitoring with stop conditions:**
1. **Stop when file is found** - success condition
2. **Stop after 15 checks** - timeout/failure condition
3. **Single-purpose** - not recurring across multiple task runs

`/loop` would try to run the check indefinitely on an interval, with no way to encode "stop when the file appears" or "give up after 15 attempts." The check would repeat forever (or until manually stopped), which isn't the desired behavior for monitoring a single task completion.

### The Right Solution: Inline Bash Loop

The inline bash monitoring loop is the correct implementation because it:
- **Is in-session** - tied to the current Claude Code conversation
- **Has bounded execution** - exactly 15 checks maximum
- **Has stop conditions** - exits on success (file found) or failure (timeout)
- **Reports outcomes** - clearly states whether completion was detected or limit hit
- **Matches the pattern** - monitor one task, report once, stop

This is what "in-session loop" means for this project: a monitoring loop that lives in the current session, has clear exit conditions, and is purpose-built for bounded task monitoring rather than indefinite recurring checks.

## Technical Notes: Launch Bug and Fix

### The Problem

Initial attempts to launch `slow_task.bat` as a detached background process failed:

1. `cmd.exe /c "start \"SlowTask\" slow_task.bat"` - didn't detach properly from bash
2. `powershell Start-Process` - PowerShell runtime errors in this environment
3. `cmd.exe /c slow_task.bat` with `&` - appeared to launch but never executed batch internals
4. Windows Task Scheduler - command parsing issues through the bash bridge

**Root cause:** The bash-to-Windows command bridge in this environment doesn't properly execute the internal commands of batch files when invoked via `cmd.exe /c`. The cmd.exe process starts and shows the copyright banner, but the batch file contents never run.

### The Solution

Use a bash script (`slow_task.sh`) instead of a batch file, and launch it using the Bash tool's `run_in_background: true` flag. This works reliably because:
- The bash script runs natively in the bash environment
- The background execution flag is handled by the harness, not by Windows process management
- File I/O (writing marker files) works without translation layers

### Verification

The `started.txt` marker file immediately confirms whether the task actually launched. If it doesn't appear within a few seconds, the launch method failed.

## Test Results

**Successful run:**
- Task launched at: `Tue, Aug 18, 2026 12:09:52 AM`
- Completion detected on: Check 4 (~3 minutes)
- Completion time: `Tue, Aug 18, 2026 12:12:53 AM`
- Loop status: Success ✓

## Use Cases

This pattern is useful for:
- Long-running builds or tests
- Deployment monitoring
- Background data processing
- Any task that takes minutes to hours where you want automated completion detection
- Avoiding timeout issues in interactive sessions or CI/CD pipelines
