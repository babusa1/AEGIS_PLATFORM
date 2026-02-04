Write-Host "Running git prune (ensure you have backups)"
git gc --prune=now --aggressive

git prune --expire now

Write-Host "Git prune completed."