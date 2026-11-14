"""Mutate completed native captures, reseal the local manifests, and require the audit to reject them."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from audit_native import Invalid, audit, filemap, read


def write(path, data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def edit_rows(t, operation):
    rows=[json.loads(line) for line in (t/'trace.jsonl').read_bytes().splitlines()]
    operation(rows)
    (t/'trace.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))


def score(t, operation):
    result=read(t/'result.json')
    operation(result)
    write(t/'result.json',result)
    edit_rows(t,lambda rows:rows[-1].update(data=result))


def change_reply(t, new):
    (t/'response.md').write_bytes(new.encode())
    def rewrite(rows):
        messages=[r['data']['item'] for r in rows if r['kind']=='codex' and
                  r['data'].get('type')=='item.completed' and r['data']['item']['type']=='agent_message']
        messages[-1]['text']=new
    edit_rows(t,rewrite)


def controls(trials, evaluation):
    completed=[p.parent for p in sorted(trials.glob('*/manifest.json'))]
    source=next(t for t in completed if read(t/'result.json').get('verified') and
                read(t/'result.json')['channel']=='file' and read(t/'result.json')['checker_acceptances'])
    audit(source,evaluation)
    def receipt(t):
        row=read(t/'result.json')
        rid=next(r['receipt'] for r in row['checker_acceptances'] if r['sha256']==row['received_sha256'])
        return t/'checker-receipts'/rid
    def hashed_path(t):
        return t/read(t/'result.json')['opened']
    def copy_substitution(t):
        path=hashed_path(t)
        path.write_bytes(path.read_bytes()+b'\n')
        (t/'received.json').write_bytes(path.read_bytes())
        from audit_native import digest
        h=digest(path.read_bytes())
        score(t,lambda x:x.update(received_bytes=len(path.read_bytes()),received_sha256=h,consumer_stderr=f'accepted sha256={h}\n'))
    def alias(t, folder, symlink):
        path=hashed_path(t)
        saved=folder/'outside-artifact'
        path.rename(saved)
        if symlink:
            path.symlink_to(saved)
        else:
            os.link(saved,path)
    def late(t):
        path=receipt(t)/'result.json'; value=read(path)
        value['time_ns']+=10**14
        write(path,value)
    def decoy(t):
        def mutate(rows):
            for r in rows:
                event=r['data']
                if not isinstance(event,dict):
                    continue
                item=event.get('item',{})
                if item.get('type')=='command_execution' and './case-check' in item['command']:
                    item['command']="echo 'synthetic receipt label'"
        edit_rows(t,mutate)
    def fake_source(t):
        path=receipt(t)/'result.json'; row=read(path); row['origin']='untrusted-replacement'; write(path,row)
    def fake_acceptance(t):
        rec=receipt(t)
        r=read(rec/'result.json')
        r['exit']=1; r['stderr']='rejected: check failed\n'
        write(rec/'result.json',r)
    cases=[
        ('recipient substitution, accepted semantics but changed bytes',copy_substitution),
        ('received body lost or gained trailing LF',lambda t:(t/'received.json').write_bytes((t/'received.json').read_bytes()+b'\n')),
        ('model final export rewrite',lambda t:(t/'response.md').write_bytes((t/'response.md').read_bytes()+b'\n')),
        ('final link now points to missing artifact',lambda t:change_reply(t,'[Download](outputs/missing.json)')),
        ('final link escaped workspace',lambda t:change_reply(t,'[Download](outputs/../../escape.json)')),
        ('post-final acceptance backfilled',late),
        ('accepting receipt replaced by rejection',fake_acceptance),
        ('workspace receipt marked as host evidence',fake_source),
        ('command replaced by echo with original digest output',decoy),
        ('unearned raw-score change',lambda t:score(t,lambda r:r.update(correct=False))),
        ('unearned identity-score change',lambda t:score(t,lambda r:r.update(verified=False))),
    ]
    report={}
    with tempfile.TemporaryDirectory() as tmp:
        t=Path(tmp)/source.name
        for title,fn in cases:
            shutil.copytree(source,t)
            fn(t); write(t/'manifest.json',filemap(t))
            try:
                audit(t,evaluation)
            except Invalid as e:
                report[title]=str(e)
            else:
                raise AssertionError(f'accepted mutation: {title}')
            shutil.rmtree(t)
        for symlink in (True,False):
            shutil.copytree(source,t)
            folder=Path(tmp)/('sym' if symlink else 'hard')
            folder.mkdir()
            alias(t,folder,symlink)
            try:
                audit(t,evaluation)
            except Invalid as e:
                report['symlink target' if symlink else 'hard-linked target']=str(e)
            else:
                raise AssertionError('archive allowed an external artifact alias')
            shutil.rmtree(t)
        if read(source/'request.json').get('link_parser'):
            # Repeat the historical whitespace failure against an actual available
            # file, retaining the exact received bytes and original host receipt.
            shutil.copytree(source,t)
            response=(t/'response.md').read_text().strip()
            change_reply(t,response.replace('](','](  ',1))
            write(t/'manifest.json',filemap(t))
            assert audit(t,evaluation)['verified']
            report['CommonMark whitespace around destination']='same checked bytes still received'
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trials',type=Path); ap.add_argument('--evaluation',type=Path,default=Path(__file__).resolve().parent)
    args=ap.parse_args()
    print(json.dumps(controls(args.trials,args.evaluation.resolve()),indent=2))
