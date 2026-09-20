"""
xsf.offline.rules.package_rules - Heuristics for npm, yarn, pnpm, cargo, and go.
"""
from typing import Optional, Tuple
from xsf.core.command import Command
from xsf.offline.rules.base import Rule

NPM_BUILTIN_COMMANDS = {
    "access", "adduser", "audit", "bugs", "cache", "ci", "completion", "config",
    "dedupe", "deprecate", "diff", "dist-tag", "docs", "doctor", "edit", "exec",
    "explain", "explore", "find-dupes", "fund", "help", "help-search", "hook",
    "init", "install", "i", "install-ci-test", "install-test", "link", "ll", "login",
    "logout", "ls", "org", "outdated", "owner", "pack", "ping", "pkg", "prefix",
    "profile", "prune", "publish", "query", "rebuild", "repo", "restart", "root",
    "run", "run-script", "search", "set", "set-script", "shrinkwrap", "star",
    "stars", "start", "stop", "team", "test", "t", "token", "uninstall", "unpublish",
    "unstar", "update", "version", "view", "whoami"
}


class NpmMissingRunRule(Rule):
    """Converts `npm dev` or `npm build` into `npm run dev` or `npm run build`."""
    name = "npm_missing_run"
    priority = 20

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 2 and cmd.tokens[0].lower() in ("npm", "pnpm"):
            sub = cmd.tokens[1].lower()
            return sub not in NPM_BUILTIN_COMMANDS and not sub.startswith("-")
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        tool = cmd.tokens[0]
        sub = cmd.tokens[1]
        new_tokens = [tool, "run"] + cmd.tokens[1:]
        return cmd.quote_join(new_tokens), 0.90, f"Inserted 'run' for custom npm script '{sub}'"


class YarnInstallPackageRule(Rule):
    """Converts `yarn install <pkg>` to `yarn add <pkg>`."""
    name = "yarn_install_to_add"
    priority = 20

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 3 and cmd.tokens[0].lower() == "yarn":
            return cmd.tokens[1].lower() == "install" and not cmd.tokens[2].startswith("-")
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        new_tokens = ["yarn", "add"] + cmd.tokens[2:]
        return cmd.quote_join(new_tokens), 0.95, "Yarn uses 'yarn add <package>' instead of 'install'"


class CargoShorthandRule(Rule):
    """Expands cargo single-letter shorthands: cargo b, cargo r, cargo t, cargo c."""
    name = "cargo_shorthands"
    priority = 25

    SHORTHANDS = {
        "b": "build",
        "r": "run",
        "t": "test",
        "c": "check",
    }

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 2 and cmd.tokens[0].lower() == "cargo":
            return cmd.tokens[1].lower() in self.SHORTHANDS
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        full_sub = self.SHORTHANDS[cmd.tokens[1].lower()]
        new_tokens = ["cargo", full_sub] + cmd.tokens[2:]
        return cmd.quote_join(new_tokens), 1.0, f"Expanded 'cargo {cmd.tokens[1]}' to 'cargo {full_sub}'"


class GoRunBareRule(Rule):
    """Converts `go run` (missing package/file) to `go run .`."""
    name = "go_run_bare"
    priority = 25

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) == 2 and cmd.tokens[0].lower() == "go" and cmd.tokens[1].lower() == "run":
            return True
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "go run .", 0.95, "Added current package '.' to 'go run'"
