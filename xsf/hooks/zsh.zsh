#!/usr/bin/env zsh
# xe-shell-fix (xsf) - Zsh Hook
# Add to ~/.zshrc:
#   eval "$(xsf init zsh)"

_XSF_INIT_PYTHON="@XSF_INIT_PYTHON@"

_xsf_runner() {
    # 1. Dedicated standalone xsf binary on PATH
    if command -v xsf &>/dev/null; then
        command xsf "$@"
        local rc=$?
        if [ $rc -ne 126 ]; then
            return $rc
        fi
    fi

    # 2. Pinned Python interpreter captured during 'xsf init' (immune to active .venv)
    if [[ -n "$_XSF_INIT_PYTHON" ]] && "$_XSF_INIT_PYTHON" -c "import xsf" &>/dev/null; then
        "$_XSF_INIT_PYTHON" -m xsf.cli "$@"
        return $?
    fi

    # 3. Active shell python / python3 ONLY IF xsf module is actually installed in it
    if command -v python &>/dev/null && python -c "import xsf" &>/dev/null; then
        python -m xsf.cli "$@"
        return $?
    elif command -v python3 &>/dev/null && python3 -c "import xsf" &>/dev/null; then
        python3 -m xsf.cli "$@"
        return $?
    fi

    # 4. Last resort fallback
    if command -v python &>/dev/null; then
        python -m xsf.cli "$@"
        return $?
    elif command -v python3 &>/dev/null; then
        python3 -m xsf.cli "$@"
        return $?
    fi
    return 1
}

_xsf_exec() {
    if [[ "$1" == "init" || "$1" == "config" || "$1" == "ui" || "$1" == "--version" || "$1" == "-v" || "$1" == "--help" || "$1" == "-h" ]]; then
        _xsf_runner "$@"
        return $?
    fi

    local last_cmd
    last_cmd=$(fc -ln -15 2>/dev/null | grep -vE '^[[:space:]]*(xsf|xefix|xeeee|fuxx)([[:space:]]|$)' | tail -n 1 | sed 's/^[[:space:]]*//')

    if [[ -z "$last_cmd" ]]; then
        print -u2 "xsf: no previous command found"
        return 1
    fi

    local fixed
    fixed=$(_xsf_runner "$last_cmd" --shell zsh "$@")
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
