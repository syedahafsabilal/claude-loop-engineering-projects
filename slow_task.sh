#!/bin/bash
echo "started at $(date)" > started.txt
echo "Starting slow task..."
echo "Waiting 3 minutes..."
sleep 180
echo "Writing completion file..."
echo "done at $(date)" > task_complete.txt
echo "Task complete!"
