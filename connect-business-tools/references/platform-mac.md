# Mac platform reference

Status (maintainers only, never shown to the owner): Mac verified. Helper baseline: macOS 13 or newer. This is a guide baseline, not a guarantee that today's browser, Python installer or agent runtime supports that version. Check current official runtime/installer requirements; if they require a newer version, record preflight blocked with that specific dependency. Do not upgrade the operating system without owner approval.

## Detect before acting

The agent reads OS/version and actual shell from the tool/runtime inventory. If a native command is needed before Python exists, run `sw_vers -productVersion` as an argument list; identify the runtime shell (usually zsh or bash), never ask the owner to open Terminal. Run `python3 scripts/preflight.py --output BUSINESS_ROOT/SYSTEMS/api-connections/preflight.json --shell SHELL_NAME` once Python works. Admin group membership and current elevation are different; the helper records both without requesting elevation. Lack of admin membership is not a reason to run everything as root.

Read only this platform reference on a Mac. If the host is too old or the runtime/browser route cannot operate, write the reason in preflight.json and stop the dependent step.

## Python and helper commands

- Agent checks `python3 --version` AND executes a small version check with the discovered executable. Require 3.9+. Do not treat a shim that only prompts for installation as a working interpreter.
- If missing, agent runs `xcode-select --install` to bring up Apple's installer. Owner sees the actual dialog and clicks **Install**, accepts any terms themselves and enters their own password if asked. Recheck Python afterward; installing developer tools does not guarantee a particular Python version. Do not give an invented download-time promise.
- Use Homebrew only if it is already installed and this installation is authorized. Otherwise use the current official Python.org installer, agent opens its page/download and gets to the installation step. Owner handles installer/password prompts. Do not install another package manager just for this skill.
- Agent runs all helpers as `python3 scripts/connection.py ...`, `python3 scripts/queue.py ...`, `python3 scripts/install.py ...`, `python3 scripts/test_connections.py`. Resolve the skill's actual path. Use argument lists, pathlib paths, UTF-8. Never send the owner a command to paste.

## Browser and computer permissions

Keep the owner's requested existing browser/profile. If no preference, Chrome is the default only after checking the runtime's current browser support. Safari support must be verified in current runtime documentation; do not claim an extension supports it by analogy. Use the official store listing for a needed extension. The owner clicks **Add to Chrome** or the real permission button when required; agent checks installation itself.

When the runtime explicitly requires Screen Recording or Accessibility, the agent opens the exact pane through its supported computer-use API. Where shell launching is permitted, the pane routes are:

```
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
```

These are technical recipes for the agent, not instructions for the owner to run. UI automation must still use the current harness's supported UI API. Deep links can move across macOS versions; verify the visible pane. Fallback: agent navigates Apple menu -> **System Settings** -> **Privacy & Security** -> the actual permission. Owner flips only the named switch and handles restart/relaunch approval; agent verifies the runtime afterward. Do not ask for blanket permissions that the task does not require.

## Credentials and security blocks

Use the existing manager's supported CLI/secure entry route, or Keychain where that is the documented business route. Agent saves directly through secure manager entry; clipboard is a fallback and may never traverse chat or logs. Keychain availability does not prove an approved bridge exists. Owner enters their own unlock/computer password; the agent does not ask for it in chat.

If Gatekeeper says an app cannot be opened or is untrusted, stop and explain the specific block in plain words. Do not use **Open Anyway**, remove quarantine, weaken protections, or run an unsigned workaround. No privilege escalation just to create skill links; installer can use managed copies without it.

## Plain words

Get to the real screen first. One action per message: "I opened the Mac's permission screen. Turn on **[actual app label]** so I can work in the browser." Replace the illustrative label with the exact visible one; never show placeholders. If manual navigation is unavoidable, start "Click the Apple menu in the top-left corner." Give timing only when supported by the actual installer or observed progress. Verify success yourself.

Official references checked 2026-10-20: [Apple command-line tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/), [Python on macOS](https://docs.python.org/3/using/mac.html). Check the selected agent/browser runtime's current official documentation during each setup.
