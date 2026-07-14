# Security Policy

## Reporting a vulnerability

If you find a security issue in Ithuriel itself, please report it privately rather than opening a public issue. Use GitHub's private security advisory feature for this repository ("Security" tab, "Report a vulnerability"). Include the affected version or commit, a minimal reproduction, and the impact you observed. Please allow a reasonable period for a fix before any public disclosure.

## Authorized use and Rules of Engagement

Ithuriel drives real scanning and adversarial probing tools (for example nmap for port scanning, AgentDojo and published attacks for prompt-injection probing) and produces assurance conclusions from their output. That makes it dual-use. It is built for authorized security assessment, defensive research, and compliance evidence, and it must only be pointed at systems you own or have explicit written authorization to test.

The codebase enforces this posture in code rather than trusting the operator to be careful:

- Rules of Engagement authorization is mandatory for any side-effecting action. An empty `allowed_targets` denies by default, and a target outside the authorized host or CIDR is refused before dispatch.
- Side-effecting actions pass through a two-phase policy enforcement point (`executor.py`). The pre-dispatch check re-computes the action hash and re-runs the policy independently, so an upstream check is never trusted as sufficient.
- Command execution is allowlist-only and structured. The allowlist governs the action type and argument grammar, not just a binary name, and no shell is ever invoked.
- The current side-effecting and scanning slices are fixture-first and mock-backed: they perform no real network egress toward, or side effects on, the target under assessment. (The AI injection slice does call a real remote model API, with real token cost and data egress to the model provider, while its tool environment remains a mock; see `docs/DESIGN.en.md` section 5 on environment fidelity versus model transport.) A Rules of Engagement denial becomes an out-of-scope coverage gap rather than a silent bypass.

Every report is scoped by an explicit `assurance_level: none` statement and applies only to the exact fixture or target variant that was assessed. Do not read a passing result as a general compliance certification, and do not use Ithuriel to attack third-party systems.

## Handling of secrets and data

Do not commit API keys, tokens, or other credentials. Do not pass secrets inline in shell commands, since a permission or history mechanism can persist the full command including the secret; read them from a file instead (for example `OPENROUTER_API_KEY=$(cat keyfile) ...`). Raw scan data and any personally identifiable information stay out of version control, minimized and de-identified.
