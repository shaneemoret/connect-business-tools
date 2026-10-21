# Verification, renewal and release acceptance

## Runtime proof

Use the stored credential through its actual route. Auth check -> minimal required data read -> specifically authorized write test -> independent readback -> cleanup if applicable. A valid key, populated registry, connector badge, HTTP 200, GraphQL schema listing or unchanged title are not proof of every permission.

Report these separately: account authentication; data read; accepted unchanged-value write; persisted write/readback; cleanup; untested capabilities. A read-only connection can be useful and should not be called broken merely because the vendor forbids a write. Do not ask for full admin access unless the actual approved workflow requires it. Record plan/scopes/tenant limitations.

Prefer isolated test data with a clear recovery plan. If using an existing value unchanged, preserve it and state the limitation. No live emails, invites, payments, production toggles, role/privacy changes or deletion of business records as a connectivity test. A write script must be reviewed before use and stay disabled unless requested/approved. Any failed restoration is a blocker requiring precise residual disclosure; do not mark connected and hide it.

## Failure and maintenance

Separate manager locked/missing -> credential absent -> expired/revoked -> authentication -> insufficient scope -> vendor plan -> rate limit -> network -> provider response. Do not repeatedly rotate a good key to solve a 429 or outage. A gateway owns its OAuth refresh; local agents should not race it. Static-key renewal can require the owner. Unknown expiration is not "never expires". Reuse the same registry reference after replacement. No automatic plugin fallback, vault export, or silent paid upgrade.

## Package checks

Release label: **Mac verified, Windows draft** until native Windows proof is recorded. Run the SAME `test_connections.py` file on each actual OS before calling it cross-platform. OS-branch mocks, managed-copy tests on Mac and non-Windows CI validate code paths only. They are not Windows execution proof. Record platform version/build, Python executable/version, full suite count and result. `preflight.py` must select only the matching guide, reject unsupported versions and block Windows live setup while its release remains draft.

Portable code rules: pathlib filesystem paths; argument-list subprocesses with no shell evaluation/pipes; no sudo/chmod or Unix executable-bit fixture dependency; explicit UTF-8; preserve CRLF outside managed instruction blocks; native-executable/Python fixture runners; managed-copy fallback without Windows link privilege; no PowerShell execution-policy changes. The skill's `.gitattributes` keeps package sources at LF during Windows Git checkout so bundle hashes remain valid; existing owner instruction files keep their own endings. Do not interpret an install default as an admin grant. Unknown/missing Windows timezone data must be reported, never treated as a failed connection or silently used for timezone conversions.

Before distributing: validate SKILL.md, run test_connections.py, check the locked manifest with `install.py --check-bundle`, and confirm no owner-specific paths or real records entered the package. Installation preserves instruction text outside managed blocks, refuses conflicting skill folders, and is idempotent. Negative checks cover malformed/expired profiles, a leaking/failed probe, redirected requests, wrong credential origin, stale/mismatched receipts, queue sequencing and unrelated instruction preservation.

Cold acceptance uses a fresh Codex context and fresh Claude Code context, an isolated fictional business and no live writes. Ask the normal owner request without explaining the implementation; verify that the agent discovers the installed skill, follows the mailbox authority, selects the registry/broker over the plugin, distinguishes untested writes, and does not renew/rotate or scan mail without authorization. Keep actual reports. Runtime auth/unavailability must be reported honestly; a parent-session self-review is not a cold-model pass. Do not alter model selections without the owner's request.

The workflow is reusable only where the agent can reach the owner's browser, manager and authorized command runner. A chat-only model needs an approved gateway/executor; documentation alone cannot grant access.
