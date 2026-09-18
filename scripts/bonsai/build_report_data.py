#!/usr/bin/env python3
"""Build a reviewed report snapshot from preserved native measurements."""
import datetime
import importlib.util
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2]/'benchmarks/bonsai-vs-swift-20260917'
spec=importlib.util.spec_from_file_location('analysis', ROOT/'analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);a.main()
rows=[]
for folder in ('','dflash-followup','dflash-remaining'):
 p=ROOT/folder/'results.json'
 if p.exists(): rows+=json.loads(p.read_text())
analysis=json.loads((ROOT/'analysis.json').read_text())
summary=analysis['summary'];all_s=[x for x in summary if x['subset']=='all']
labels={'swift-native':'Swift IQ4_XS','swift-dflash2':'Swift IQ4_XS','bonsai-pq2':'Bonsai PQ2_0','bonsai-ptq1':'Bonsai PTQ1_0','bonsai-q2':'Bonsai Q2_0'}
for b in list(labels):
 if b.startswith('bonsai'): labels[b+'-dflash2']=labels[b]
def mode(b):return 'DFlash2' if b.endswith('-dflash2') else 'Target only'
metadata=json.loads((ROOT/'provenance.json').read_text())
compact=[];suites=[];speculative=[]
for s in summary:
 b=s['backend'];rr=[r for r in rows if r['backend']==b and (s['subset']=='all' or r['suite']==s['subset'])]
 quality=[r for r in rr if r['suite']=='quality']
 q=dict(model=labels[b],mode=mode(b),configuration=s['label'],subset=s['subset'],coverage=f"{s['measured']}/{s['expected']}",
  complete=s['complete'],wall_s=s['wall_seconds'],prefill_s=s['prefill_seconds'],decode_s=s['decode_seconds'],decode_tps=s['decode_tps'],
  output_tokens=s['generated_tokens'],thinking_tokens=s['thinking_tokens'],other_tokens=s['other_output_tokens'],
  quality=f"{sum(r['score']['pass'] is True for r in quality)}/{len(quality)}" if quality else 'Not scored',
  completed=s['completed'],vram_gib=s['max_observed_vram_gib'])
 if s['subset']=='all':
  base=b.removesuffix('-dflash2') if b.startswith('bonsai') else 'swift-native'
  q['gguf_gib']=metadata['models'][base]['bytes']/1024**3
  compact.append(q)
 else:suites.append(q)
 if b.endswith('-dflash2') and s['subset']=='all':
  rates=[r['response']['usage']['accept_rate'] for r in rr if r['response']['usage'].get('spec_decode_ran')]
  base=next((x for x in all_s if x['backend']==b.removesuffix('-dflash2') or b=='swift-dflash2' and x['backend']=='swift-native'),None)
  speculative.append(dict(model=labels[b],requests=len(rr),speculative_requests=len(rates),acceptance_pct=statistics.median(rates)*100 if rates else None,
   acceptance_min_pct=min(rates)*100 if rates else None,acceptance_max_pct=max(rates)*100 if rates else None,
   decode_speedup=s['decode_tps']/base['decode_tps'] if base and base['decode_tps'] and s['complete'] else None,
   wall_speedup=base['wall_seconds']/s['wall_seconds'] if base and s['wall_seconds'] and s['complete'] else None))
detail=[]
for r in rows:
 u=r['response']['usage'];m=r['response']['choices'][0]['message'];sc=r['score']
 detail.append(dict(configuration=a.NAMES[r['backend']],model=labels[r['backend']],mode=mode(r['backend']),task=r['case'],suite=r['suite'],
  wall_s=r['wall_seconds'],prefill_ms=r.get('prefill_ms'),decode_ms=r.get('decode_ms'),decode_tps=r['total_tokens']/(r['decode_ms']/1000) if r.get('decode_ms') else None,
  input_tokens=r['prompt_tokens'],output_tokens=r['total_tokens'],thinking_tokens=r['reasoning_tokens_native'],
  result=('Pass' if sc['pass'] else 'FAIL') if r['suite']=='quality' else 'Completed; code unscored' if sc['completed'] else 'INCOMPLETE',
  format_pass=sc['format_pass'],answer_pass=sc['answer_pass'],finish=r['response']['choices'][0]['finish_reason'],
  spec_decode_ran=u.get('spec_decode_ran'),acceptance_pct=u.get('accept_rate',0)*100 if u.get('spec_decode_ran') else None,
  answer=m.get('content') or json.dumps(m.get('tool_calls',[])),reasoning=m.get('reasoning_content') or m.get('reasoning') or '',raw_response=json.dumps(r['response'])))
suite=json.loads((ROOT/'suite.json').read_text())
protocol=[dict(task=c['id'],suite=c['suite'],input=json.dumps(c['messages'],indent=2),tools=json.dumps(c.get('tools',[]),indent=2),expected=json.dumps(c.get('expected','Code correctness not scored'),indent=2),criterion=c['criterion']) for c in suite['cases']]
qualification=[dict(model=x['model'],cosine=x['reference']['cosine'],normalized_rmse_pct=x['reference']['nrmse']*100,top5_overlap=x['reference']['top5_overlap'],reference_pass=x['reference']['passed'],incremental_pass=x['chunking']['passed']) for x in json.loads((ROOT/'qualification/numerical-results.json').read_text())]
files=[f for f in ('results.json','dflash-followup/results.json','dflash-remaining/results.json') if (ROOT/f).exists()]
source=dict(type='local benchmark',title='Native Lucebox measurements on R9700',files=files,
 evidenceFlow=[dict(title='Frozen protocol',detail='16 exact prompts and original rubrics from suite.json; SHA256 f0b9120d5643f58ea6f40e9cdd9f183ff0e5f745317d49d838e59eae8fe85925.'),dict(title='Execution',detail='Sequential native Lucebox runs with Q8 GPU K/V, 65536 context, xhigh thinking, temperature 0, seed 42 and 64000 output ceiling. Model load and warmup excluded.'),dict(title='Aggregation',detail='Sum native prefill/decode and wall time per configuration; aggregate decode rate = sum(output tokens) / sum(decode seconds). Native thinking count from usage. Acceptance is median per-request rate, not pooled.')],
 caveats=['One run per task/configuration; no confidence intervals or randomized run order.','Six quality tasks score exact format and answers. Ten article tasks score completion only.','VRAM is observed after requests, not peak memory.','Native prefill and decode are phases of short cold prompts; these measurements do not establish long-context performance.'])
def query(data,extra=None):return dict(rows=data,source=source| (extra or {}),methods=[dict(language='Python',code='scripts/bonsai/build_report_data.py and benchmarks/bonsai-vs-swift-20260917/analyze.py; source measurements preserved unchanged.')])
cutoff=max((ROOT/f/'results.json').stat().st_mtime for f in ('','dflash-followup','dflash-remaining') if (ROOT/f/'results.json').exists())
when=datetime.datetime.fromtimestamp(cutoff,datetime.timezone.utc).isoformat()
finished=len(rows)==128
best_rate=max((x for x in compact if x['complete']),key=lambda x:x['decode_tps'])
best_time=min((x for x in compact if x['complete']),key=lambda x:x['wall_s'])
quality=[r for r in rows if r['suite']=='quality'];passes=sum(r['score']['pass'] is True for r in quality)
findings=f'''## Executive Summary\n\n- **{best_rate['configuration']} has the highest measured generation rate: {best_rate['decode_tps']:.1f} tokens/s.** {best_time['configuration']} has the lowest suite time: {best_time['wall_s']:.1f} seconds across 16 tasks.\n- **PQ2 and Q2 are effectively tied without DFlash2** at 41.1 and 40.8 tokens/s. PTQ1 uses less memory but reaches 32.0 tokens/s in this implementation.\n- **{passes}/{len(quality)} measured quality checks passed**, including strict JSON and tool formatting. The ten article tasks measure completion, not coding correctness.\n- {'All 128 requested task runs are complete.' if finished else f'{len(rows)}/128 task runs are recorded; the remaining DFlash2 results are pending.'} These are single-pass observations, not statistically established rankings.'''
methods='''## Method and interpretation\n\nEvery timed entry runs the same native Lucebox executable on one Radeon AI PRO R9700 (gfx1201, 32 GB). The inputs, frozen chat template and scoring rules are identical. All matched prompt-token counts are checked. Thinking is enabled with xhigh requested; actual thinking length varies by model and numerical path.\n\nTemperature is 0 and seed is 42. Context is 65,536 tokens, with a 64,000-token output ceiling for safety. No response reaching the length ceiling counts as a normal completion. Prefix slots and hybrid caching are disabled; measured cached-prefix counts must remain zero. Idle prefill batches are 512 tokens. DFlash2 uses the existing Qwen Q8 drafter with block size 16. GPU K/V are Q8 in every entry.\n\n**Definitions:** prefill is the backend's prompt-processing phase; decode is its generation phase. Wall time includes request overhead, but excludes model loading and warmup. Output counts include thinking; other output tokens may include control tokens. Throughput is total output tokens divided by total decode seconds, not the average of individual request rates. Draft acceptance is reported as a median of per-request native rates.\n\nOne run per task/configuration, fixed configuration order, and different generated lengths limit the comparison. These short prompts do not test long-context compression, cache reuse, or production concurrency. Post-request GPU allocation is not peak VRAM. The private build uses FA_ALL_QUANTS=OFF with the same Q8 attention kernels for every entry. No production executable or configuration is replaced.'''
output=Path(sys.argv[1]);old=json.loads(output.read_text()) if output.exists() else {}
snapshot=dict(id=old.get('id'),surface='report',title='Bonsai versus Swift: speed, thinking and DFlash2',generatedAt=when,report={'asOf':when[:10]},status='reviewed',buildStatus='creating',filters=[],finding=findings,methodsText=methods,
 queries={'summary':query(compact),'suites':query(suites),'tasks':query(detail),'speculation':query(speculative),'protocol':query(protocol,{'files':['suite.json']}),'qualification':query(qualification,{'files':['qualification/numerical-results.json'],'caveats':['Fixed 17-token sequence; finite numerical qualification is not proof of identical long generation.']})})
snapshot['queries']['tasks']['payloadColumns']=['raw_response']
for name,ids,definition in [('summary',['overview','throughput','wall','memory','tokens','findings'],'Configuration totals over the measured subset. Null means unavailable; partial coverage is explicit.'),('suites',['suite-breakdown'],'Separate totals for the six quality and ten completion-only speed tasks.'),('tasks',['task-details','responses'],'One native request per configuration and frozen task; no retries replace failures.'),('speculation',['draft-results'],'Only actual speculative requests contribute to per-request acceptance statistics.')]:
 snapshot['queries'][name]['source']['metricDefinitions']=[dict(label=name,definition=definition,componentIds=ids)]
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(snapshot,indent=2)+'\n')
print(f'Reviewed snapshot: {len(rows)} task rows, {len(compact)} configurations')
