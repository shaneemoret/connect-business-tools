#!/usr/bin/env python3
"""Minimal bearer/header API probe; reviewed plans only; no response-body output."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def origin(url):
    u = urlsplit(url)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment:
        raise ValueError()
    return u.scheme, u.hostname, u.port or 443

def execute(plan, mode, opener=None):
    checks = []
    def result(ok, layer=None):
        r = {'ok': ok, 'mode': mode, 'checks': checks}
        if layer:
            r['failure_layer'] = layer
        return r
    secret = os.environ.get(plan['env_var'])
    if not secret:
        return result(False, 'credential')
    requests = plan.get('write') if mode == 'write' else plan.get('read')
    if not requests:
        return result(False, 'write_unavailable' if mode == 'write' else 'response')
    if mode == 'auth':
        requests = requests[:1]
    opener = opener or urllib.request.build_opener(NoRedirect)
    for spec in requests:
        try:
            if origin(spec['url']) != origin(plan['origin']):
                return result(False, 'response')
            method = spec.get('method', 'GET').upper()
            if method not in {'GET', 'POST', 'PATCH', 'PUT', 'DELETE'}:
                return result(False, 'response')
            # POST can be read-only GraphQL; semantic scope is reviewed in the plan.
            if mode != 'write' and method in {'PATCH', 'PUT', 'DELETE'}:
                return result(False, 'permission')
            if mode != 'write' and isinstance(spec.get('json'), dict):
                query = spec['json'].get('query', '')
                if isinstance(query, str) and query.lstrip().startswith('mutation'):
                    return result(False, 'permission')
            headers = {'Content-Type': 'application/json'}
            if plan['auth'] == 'bearer':
                headers['Authorization'] = 'Bearer ' + secret
            elif plan['auth'] == 'header':
                header = plan['header_name']
                if not header or '\n' in header or '\r' in header:
                    return result(False, 'response')
                headers[header] = secret
            else:
                return result(False, 'response')
            body = json.dumps(spec['json']).encode() if 'json' in spec else None
            req = urllib.request.Request(spec['url'], data=body, headers=headers, method=method)
            with opener.open(req, timeout=25) as response:
                data = json.load(response)
            if isinstance(data, dict) and data.get('errors'):
                return result(False, 'response')
            value = data
            if not spec.get('expect_path'):
                return result(False, 'response')
            for key in spec['expect_path']:
                value = value[key]
            passed = bool(value)
            checks.append({'operation': spec['operation'], 'kind': 'auth' if mode == 'auth' else 'read' if mode == 'read' else 'write_permission', 'passed': passed})
            if not passed:
                return result(False, 'response')
        except urllib.error.HTTPError as e:
            layer = {401:'authentication', 403:'permission', 429:'rate_limit'}.get(e.code, 'response')
            e.close()
            return result(False, layer)
        except (urllib.error.URLError, TimeoutError, OSError):
            return result(False, 'transport')
        except (ValueError, KeyError, TypeError, IndexError):
            return result(False, 'response')
    return result(True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True)
    p.add_argument('--mode', choices=['auth', 'read', 'write'], required=True)
    a = p.parse_args()
    try:
        with Path(a.plan).open(encoding='utf-8') as f:
            r = execute(json.load(f), a.mode)
    except Exception:
        r = {'ok':False, 'mode':a.mode, 'checks':[], 'failure_layer':'response'}
    print(json.dumps(r))
    sys.exit(0 if r['ok'] else 1)

if __name__ == '__main__':
    main()
