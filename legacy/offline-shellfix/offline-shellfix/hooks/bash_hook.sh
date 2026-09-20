# shellfix (offline) - bash / Git Bash hook
#
# Add this to ~/.bashrc (the installer does this for you):
#   source "$HOME/.shellfix/offline/hooks/bash_hook.sh"
#
# Usage:
#   <run a command with a typo>
#   fix              # suggest a fix, ask to run it
#   fix --rerun      # also re-run the previous command first, so a small
#                     # set of error-text-based rules (chmod +x, ./ prefix)
#                     # can kick in too. This genuinely re-executes the
#                     # previous command, so you'll be asked to confirm
#                     # that separately before it happens.

export SHELLFIX_HOME="${SHELLFIX_HOME:-$HOME/.shellfix/offline}"

_shellfix_py() {
    if command -v python >/dev/null 2>&1; then
        echo python
    elif command -v python3 >/dev/null 2>&1; then
        echo python3
    else
        echo ""
    fi
}

fix() {
    local py
    py=$(_shellfix_py)
    if [ -z "$py" ]; then
        echo "fixcmd: no 'python' or 'python3' found on PATH" >&2
        return 1
    fi

    local last
    last=$(fc -ln -1 2>/dev/null | sed -e 's/^[[:space:]]*//')
    if [ -z "$last" ] || [ "$last" = "fix" ] || [ "$last" = "fix --rerun" ]; then
        echo "fixcmd: no previous command found" >&2
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
    fixed=$("$py" "$SHELLFIX_HOME/fixcmd.py" "$last" --shell bash "${stderr_args[@]}")
    local rc=$?
    if [ "$rc" -eq 0 ] && [ -n "$fixed" ]; then
        eval "$fixed"
    fi
    return $rc
}
