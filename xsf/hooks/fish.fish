# xe-shell-fix (xsf) - Fish Shell Hook
# Add to ~/.config/fish/config.fish:
#   xsf init fish | source

set -g _XSF_INIT_PYTHON "@XSF_INIT_PYTHON@"

function _xsf_run_cli
    if type -q xsf
        command xsf $argv
    else if test -n "$_XSF_INIT_PYTHON" -a -x "$_XSF_INIT_PYTHON"
        "$_XSF_INIT_PYTHON" -m xsf.cli $argv
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
    if count $argv > 0; and contains -- $argv[1] init config ui setup power key keys commands help --commands --version -v --help -h
        _xsf_run_cli $argv
        return $status
    end

    set -l has_pos 0
    set -l skip_next 0
    for arg in $argv
        if test $skip_next -eq 1
            set skip_next 0
            continue
        end
        switch "$arg"
            case --shell --stderr-file
                set skip_next 1
            case '-*'
            case '*'
                set has_pos 1
        end
    end

    set -l fixed ""
    set -l status_code 1
    if test $has_pos -eq 1
        set fixed (_xsf_run_cli --shell fish $argv)
        set status_code $status
    else
        set -l last_cmd ""
        for item in $history[1..15]
            set -l trimmed (string trim -- "$item")
            if test -n "$trimmed"; and not string match -qr '^(xsf|xefix|xeeee|fuxx)(\s|$)' -- "$trimmed"
                set last_cmd "$trimmed"
                break
            end
        end

        if test -z "$last_cmd"
            if contains -- --ai $argv
                _xsf_run_cli --shell fish $argv
                return $status
            end
            echo "xsf: no previous command found" >&2
            return 1
        end

        set fixed (_xsf_run_cli "$last_cmd" --shell fish $argv)
        set status_code $status
    end

    if test $status_code -eq 0; and test -n "$fixed"
        builtin history add -- $fixed
        eval $fixed
    end
end

function xsf;   _xsf_exec $argv; end
function xefix; _xsf_exec $argv; end
function xeeee; _xsf_exec $argv; end
function fuxx;  _xsf_exec $argv; end
