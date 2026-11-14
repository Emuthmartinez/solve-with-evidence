"""Exercise the link reader against a real subprocess and independent checked bytes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from recipient import digest, inspect


def controls(gate):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp).resolve()
        consumer=root/'consumer.py'
        consumer.write_text("import sys,json\ntry: ok=json.load(sys.stdin)=={'a':1}\nexcept ValueError: ok=False\nsys.exit(0 if ok else 1)\n")
        raw=b'{ "a":1 }\r\n'
        source=root/'produced'
        source.write_bytes(raw)
        message=root/'response.md'
        def run(payload, attempts):
            message.write_bytes(payload)
            return inspect('demo',message,consumer,attempts)
        accepted=subprocess.run([sys.executable,'-B',str(gate),str(source),'--deliver-to','artifacts',
                                 '--',sys.executable,'-B',str(consumer),'demo'],capture_output=True,cwd=root,check=True)
        receipt=json.loads(accepted.stdout)
        target=Path(receipt['path'])
        path=target.relative_to(root).as_posix()
        link=f'[Download verified JSON]({path})'.encode()
        records=[{'status':'accepted','producer_call_id':'python-1','producer_sha256':digest(raw),
                  'producer_bytes':len(raw),'receipt':{**receipt,'path':path}}]
        report,opened=run(link,records)
        assert report['verified_link_delivery'] and opened==raw and opened.endswith(b'\r\n')
        for name,final in [('duplicate',link+b'\n'+link),('prose',b'Accepted: '+link),
                           ('wrong directory',link.replace(b'artifacts/',b'other/')),('missing',link.replace(digest(raw).encode(),b'0'*64))]:
            report,_=run(final,records)
            assert not report['verified_link_delivery'] and not report['consumer_accepted'],name
        assert run(raw,records)[0]['checked_before_delivery']
        assert not run(raw,records)[0]['verified_link_delivery']
        assert not run(b'{"a":1}',records)[0]['checked_before_delivery']
        assert not run(link,[])[0]['verified_link_delivery']
        target.chmod(0o644)
        target.write_bytes(b'{"a":1}')
        report,opened=run(link,records)
        assert report['consumer_accepted'] and not report['verified_link_delivery'] and opened!=raw
        target.unlink()
        target.symlink_to(source)
        assert not run(link,records)[0]['consumer_accepted']
    print('Recipient controls passed: retained bytes, duplicate, prose, traversal/missing target, independent rendering, missing receipt, post-check change, symlink.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gate',required=True,type=Path)
    controls(p.parse_args().gate.resolve())
