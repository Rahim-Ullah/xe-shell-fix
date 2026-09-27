"""
xsf.offline.rules - Rule registry and evaluator.
"""
from typing import List, Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule
from xsf.offline.rules.python_rules import PythonMissingModuleFlagRule, VenvActivationRule
from xsf.offline.rules.git_rules import (
    GitPushNoUpstreamRule, GitCommitBareMessageRule, GitBranchRenameOrDeleteRule,
    GitDidYouMeanRule, GitDetachedHeadRule, GitStashBeforeCheckoutRule,
    GitMergeConflictRule, GitAddBeforeCommitRule, GitPullRebaseRule,
)
from xsf.offline.rules.package_rules import NpmMissingRunRule, YarnInstallPackageRule, CargoShorthandRule, GoRunBareRule
from xsf.offline.rules.docker_rules import DockerComposeMigrationRule, DockerRunInteractiveRule
from xsf.offline.rules.shell_rules import (
    CommonShellTyposRule,
    CdDotDotRule,
    CrossShellNaturalCommandsRule,
    RelativeExecutablePrefixRule,
    ChmodExecutableRule,
    SudoPrefixRule,
)
from xsf.offline.rules.stderr_rules import (
    NoSuchFileOrDirRule,
    PythonModuleNotFoundRule,
    GitNotARepoRule,
    PipExternallyManagedRule,
    NodeModuleNotFoundRule,
    PortInUseRule,
    FilePermissionDeniedRule,
)
from xsf.offline.rules.env_rules import (
    PythonVenvNotFoundRule,
    NpmPermissionRule,
    EnvVariableNotSetRule,
    RustCompilerNotFoundRule,
)
from xsf.offline.rules.ssh_net_rules import (
    SSHHostKeyVerificationRule,
    CurlConnectionFailedRule,
    SSLCertificateErrorRule,
)

# Registry of all built-in deterministic rules, sorted by priority (lowest integer first)
ALL_RULES: List[Rule] = sorted([
    # Shell typos, builtins, and cross-shell natural verbs (priority 4-6)
    CommonShellTyposRule(),
    CdDotDotRule(),
    CrossShellNaturalCommandsRule(),
    # Git rules (priority 8-15)
    GitDidYouMeanRule(),
    GitPushNoUpstreamRule(),
    GitCommitBareMessageRule(),
    GitBranchRenameOrDeleteRule(),
    GitDetachedHeadRule(),
    GitStashBeforeCheckoutRule(),
    GitMergeConflictRule(),
    GitAddBeforeCommitRule(),
    GitPullRebaseRule(),
    # Python rules (priority 10-15)
    PythonMissingModuleFlagRule(),
    VenvActivationRule(),
    # Stderr-driven recovery (priority 9-16)
    NoSuchFileOrDirRule(),
    PythonModuleNotFoundRule(),
    GitNotARepoRule(),
    PipExternallyManagedRule(),
    NodeModuleNotFoundRule(),
    PortInUseRule(),
    FilePermissionDeniedRule(),
    # Environment rules (priority 15-18)
    PythonVenvNotFoundRule(),
    NpmPermissionRule(),
    EnvVariableNotSetRule(),
    RustCompilerNotFoundRule(),
    # Package managers (priority 20-25)
    NpmMissingRunRule(),
    YarnInstallPackageRule(),
    CargoShorthandRule(),
    GoRunBareRule(),
    # Docker (priority 10-20)
    DockerComposeMigrationRule(),
    DockerRunInteractiveRule(),
    # SSH/Network (priority 20-24)
    SSHHostKeyVerificationRule(),
    CurlConnectionFailedRule(),
    SSLCertificateErrorRule(),
    # Shell execution (priority 25-40)
    RelativeExecutablePrefixRule(),
    ChmodExecutableRule(),
    SudoPrefixRule(),
], key=lambda r: r.priority)


def get_all_rule_candidates(cmd: Command, include_user_rules: bool = True) -> List[Tuple[str, float, str]]:
    """
    Evaluates command against built-in and user custom rules.
    Returns all candidate fixes sorted by priority:
        [(fixed_cmd, confidence, explanation), ...]
    """
    from xsf.offline.rules.user_rules import load_user_rules

    rules = list(ALL_RULES)
    if include_user_rules:
        user_rules = load_user_rules()
        if user_rules:
            rules.extend(user_rules)
            rules.sort(key=lambda r: r.priority)

    candidates: List[Tuple[str, float, str]] = []
    seen_commands = set()

    for rule in rules:
        try:
            if rule.match(cmd):
                rule_candidates = rule.get_candidates(cmd)
                for cand in rule_candidates:
                    fixed_cmd = cand[0].strip()
                    if fixed_cmd and fixed_cmd != cmd.raw.strip() and fixed_cmd not in seen_commands:
                        candidates.append(cand)
                        seen_commands.add(fixed_cmd)
        except Exception:
            continue

    return candidates


def evaluate_rules(cmd: Command, include_user_rules: bool = True) -> Optional[Tuple[str, float, str]]:
    """
    Runs command through all registered rule plugins.
    Returns the first matching rule's fix: (fixed_cmd, confidence, explanation) or None.
    """
    candidates = get_all_rule_candidates(cmd, include_user_rules=include_user_rules)
    return candidates[0] if candidates else None

