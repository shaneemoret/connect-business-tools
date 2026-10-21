# Windows platform reference

Release: **Windows draft. Not verified on an actual Windows machine.** Do not onboard an owner live using this draft. Preflight records Windows details but blocks live setup until the full unchanged suite passes on an actual Windows machine and the release record is updated with that receipt. Mock tests, WSL, a Mac and a Linux CI job do not satisfy that gate.

Guide baseline: native Windows 10 build 19045 or Windows 11 (build 22000+) with a runtime and Python installation that officially support the actual release. This guide baseline is not a declaration that an old Windows release remains vendor-supported. Verify current OS/runtime eligibility and any required security support. Older builds, Windows Server and WSL are outside this guide; record preflight blocked rather than giving Mac or Linux steps.

## Detect before acting

Use runtime inventory to identify Windows version/build, actual shell (PowerShell, pwsh or Command Prompt), and current admin status. Agent can inspect `$PSVersionTable` in its existing PowerShell tool when available; this is not a command for the owner to type. `preflight.py` reads OS/build and administrator/elevation token information without elevating. Pass the actual runtime shell through `--shell`. Membership and current elevation are different; user-level work should not be elevated unnecessarily.

Read only this platform reference on Windows. If Python is absent, the agent writes preliminary preflight metadata through its existing file tool, then completes detection after the approved install. Unsupported/missing requirements remain blocked, not marked ready.

## Python and helper commands

- Check `py --version`, then run a version probe through that launcher; require 3.9+. Do not trust the `python` command by itself: an app-execution alias may open Microsoft Store. Never change Windows execution aliases or PowerShell execution policy to make this skill work.
- If Python is missing, agent uses the official WinGet entry: `winget install --id Python.Python.3.12 --exact`. The owner handles any **Yes**, **Install** or terms prompt. An install may be per-user and show no UAC prompt; do not promise a particular colored dialog. Do not use flags that silently accept agreements or elevate.
- If WinGet is missing, agent opens Python's official Microsoft Store listing and brings the owner to **Get**. Owner clicks it. Recheck the launcher; Store distributions can expose a verified versioned executable without installing the legacy `py` launcher. Prefer `py`; if unavailable after Store installation, locate and verify that actual Python executable (for example `python3.12 --version`) and use its absolute path. Record the selected executable. Do not loop between the Store alias and installation, or mark a missing launcher as a broken interpreter.
- Agent normally runs `py scripts\preflight.py --output BUSINESS_ROOT\SYSTEMS\api-connections\preflight.json --shell SHELL_NAME`, `py scripts\connection.py ...`, `py scripts\queue.py ...`, `py scripts\install.py ...`, `py scripts\test_connections.py`. Use the actual verified executable if the launcher is absent. Arguments are lists, not composed shell strings. No bash syntax, pipes, sudo, chmod or execution-policy changes. The owner never types these commands.

## Admin, security and browser

Owner handles the actual **Do you want to allow this app to make changes?** User Account Control prompt, clicking **Yes** only for the expected authorized official installer; a standard user may instead need their administrator. Agent never types admin credentials or tries to bypass the secure desktop.

If SmartScreen says **Windows protected your PC**, stop and explain. Do not click **More info** -> **Run anyway**, disable Defender/SmartScreen, change security policy, or coach the owner through bypassing it. Never alter the PowerShell execution policy.

Use the owner's existing Chrome profile when requested. Chrome is the default candidate; Edge is allowed only if the selected runtime's current official docs explicitly support its extension/control route. Do not assume the Mac computer-use setup exists on Windows. Verify the runtime's current Windows instructions and availability before asking for any permission or installing extensions. No agent changes to Windows security/privacy settings; the owner controls required approvals.

## Opening settings and saving credentials

Use the supported computer-use API to open the exact settings page first. The native Windows recipe is `start ms-settings:...` in Command Prompt, or `Start-Process 'ms-settings:...'` in PowerShell; verify the precise documented URI and visible page. These are agent recipes only. Shared Python helpers do not execute those shell strings. If the runtime disallows direct shell UI launching, navigate with its UI tools. When necessary say "Click **Start** on the taskbar"; Windows 11 commonly centers it, so do not insist it is bottom-left without checking.

Use the existing manager's supported Windows CLI/bridge, or Windows Credential Manager where that is the approved route. A Keychain-only bridge cannot be used here. Agent saves securely through manager entry; no pasted key in chat. If no supported secure bridge exists, name that specific gap and implement an approved Windows route rather than installing a second manager silently. Skill installation uses verified managed copies if directory links are unavailable; do not enable Developer Mode or request admin solely for links. No Windows ACL weakening.

Official references checked 2026-10-20: [WinGet requirements](https://learn.microsoft.com/en-us/windows/package-manager/winget/), [Microsoft Python setup](https://learn.microsoft.com/en-us/windows/dev-environment/python), [Python 3.12 Windows launcher and Store behavior](https://docs.python.org/3.12/using/windows.html). Recheck the chosen runtime's actual Windows support during validation.
