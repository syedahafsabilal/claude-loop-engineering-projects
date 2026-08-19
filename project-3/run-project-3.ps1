Set-Location "C:\Users\Ali\Desktop\claude-loop-engineering-projects"
$taskText = Get-Content "project-3\task.md" -Raw

$job = Start-Job -ScriptBlock {
    param($text)
    Set-Location "C:\Users\Ali\Desktop\claude-loop-engineering-projects"
    opencode run $text --dir "C:\Users\Ali\Desktop\claude-loop-engineering-projects" --title "project-3-loop" --dangerously-skip-permissions
} -ArgumentList $taskText

$completed = Wait-Job $job -Timeout 300

if (-not $completed) {
    Stop-Job $job
    Add-Content "project-3\progress.md" "`n## TIMEOUT $(Get-Date -Format yyyy-MM-dd) - run exceeded 5 minute limit and was killed"
} else {
    Receive-Job $job
}

Remove-Job $job -Force
