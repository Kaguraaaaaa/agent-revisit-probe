#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI from https://cli.github.com/ and run 'gh auth login'." >&2
  exit 1
fi
gh auth status >/dev/null
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -b main
fi
git add app.py requirements.txt .python-version render.yaml .gitignore README.md EXPERIMENT_PROTOCOL.md GITHUB_UPLOAD_INSTRUCTIONS.md publish_to_github.sh tests smoke_test.py trial_registry.csv
git diff --cached --quiet || git commit -m 'Add Atlas-47 research access probe'
if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create agent-revisit-probe --public --source=. --remote=origin --push
else
  git push -u origin main
fi
echo 'Source pushed. In Render open https://dashboard.render.com/blueprint/new and select the repository.'
