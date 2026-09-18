#!/usr/bin/env python3
"""Finish the user-expanded DFlash2 matrix, retaining the completed PQ2 run."""
import json
import shutil
from pathlib import Path
import run

if __name__=='__main__':
    parent=Path(__file__).resolve().parent
    existing=json.loads((parent/'dflash-followup/results.json').read_text())
    assert len(existing)==16 and {r['backend'] for r in existing}=={'bonsai-pq2-dflash2'}
    destination=parent/'dflash-remaining'
    destination.mkdir(exist_ok=True)
    assert not (destination/'results.json').exists(), 'Preserve previous measurements'
    for name in ('suite.json','frozen-template.jinja','source-revision.txt'):
        shutil.copyfile(parent/name,destination/name)
    run.ROOT=destination
    run.MODELS={name+'-dflash2':run.MODELS[name] for name in ('bonsai-ptq1','bonsai-q2')}
    run.main()
