#!/usr/bin/env python3
"""Apply DFlash2 to the fastest qualified native packing; preserve phase-one data."""
import json
import shutil
from pathlib import Path
import run


def select(rows):
    candidates=[]
    for backend in ('bonsai-pq2', 'bonsai-ptq1', 'bonsai-q2'):
        rr=[r for r in rows if r['backend']==backend]
        if len(rr)!=16 or len({r['case'] for r in rr})!=16: continue
        if not all(r['score']['completed'] and (r['suite']!='quality' or r['score']['pass']) for r in rr): continue
        if not all(r.get('decode_ms',0)>0 for r in rr): continue
        tps=sum(r['total_tokens'] for r in rr)/(sum(r['decode_ms'] for r in rr)/1000)
        candidates.append((tps,backend))
    if not candidates: raise RuntimeError('No complete, quality-passing Bonsai baseline')
    return max(candidates)[1],dict((name,tps) for tps,name in candidates)


def main():
    parent=Path(__file__).resolve().parent
    selected,rates=select(json.loads((parent/'results.json').read_text()))
    destination=parent/'dflash-followup'
    if destination.exists():
        raise FileExistsError('Preserve prior followup evidence: '+str(destination))
    destination.mkdir()
    for name in ('suite.json','frozen-template.jinja','source-revision.txt'):
        shutil.copyfile(parent/name,destination/name)
    (destination/'selection.json').write_text(json.dumps(dict(selected=selected,decode_tps=rates,
        rule='Highest aggregate decode tokens/s across all 16 completed tasks; all six quality checks must pass'),indent=2)+'\n')
    run.ROOT=destination
    run.MODELS={selected+'-dflash2':run.MODELS[selected]}
    run.main()

if __name__=='__main__': main()
