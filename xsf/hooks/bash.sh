#!/usr/bin/env bash
# xe-shell-fix (xsf) - Bash & Git Bash Hook
# Add to ~/.bashrc:
#   eval "$(command xsf init bash)"

_xsf_exec() {
    # If called with subcommands or flags, delegate to real binary
    if [ "$1" = "init" ] || [ "$1" = "config" ] || [ "$1" = "ui" ] || [ "$1" = "--version" ] || [ "$1" = "-v" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        command xsf "$@"
        return $?
    fi

    local last_cmd
    last_cmd=$(fc -ln -15 2>/dev/null | grep -vE '^[[:space:]]*(xsf|xefix|xeeee|fuxx)([[:space:]]|$)' | tail -n 1 | sed 's/^[[:space:]]*//')

    if [ -z "$last_cmd" ]; then
        echo "xsf: no previous command found" >&2
        return 1
    fi

    local fixed
    if command -v xsf &>/dev/null; then
        fixed=$(command xsf "$last_cmd" --shell bash "$@")
    elif command -v python &>/dev/null; then
        fixed=$(python -m xsf.cli "$last_cmd" --shell bash "$@")
    else
        fixed=$(python3 -m xsf.cli "$last_cmd" --shell bash "$@")
    fi
    local status=$?

    if [ $status -eq 0 ] && [ -n "$fixed" ]; then
        # Append to history and evaluate in current shell session
        history -s "$fixed"
        eval "$fixed"
    fi
}

alias xsf='_xsf_exec'
alias xefix='_xsf_exec'
alias xeeee='_xsf_exec'
alias fuxx='_xsf_exec'
