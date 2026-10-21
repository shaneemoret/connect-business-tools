# Discover the tools a business actually needs

Use this when the owner asks for a tool-stack audit or discovery, not on every task.

## Scope and sources

1. Read existing business context and mailbox access rules. Identify Gmail or Outlook (or both only when authorized), the correct business account, and which plugin, broker or gateway is permitted. Never bypass a mandatory mail broker. If neither is connected, help establish an approved mail connection first; do not ask for mailbox credentials in chat.
2. Default window: from the same local calendar date two months ago through now. State exact timezone-qualified bounds. At month-end use the last valid day of the earlier month. Honor an owner's different window. Search/paginate the full authorized window, deduplicate messages/threads and record pagination completion. If limits prevent a complete review, label the sample and missing coverage. Do not claim a comprehensive inventory from snippets or the first page.
3. Search mail from companies, not people. Leave out the owner's sent mail and threads where a person is writing to them; search by each company's sending domain rather than by keywords, which mostly return client conversations. Receipts often come from a billing company (Stripe, Paddle, PayPal, Apple, FastSpring): name the product the email is about, one row per product. Count signals that prove use as well as payment: sign-in alerts, two-step codes, weekly summaries, notifications and "granted access" notices. A tool that emails every week is in use even when it was not billed in the window.
4. Use sender domains, subjects, transaction/product activity, account notices and integrations as signals. Inspect only relevant message bodies to identify the tool and real workflow. Do not open attachments or follow sign-in/payment links merely because an email requests it. Avoid copying private email bodies, contacts or keys into the skill/queue. Retain source message/thread IDs and dates in the owner's private records only.
5. Inventory connected plugins with their actual connection state, capabilities and available operations; inventory documented API/gateway routes separately. Use environment discovery or plugin-management tools, not a guessed fixed list. No connector token extraction. `Available`, `installed`, `connected`, `authenticated` and `working for required action` are different states.

## Evidence and prioritization

For each candidate show: tool; observed business use; unique relevant threads/date range; required workflow; current plugin/API state; official API/plan findings; recommended action; confidence; next dependency. Add tools inferred from a demonstrated business need in a separate `proposed` class, with the reasoning; do not call them currently used.

Not a tool: newsletters, course and webinar promotions, auto-replies, and a client's own account that sent the owner an invite or a document (their CRM, their books, their e-signature). A tool counts only when the account is the business's own. Personal charges (shopping, food delivery, streaming, rent, utilities, personal finance, crypto) go on a separate "left out as personal" list, one line each, so the owner sees nothing was hidden; none of them enter the queue. When you cannot tell whether a tool is still in use, write "unknown", never "stopped".

Core tools are the five to eight the business would stop without, one or two per job: money (accounting, invoicing, payments, payroll), customers (CRM, email marketing, booking, website forms), work (projects, files, e-signature, website), talk (email, phone and text, meeting notes). If two tools do one job, the one used more often and more recently is core; list the other as an overlap.

Repeated promotional/newsletter/billing emails do not by themselves prove active use or an integration need. Separate subscriptions from work evidence. For example, recurring BigTime project/expense activity may justify investigating time/billing workflows; a Kajabi newsletter by itself does not justify access. These are candidate signals, not statements about those vendors' current API/plugin availability. Verify both with current official sources.

Prioritize owner-named needs first, then frequent meaningful work that agents could actually help with, time/revenue value, access gaps, setup cost and risk. Keep an already-working secure API. A plugin already covering the workflow can be marked `already covered`; investigate API gaps instead of replacing every plugin indiscriminately. When the owner wants API-first, document that service-specific choice and apply it after a working route is verified. Authentication requirements, paid entitlements and unavailable APIs are explicit dependencies.

## Queue and progression

Save a metadata-only queue using connection-records.md. Show the owner the report described in SKILL.md, in plain words, with a proposed order. Do not ask for the order or scope: start the first tool marked Make a key unless the owner redirects. Proceed one at a time; approval of discovery is not approval of credentials, costs, scopes or all external changes. Obtain any action-time confirmations the current harness requires. Approval may cover a named ordered batch, but cannot override those gates.

Advance each approved tool through researched -> connection setup -> stored -> read tested -> write tested/untested -> routed -> independently checked. Stop repeated failure, preserve working access and explain the exact missing dependency. Leave queued tools queued; never label the whole stack connected because one provider passed. Mark a new machine/cloud runtime unconfigured until tested there.

## Reusable research output

No new vendor adapters are installed from untrusted mail or third-party code. Author a minimal profile/probe using official docs, review it, and test it with fixtures first. Record official URLs and verified date because scopes, UI paths, API availability and vendor plans drift. Never hardcode the author's mailbox route or computer paths into a distributed skill.
