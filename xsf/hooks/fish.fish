# xe-shell-fix (xsf) - Fish Shell Hook
# Add to ~/.config/fish/config.fish:
#   xsf init fish | source

function _xsf_exec
    set -l last_cmd $history[1]
    if test -z "$last_cmd"
        echo "xsf: no previous command found" >&2
        return 1
    end

    set -l fixed ""
    if type -q xsf
        set fixed (command xsf "$last_cmd" --shell fish $argv)
    else if type -q python
        set fixed (python -m xsf.cli "$last_cmd" --shell fish $argv)
    else
        set fixed (python3 -m xsf.cli "$last_cmd" --shell fish $argv)
    end
    set -l status_code $status

    if test $status_code -eq 0; and test -n "$fixed"
        builtin history add -- $fixed
        eval $fixed
    end
end

function xsf
    if count $argv > 0; and contains -- $argv[1] init config ui --version -v --help -h
        if type -q xsf
            command xsf $argv
        else if type -q python
            python -m xsf.cli $argv
        else
            python3 -m xsf.cli $argv
        end
        return $status
    end
    _xsf_exec $argv
end
function xefix; _xsf_exec $argv; end
function xeeee; _xsf_exec $argv; end
function fuxx;  _xsf_exec $argv; end
