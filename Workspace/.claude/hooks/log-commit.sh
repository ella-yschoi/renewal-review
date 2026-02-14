#!/bin/bash
# PostToolUse hook: log work history on git commit
# Trigger: Bash commands containing "git commit"
# Output: appends to docs/experiment-log.md in the repo

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only act on git commit commands
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# Find the renewal-review repo root from cwd
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

# Find the renewal-review directory (could be in worktree)
RR_DIR=""
if [[ -d "$REPO_ROOT/Workspace/renewal-review" ]]; then
  RR_DIR="$REPO_ROOT/Workspace/renewal-review"
elif [[ "$(basename "$REPO_ROOT")" == "renewal-review" ]]; then
  RR_DIR="$REPO_ROOT"
fi

# Fallback: search from pwd
if [ -z "$RR_DIR" ]; then
  D=$(pwd)
  while [ "$D" != "/" ]; do
    if [[ "$(basename "$D")" == "renewal-review" ]]; then
      RR_DIR="$D"
      break
    fi
    D=$(dirname "$D")
  done
fi

if [ -z "$RR_DIR" ]; then
  exit 0
fi

LOG_FILE="$RR_DIR/docs/experiment-log.md"
mkdir -p "$(dirname "$LOG_FILE")"

# Initialize log file if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  echo "# Experiment Log" > "$LOG_FILE"
  echo "" >> "$LOG_FILE"
fi

# Extract latest commit info
HASH=$(git log -1 --format='%h' 2>/dev/null)
SUBJECT=$(git log -1 --format='%s' 2>/dev/null)
BODY=$(git log -1 --format='%b' 2>/dev/null)
BRANCH=$(git branch --show-current 2>/dev/null)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DIFFSTAT=$(git diff --stat HEAD~1..HEAD 2>/dev/null | tail -1)
FILES=$(git diff --name-only HEAD~1..HEAD 2>/dev/null)

# Append entry
{
  echo ""
  echo "## $TIMESTAMP | $BRANCH"
  echo ""
  echo "### \`$HASH\` $SUBJECT"
  echo ""
  # Body = AI's work summary (from commit message)
  if [ -n "$BODY" ]; then
    # Strip Co-Authored-By line
    CLEAN_BODY=$(echo "$BODY" | grep -v '^Co-Authored-By:' | sed '/^$/d')
    if [ -n "$CLEAN_BODY" ]; then
      echo "**작업 요약:**"
      echo "$CLEAN_BODY"
      echo ""
    fi
  fi
  echo "**변경 파일:**"
  if [ -n "$FILES" ]; then
    echo "$FILES" | while read -r f; do
      echo "- \`$f\`"
    done
  fi
  if [ -n "$DIFFSTAT" ]; then
    echo ""
    echo "> $DIFFSTAT"
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"
