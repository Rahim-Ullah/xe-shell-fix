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
    # Shell typos and builtins (priority 4-5)
    CommonShellTyposRule(),
    CdDotDotRule(),
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


def evaluate_rules(cmd: Command) -> Optional[Tuple[str, float, str]]:
    """
    Runs command through all registered rule plugins.
    Returns the first matching rule's fix: (fixed_cmd, confidence, explanation) or None.
    """
    for rule in ALL_RULES:
        try:
            if rule.match(cmd):
                result = rule.get_new_command(cmd)
                if result:
                    return result
        except Exception:
            continue
    return None
