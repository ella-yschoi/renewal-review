#!/bin/bash
# Stop hook: remind to verify before claiming done (once per session)
# Uses a temp file to avoid blocking repeatedly in the same session
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
MARKER="/tmp/claude-stop-verified-${SESSION_ID}"

if [ -f "$MARKER" ]; then
  # Already verified this session, let it through
  exit 0
fi

# First time: block and remind, then mark as shown
touch "$MARKER"
echo "{\"decision\": \"block\", \"reason\": \"Before finishing: 1) Did you run tests? 2) Did you run ruff check? 3) Are there uncommitted changes that should be committed? If all verified, say so and stop.\"}"
