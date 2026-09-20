# shellfix (AI) - bash / Git Bash hook
#
# Add this to ~/.bashrc (the installer does this for you):
#   source "$HOME/.shellfix/api/hooks/bash_hook.sh"
#
# Named `fixai` (not `fix`) so this can be installed side by side with the
# offline project without clashing.
#
# Usage:
#   <run a command with a less common error>
#   fixai              # ask Gemini, then ask you to confirm
#   fixai --rerun      # also re-run the previous command first, so the
#                       # model gets the real error text, not just the
#                       # command string. You'll be asked to confirm that
#                       # re-run separately.

export SHELLFIX_AI_HOME="${SHELLFIX_AI_HOME:-$HOME/.shellfix/api}"

_shellfix_ai_py() {
    if command -v python >/dev/null 2>&1; then
        echo python
    elif command -v python3 >/dev/null 2>&1; then
        echo python3
    else
        echo ""
    fi
}

fixai() {
    local py
    py=$(_shellfix_ai_py)
    if [ -z "$py" ]; then
        echo "fixcmd-ai: no 'python' or 'python3' found on PATH" >&2
        return 1
    fi

    local last
    last=$(fc -ln -1 2>/dev/null | sed -e 's/^[[:space:]]*//')
    if [ -z "$last" ] || [ "$last" = "fixai" ] || [ "$last" = "fixai --rerun" ]; then
        echo "fixcmd-ai: no previous command found" >&2
        return 1
    fi

    local stderr_args=()
    if [ "$1" = "--rerun" ]; then
        echo "This will re-run the previous command to capture its exact error text:" >&2
        echo "  $last" >&2
        read -r -p "Continue? [y/N] " ans
        if [[ "$ans" =~ ^[Yy] ]]; then
            local tmp
            tmp=$(mktemp)
            eval "$last" >/dev/null 2>"$tmp"
            stderr_args=(--stderr-file "$tmp")
        fi
    fi

    local fixed
    fixed=$("$py" "$SHELLFIX_AI_HOME/fixcmd_ai.py" "$last" --shell bash "${stderr_args[@]}")
    local rc=$?
    if [ "$rc" -eq 0 ] && [ -n "$fixed" ]; then
        eval "$fixed"
    fi
    return $rc
}
