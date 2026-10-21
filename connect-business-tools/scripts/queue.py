#!/usr/bin/env python3
"""Check metadata-only discovery coverage and one-at-a-time connection evidence."""
import argparse
import datetime as dt
from pathlib import Path
import re
import sys
from zoneinfo import available_timezones
from connection import ConnectionError, exact_keys, fail, read_json, safe_text, validate_receipt, profile, now

def timestamp(value):
    try:
        t = dt.datetime.fromisoformat(value)
        if t.tzinfo is None or t > now() + dt.timedelta(minutes=1):
            fail('Pause/reminder timestamp must be timezone-aware and not in the future.')
        return t
    except (ValueError, TypeError):
        fail('Invalid pause/reminder timestamp.')

def validate_pause(item):
    pause = item.get('pause')
    if item['status'] == 'paused':
        if not pause:
            fail('Paused tool needs a recorded step, owner action, time and resume instruction.')
        exact_keys(pause, ['step','owner_action','paused_at','verified','resume_hint'])
        for key in ('step','owner_action','resume_hint'):
            safe_text(pause[key])
        timestamp(pause['paused_at'])
        if not isinstance(pause['verified'], list):
            fail('Pause verification notes must be a list of safe operation labels.')
        for value in pause['verified']:
            safe_text(value)
    reminder = item.get('reminder')
    if reminder is None:
        return
    exact_keys(reminder, ['channel','consented','delay_hours','max_count','sent_count','consent_evidence','owner_recipient_ref','last_sent_at','scheduled_id'], ['last_receipt_ref'])
    if reminder['channel'] not in {'email','calendar','task','none'} or type(reminder['consented']) is not bool:
        fail('Invalid reminder channel or consent.')
    for field, lo, hi in (('delay_hours',1,720),('max_count',1,5),('sent_count',0,5)):
        if type(reminder[field]) is not int or not lo <= reminder[field] <= hi:
            fail('Reminder delay/count must be explicitly bounded.')
    if reminder['sent_count'] > reminder['max_count']:
        fail('Approved reminder limit has been exceeded.')
    if reminder['consented']:
        if reminder['channel'] == 'none':
            fail('No reminder channel was chosen.')
        safe_text(reminder['consent_evidence'])
        if reminder['channel'] == 'email':
            safe_text(reminder['owner_recipient_ref'])
    if reminder['last_sent_at']:
        timestamp(reminder['last_sent_at'])
    if reminder['sent_count'] and (not reminder['last_sent_at'] or not reminder.get('last_receipt_ref')):
        fail('Reminder count needs a real send/delivery receipt and time.')
    if (reminder['scheduled_id'] or reminder['sent_count']) and not reminder['consented']:
        fail('No reminder may be scheduled or sent without recorded owner consent.')
    if reminder['scheduled_id'] and item['status'] != 'paused':
        fail('Cancel the pending reminder when this tool resumes or completes.')

def reminder_plan(item):
    """Pure metadata planner. It never sends, schedules, or changes a count."""
    validate_pause(item)
    r = item.get('reminder')
    if item['status'] != 'paused' or not r or not r['consented'] or r['channel']=='none' or r['sent_count']>=r['max_count']:
        return {'action':'none','reason':'Not paused, no consent, or approved reminder limit reached.'}
    base = timestamp(r['last_sent_at'] or item['pause']['paused_at'])
    due = base + dt.timedelta(hours=r['delay_hours'])
    return {'action':'reminder_due' if now()>=due else 'wait','due_at':due.isoformat(),
            'channel':r['channel'],'owner_recipient_ref':r['owner_recipient_ref'],
            'remaining':r['max_count']-r['sent_count'],
            'rule':'Use only the approved self-only channel and real persistent scheduler. No auth links or secrets. Recheck paused state before delivery. Record actual receipt; never assume sent.'}

def check(path):
    path = Path(path).resolve()
    q = read_json(path)
    exact_keys(q, ['version', 'window', 'mail_source', 'items'])
    w = q['window']
    exact_keys(w, ['from', 'through', 'timezone', 'coverage'])
    try:
        if dt.date.fromisoformat(w['from']) > dt.date.fromisoformat(w['through']):
            fail('Discovery window is reversed.')
        zone = w['timezone']
        if not isinstance(zone, str) or not re.fullmatch(r'(?:UTC|[A-Za-z_+-]+(?:/[A-Za-z0-9_+.-]+)+)', zone):
            fail('Invalid timezone identifier.')
        zones = available_timezones()
        if zones and zone not in zones:
            fail('Unknown timezone identifier.')
    except (ValueError, TypeError, KeyError):
        fail('Invalid discovery dates/timezone.')
    if q['version'] != 1 or q['mail_source'] not in {'gmail','outlook','both','none'} or w['coverage'] not in {'complete','partial','unavailable'} or not isinstance(q['items'], list):
        fail('Invalid queue source/coverage/version.')
    states = {'proposed','approved','in_progress','paused','connected','blocked','dismissed','already_covered','unsupported'}
    seen = set()
    active = 0
    for item in q['items']:
        exact_keys(item, ['service','basis','workflow','evidence_refs','plugin_state','api_state','confidence','status','owner_approved','receipt'], ['note','pause','reminder'])
        slug = item['service']
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', slug) or slug in seen:
            fail('Invalid/duplicate service in queue.')
        if slug.replace('-', '').startswith('linkedin'):
            fail('This service is excluded from this skill for every owner; remove it from the queue.')
        seen.add(slug)
        if item['basis'] not in {'observed','proposed'} or item['confidence'] not in {'low','medium','high'} or item['status'] not in states or type(item['owner_approved']) is not bool:
            fail('Invalid queue classification/state.')
        for name in ('workflow','plugin_state','api_state'):
            safe_text(item[name])
        if not isinstance(item['evidence_refs'], list) or (item['basis']=='observed' and not item['evidence_refs']):
            fail('Observed tool needs source references; proposed needs must be distinguished.')
        for ref in item['evidence_refs']:
            safe_text(ref)
        if item['status'] in {'approved','in_progress','connected'} and not item['owner_approved']:
            fail('Discovery is not owner authorization to connect.')
        validate_pause(item)
        active += item['status'] in {'in_progress','paused'}
        if item['status']=='connected':
            if not item['receipt']:
                fail('Connected state needs a live verification receipt.')
            rp = (path.parent / item['receipt']).resolve()
            if not rp.is_relative_to(path.parent):
                fail('Queue receipt must stay inside the local connection registry.')
            c = profile(path.parent / (slug + '.json'))
            r = validate_receipt(read_json(rp), c)
            attempt = (path.parent / (slug + '.attempt.json'))
            if attempt.exists() and not read_json(attempt).get('ok'):
                fail('Latest verification failed; cannot call this service connected.')
            if r['service'] != slug:
                fail('Queue receipt belongs to another service.')
    if active > 1:
        fail('Only one tool may be in progress or paused at a time; do not skip an owner-dependent pause.')
    return q

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['check','reminder-plan'])
    p.add_argument('path')
    p.add_argument('--service')
    a = p.parse_args()
    try:
        data = check(a.path)
        if a.action == 'check':
            print('PASS: queue coverage, approval, pause/reminder bounds, sequencing and connected receipts.')
            if not available_timezones():
                print('Timezone database absent: identifier format checked only; no timezone conversion is performed.')
        else:
            import json
            item = next((x for x in data['items'] if x['service']==a.service),None)
            if item is None:
                fail('Choose an existing queued service for the reminder plan.')
            print(json.dumps(reminder_plan(item)))
    except (ConnectionError, OSError, TypeError) as e:
        print(str(e) if isinstance(e, ConnectionError) else 'Queue check failed; details suppressed.', file=sys.stderr)
        sys.exit(1)
