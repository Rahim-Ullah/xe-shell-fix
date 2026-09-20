"""
xsf.offline.rules.docker_rules - Docker and container heuristics.
"""
from typing import Optional, Tuple
from xsf.core.command import Command
from xsf.offline.rules.base import Rule


class DockerComposeMigrationRule(Rule):
    """Converts legacy `docker-compose` to modern `docker compose`."""
    name = "docker_compose_v2"
    priority = 10

    def match(self, cmd: Command) -> bool:
        return bool(cmd.tokens and cmd.tokens[0].lower() == "docker-compose")

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        new_tokens = ["docker", "compose"] + cmd.tokens[1:]
        return cmd.quote_join(new_tokens), 0.98, "Modernized 'docker-compose' to 'docker compose'"


class DockerRunInteractiveRule(Rule):
    """Adds `-it` if running an interactive shell container without TTY."""
    name = "docker_run_interactive"
    priority = 20

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 3 and cmd.tokens[0].lower() in ("docker", "podman") and cmd.tokens[1].lower() == "run":
            last_token = cmd.tokens[-1].lower()
            has_it = any(t in ("-it", "-ti", "-i", "-t") for t in cmd.tokens)
            return last_token in ("bash", "sh", "zsh", "/bin/bash", "/bin/sh") and not has_it
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        # Insert `-it` after `run`
        new_tokens = cmd.tokens[:2] + ["-it"] + cmd.tokens[2:]
        return cmd.quote_join(new_tokens), 0.95, "Added '-it' for interactive container terminal session"
