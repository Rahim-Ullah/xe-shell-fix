"""
shellutil.py - small shared helpers used by both fixcmd.py and flag_rules.py.

quote_join() is a deliberately simple, good-enough-for-most-cases requoter:
wrap any token containing whitespace or quotes in double quotes. This is not
a fully correct shell-quoting implementation for every dialect (bash, cmd,
and PowerShell each have their own escaping rules for edge cases like
embedded backticks or $-expansion), but double-quoting plain text works
consistently across all three for the common case: a filename or a commit
message with spaces in it.
"""


def quote_join(tokens) -> str:
    out = []
    for t in tokens:
        if t == "":
            out.append('""')
        elif any(c in t for c in (" ", "\t", '"', "'")):
            out.append('"' + t.replace('"', '\\"') + '"')
        else:
            out.append(t)
    return " ".join(out)
