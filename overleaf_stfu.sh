#!/bin/bash

# 1. Fetch the latest nonsense from GitHub
echo "Fetching from origin..."
git fetch origin

# 2. Find the most recent Overleaf branch
# grep filters for overleaf branches, sort ensures chronological order, tail grabs the latest
TARGET_BRANCH=$(git branch -r | grep 'origin/overleaf-' | sort | tail -n 1 | xargs)

if [[ -z "$TARGET_BRANCH" ]]; then
    echo "No Overleaf ghost branches found. You survived this round."
    exit 0
fi

echo "Target acquired: $TARGET_BRANCH"
echo "Nuking from orbit..."

# 3. Perform the '-s ours' merge and push
git merge -s ours "$TARGET_BRANCH" -m "Automated execution of Overleaf ghost branch"

if git push origin main; then
    echo ""
    echo "Success. Go back to Overleaf and click the green 'I have manually merged' button."
else
    echo "Push failed. Check your git status."
fi
