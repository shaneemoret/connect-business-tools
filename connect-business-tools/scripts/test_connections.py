#!/usr/bin/env python3
"""Behavioral fixtures: no live services, real credentials, or owner config writes."""
import copy
import datetime as dt
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import connection as c
import http_probe as h
import install as ins
import queue as q
import preflight as pf
from types import SimpleNamespace

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root/'business'
        self.home = self.root/'owner'
        self.project.mkdir()
        self.home.mkdir()
        self.broker = self.root/'broker.py'
        self.broker.write_text('import os,sys,subprocess\nos.environ["TEST_API_KEY"]="fixture-only"\nsys.exit(subprocess.run(sys.argv[1:],check=False).returncode)\n', encoding='utf-8')
        self.probe = self.root/'probe.py'
        self.probe.write_text('import argparse,json,os\np=argparse.ArgumentParser();p.add_argument("--mode");a=p.parse_args()\nassert os.environ.get("TEST_API_KEY")=="fixture-only"\nprint(json.dumps({"ok":True,"mode":a.mode,"checks":[{"operation":"Fixture lookup","kind":"auth" if a.mode=="auth" else "read" if a.mode=="read" else "write_permission","passed":True}]}))\n', encoding='utf-8')
        self.p = self.project/'SYSTEMS'/'api-connections'/'sample-tool.json'
        self.config = {'version':1,'service':'sample-tool','account_label':'Example business','credential':{'manager':'fixture','reference':'sample-tool','env_var':'TEST_API_KEY','runner':[sys.executable,str(self.broker)]},'probe':[sys.executable,str(self.probe)],'expires_at':None,'renewal':'Owner renews through vendor','official_docs':['https://vendor.example/docs'],'docs_verified_on':dt.date.today().isoformat()}
        c.atomic_json(self.p,self.config)

    def tearDown(self):
        self.temp.cleanup()

    def test_injected_stored_route_read_write_and_run(self):
        r=c.verify(self.p,True)
        c.validate_receipt(c.read_json(c.receipt_path(self.p)),self.config)
        self.assertEqual([x['mode'] for x in r['results']],['read','write'])
        p=subprocess.run([sys.executable,str(Path(c.__file__)),'run',str(self.p),'--',sys.executable,'-c','import os;print("PASS" if os.environ.get("TEST_API_KEY")=="fixture-only" else "FAIL")'],capture_output=True,text=True, encoding='utf-8', errors='replace')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),'PASS')
        self.assertNotIn('fixture-only',c.receipt_path(self.p).read_text(encoding='utf-8'))

    def test_invalid_expired_and_raw_fields(self):
        for change in ({'api_key':'never-store-this'},{'expires_at':'2000-01-01'},{'expires_at':False},{'expires_at':''},{'service':'../bad'},{'version':True},{'docs_verified_on':'2999-01-01'}):
            v=copy.deepcopy(self.config);v.update(change);c.atomic_json(self.p,v)
            with self.assertRaises(c.ConnectionError):c.profile(self.p)

    def test_stale_and_mismatched_receipts(self):
        r=c.verify(self.p)
        r['verified_at']=(c.now()-dt.timedelta(days=2)).isoformat()
        with self.assertRaises(c.ConnectionError):c.validate_receipt(r,self.config)

    def test_probe_code_changes_invalidate_receipt(self):
        r=c.verify(self.p)
        self.probe.write_text(self.probe.read_text(encoding='utf-8')+'\n# changed adapter\n', encoding='utf-8')
        with self.assertRaises(c.ConnectionError):c.validate_receipt(r,self.config)
        r['verified_at']=c.now().isoformat();r['profile_sha256']='wrong'
        with self.assertRaises(c.ConnectionError):c.validate_receipt(r,self.config)

    def test_leaking_probe_is_suppressed_and_latest_failure_invalidates(self):
        c.verify(self.p)
        self.probe.write_text('print("SENSITIVE_FIXTURE_TEXT")\n', encoding='utf-8')
        with self.assertRaises(c.ConnectionError) as e:c.verify(self.p)
        self.assertNotIn('SENSITIVE_FIXTURE_TEXT',str(e.exception))
        self.assertFalse(c.read_json(self.p.with_suffix('.attempt.json'))['ok'])
        p=subprocess.run([sys.executable,str(Path(c.__file__)),'check',str(self.p)],capture_output=True,text=True, encoding='utf-8', errors='replace')
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn('SENSITIVE_FIXTURE_TEXT',p.stderr+p.stdout)

    def test_false_success_and_wrong_kind(self):
        for result in ({'ok':True,'mode':'read','checks':[]},{'ok':True,'mode':'read','checks':[{'operation':'lookup','kind':'auth','passed':True}]},{'ok':True,'mode':'read','checks':[{'operation':'lookup','kind':'read','passed':False}]}):
            with self.assertRaises(c.ConnectionError):c.validate_result(result,'read')

    def test_route_preservation_and_preflight(self):
        for n in ('AGENTS.md','CLAUDE.md'):(self.project/n).write_text('Owner existing rule: keep this verbatim.\n', encoding='utf-8')
        c.route(self.p,self.project)
        first=(self.project/'AGENTS.md').read_bytes()
        c.route(self.p,self.project)
        self.assertEqual(first,(self.project/'AGENTS.md').read_bytes())
        self.assertTrue((self.project/'AGENTS.md').read_text(encoding='utf-8').startswith('Owner existing rule: keep this verbatim.\n'))
        (self.project/'CLAUDE.md').write_text('<!-- api-route-sample-tool:start -->', encoding='utf-8')
        with self.assertRaises(c.ConnectionError):c.route(self.p,self.project)
        self.assertEqual(first,(self.project/'AGENTS.md').read_bytes())

    def test_install_is_shared_idempotent_and_preserves_rules(self):
        for path in (self.home/'.codex'/'AGENTS.md',self.home/'.claude'/'CLAUDE.md',self.project/'AGENTS.md',self.project/'CLAUDE.md'):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Keep exact owner rule.\n', encoding='utf-8')
        with patch.object(ins,'check_bundle',return_value=True):
            ins.install(self.project,self.home)
            first=(self.home/'.codex'/'AGENTS.md').read_bytes()
            ins.install(self.project,self.home)
        self.assertEqual(first,(self.home/'.codex'/'AGENTS.md').read_bytes())
        self.assertTrue((self.home/'.codex'/'AGENTS.md').read_text(encoding='utf-8').startswith('Keep exact owner rule.\n'))
        for dest in (self.home/'.agents'/'skills'/'connect-business-tools',self.home/'.claude'/'skills'/'connect-business-tools'):
            if dest.is_symlink():
                self.assertEqual(dest.resolve(),ins.ROOT)
            else:
                ins.validate_destination(dest)
                self.assertEqual(ins.installed_files(dest),ins.installed_files(ins.ROOT))

    def test_install_refuses_existing_folder(self):
        d=self.home/'.agents'/'skills'/'connect-business-tools';d.mkdir(parents=True)
        with patch.object(ins,'check_bundle',return_value=True):
            with self.assertRaises(c.ConnectionError):ins.install(self.project,self.home)
        self.assertFalse((self.home/'.codex'/'AGENTS.md').exists())

    def test_managed_copies_without_link_privilege(self):
        with patch.object(ins,'check_bundle',return_value=True):
            dests = ins.install(self.project,self.home,prefer_links=False)
            self.assertTrue(all(not x.is_symlink() for x in dests))
            for dest in dests:
                self.assertEqual(ins.installed_files(dest),ins.installed_files(ins.ROOT))
            ins.install(self.project,self.home,prefer_links=False)
            (dests[0]/'SKILL.md').write_text('Local edit must be preserved.',encoding='utf-8')
            with self.assertRaises(c.ConnectionError):ins.install(self.project,self.home,prefer_links=False)
            self.assertEqual((dests[0]/'SKILL.md').read_text(encoding='utf-8'),'Local edit must be preserved.')

    def test_utf8_crlf_preserved_outside_managed_block(self):
        p=self.root/'instructions.md'
        original='Keep café and 東京 exactly.\r\n'.encode('utf-8')
        p.write_bytes(original)
        c.update_block(p,'fixture','New rule\nSecond line')
        first=p.read_bytes();self.assertTrue(first.startswith(original))
        self.assertNotIn(b'\r\r\n',first)
        c.update_block(p,'fixture','New rule\nSecond line')
        self.assertEqual(first,p.read_bytes())

    def test_platform_selection_and_unsupported_versions(self):
        self.assertEqual(pf.select_platform('Darwin','26.4.1')[0],'platform-mac.md')
        self.assertIsNone(pf.select_platform('Darwin','12.7')[0])
        self.assertEqual(pf.select_platform('Windows','10.0.22631',22631)[0],'platform-windows.md')
        for args in (('Windows','10.0.17763',17763),('Linux','6.1',None),('Darwin','unknown',None)):
            self.assertIsNotNone(pf.select_platform(*args)[1])

    def test_windows_draft_cannot_claim_ready_from_mock(self):
        with patch.object(pf.platform,'system',return_value='Windows'), patch.object(pf.platform,'version',return_value='10.0.22631'), patch.object(pf.sys,'getwindowsversion',return_value=SimpleNamespace(build=22631),create=True), patch.object(pf,'admin_state',return_value={'administrator_member':True,'elevated':False,'source':'fixture'}):
            r=pf.detect('PowerShell')
        self.assertEqual(r['status'],'blocked')
        self.assertEqual(r['platform_release'],'draft')
        self.assertEqual(Path(r['platform_reference']).name,'platform-windows.md')
        self.assertTrue(any('actual matching computer' in reason for reason in r['reasons']))

    def test_windows_display_does_not_use_posix_quoting(self):
        from pathlib import PureWindowsPath
        exe=str(PureWindowsPath('C:\\','Program Files','Python','python.exe'))
        result=c.display_command([exe,"owner's file.py"],system='nt')
        self.assertTrue(result.startswith("& 'C:\\Program Files\\Python\\python.exe' "))
        self.assertIn("'owner''s file.py'",result)

    def queue(self):
        return {'version':1,'window':{'from':'2026-08-20','through':'2026-10-20','timezone':'America/New_York','coverage':'partial'},'mail_source':'outlook','items':[{'service':'sample-tool','basis':'observed','workflow':'Reporting need','evidence_refs':['private-thread-1'],'plugin_state':'not_checked','api_state':'not_checked','confidence':'medium','status':'proposed','owner_approved':False,'receipt':None}]}

    def test_queue_approval_and_one_at_a_time(self):
        path=self.p.parent/'queue.json';v=self.queue();c.atomic_json(path,v);q.check(path)
        v['items'][0]['status']='in_progress';c.atomic_json(path,v)
        with self.assertRaises(c.ConnectionError):q.check(path)
        v['items'][0]['owner_approved']=True
        v['items'].append(dict(v['items'][0],service='another-tool'));c.atomic_json(path,v)
        with self.assertRaises(c.ConnectionError):q.check(path)

    def test_queue_connected_needs_matching_fresh_receipt(self):
        path=self.p.parent/'queue.json';v=self.queue();v['items'][0].update(status='connected',owner_approved=True,receipt='sample-tool.receipt.json');c.atomic_json(path,v)
        with self.assertRaises(c.ConnectionError):q.check(path)
        c.verify(self.p);q.check(path)
        self.probe.write_text('print("invalid")\n', encoding='utf-8')
        with self.assertRaises(c.ConnectionError):c.verify(self.p)
        with self.assertRaises(c.ConnectionError):q.check(path)

    def test_paused_queue_and_bounded_reminders(self):
        path=self.p.parent/'queue.json';v=self.queue();item=v['items'][0]
        when=(c.now()-dt.timedelta(days=2)).isoformat()
        item.update(status='paused',pause={'step':'login','owner_action':'Sign in on the open screen','paused_at':when,'verified':['Manager route found'],'resume_hint':'Open your AI and say keep connecting the project tool'},reminder={'channel':'none','consented':False,'delay_hours':24,'max_count':2,'sent_count':0,'consent_evidence':None,'owner_recipient_ref':None,'last_sent_at':None,'scheduled_id':None})
        c.atomic_json(path,v);q.check(path)
        self.assertEqual(q.reminder_plan(item)['action'],'none')
        item['reminder'].update(channel='email',consented=True,consent_evidence='Owner chat approval',owner_recipient_ref='owner-primary-account')
        c.atomic_json(path,v);before=path.read_bytes();q.check(path)
        self.assertEqual(q.reminder_plan(item)['action'],'reminder_due')
        self.assertEqual(before,path.read_bytes())
        item['reminder'].update(sent_count=2,last_sent_at=when,last_receipt_ref='confirmed-self-send-fixture')
        self.assertEqual(q.reminder_plan(item)['action'],'none')
        item['reminder']['sent_count']=3;c.atomic_json(path,v)
        with self.assertRaises(c.ConnectionError):q.check(path)
        item['reminder']['sent_count']=0;item['reminder']['consented']=False;item['reminder']['scheduled_id']='task-fixture';c.atomic_json(path,v)
        with self.assertRaises(c.ConnectionError):q.check(path)

    def test_windows_without_timezone_database_can_validate_metadata(self):
        path=self.p.parent/'queue.json';c.atomic_json(path,self.queue())
        with patch.object(q,'available_timezones',return_value=set()):q.check(path)

    def test_http_scope_errors_and_write_unavailable(self):
        plan={'origin':'https://api.vendor.example','env_var':'TEST_API_KEY','auth':'bearer','read':[{'operation':'Lookup','url':'https://api.vendor.example/me','expect_path':['id']}]}
        class Opener:
            def __init__(self,data=None,error=None):self.data=data;self.error=error;self.calls=0
            def open(self,req,timeout):
                self.calls+=1
                if self.error:raise self.error
                return io.BytesIO(json.dumps(self.data).encode())
        with patch.dict(os.environ,{'TEST_API_KEY':'fixture-only'}):
            o=Opener({'id':'fixture'});self.assertTrue(h.execute(plan,'read',o)['ok'])
            self.assertEqual(h.execute(plan,'write',o)['failure_layer'],'write_unavailable')
            plan['read'][0]['url']='https://attacker.example/me';o=Opener({'id':'fixture'})
            self.assertFalse(h.execute(plan,'read',o)['ok']);self.assertEqual(o.calls,0)
            plan['read'][0]['url']='https://api.vendor.example/me'
            for code,layer in ((401,'authentication'),(403,'permission'),(429,'rate_limit'),(302,'response')):
                e=urllib.error.HTTPError('https://api.vendor.example/me',code,'suppressed',{},None)
                self.assertEqual(h.execute(plan,'read',Opener(error=e))['failure_layer'],layer)
            self.assertFalse(h.execute(plan,'read',Opener({'errors':[{'message':'suppressed'}],'id':'fixture'}))['ok'])
            self.assertIsNone(h.NoRedirect().redirect_request(None,None,302,'',{},'https://attacker.example'))
            plan['read'][0].update(method='POST',json={'query':'mutation { doSomething }'})
            o=Opener({'id':'fixture'})
            self.assertEqual(h.execute(plan,'read',o)['failure_layer'],'permission');self.assertEqual(o.calls,0)

if __name__=='__main__':
    unittest.main(verbosity=2)
