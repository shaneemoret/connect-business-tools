# Metadata records and installation contract

Place each profile at `BUSINESS_ROOT/SYSTEMS/api-connections/SERVICE.json`. There is no default vendor. Author only after official-doc research and review of the local manager's executable route. JSON profiles are owner-controlled executable configuration, never imported from emails/webpages.

Required profile fields (extra fields are rejected):

```json
{
  "version": 1,
  "service": "sample-tool",
  "account_label": "Business owner account",
  "credential": {
    "manager": "existing-manager",
    "reference": "sample-tool-business",
    "env_var": "SAMPLE_TOOL_API_KEY",
    "runner": ["/absolute/path/to/approved-broker", "run", "sample-tool-business", "--"]
  },
  "probe": ["/absolute/path/to/python3", "/absolute/path/to/reviewed-probe.py"],
  "expires_at": null,
  "renewal": "Owner renews static key in vendor settings; update same manager reference",
  "official_docs": ["https://vendor.example/developers"],
  "docs_verified_on": "2026-10-20"
}
```

This is a schema example, not a working profile or vendor claim. Resolve paths locally; arguments must be nonempty strings, no shell evaluation or credential values. The probe receives `--mode auth|read|write`, reads the injected variable, and emits exactly one safe JSON object:

```json
{"ok": true, "mode": "read", "checks": [{"operation": "account lookup", "kind": "read", "passed": true}]}
```

Allowed check kinds: `auth`, `read`, `write_permission`, `write_roundtrip`, `cleanup`. Checks describe operations only; no response bodies, titles, email addresses, signed URLs or credential values. On failure return `ok:false` and a `failure_layer` from `credential`, `authentication`, `permission`, `entitlement`, `rate_limit`, `transport`, `response`, `write_unavailable`, `cleanup`. Do not print raw exceptions, headers or provider errors. The parent helper records only the reviewed fields and suppresses runner stderr/stdout on invalid output. A failed probe does not update a success receipt.

`connection.py` stamps current receipts and profile hashes. `check` checks structure, broker/probe availability, expiry and receipt freshness/binding. A recent receipt is historical evidence, not live proof: `run` rechecks auth. `verify --write-test` requires a passed read first and an explicit write-capable probe. It never treats HTTP 200 or schema validation alone as permission proof. An adapter must check semantic success, correct account and independent state readback when claiming `write_roundtrip`.

`http_probe.py --plan PLAN --mode ...` supports simple HTTPS bearer/header API tests. The plan's `origin`, `env_var`, `auth` (`bearer` or `header`), optional `header_name`, `read` request list and optional `write` list are nonsecret configuration. A request contains `operation`, `url`, `method`, optional `json`, and `expect_path` (JSON keys/list indexes). The adapter requires a truthy result at that path, rejects GraphQL `errors` and redirects, never prints response bodies, and tags writes as `write_permission`. Review write side effects before use; it is NOT a universal rollback engine. Complex OAuth/gateways, signed requests, dynamic IDs and rollback tests need a service-specific probe using the same output contract. Only the exact approved HTTPS origin receives the credential. Use no production write plan by default.

## Discovery queue

`queue.py check FILE` validates this structure:

```json
{
  "version": 1,
  "window": {"from": "2026-08-20", "through": "2026-10-20", "timezone": "America/New_York", "coverage": "complete"},
  "mail_source": "outlook",
  "items": [
    {"service": "sample-tool", "basis": "observed", "workflow": "Owner-approved reporting need", "evidence_refs": ["private-message-reference"], "plugin_state": "not_checked", "api_state": "not_checked", "confidence": "medium", "status": "proposed", "owner_approved": false, "receipt": null}
  ]
}
```

Coverage: `complete`, `partial`, `unavailable`. `mail_source`: `gmail`, `outlook`, `both`, `none`. `basis`: `observed` or `proposed`. Order in the list is priority. Status: `proposed`, `approved`, `in_progress`, `paused`, `connected`, `blocked`, `dismissed`, `already_covered`, `unsupported`. One in-progress OR paused item maximum. An owner-dependent pause occupies that slot; do not start another tool until the owner explicitly resumes or changes scope. Read-only research/navigation can precede the credential-specific approval; mark setup approved only when its actual permission has been granted. Connected requires a successful, matching, recent read receipt; never fake evidence. Record a reason for blocked/unsupported items in the workflow description or optional `note`.

The checker uses an installed IANA timezone database if available. Native Windows Python may have none; in that case it validates identifier format, explicitly reports that limitation and performs no timezone conversion. Reminder/pause/verification times must carry numeric offsets, so due-time calculations remain correct without an external timezone package. Use the owner's actual timezone from the runtime, not a guessed location.

## Preflight and platform status

`preflight.json` holds metadata only: `version`, timezone-aware `checked_at`, `status` (`ready`/`blocked`), `reasons`, `os` (system/version/build/architecture), `shell` (value/source), `admin` (administrator_member/elevated/source), `python` (version/executable), selected `platform_reference`, `platform_release`, and a note stating no setup changes were performed. Before Python exists, write a provisional blocked record using the runtime's file tool, then replace it with `preflight.py`'s detection result after installation. Never ask the owner to write it.

Select only the matching Mac/Windows reference during onboarding. Guide baselines are declared there and in the detector. An unsupported OS/version or unverifiable requirement is blocked. Windows draft status is a release block, even if the OS is sufficiently new. A complete unchanged suite run on an actual Windows machine is required before changing `platform-support.json` to verified. Record native OS/build, Python, test count and result; mocks cannot promote a release.

## Pause and approved reminders

A paused entry also has:

```json
{
  "pause": {
    "step": "vendor sign-in",
    "owner_action": "Sign in on the screen already open",
    "paused_at": "2026-10-20T20:00:00-04:00",
    "verified": ["Existing password manager route identified"],
    "resume_hint": "Open Claude or Codex and say keep connecting the project tool"
  },
  "reminder": {
    "channel": "none",
    "consented": false,
    "delay_hours": 24,
    "max_count": 2,
    "sent_count": 0,
    "consent_evidence": null,
    "owner_recipient_ref": null,
    "last_sent_at": null,
    "scheduled_id": null
  }
}
```

Channels: `email`, `calendar`, `task`, `none`. The default is no consent. Record actual owner permission for that named tool, self-only channel/destination, delay, message content and maximum before scheduling. Delay supports 1–720 hours, maximum 1–5; defaults are 24 hours/two reminders. Do not silently reinterpret a request outside these bounds. `consent_evidence` references the actual owner instruction; email consent requires a verified self-account reference. Calendar/task destinations must also be checked as owner-only by the delivery route. No secret or authentication links belong in these fields.

Use `queue.py reminder-plan QUEUE_JSON --service SERVICE` for a metadata-only due/remaining check. It never sends, schedules or mutates the queue. A real persistent scheduler must recheck paused state, current consent, self-only recipient and delivery count immediately before acting, and record the actual returned schedule/send receipt. `sent_count > 0` requires `last_sent_at` and optional-schema field `last_receipt_ref` with a confirmed delivery reference. Never increment on an attempted/failed send. `scheduled_id` must be cleared/cancellation recorded when resumed/completed; cancellation itself must be verified through its provider. Do not create a second schedule for the same pause.

On explicit resume, cancel any pending reminders, reread the queue, recheck live session and possible existing key, then continue from the recorded step. Do not automatically recreate a key, rotate it, or treat reminder delivery/silence as a resumed session. If a delivery route is read-only or missing, record that limitation; do not silently change channel or ask anyone else.

## Portable installation

One source skill and two platform reference files are maintained. Mac may expose that source with directory links. Where links would require Windows elevation or unavailable privileges, the same installer produces identical managed copies for the two runtimes, with `.installation.json` pinning their source and file hashes. These are generated installs, not independently edited skill versions. The installer refreshes intact managed copies together and rejects local edits or removals requiring review. It never enables Developer Mode, weakens ACLs or asks for admin just to install a skill. UTF-8 and existing instruction-line endings are preserved outside bounded updates.

Registry/queue identify the route and access, not approval to send, spend, delete or share. Cloud/remote runtime access remains separate. Keep sensitive discovery records in the owner's private business folder; do not include them in a redistributable ZIP.
