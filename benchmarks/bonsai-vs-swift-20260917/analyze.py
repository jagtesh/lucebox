#!/usr/bin/env python3
"""Summarize native Lucebox measurements without imputing missing observations."""
import csv
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
NAMES = {'swift-native': 'Swift IQ4_XS', 'bonsai-pq2': 'Bonsai PQ2_0',
         'bonsai-ptq1': 'Bonsai PTQ1_0', 'bonsai-q2': 'Bonsai Q2_0',
         'swift-dflash2': 'Swift IQ4_XS + DFlash2'}


def fmt(x, digits=2):
    return '—' if x is None else f'{x:.{digits}f}'


def summarize(rows, expected):
    def total(key, scale=1):
        return sum(r[key] for r in rows)/scale if rows and all(r.get(key) is not None for r in rows) else None
    decode = total('decode_ms', 1000)
    tokens = total('total_tokens')
    thinking = total('reasoning_tokens_native')
    return dict(measured=len(rows), expected=expected, complete=len(rows)==expected,
        completed=sum(bool(r['score']['completed']) for r in rows),
        passed=sum(r['score']['pass'] is True for r in rows),
        wall_seconds=total('wall_seconds'), prefill_seconds=total('prefill_ms', 1000),
        decode_seconds=decode, generated_tokens=tokens, thinking_tokens=thinking,
        other_output_tokens=tokens-thinking if tokens is not None and thinking is not None else None,
        decode_tps=tokens/decode if decode else None,
        max_observed_vram_gib=max((r['vram_bytes_after']/1024**3 for r in rows), default=None))


def main():
    rows = json.loads((ROOT/'results.json').read_text()) if (ROOT/'results.json').exists() else []
    for folder in ('dflash-followup', 'dflash-remaining'):
        followup = ROOT/folder/'results.json'
        if followup.exists(): rows += json.loads(followup.read_text())
    for backend in sorted({r['backend'] for r in rows}):
        if backend not in NAMES and backend.endswith('-dflash2'):
            NAMES[backend] = NAMES[backend.removesuffix('-dflash2')]+' + DFlash2'
    suite = json.loads((ROOT/'suite.json').read_text())
    failures = json.loads((ROOT/'failures.json').read_text()) if (ROOT/'failures.json').exists() else []
    for folder in ('dflash-followup', 'dflash-remaining'):
        followup_failures=ROOT/folder/'failures.json'
        if followup_failures.exists(): failures += json.loads(followup_failures.read_text())
    summaries, detail = [], []
    for backend, label in NAMES.items():
        rr = [r for r in rows if r['backend']==backend]
        assert len({r['case'] for r in rr})==len(rr), f'Duplicate cases: {backend}'
        for subset in ('all', 'quality', 'speed'):
            selected = [r for r in rr if subset=='all' or r['suite']==subset]
            expected = sum(subset=='all' or c['suite']==subset for c in suite['cases'])
            summaries.append(dict(backend=backend, label=label, subset=subset, **summarize(selected, expected)))
        for r in rr:
            detail.append({k:r.get(k) for k in ('backend','case','suite','wall_seconds','prefill_ms','decode_ms','prompt_tokens','total_tokens','reasoning_tokens_native')}
                | dict(finish_reason=r['response']['choices'][0]['finish_reason'], **r['score']))
    for s in summaries:
        for key, backend in [('wall_speedup_vs_swift','swift-native'),('wall_speedup_vs_swift_dflash2','swift-dflash2')]:
            base=next(x for x in summaries if x['backend']==backend and x['subset']==s['subset'])
            s[key]=base['wall_seconds']/s['wall_seconds'] if base['complete'] and s['complete'] and s['wall_seconds'] else None
    counts = {r['case']:r['prompt_tokens'] for r in rows if r['backend']=='swift-native'}
    mismatches = [dict(backend=r['backend'], case=r['case'], prompt_tokens=r['prompt_tokens'], swift_prompt_tokens=counts[r['case']])
                  for r in rows if r['case'] in counts and r['prompt_tokens']!=counts[r['case']]]
    (ROOT/'analysis.json').write_text(json.dumps(dict(summary=summaries, failures=failures, prompt_count_mismatches=mismatches),indent=2)+'\n')
    if detail:
        with (ROOT/'measurements.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(detail[0]));w.writeheader();w.writerows(detail)
    lines=['# Bonsai versus Swift on R9700', '',
        'Every timed entry uses the same native Lucebox build. Bonsai includes its packed HIP kernels and signed Hadamard transforms. Prism is used only for prior numerical qualification.', '',
        '**Method:** one run per task, thinking enabled with xhigh requested, temperature 0, seed 42, identical frozen template and 16 prompts. Six quality tasks have unchanged strict format/answer checks. Ten article speed tasks check completion only; their code correctness is not established. Results are preliminary, without confidence intervals.', '']
    for subset, title in [('all','All 16 tasks'),('quality','Six quality tasks'),('speed','Ten article speed tasks')]:
        lines += [f'## {title}', '', '| Configuration | Completed | Quality passed | Wall s | Prefill s | Decode s | Output tokens | Thinking tokens | Decode tok/s | Wall speedup vs Swift |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for s in [x for x in summaries if x['subset']==subset]:
            quality=next(x for x in summaries if x['backend']==s['backend'] and x['subset']=='quality')
            qp=f"{quality['passed']}/{quality['measured']} measured" if subset!='speed' else 'Not scored'
            label=s['label']+(' (partial)' if not s['complete'] else '')
            speed=fmt(s['wall_speedup_vs_swift'])+'×' if s['wall_speedup_vs_swift'] is not None else '—'
            lines.append(f"| {label} | {s['completed']}/{s['expected']} | {qp} | {fmt(s['wall_seconds'])} | {fmt(s['prefill_seconds'])} | {fmt(s['decode_seconds'])} | {fmt(s['generated_tokens'],0)} | {fmt(s['thinking_tokens'],0)} | {fmt(s['decode_tps'])} | {speed} |")
        lines.append('')
    lines += ['Decode rate is total generated tokens divided by total measured decode time, including thinking. Wall time excludes model loading and warmup. Partial totals must not be compared with complete suites. Shorter reasoning can improve task time without faster kernels.', '', '## Per-task results', '',
              '| Configuration | Task | Wall s | Prefill ms | Decode ms | Output tokens | Thinking tokens | Result |', '|---|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        verdict=('pass' if r['score']['pass'] else 'FAIL') if r['suite']=='quality' else ('completed; correctness unscored' if r['score']['completed'] else 'INCOMPLETE')
        lines.append(f"| {NAMES[r['backend']]} | {r['case']} | {fmt(r['wall_seconds'])} | {fmt(r.get('prefill_ms'),1)} | {fmt(r.get('decode_ms'),1)} | {r['total_tokens']} | {fmt(r.get('reasoning_tokens_native'),0)} | {verdict} |")
    lines += ['', '## DFlash2 verification', '', '| Configuration | Speculation actually ran | Median request acceptance |', '|---|---:|---:|']
    for backend,label in NAMES.items():
        if not backend.endswith('-dflash2'): continue
        rr=[r for r in rows if r['backend']==backend]
        rates=[r['response']['usage']['accept_rate'] for r in rr if r['response']['usage'].get('spec_decode_ran')]
        lines.append(f"| {label} | {sum(bool(r['response']['usage'].get('spec_decode_ran')) for r in rr)}/{len(rr)} | {fmt(median(rates)*100 if rates else None)}% |")
    lines += ['', 'Acceptance is the median of native per-request rates, not a pooled token-weighted acceptance estimate.', '', '## Quality failures', '']
    bad=[r for r in rows if r['suite']=='quality' and not r['score']['pass']]
    for r in bad:
        lines.append(f"- {NAMES[r['backend']]} / `{r['case']}`: format={r['score']['format_pass']}, answer={r['score']['answer_pass']}, finish={r['response']['choices'][0]['finish_reason']}.")
    if not bad: lines.append('No failed quality checks among measured requests; see coverage above.')
    lines += ['', '## Limits and reproducibility', '',
        '- All reasoning counts come from native usage accounting. Other output tokens include any protocol/control tokens counted by the runtime; they are not necessarily just visible answer text.',
        '- The same xhigh setting does not imply equal reasoning length. Maximum output is 64,000 within a 65,536 context; reaching the length ceiling is not normal completion.',
        '- Post-request VRAM observations are not peak memory measurements. No synthetic throughput microbenchmark or thermal/order randomization is included in this first pass.',
        '- Target-only results and the separately executed Bonsai DFlash2 runs are labelled explicitly. Shared ancestry alone is not treated as evidence of drafter compatibility.',
        '- The private build uses the same Q8 K/V kernels for every entry with FA_ALL_QUANTS=OFF. This is not a production deployment.',
        '- Numerical qualification compares fixed-token final logits with Prism and batched versus incremental processing. It does not establish bit-identical long generations or broader model quality.']
    lines.append('- **Prompt counts differ:** inspect `analysis.json`; no equal-token-work claim is made.' if mismatches else '- Prompt counts match Swift for all available matched cases.' if counts else '- Matched prompt-count comparison unavailable.')
    for f in failures: lines.append(f"- Runtime failure: `{f['backend']}` — {f['error']}")
    lines += ['', 'Evidence: [raw requests and responses](results.json), [CSV measurements](measurements.csv), [launch arguments](launch.json), [provenance](provenance.json), [numerical qualification](qualification/numerical-results.json).']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
