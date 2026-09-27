# xe-shell-fix (xsf) - Fish Shell Hook
# Add to ~/.config/fish/config.fish:
#   xsf init fish | source

set -g _XSF_INIT_PYTHON "@XSF_INIT_PYTHON@"

function _xsf_run_cli
    if type -q xsf
        command xsf $argv
    else if test -n "$_XSF_INIT_PYTHON" -a -x "$_XSF_INIT_PYTHON"
        $_XSF_INIT_PYTHON -m xsf.cli $argv
    else if type -q python; and python -c "import xsf" 2>/dev/null
        python -m xsf.cli $argv
    else if type -q python3; and python3 -c "import xsf" 2>/dev/null
        python3 -m xsf.cli $argv
    else if type -q python
        python -m xsf.cli $argv
    else
        python3 -m xsf.cli $argv
    end
end

function _xsf_exec
    set -l last_cmd $history[1]
    if test -z "$last_cmd"
        echo "xsf: no previous command found" >&2
        return 1
    end

    set -l fixed (_xsf_run_cli "$last_cmd" --shell fish $argv)
    set -l status_code $status

    if test $status_code -eq 0; and test -n "$fixed"
        builtin history add -- $fixed
        eval $fixed
    end
end

function xsf
    if count $argv > 0; and contains -- $argv[1] init config ui --version -v --help -h
        _xsf_run_cli $argv
        return $status
    end
    _xsf_exec $argv
end
function xefix; _xsf_exec $argv; end
function xeeee; _xsf_exec $argv; end
function fuxx;  _xsf_exec $argv; end
