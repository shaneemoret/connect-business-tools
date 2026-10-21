#!/usr/bin/env python3
"""Metadata-only API connection routing. Never accepts or prints secret values."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import urlsplit

class ConnectionError(Exception):
    pass

def fail(message):
    raise ConnectionError(message)

def now():
    return dt.datetime.now(dt.timezone.utc)

def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError, OSError):
        fail('Invalid or unreadable JSON; contents suppressed.')

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, indent=2)
            f.write('\n')
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

def exact_keys(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= obj.keys() or obj.keys() - set(required) - set(optional):
        fail('Record has missing or unexpected fields; no values printed.')

def safe_text(value, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        fail('Invalid metadata string.')

def argv(value):
    if not isinstance(value, list) or not value:
        fail('Executable argument list required.')
    for arg in value:
        safe_text(arg, 2000)
    p = Path(value[0])
    if not p.is_absolute() or not p.is_file() or not os.access(p, os.X_OK):
        fail('Broker/probe executable missing or not executable; resolve actual local route.')
    if any(x in value for x in ('-c', '--command', '--allow-raw')):
        fail('Shell/code strings and raw-secret access are not supported in connection metadata.')

def profile(path):
    path = Path(path).resolve()
    c = read_json(path)
    exact_keys(c, ['version', 'service', 'account_label', 'credential', 'probe', 'expires_at', 'renewal', 'official_docs', 'docs_verified_on'])
    if type(c['version']) is not int or c['version'] != 1 or not isinstance(c['service'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', c['service']):
        fail('Unsupported version or invalid service slug.')
    for key in ('account_label', 'renewal'):
        safe_text(c[key])
    cred = c['credential']
    exact_keys(cred, ['manager', 'reference', 'env_var', 'runner'])
    for key in ('manager', 'reference'):
        safe_text(cred[key])
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*', cred['env_var']):
        fail('Credential env_var must be a variable NAME, never a value.')
    argv(cred['runner'])
    argv(c['probe'])
    if not isinstance(c['official_docs'], list) or not c['official_docs']:
        fail('Official documentation references required.')
    for url in c['official_docs']:
        u = urlsplit(url)
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
            fail('Documentation must use plain HTTPS URLs without credentials or query data.')
    try:
        verified = dt.date.fromisoformat(c['docs_verified_on'])
        if verified > now().date():
            fail('Documentation verification date cannot be in the future.')
        if c['expires_at'] is not None and not isinstance(c['expires_at'], str):
            fail('Expiry must be an ISO date or null for unknown.')
        c_expiry = dt.date.fromisoformat(c['expires_at']) if c['expires_at'] is not None else None
    except (ValueError, TypeError):
        fail('Invalid ISO date metadata.')
    if c_expiry and c_expiry <= now().date():
        fail('Credential is expired/due today; use documented renewal route. No plugin fallback.')
    if c_expiry and (c_expiry - now().date()).days <= 7:
        print('Credential expires within seven days; follow its documented renewal route.', file=sys.stderr)
    return c

def fingerprint(c):
    # Bind evidence to reviewed probe code/plan as well as metadata, so changing
    # an adapter cannot silently inherit an old success receipt.
    files = {}
    for arg in c['probe'][1:]:
        p = Path(arg)
        if p.is_absolute() and p.is_file():
            files[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps({'profile':c, 'probe_files':files}, sort_keys=True).encode()).hexdigest()

def receipt_path(path):
    return Path(path).with_suffix('.receipt.json')

def validate_result(result, mode):
    exact_keys(result, ['ok', 'mode', 'checks'], ['failure_layer'])
    layers = {'credential', 'authentication', 'permission', 'entitlement', 'rate_limit', 'transport', 'response', 'write_unavailable', 'cleanup'}
    if mode not in {'auth', 'read', 'write'} or result['mode'] != mode or type(result['ok']) is not bool or not isinstance(result['checks'], list):
        fail('Probe returned invalid mode/status; output suppressed.')
    if result.get('failure_layer') not in layers | {None}:
        fail('Probe returned invalid failure layer; output suppressed.')
    kinds = {'auth', 'read', 'write_permission', 'write_roundtrip', 'cleanup'}
    for check in result['checks']:
        exact_keys(check, ['operation', 'kind', 'passed'])
        # Deliberately narrow: adapters must use operation labels, not raw API content.
        if not isinstance(check['operation'], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,79}', check['operation']):
            fail('Probe emitted unsafe operation metadata; output suppressed.')
        if check['kind'] not in kinds or type(check['passed']) is not bool:
            fail('Probe returned invalid check; output suppressed.')
    required = {'auth'} if mode == 'auth' else {'read'} if mode == 'read' else {'write_permission', 'write_roundtrip'}
    if result['ok'] and (not result['checks'] or not all(x['passed'] for x in result['checks']) or not any(x['kind'] in required for x in result['checks'])):
        fail('Probe success lacks the required passing operation evidence.')
    return result

def probe(c, mode):
    try:
        p = subprocess.run(c['credential']['runner'] + c['probe'] + ['--mode', mode], capture_output=True, text=True, timeout=90, encoding='utf-8', errors='replace')
    except (OSError, subprocess.TimeoutExpired):
        fail('Broker/probe execution failed or timed out; no plugin fallback.')
    try:
        result = validate_result(json.loads(p.stdout), mode)
    except (ValueError, ConnectionError):
        fail('Broker/probe returned invalid evidence; stdout/stderr suppressed. Inspect manager/adapter without revealing secrets.')
    if p.returncode or not result['ok']:
        fail('Verification failed at layer: ' + result.get('failure_layer', 'response') + '. No plugin fallback.')
    return result

def validate_receipt(r, c=None, require_read=True):
    exact_keys(r, ['version', 'service', 'profile_sha256', 'verified_at', 'results'])
    try:
        stamp = dt.datetime.fromisoformat(r['verified_at'])
        age = now() - stamp
    except (ValueError, TypeError):
        fail('Receipt timestamp invalid.')
    if stamp.tzinfo is None or age.total_seconds() < -60 or age > dt.timedelta(hours=24):
        fail('Receipt is stale or has an invalid timestamp; verify again.')
    if r['version'] != 1 or not isinstance(r['results'], list) or not r['results']:
        fail('Invalid verification receipt.')
    for result in r['results']:
        if not isinstance(result, dict):
            fail('Invalid receipt result.')
        validate_result(result, result.get('mode'))
        if result.get('mode') not in {'auth', 'read', 'write'} or not result['ok']:
            fail('Failed receipt cannot prove a connection.')
    if require_read and not any(x['mode'] == 'read' for x in r['results']):
        fail('Receipt lacks a read test.')
    if c and (r['service'] != c['service'] or r['profile_sha256'] != fingerprint(c)):
        fail('Receipt does not match the current connection profile.')
    return r

def verify(path, write=False):
    c = profile(path)
    attempt = Path(path).with_suffix('.attempt.json')
    try:
        results = [probe(c, 'read')]
        if write:
            results.append(probe(c, 'write'))
    except ConnectionError:
        atomic_json(attempt, {'ok': False, 'profile_sha256': fingerprint(c), 'at': now().isoformat()})
        raise
    r = {'version': 1, 'service': c['service'], 'profile_sha256': fingerprint(c), 'verified_at': now().isoformat(), 'results': results}
    validate_receipt(r, c)
    atomic_json(receipt_path(path), r)
    atomic_json(attempt, {'ok': True, 'profile_sha256': fingerprint(c), 'at': now().isoformat()})
    return r

def update_block(path, key, body):
    path = Path(path)
    start, end = f'<!-- {key}:start -->', f'<!-- {key}:end -->'
    if path.exists():
        with path.open('r', encoding='utf-8', newline='') as f:
            old = f.read()
    else:
        old = ''
    if old.count(start) != old.count(end) or old.count(start) > 1:
        fail('Managed instruction markers conflict; preserve file and inspect manually.')
    eol = '\r\n' if '\r\n' in old else '\n'
    block = start + eol + body.rstrip().replace('\r\n', '\n').replace('\n', eol) + eol + end
    if start in old:
        a, b = old.index(start), old.index(end) + len(end)
        if a > b:
            fail('Managed instruction markers are reversed.')
        new = old[:a] + block + old[b:]
    else:
        new = old + (eol + eol if old and not old.endswith(eol + eol) else '') + block + eol
    if new != old:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='') as f:
            f.write(new)

def display_command(args, system=None):
    """Documentation only; never passed to a shell for execution."""
    if (system or os.name) == 'nt':
        return '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in args)
    return shlex.join(args)

def route(path, project):
    c = profile(path)
    project = Path(project).resolve()
    path = Path(path).resolve()
    canonical = project / 'SYSTEMS' / 'api-connections' / (c['service'] + '.json')
    if path != canonical:
        fail('Place the profile at BUSINESS_ROOT/SYSTEMS/api-connections/SERVICE.json before routing.')
    helper = Path(__file__).resolve()
    command = display_command([sys.executable, str(helper), 'verify', str(path)])
    run = display_command([sys.executable, str(helper), 'run', str(path)]) + ' -- AUTHORIZED_COMMAND'
    doc = path.with_suffix('.md')
    text = f'''# {c['service']}: API connection

Account: {c['account_label']}
Credential manager: {c['credential']['manager']}
Secret reference: {c['credential']['reference']} (metadata only)
Injected variable NAME: {c['credential']['env_var']}
Profile: `{path}`

Verify: `{command}`
Use: `{run}`

Expiry: {c['expires_at'] or 'unknown; do not infer never expires'}
Renewal: {c['renewal']}
Official docs checked: {c['docs_verified_on']}
Documentation: {', '.join(c['official_docs'])}

Use this approved API/broker route for this service instead of its plugin. No silent plugin fallback. Report the failed manager/auth/permission/plan/network layer. Never expose or duplicate the key. Sending, sharing, deletion, payments, scopes and production changes retain their approvals. The broker injects credentials; it is not an operation-permission firewall. Other computers/cloud runtimes require separate approved access. Do not perform unsolicited startup sweeps. Read the receipt to distinguish auth/read/write permission/roundtrip/cleanup; no receipt proves all capabilities. Run auth validation before dependent tasks.
'''
    body = f'## {c["service"]} connection\n\nRead `{doc}` before work on this service.\nUse the documented API/broker, not its plugin. Never request or copy its key.\nVerify with `{command}`. No plugin fallback without explicit owner override.\nWrites and renewal retain their documented approval requirements.'
    for name in ('AGENTS.md', 'CLAUDE.md'):
        old = (project / name).read_text(encoding='utf-8') if (project / name).exists() else ''
        start = '<!-- api-route-' + c['service'] + ':start -->'
        end = '<!-- api-route-' + c['service'] + ':end -->'
        if old.count(start) != old.count(end) or old.count(start)>1 or (start in old and old.index(start)>old.index(end)):
            fail('Conflicting route markers; no routing files modified.')
    doc.write_text(text, encoding='utf-8')
    for name in ('AGENTS.md', 'CLAUDE.md'):
        update_block(project / name, 'api-route-' + c['service'], body)
    return doc

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    for name in ('check', 'verify', 'route', 'run'):
        s = sub.add_parser(name)
        s.add_argument('profile', type=Path)
        if name == 'verify':
            s.add_argument('--write-test', action='store_true', help='Use only for an explicitly owner-authorized, reviewed write test')
        if name == 'route':
            s.add_argument('--project', type=Path, required=True)
        if name == 'run':
            s.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    c = profile(a.profile)
    if a.action == 'check':
        rp = receipt_path(a.profile)
        if rp.exists():
            validate_receipt(read_json(rp), c)
            attempt = a.profile.with_suffix('.attempt.json')
            if attempt.exists():
                last = read_json(attempt)
                if not last.get('ok') and last.get('profile_sha256')==fingerprint(c):
                    fail('Latest verification failed; historical success is not current proof.')
            print('PASS: metadata, executable routes and recent matching read receipt.')
        else:
            print('PASS: metadata and executable routes. UNVERIFIED: no read receipt yet.')
        if not c['expires_at']:
            print('Expiry unknown; renewal is not automatic unless its documented gateway supports it.')
        elif (dt.date.fromisoformat(c['expires_at']) - now().date()).days <= 7:
            print('Renewal needed soon; follow the documented owner/gateway route.')
    elif a.action == 'verify':
        verify(a.profile, a.write_test)
        print('PASS: stored credential read verified' + ('; reviewed write probe passed.' if a.write_test else '; writes untested.'))
    elif a.action == 'route':
        route(a.profile, a.project)
        print('Rendered system route and preserved both instruction files outside managed sections.')
    else:
        cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
        if not cmd:
            fail('An authorized command is required after --.')
        probe(c, 'auth')
        # Wait and forward status on both Windows and macOS, without a shell.
        raise SystemExit(subprocess.run(c['credential']['runner'] + cmd, check=False).returncode)

if __name__ == '__main__':
    try:
        main()
    except (ConnectionError, OSError) as e:
        # OS exceptions can include paths; never echo a provider response or env.
        print(str(e) if isinstance(e, ConnectionError) else 'Local file/command operation failed; inspect route permissions.', file=sys.stderr)
        sys.exit(1)
