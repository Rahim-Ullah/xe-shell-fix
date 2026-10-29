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
    case "$1" in
        init|config|ui|setup|power|key|keys|commands|help|--commands|--version|-v|--help|-h)
            _xsf_runner "$@"
            return $?
            ;;
    esac

    local has_pos=0
    local skip_next=0
    local has_ai=0
    for arg in "$@"; do
        if [ $skip_next -eq 1 ]; then
            skip_next=0
            continue
        fi
        case "$arg" in
            --shell|--stderr-file) skip_next=1 ;;
            --ai) has_ai=1 ;;
            -*) ;;
            *) has_pos=1 ;;
        esac
    done

    local fixed
    local status
    if [ $has_pos -eq 1 ]; then
        fixed=$(_xsf_runner --shell zsh "$@")
        status=$?
    else
        local last_cmd
        last_cmd=$(fc -ln -15 2>/dev/null | grep -vE '^[[:space:]]*(xsf|xefix|xeeee|fuxx)([[:space:]]|$)' | tail -n 1 | sed 's/^[[:space:]]*//')

        if [[ -z "$last_cmd" ]]; then
            if [ $has_ai -eq 1 ]; then
                _xsf_runner --shell zsh "$@"
                return $?
            fi
            print -u2 "xsf: no previous command found"
            return 1
        fi

        fixed=$(_xsf_runner "$last_cmd" --shell zsh "$@")
        status=$?
    fi

    if [ $status -eq 0 ] && [ -n "$fixed" ]; then
        print -s "$fixed"
        eval "$fixed"
    fi
}

alias xsf='_xsf_exec'
alias xefix='_xsf_exec'
alias xeeee='_xsf_exec'
alias fuxx='_xsf_exec'
