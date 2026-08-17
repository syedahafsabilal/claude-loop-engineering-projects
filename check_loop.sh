#!/bin/bash
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
    echo ""
    echo "=== SUCCESS: File found! Contents: ==="
    cat task_complete.txt
    echo ""
    echo "✓ Loop completed successfully. STOP THE LOOP NOW."
    exit 0
fi

# Check if we hit the limit
if [ $count -ge 15 ]; then
    echo ""
    echo "=== LIMIT HIT: Checked 15 times, file never appeared ==="
    echo "⚠ Please STOP THE LOOP NOW."
    exit 1
fi

echo "Not found yet. Waiting for next check (60s)..."
