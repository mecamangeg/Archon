#!/bin/bash

# Claude Code Status Line - Context Window Tracker
# Displays: [Model] 📊 XX.Xk/200k (XX%) | 📁 directory | 🌿 git-branch

# Read JSON input from stdin
input=$(cat)

# Extract values using jq
MODEL=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
TRANSCRIPT_PATH=$(echo "$input" | jq -r '.transcript_path // ""')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir // ""')
SESSION_ID=$(echo "$input" | jq -r '.session_id // ""')

# Constants
CONTEXT_WINDOW=200000

# Function to estimate tokens from transcript
estimate_tokens() {
    local transcript_path="$1"

    if [ ! -f "$transcript_path" ]; then
        echo "0"
        return
    fi

    # Try to parse transcript and count tokens accurately
    # Claude API typical structure: {"messages": [{"role": "user", "content": "..."}, ...]}

    # Method 1: Try to extract all message content and sum
    local total_chars=$(jq -r '
        if type == "object" then
            if .messages then
                [.messages[] | .content // "" | length] | add // 0
            elif .transcript then
                [.transcript[] | .content // "" | length] | add // 0
            else
                # Fallback: stringify entire object and count
                tostring | length
            end
        else
            tostring | length
        end
    ' "$transcript_path" 2>/dev/null)

    # If jq parsing failed, fall back to character count
    if [ -z "$total_chars" ] || [ "$total_chars" == "null" ]; then
        total_chars=$(wc -c < "$transcript_path" 2>/dev/null || echo "0")
    fi

    # Convert chars to tokens (Claude tokenization: ~3.5 chars per token on average)
    # Using integer arithmetic: tokens = chars * 10 / 35
    local tokens=$((total_chars * 10 / 35))

    echo "$tokens"
}

# Function to format tokens with K suffix
format_tokens() {
    local tokens=$1
    if [ $tokens -ge 1000 ]; then
        # Convert to K with one decimal place: 15234 -> 15.2k
        local k=$((tokens / 100))
        local decimal=$((k % 10))
        local whole=$((k / 10))
        echo "${whole}.${decimal}k"
    else
        echo "${tokens}"
    fi
}

# Calculate token usage
TOKENS=$(estimate_tokens "$TRANSCRIPT_PATH")
TOKENS_FORMATTED=$(format_tokens "$TOKENS")

# Calculate percentage (using integer arithmetic)
if [ $TOKENS -gt 0 ]; then
    PERCENT=$((TOKENS * 100 / CONTEXT_WINDOW))
else
    PERCENT=0
fi

# Color coding based on usage
# Green: 0-60%, Yellow: 60-85%, Red: 85%+
if [ $PERCENT -ge 85 ]; then
    COLOR="\033[31m"  # Red
elif [ $PERCENT -ge 60 ]; then
    COLOR="\033[33m"  # Yellow
else
    COLOR="\033[32m"  # Green
fi
RESET="\033[0m"

# Build status line
STATUS="[$MODEL] 📊 ${COLOR}${TOKENS_FORMATTED}/200k${RESET} (${PERCENT}%)"

# Add directory info
if [ -n "$CURRENT_DIR" ]; then
    DIR_NAME=$(basename "$CURRENT_DIR")
    STATUS="$STATUS | 📁 $DIR_NAME"
fi

# Add git branch if in a repo
if [ -n "$CURRENT_DIR" ] && [ -d "$CURRENT_DIR/.git" ]; then
    BRANCH=$(cd "$CURRENT_DIR" && git branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        STATUS="$STATUS | 🌿 $BRANCH"
    fi
fi

# Output status line (must be single line, ANSI colors supported)
echo -e "$STATUS"
