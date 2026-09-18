#!/usr/bin/env python3
"""Summarize real measurements; never impute missing runs or timings."""
import csv
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
NAMES = {'swift-prism':'Swift · Prism', 'bonsai-pq2':'Bonsai PQ2_0 · Prism',
         'bonsai-ptq1':'Bonsai PTQ1_0 · Prism', 'bonsai-q2':'Bonsai Q2_0 · Prism',
         'swift-dflash2':'Swift · Lucebox + DFlash2'}

def fmt(x, digits=2):
    return '—' if x is None else f'{x:.{digits}f}'

def main():
    rows = json.loads((ROOT/'results.json').read_text()) if (ROOT/'results.json').exists() else []
    suite = json.loads((ROOT/'suite.json').read_text())
    failures = json.loads((ROOT/'failures.json').read_text()) if (ROOT/'failures.json').exists() else []
    summaries, detail = [], []
    for backend, label in NAMES.items():
        rr = [r for r in rows if r['backend']==backend]
        seen = {r['case'] for r in rr}
        assert len(seen)==len(rr), f'Duplicate cases: {backend}'
        quality = [r for r in rr if r['suite']=='quality']
        times_ok = bool(rr) and all(r.get('decode_ms') is not None and r.get('prefill_ms') is not None for r in rr)
        decode = sum(r['decode_ms'] for r in rr)/1000 if times_ok else None
        prefill = sum(r['prefill_ms'] for r in rr)/1000 if times_ok else None
        tokens = sum(r['total_tokens'] for r in rr)
        summary = dict(backend=backend, label=label, measured=len(rr),
            completed=sum(bool(r['score']['completed']) for r in rr),
            quality_pass=sum(r['score']['pass'] is True for r in quality), quality_measured=len(quality),
            quality_expected=sum(c['suite']=='quality' for c in suite['cases']),
            full_suite=len(rr)==len(suite['cases']), wall_seconds=sum(r['wall_seconds'] for r in rr) if rr else None,
            prefill_seconds=prefill, decode_seconds=decode, generated_tokens=tokens if rr else None,
            decode_tps=tokens/decode if decode else None,
            max_observed_vram_gib=max((r['vram_bytes_after']/1024**3 for r in rr), default=None))
        summaries.append(summary)
        for r in rr:
            detail.append({k:r.get(k) for k in ('backend','case','suite','wall_seconds','prefill_ms','decode_ms','prompt_tokens','total_tokens','reasoning_tokens_native','reasoning_text_tokens')} | dict(finish_reason=r['response']['choices'][0]['finish_reason'], **r['score']))
    baseline = next(s for s in summaries if s['backend']=='swift-prism')
    practical = next(s for s in summaries if s['backend']=='swift-dflash2')
    for s in summaries:
        for key, base in [('same_runtime_wall_speedup',baseline),('practical_wall_speedup',practical)]:
            s[key] = base['wall_seconds']/s['wall_seconds'] if base['full_suite'] and s['full_suite'] and s['wall_seconds'] else None
    micro = []
    for backend in NAMES:
        path = ROOT/(backend+'-micro.json')
        if path.exists():
            try:
                for m in json.loads(path.read_text()):
                    micro.append(dict(backend=backend, prompt_tokens=m['n_prompt'], decode_tokens=m['n_gen'],
                        median_tps=median(m['samples_ts']), samples_tps=m['samples_ts']))
            except (ValueError,KeyError) as e:
                failures.append(dict(backend=backend, error='Incomplete microbenchmark: '+str(e)))
    base_counts = {r['case']:r['prompt_tokens'] for r in rows if r['backend']=='swift-prism'}
    mismatches = [dict(backend=r['backend'], case=r['case'], prompt_tokens=r['prompt_tokens'], swift_prompt_tokens=base_counts[r['case']])
                  for r in rows if r['case'] in base_counts and r['prompt_tokens']!=base_counts[r['case']]]
    data=dict(summary=summaries, micro=micro, failures=failures, prompt_count_mismatches=mismatches)
    (ROOT/'analysis.json').write_text(json.dumps(data,indent=2)+'\n')
    if detail:
        with (ROOT/'measurements.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(detail[0]));w.writeheader();w.writerows(detail)
    lines=['# Bonsai versus Swift on R9700', '',
        '**Scope:** first-pass natural task measurements, plus three-repeat fixed-token throughput measurements. Bonsai runs in Prism’s reference engine, not Lucebox/DFlash2. Swift is measured in both engines.', '',
        '## Same tasks, unchanged rubric', '',
        'Thinking is enabled (xhigh requested), temperature 0, seed 42, identical frozen template and 16 prompts. Six quality tasks have strict format/answer checks. Ten article speed tasks check completion only; code correctness is not established. Each task is run once per entry, so task totals are preliminary, not medians.', '',
        '| Configuration | Completed / 16 | Quality pass / 6 | Total wall s | Prefill s | Decode s | Generated tokens | Decode tok/s | Wall speedup vs Swift/Prism |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        suffix='' if s['full_suite'] else ' (partial)'
        lines.append(f"| {s['label']}{suffix} | {s['completed']}/16 | {s['quality_pass']}/6 | {fmt(s['wall_seconds'])} | {fmt(s['prefill_seconds'])} | {fmt(s['decode_seconds'])} | {s['generated_tokens'] if s['generated_tokens'] is not None else '—'} | {fmt(s['decode_tps'])} | {fmt(s['same_runtime_wall_speedup'])}× |")
    lines += ['', 'Decode rate is total generated tokens divided by total measured decode time, including thinking. Wall time includes request overhead but excludes model loading and warmup. A shorter answer can improve wall time without improving kernel throughput. Partial totals must not be compared with complete suites.', '',
        '## Fixed-token throughput', '', '| Configuration | Prefill tokens | Decode tokens | Median tok/s | Three samples tok/s |', '|---|---:|---:|---:|---|']
    for m in micro:
        lines.append(f"| {NAMES[m['backend']]} | {m['prompt_tokens']} | {m['decode_tokens']} | {fmt(m['median_tps'])} | {', '.join(fmt(x) for x in m['samples_tps'])} |")
    lines += ['', 'Synthetic tests isolate fixed-size work; their throughput is not the same metric as natural chat completion.', '', '## Quality failures', '']
    bad=[r for r in rows if r['suite']=='quality' and not r['score']['pass']]
    for r in bad:
        lines.append(f"- {NAMES[r['backend']]} / `{r['case']}`: format={r['score']['format_pass']}, answer={r['score']['answer_pass']}, finish={r['response']['choices'][0]['finish_reason']}.")
    if not bad: lines.append('No failed quality checks among measured requests. See coverage above for missing runs.')
    lines += ['', '## Measurement limits', '',
        '- Native reasoning-token counts and separately re-tokenized visible-reasoning estimates are recorded in `measurements.csv`; estimates are not exact internal accounting.',
        '- Identical effort labels do not imply identical reasoning length or policy. A native runtime’s unsupported budget label cannot be treated as proof of xhigh behavior.',
        '- GPU memory values are after-request observations, not peak allocation measurements.',
        '- No Bonsai/DFlash2 acceptance claim is made. Those kernels and activation transforms still need integration into Lucebox.']
    if mismatches: lines.append('- **Prompt-token counts differ.** See `analysis.json`; identical textual requests do not establish identical tokenized inputs.')
    else: lines.append('- Prompt-token counts match Swift/Prism for all available matched cases.' if base_counts else '- No matched prompt-token comparison is available.')
    for f in failures: lines.append(f"- Runtime failure: `{f['backend']}` — {f['error']}")
    lines += ['', 'Raw requests/responses are in `results.json`; exact launch arguments and source identities are in `launch.json` and `provenance.json`.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
