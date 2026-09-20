"""
xsf.offline.rules.git_rules - Comprehensive Git heuristics and error fixes.
"""
import re
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule

RE_GIT_UPSTREAM = re.compile(r"git push --set-upstream\s+([^\n\r]+)", re.IGNORECASE)
RE_GIT_UPSTREAM_ALT = re.compile(r"The current branch\s+(\S+)\s+has no upstream branch", re.IGNORECASE)


class GitPushNoUpstreamRule(Rule):
    """Detects `git push` failure when branch has no upstream branch configured."""
    name = "git_push_no_upstream"
    priority = 10

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 2 and cmd.tokens[0].lower() == "git" and cmd.tokens[1].lower() == "push":
            return bool(RE_GIT_UPSTREAM.search(cmd.stderr_text) or RE_GIT_UPSTREAM_ALT.search(cmd.stderr_text))
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        match = RE_GIT_UPSTREAM.search(cmd.stderr_text)
        if match:
            target = match.group(1).strip()
            return f"git push --set-upstream {target}", 1.0, "Set upstream branch and push"
        
        match_alt = RE_GIT_UPSTREAM_ALT.search(cmd.stderr_text)
        if match_alt:
            branch = match_alt.group(1).strip()
            return f"git push -u origin {branch}", 0.95, f"Set upstream for '{branch}' and push"
        
        return None


class GitCommitBareMessageRule(Rule):
    """Detects `git commit "some message"` missing `-m` flag."""
    name = "git_commit_missing_m"
    priority = 12

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) == 3 and cmd.tokens[0].lower() == "git" and cmd.tokens[1].lower() == "commit":
            # 3rd token is not a flag (e.g. -m, -a, --amend)
            return not cmd.tokens[2].startswith("-")
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        fixed_tokens = [cmd.tokens[0], cmd.tokens[1], "-m", cmd.tokens[2]]
        return cmd.quote_join(fixed_tokens), 0.95, "Added missing '-m' flag for commit message"


class GitBranchRenameOrDeleteRule(Rule):
    """Detects `git branch d <branch>` -> `git branch -d <branch>`."""
    name = "git_branch_flag_fix"
    priority = 15

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 4 and cmd.tokens[0].lower() == "git" and cmd.tokens[1].lower() == "branch":
            return cmd.tokens[2] in ("d", "D", "m", "M")
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        new_tokens = list(cmd.tokens)
        new_tokens[2] = f"-{new_tokens[2]}"
        return cmd.quote_join(new_tokens), 0.95, f"Added '-' prefix to branch flag '-{cmd.tokens[2]}'"


class GitDidYouMeanRule(Rule):
    """Parses git's 'did you mean' suggestion from stderr."""
    name = "git_did_you_mean"
    priority = 8

    def match(self, cmd: Command) -> bool:
        return bool(cmd.stderr_text and "Did you mean this?" in cmd.stderr_text)

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        match = re.search(r"Did you mean this\?\n\s+([^\n]+)", cmd.stderr_text)
        if match:
            suggestion = match.group(1).strip()
            tokens = list(cmd.tokens)
            if len(tokens) >= 2 and tokens[0].lower() == "git":
                tokens[1] = suggestion
                return cmd.quote_join(tokens), 0.9, f"Use suggested command '{suggestion}'"
        return None


class GitDetachedHeadRule(Rule):
    """Detects detached HEAD state and suggests creating a branch."""
    name = "git_detached_head"
    priority = 12

    def match(self, cmd: Command) -> bool:
        return bool(cmd.stderr_text and ("HEAD detached" in cmd.stderr_text or "detached HEAD" in cmd.stderr_text))

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "git checkout -b temp-branch", 0.6, "Create a new branch from detached HEAD"


class GitStashBeforeCheckoutRule(Rule):
    """Detects uncommitted changes blocking checkout."""
    name = "git_stash_before_checkout"
    priority = 12

    def match(self, cmd: Command) -> bool:
        return bool(cmd.stderr_text and ("would be overwritten" in cmd.stderr_text or "Please commit your changes or stash them" in cmd.stderr_text))

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return f"git stash && {cmd.raw}", 0.9, "Stash local changes and retry"


class GitMergeConflictRule(Rule):
    """Provides guidance when merge conflicts occur."""
    name = "git_merge_conflict"
    priority = 13

    def match(self, cmd: Command) -> bool:
        return bool(cmd.stderr_text and ("CONFLICT (content):" in cmd.stderr_text or "Automatic merge failed" in cmd.stderr_text))

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "git status", 0.9, "Check status to resolve merge conflicts"


class GitAddBeforeCommitRule(Rule):
    """Detects when user tries to commit with nothing staged."""
    name = "git_add_before_commit"
    priority = 14

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 2 and cmd.tokens[0].lower() == "git" and cmd.tokens[1].lower() == "commit":
            return bool(cmd.stderr_text and ("nothing to commit" in cmd.stderr_text or "no changes added to commit" in cmd.stderr_text))
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "git add -u && " + cmd.raw, 0.8, "Stage updated files and commit"


class GitPullRebaseRule(Rule):
    """Detects divergent branches on pull."""
    name = "git_pull_rebase"
    priority = 15

    def match(self, cmd: Command) -> bool:
        return bool(cmd.stderr_text and "You have divergent branches" in cmd.stderr_text)

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "git pull --rebase", 0.9, "Pull with rebase to resolve divergent branches"

