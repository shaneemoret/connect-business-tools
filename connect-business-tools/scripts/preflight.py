#!/usr/bin/env python3
"""Read-only host detection; writes only the requested metadata receipt."""
import argparse
import datetime as dt
import os
from pathlib import Path
import platform
import sys
from connection import atomic_json, read_json

ROOT = Path(__file__).resolve().parent.parent

def admin_state(system):
    if system == 'Darwin':
        try:
            import grp
            elevated = os.geteuid() == 0
            return {'administrator_member': elevated or grp.getgrnam('admin').gr_gid in os.getgroups(), 'elevated': elevated, 'source': 'local group membership'}
        except (ImportError, KeyError, OSError):
            pass
    elif system == 'Windows':
        try:
            import ctypes
            from ctypes import wintypes
            k, a = ctypes.WinDLL('kernel32', use_last_error=True), ctypes.WinDLL('advapi32', use_last_error=True)
            k.GetCurrentProcess.restype = wintypes.HANDLE
            a.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
            a.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
            k.CloseHandle.argtypes = [wintypes.HANDLE]
            token, size, elevation_type = wintypes.HANDLE(), wintypes.DWORD(), wintypes.DWORD()
            if not a.OpenProcessToken(k.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
                raise OSError()
            try:
                if not a.GetTokenInformation(token, 18, ctypes.byref(elevation_type), ctypes.sizeof(elevation_type), ctypes.byref(size)):
                    raise OSError()
                elevated = bool(ctypes.windll.shell32.IsUserAnAdmin())
                return {'administrator_member': elevated or elevation_type.value in (2, 3), 'elevated': elevated, 'source': 'Windows token elevation type; no elevation requested'}
            finally:
                k.CloseHandle(token)
        except (AttributeError, OSError):
            pass
    return {'administrator_member': None, 'elevated': None, 'source': 'unavailable; do not assume admin access'}

def select_platform(system, version, build=None):
    """Conservative guide baselines, not a claim of vendor/runtime support."""
    try:
        major = int(version.split('.')[0])
        if system == 'Darwin':
            return ('platform-mac.md', None) if major >= 13 else (None, 'This guide requires macOS 13 or newer.')
        if system == 'Windows':
            if major >= 10 and build is not None and int(build) >= 19045:
                return 'platform-windows.md', None
            return None, 'This draft guide requires Windows 10 build 19045 or a newer Windows release.'
    except (ValueError, AttributeError, TypeError):
        return None, 'The operating system version could not be verified.'
    return None, 'Only macOS and native Windows are covered; Linux and WSL are blocked.'

def detect(shell=None):
    system = platform.system()
    version = platform.mac_ver()[0] if system == 'Darwin' else platform.version()
    build = sys.getwindowsversion().build if system == 'Windows' and hasattr(sys, 'getwindowsversion') else None
    reference, reason = select_platform(system, version, build)
    inferred = os.environ.get('SHELL') if system == 'Darwin' else os.environ.get('ComSpec') if system == 'Windows' else None
    shell_name = shell or inferred
    reasons = [reason] if reason else []
    if not shell_name:
        reasons.append('The execution shell has not been identified; resolve it from the runtime.')
    if sys.version_info < (3, 9):
        reasons.append('Python 3.9 or newer is required; follow the matching platform installation steps.')
    admin = admin_state(system)
    if admin['administrator_member'] is None:
        reasons.append('Administrator membership could not be established; inspect through the matching platform route.')
    support = read_json(ROOT / 'platform-support.json')
    key = 'mac' if system == 'Darwin' else 'windows' if system == 'Windows' else None
    release = support.get(key, {}).get('status', 'unsupported')
    if reference and release != 'verified':
        reasons.append('This platform is a draft until the complete suite passes on an actual matching computer; live onboarding is blocked.')
    return {'version': 1, 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'status': 'blocked' if reasons else 'ready', 'reasons': reasons,
            'os': {'system': system, 'version': version, 'build': build, 'architecture': platform.machine()},
            'shell': {'value': shell_name, 'source': 'runtime-declared' if shell else 'environment; verify against actual runtime'},
            'admin': admin, 'python': {'version': platform.python_version(), 'executable': str(Path(sys.executable).resolve())},
            'platform_reference': str(Path('references') / reference) if reference else None,
            'platform_release': release,
            'note': 'No installations, permissions, credentials, mailbox reads or elevation performed. Missing admin rights alone do not block user-level work.'}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--shell', help='Actual shell identified by the agent runtime; do not ask the owner')
    a = p.parse_args()
    result = detect(a.shell)
    atomic_json(a.output, result)
    print('Preflight recorded: ' + result['status'] + '. Platform: ' + result['os']['system'] + '. No system changes made.')
    return 0 if result['status'] == 'ready' else 1

if __name__ == '__main__':
    sys.exit(main())
