# Connect My Business Tools

A skill for Codex (and Claude Code) that gets your AI working inside the tools your business runs on.

It reads the last two months of your business email, finds your core tools, and shows you a plain report: what your AI can reach today, what an API key would let it read and change, and what to do next. Then it walks you through making each key in your own browser and saving it in your computer's password vault, one tool at a time.

## Use it

Paste this into Codex in the ChatGPT desktop app:

```
Install the connect-business-tools skill from https://github.com/shaneemoret/connect-business-tools (the connect-business-tools folder) into my Codex skills. Then read its SKILL.md and follow it: find my tools from the last two months of my email, show me the report, and walk me through the API key for each core tool, one at a time.
```

## Works on

- Mac: tested and ready.
- Windows: being tested. On Windows the skill checks your computer first and tells you plainly if it can go ahead yet.

## What it will and won't do

- It reads your email. It never sends, buys, deletes or changes anything in your accounts.
- You sign in and click Create and Copy yourself. A key never goes in the chat, a file or a command.
- Each key goes into the password vault already on your computer (Keychain on a Mac, Credential Manager on Windows, or the manager you already use).
- It tests each key by reading, never by changing your business data.
- It never connects LinkedIn, by key, plugin, browser or any other route. Automating LinkedIn can get your account suspended or banned.

## What's inside

- `connect-business-tools/SKILL.md`: the workflow your AI follows.
- `connect-business-tools/references/`: how it finds your tools, stores keys, keeps records and tests access.
- `connect-business-tools/scripts/`: small Python helpers (no extra packages) that store, test and reuse each connection. Run `python3 scripts/test_connections.py` to check them.

Made by GrowthAcademy.Global.
