"""
xsf.offline.rules.shell_rules - Shell execution, permissions, and path separator fixes.
"""
import os
from pathlib import Path
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule


COMMON_SHELL_TYPOS = {
    # cd
    "cdd": "cd", "cs": "cd", "dc": "cd", "vd": "cd", "xd": "cd",
    # ls
    "lss": "ls", "sl": "ls", "lls": "ls", "l": "ls", "ls ": "ls", "LS": "ls", "sls": "ls",
    # clear
    "claer": "clear", "clea": "clear", "cler": "clear", "clera": "clear", "cllear": "clear", "clar": "clear", "lcear": "clear",
    # mkdir
    "mkidr": "mkdir", "mkrdir": "mkdir", "mkdr": "mkdir", "mdir": "mkdir", "mdkir": "mkdir",
    # pwd
    "pwdd": "pwd", "pdw": "pwd", "wdp": "pwd", "pwe": "pwd",
    # grep
    "grpe": "grep", "grrp": "grep", "gerp": "grep", "grp": "grep", "grepp": "grep",
    # echo
    "ehco": "echo", "eoch": "echo", "ecoh": "echo", "echoo": "echo",
    # cat
    "cta": "cat", "caat": "cat", "caot": "cat", "ca": "cat", "tac": "cat",
    # sudo
    "suod": "sudo", "sudoo": "sudo", "sdo": "sudo", "sduo": "sudo", "usdo": "sudo",
    # touch
    "tuch": "touch", "touhc": "touch", "tuoch": "touch", "touche": "touch",
    # chmod
    "chmdo": "chmod", "chmd": "chmod", "chomd": "chmod",
    # chown
    "chonw": "chown", "chwon": "chown",
    # rm
    "rmm": "rm", "rn": "rm",
    # cp
    "cpp": "cp", "ccp": "cp",
    # mv
    "mvv": "mv", "mve": "mv",
    # tail
    "tial": "tail", "taill": "tail",
    # head
    "haed": "head", "heaad": "head",
    # less
    "les": "less", "lees": "less", "lses": "less",
    # more
    "mroe": "more", "moer": "more",
    # which
    "whcih": "which", "wihch": "which", "wich": "which",
    # ssh
    "sssh": "ssh", "shh": "ssh",
    # scp
    "scpp": "scp", "spc": "scp",
    # curl
    "crul": "curl", "ucrl": "curl", "crlu": "curl",
    # wget
    "wgte": "wget", "wegt": "wget", "weget": "wget",
    # vim
    "viim": "vim", "vmi": "vim", "ivm": "vim",
    # nano
    "nnano": "nano", "naon": "nano", "nao": "nano",
    # python
    "pyhton": "python", "pytohn": "python", "pyton": "python", "ptyhon": "python", "pythno": "python", "pytho": "python", "pthon": "python", "pyrhon": "python",
    # python3
    "pyhton3": "python3", "pytohn3": "python3", "pyton3": "python3", "python33": "python3",
    # node
    "ndoe": "node", "noed": "node", "nde": "node", "onde": "node",
    # npm
    "nmp": "npm", "nmpp": "npm", "mpm": "npm",
    # docker
    "doker": "docker", "dcoker": "docker", "dokcer": "docker", "dockr": "docker", "docekr": "docker",
    # kubectl
    "kubeclt": "kubectl", "kubctl": "kubectl", "kubectll": "kubectl", "kuebctl": "kubectl",
    # terraform
    "teerraform": "terraform", "terrafrom": "terraform", "terrform": "terraform",
    # git
    "gti": "git", "igt": "git", "gitt": "git", "gi": "git", "tgi": "git",
    # pip
    "pipp": "pip", "pi": "pip", "ppi": "pip",
    # pip3
    "pip33": "pip3", "pipp3": "pip3",
    # cargo
    "carog": "cargo", "crago": "cargo", "cagro": "cargo",
    # go
    "og": "go", "goo": "go",
    # helm
    "helmp": "helm", "hemm": "helm",
    # code
    "cde": "code", "coed": "code", "cod": "code",
    # sort
    "srot": "sort", "osrt": "sort",
    # diff
    "difff": "diff", "idff": "diff",
    # find
    "fnd": "find", "fidn": "find", "fnid": "find",
    # kill
    "kll": "kill", "klil": "kill",
    # man
    "mna": "man", "amn": "man",
    # top/htop
    "tpo": "top", "otp": "top", "htopp": "htop", "hotp": "htop",
    # tar
    "tra": "tar", "taar": "tar",
    # zip/unzip
    "zipp": "zip", "unzipp": "unzip", "unzpi": "unzip",
    # df/du
    "dff": "df", "ddu": "du",
    # history
    "histroy": "history", "hisotry": "history", "hsitory": "history",
    # exit
    "exti": "exit", "eixt": "exit", "ext": "exit", "exiit": "exit",
    # env
    "evn": "env", "nev": "env",
    # export
    "exprot": "export", "exoprt": "export", "expotr": "export",
    # source
    "souce": "source", "soruce": "source", "soucre": "source", "surce": "source",
    # apt
    "atp": "apt", "ap": "apt", "pat": "apt",
    # brew
    "bew": "brew", "berw": "brew", "bwer": "brew",
    # systemctl
    "systmctl": "systemctl", "systemclt": "systemctl", "sytemctl": "systemctl",
    # journalctl
    "journlctl": "journalctl", "jounralctl": "journalctl",
    # service
    "servcie": "service", "serivce": "service",
    # ps
    "pss": "ps",
    # sed
    "sde": "sed",
    # awk
    "akw": "awk", "wak": "awk",
    # make
    "mkae": "make", "maek": "make", "amke": "make",
    # ping
    "pign": "ping", "pnig": "ping",
    # traceroute
    "tracerout": "traceroute", "traceroue": "traceroute",
    # ifconfig/ip
    "ifocnfig": "ifconfig", "ifconifg": "ifconfig",
    # netstat
    "netsta": "netstat", "nesttat": "netstat",
    # whoami
    "whomai": "whoami", "whaomi": "whoami",
    # hostname
    "hostnmae": "hostname", "hsotname": "hostname",
    # reboot
    "reboto": "reboot", "rebooot": "reboot",
    # shutdown
    "shutdwon": "shutdown", "shutdonw": "shutdown",
}


class CommonShellTyposRule(Rule):
    """Corrects common shell builtin typos like cdd -> cd, lss/sl -> ls, claer -> clear."""
    name = "common_shell_typos"
    priority = 4

    def match(self, cmd: Command) -> bool:
        if not cmd.tokens:
            return False
        return cmd.tokens[0].lower() in COMMON_SHELL_TYPOS

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        typo = cmd.tokens[0].lower()
        correct = COMMON_SHELL_TYPOS[typo]
        new_tokens = [correct] + cmd.tokens[1:]
        return cmd.quote_join(new_tokens), 1.0, f"Corrected shell typo '{typo}' to '{correct}'"


class CdDotDotRule(Rule):
    """Corrects `cd..` to `cd ..`."""
    name = "cd_dot_dot"
    priority = 5

    def match(self, cmd: Command) -> bool:
        return cmd.raw.strip() == "cd.." or cmd.tokens == ["cd.."]

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "cd ..", 1.0, "Added space between 'cd' and '..'"


class RelativeExecutablePrefixRule(Rule):
    """Detects when user runs a local script like `build.sh` or `setup.ps1` without `./`."""
    name = "relative_executable_prefix"
    priority = 25

    def match(self, cmd: Command) -> bool:
        if not cmd.tokens:
            return False
        first = cmd.tokens[0]
        # Only if not already path prefixed
        if not first.startswith("./") and not first.startswith(".\\") and "/" not in first and "\\" not in first:
            return Path(first).is_file()
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        first = cmd.tokens[0]
        prefix = ".\\" if cmd.shell == "powershell" else "./"
        new_tokens = [prefix + first] + cmd.tokens[1:]
        return cmd.quote_join(new_tokens), 0.95, f"Added '{prefix}' prefix to execute local file '{first}'"


class ChmodExecutableRule(Rule):
    """Detects 'Permission denied' when running a script and suggests adding +x."""
    name = "chmod_plus_x"
    priority = 30

    def match(self, cmd: Command) -> bool:
        if cmd.shell in ("powershell",):
            return False
        if not cmd.tokens:
            return False
        err = cmd.stderr_text.lower()
        if "permission denied" in err:
            target = cmd.tokens[0]
            if target.startswith("./"):
                target = target[2:]
            return Path(target).is_file()
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        target = cmd.tokens[0]
        file_path = target[2:] if target.startswith("./") else target
        return f"chmod +x {file_path} && {cmd.raw}", 0.90, f"Make '{file_path}' executable with 'chmod +x'"


class SudoPrefixRule(Rule):
    """Suggests sudo for permission errors on POSIX shells."""
    name = "sudo_prefix"
    priority = 40

    def match(self, cmd: Command) -> bool:
        if cmd.shell in ("powershell",):
            return False
        if not cmd.tokens or cmd.tokens[0] == "sudo":
            return False
        err = cmd.stderr_text.lower()
        return "permission denied" in err or "are you root?" in err or "must be run as root" in err

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return f"sudo {cmd.raw}", 0.85, "Prepend 'sudo' to run with elevated privileges"
