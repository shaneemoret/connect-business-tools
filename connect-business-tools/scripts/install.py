#!/usr/bin/env python3
"""Install one shared skill for Codex and Claude; preserve other instructions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from connection import ConnectionError, fail, update_block, atomic_json, read_json

ROOT = Path(__file__).resolve().parent.parent

def check_bundle():
    manifest = json.loads((ROOT / 'bundle-manifest.json').read_text(encoding='utf-8'))
    expected = manifest['sha256']
    for rel, digest in expected.items():
        path = (ROOT / rel).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            fail('Bundle file missing or changed; validate and intentionally relock before distribution.')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in {'bundle-manifest.json', '.installation.json'}}
    if actual != set(expected):
        fail('Bundle contains unexpected or unmanifested files.')
    return True

def installed_files(dest):
    return {p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in dest.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != '.installation.json'}

def validate_destination(dest):
    if not (dest.exists() or dest.is_symlink()):
        return
    if dest.resolve() == ROOT:
        return
    if dest.is_symlink():
        if dest.resolve() != ROOT:
            fail('Existing skill link belongs to another source; preserve it.')
        return
    marker = dest / '.installation.json'
    if not marker.is_file():
        fail('Existing skill folder belongs to another installation; preserve and review it.')
    state = read_json(marker)
    if state.get('source') != str(ROOT) or state.get('files') != installed_files(dest):
        fail('Managed skill copy changed locally; preserve it and reconcile before refresh.')
    removed = set(state['files']) - set(installed_files(ROOT))
    if removed:
        fail('Update would remove managed files; preserve the copy and review cleanup separately.')

def put_skill(dest, prefer_links):
    if dest.is_symlink() or (dest.exists() and dest.resolve() == ROOT):
        return
    if not dest.exists() and prefer_links:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.symlink_to(ROOT, target_is_directory=True)
            return
        except OSError:
            pass  # No elevation or OS-security changes just for links.
    dest.mkdir(parents=True, exist_ok=True)
    for rel in installed_files(ROOT):
        source = ROOT / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    atomic_json(dest / '.installation.json', {'version':1, 'source':str(ROOT), 'files':installed_files(dest)})

def install(project, home, prefer_links=None):
    check_bundle()
    project, home = Path(project).resolve(), Path(home).resolve()
    # Preflight all collisions and markers before making changes.
    destinations = [home/'.agents'/'skills'/'connect-business-tools', home/'.claude'/'skills'/'connect-business-tools']
    for dest in destinations:
        validate_destination(dest)
    docs = [home/'.codex'/'AGENTS.md', home/'.claude'/'CLAUDE.md', project/'AGENTS.md', project/'CLAUDE.md']
    key = 'connect-business-tools'
    for doc in docs:
        old = doc.read_text(encoding='utf-8') if doc.exists() else ''
        if old.count(f'<!-- {key}:start -->') != old.count(f'<!-- {key}:end -->') or old.count(f'<!-- {key}:start -->')>1 or (f'<!-- {key}:start -->' in old and old.index(f'<!-- {key}:start -->')>old.index(f'<!-- {key}:end -->')):
            fail('Existing instruction markers conflict; no installation performed.')
    for dest in destinations:
        put_skill(dest, os.name != 'nt' if prefer_links is None else prefer_links)
    body = f'''## Business tool connections

For a requested connection or a Gmail/Outlook tool audit, use the skill at `{ROOT / 'SKILL.md'}`.
This business's approved API registry is `{project / 'SYSTEMS' / 'api-connections'}`.
Inspect existing routes first; use each configured service's API/broker instead of its plugin.
No silent plugin fallback, raw key copying, unsolicited mail sweeps or automatic key rotation.
Honor this business's mailbox broker/gateway rules; an email plugin is used only when permitted.
Discover needs when requested, show an evidenced list, then connect approved tools one at a time.
Existing action-specific approvals still apply; a local path grants no cloud/remote execution access.'''
    for doc in docs:
        update_block(doc, key, body)
    return destinations

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path)
    p.add_argument('--home', type=Path)
    p.add_argument('--check-bundle', action='store_true')
    a = p.parse_args()
    try:
        if a.check_bundle:
            check_bundle()
            print('PASS: locked skill bundle hashes and file inventory.')
        elif a.project and a.home:
            from preflight import detect
            preflight = detect()
            atomic_json(a.project / 'SYSTEMS' / 'api-connections' / 'preflight.json', preflight)
            if preflight['status'] != 'ready':
                fail('Setup preflight is blocked; inspect the recorded platform reason. No installation performed.')
            install(a.project, a.home)
            print('Installed shared skill in Codex and Claude Code; both startup routes updated without replacing unrelated instructions.')
        else:
            p.error('Provide --check-bundle or both --project and --home.')
    except (ConnectionError, OSError, ValueError) as e:
        print(str(e) if isinstance(e, ConnectionError) else 'Installation failed; existing unrelated files preserved.', file=sys.stderr)
        sys.exit(1)
