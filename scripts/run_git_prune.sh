#!/usr/bin/env bash
set -euo pipefail

echo "Running git prune (ensure you have backups)"
git gc --prune=now --aggressive

git prune --expire now

echo "Git prune completed."