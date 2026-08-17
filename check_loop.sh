#!/bin/bash
# Check if monitoring already completed
if [ -f monitoring_done.txt ]; then
    echo "(Monitoring already complete - this is a no-op)"
    exit 0
fi

# Initialize or increment the check counter
if [ ! -f check_count.txt ]; then
    echo "0" > check_count.txt
fi

count=$(cat check_count.txt)
count=$((count + 1))
echo "$count" > check_count.txt

echo "Check $count/15: Looking for task_complete.txt..."

# Check if we found the completion file
if [ -f task_complete.txt ]; then
    echo "complete" > monitoring_done.txt
    echo ""
    echo "=== SUCCESS: File found! Contents: ==="
    cat task_complete.txt
    echo ""
    echo "✓ Monitoring complete. Claude should now cancel the cron job."
    exit 0
fi

# Check if we hit the limit
if [ $count -ge 15 ]; then
    echo "timeout" > monitoring_done.txt
    echo ""
    echo "=== LIMIT HIT: Checked 15 times, file never appeared ==="
    echo "⚠ Monitoring timed out. Claude should now cancel the cron job."
    exit 1
fi

echo "Not found yet. Waiting for next check (60s)..."
