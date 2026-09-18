#!/usr/bin/env python3
"""Full-model numerical qualification only; no performance measurements."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import numpy as np

ROOT=Path('/root/bonsai2-qualification')
ENV=dict(os.environ,LD_LIBRARY_PATH='/opt/rocm/core-10.0/lib')
LUCE='/root/lucebox-bonsai/server/build-hip/test_bonsai_forward'
PRISM='/root/bonsai2-bench/prism-reference'
MODELS=[('pq2','Ternary-Bonsai-2-27B-PQ2_0.gguf'),('ptq1','Ternary-Bonsai-2-27B-PTQ1_0.gguf'),('q2','Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf')]

def compare(a,b):
    a=np.fromfile(a,dtype=np.float32).astype(np.float64)
    b=np.fromfile(b,dtype=np.float32).astype(np.float64)
    assert a.shape==b.shape and a.size>100000 and np.isfinite(a).all() and np.isfinite(b).all()
    top_a=np.argsort(a)[-5:][::-1];top_b=np.argsort(b)[-5:][::-1]
    cosine=float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)))
    nrmse=float(np.linalg.norm(a-b)/np.linalg.norm(b))
    margin=float(b[top_b[0]]-b[top_b[1]])
    overlap=len(set(top_a)&set(top_b))
    passed=cosine>=0.999 and nrmse<=0.05 and overlap>=4 and (margin<=0.2 or top_a[0]==top_b[0])
    return dict(cosine=cosine,nrmse=nrmse,max_abs=float(np.max(np.abs(a-b))),top5_a=top_a.tolist(),top5_b=top_b.tolist(),reference_margin=margin,top5_overlap=overlap,passed=bool(passed))

def drain_gpu():
    for _ in range(150):
        if int(Path('/sys/class/drm/card5/device/mem_info_vram_used').read_text()) < 1536*1024**2:
            return
        time.sleep(.2)
    raise RuntimeError('GPU allocations did not drain')

def main():
    ROOT.mkdir(exist_ok=True)
    assert not (ROOT/'results.json').exists(),'Do not overwrite previous qualification evidence'
    # Fixed valid IDs including a chat prefix, ordinary tokens and newline. Same
    # exact IDs, zero initial state and Q8 K/V in both independent runtimes.
    tokens=[151644,872,198,9707,11,576,374,264,1296,13,151645,198,151644,77091,198,100,200]
    (ROOT/'tokens.txt').write_text(' '.join(map(str,tokens))+'\n')
    h=json.load(urllib.request.urlopen('http://127.0.0.1:8216/health',timeout=10))
    assert not h.get('busy') and not h.get('active_requests') and not h.get('pending_requests'),h
    results=[]
    subprocess.run(['systemctl','stop','lucebox.service'],check=True)
    try:
        drain_gpu()
        for label,filename in MODELS:
            model='/root/bonsai2-models/'+filename
            for runtime,executable,chunk in [('prism',PRISM,32),('luce',LUCE,32),('luce',LUCE,1)]:
                name=f'{label}-{runtime}-{chunk}'
                (ROOT/'progress.json').write_text(json.dumps(dict(running=name)))
                command=[executable,model,str(ROOT/'tokens.txt'),str(chunk),str(ROOT/(name+'.f32'))]
                with (ROOT/(name+'.log')).open('w') as log:
                    subprocess.run(command,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
                drain_gpu()
            row=dict(model=label,reference=compare(ROOT/f'{label}-luce-32.f32',ROOT/f'{label}-prism-32.f32'),
                     chunking=compare(ROOT/f'{label}-luce-1.f32',ROOT/f'{label}-luce-32.f32'))
            results.append(row)
            (ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(row),flush=True)
            assert row['reference']['passed'] and row['chunking']['passed'], 'Numerical qualification failed'
    finally:
        subprocess.run(['systemctl','start','lucebox.service'],check=True)
        (ROOT/'progress.json').write_text(json.dumps(dict(finished=True,models_compared=len(results))))

if __name__=='__main__':main()
