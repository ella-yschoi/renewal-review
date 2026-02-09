#!/bin/bash
# PostToolUse hook: run ruff on edited Python files
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only check Python files
if [[ "$FILE_PATH" == *.py ]]; then
  RESULT=$(~/.local/bin/ruff check "$FILE_PATH" 2>&1)
  EXIT_CODE=$?

  if [ $EXIT_CODE -ne 0 ]; then
    echo "{\"decision\": \"block\", \"reason\": \"Ruff lint errors in $FILE_PATH:\\n$RESULT\"}"
    exit 0
  fi
fi
