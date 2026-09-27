# Code of Conduct

## Our Commitment

xe-shell-fix (`xsf`) is a tool that executes shell commands on behalf of users. Because of this, the security and trustworthiness of every contribution matters deeply. We are committed to maintaining an inclusive, respectful, and technically rigorous community.

All participants — contributors, maintainers, issue reporters, and users — are expected to uphold these standards.

---

## Our Standards

### ✅ Expected Behaviour

- **Respectful technical discussion.** Critique ideas and code, not people.
- **Constructive feedback.** Issue reports and reviews should identify problems and, where possible, suggest solutions.
- **Transparency.** Be clear about what your code does, especially changes that affect command execution, AI integration, or user data.
- **Patience.** This is an open-source project maintained by volunteers. Response times vary.
- **Security awareness.** Because xsf executes shell commands, contributors must understand the security implications of their changes.

### ❌ Unacceptable Behaviour

- Personal attacks, harassment, or discriminatory language.
- Deliberately introducing code that bypasses the safety gate, weakens the command confirmation flow, or enables silent execution of dangerous commands.
- Committing API keys, tokens, passwords, or any secrets to the repository.
- Submitting a rule, AI provider, or shell hook that reads, transmits, or stores user data beyond what is required for command repair.
- Filing false security reports or using vulnerability reports to harass maintainers.
- Trolling, spamming, or off-topic disruption.

---

## Security-Specific Expectations

xe-shell-fix sits in a privileged position: it takes failed commands and suggests (and optionally executes) replacements. This makes security a **first-class concern** in every contribution:

1. **Do not weaken the confirmation flow.** Every AI-generated or heuristic fix must go through the safety gate before reaching the shell.
2. **Do not add remote code execution vectors.** No contribution should allow xsf to fetch and execute arbitrary code without explicit user knowledge.
3. **Do not exfiltrate data.** The AI request payload contains only the failed command and its stderr. It must not include filesystem contents, environment variables, or credentials.
4. **Vulnerabilities must be reported privately.** See [`SECURITY.md`](./SECURITY.md).

---

## Enforcement

Maintainers are responsible for clarifying and enforcing this Code of Conduct. Instances of unacceptable behaviour may be reported to the maintainer:

- **GitHub Issues** (for non-sensitive conduct concerns)
- **GitHub Security Advisories** (for security violations)
- **Direct contact** via the profile linked in the repository

Maintainers will review all reports and respond appropriately. Consequences range from a written warning to a permanent ban from the project, depending on severity.

---

## Attribution

This Code of Conduct is tailored for xe-shell-fix and draws on the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) as a reference baseline.
