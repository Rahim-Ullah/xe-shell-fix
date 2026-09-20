#!/usr/bin/env zsh
# xe-shell-fix (xsf) - Zsh Hook
# Add to ~/.zshrc:
#   eval "$(xsf init zsh)"

_xsf_exec() {
    if [[ "$1" == "init" || "$1" == "config" || "$1" == "ui" || "$1" == "--version" || "$1" == "-v" || "$1" == "--help" || "$1" == "-h" ]]; then
        command xsf "$@"
        return $?
    fi

    local last_cmd
    last_cmd=$(fc -ln -15 2>/dev/null | grep -vE '^[[:space:]]*(xsf|xefix|xeeee|fuxx)([[:space:]]|$)' | tail -n 1 | sed 's/^[[:space:]]*//')

    if [[ -z "$last_cmd" ]]; then
        print -u2 "xsf: no previous command found"
        return 1
    fi

    local fixed
    if command -v xsf &>/dev/null; then
        fixed=$(command xsf "$last_cmd" --shell zsh "$@")
    elif command -v python &>/dev/null; then
        fixed=$(python -m xsf.cli "$last_cmd" --shell zsh "$@")
    else
        fixed=$(python3 -m xsf.cli "$last_cmd" --shell zsh "$@")
    fi
    local status=$?

    if [ $status -eq 0 ] && [ -n "$fixed" ]; then
        print -s "$fixed"
        eval "$fixed"
    fi
}

alias xsf='_xsf_exec'
alias xefix='_xsf_exec'
alias xeeee='_xsf_exec'
alias fuxx='_xsf_exec'
