#!/usr/bin/env python3
"""Private single-GPU comparison. Run only under the restoration systemd unit."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
PORT = 18217
SUITE_HASH = 'f0b9120d5643f58ea6f40e9cdd9f183ff0e5f745317d49d838e59eae8fe85925'
PRISM_REV = 'c1abda39458458ebfb4ec0722bd2224aab26e680'
BUILD = Path('/root/lucebox-bonsai/server/build-hip')
SWIFT = '/code/models/swift-qwen/ukisai_Swift-Qwen3.8-27b-IQ4_XS.gguf'
MODELS = {
    'swift-native': SWIFT,
    'bonsai-pq2': '/root/bonsai2-models/Ternary-Bonsai-2-27B-PQ2_0.gguf',
    'bonsai-ptq1': '/root/bonsai2-models/Ternary-Bonsai-2-27B-PTQ1_0.gguf',
    'bonsai-q2': '/root/bonsai2-models/Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf',
    'swift-dflash2': SWIFT,
}
ENV = dict(os.environ, LD_LIBRARY_PATH='/opt/rocm/core-10.0/lib',
           DFLASH_IDLE_PREFILL_TOKENS='512', DFLASH_MIXED_PREFILL_TOKENS='64',
           DFLASH_LONG_MIXED_PREFILL_TOKENS='64', DFLASH_HYBRID_CACHE='off')


def save(name, obj):
    tmp = ROOT / (name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    tmp.replace(ROOT / name)


def call(path, body=None, port=PORT, timeout=900):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def shape(a, b):
    if type(a) != type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(shape(a[k], b[k]) for k in b)
    if isinstance(a, list):
        return len(a) == len(b) and all(shape(x, y) for x, y in zip(a, b))
    return True


def score(case, response):
    # Unchanged rubric from swift-controlled-v1/run.py.
    ch = response['choices'][0]
    m = ch['message']
    ok = ch['finish_reason'] in ('stop', 'tool_calls')
    if case['suite'] == 'speed':
        return {'completed': ok and bool(m.get('content', '').strip()),
                'format_pass': None, 'answer_pass': None, 'pass': None}
    value, fmt = None, False
    try:
        if case['id'] == 'tool_call':
            tc = m.get('tool_calls', [])
            assert len(tc) == 1 and tc[0]['function']['name'] == 'lookup_weather' and ch['finish_reason'] == 'tool_calls'
            value = json.loads(tc[0]['function']['arguments'])
        else:
            value = json.loads(m.get('content', ''))
        fmt = shape(value, case['expected'])
    except (ValueError, AssertionError, KeyError, TypeError):
        pass
    return {'completed': ok, 'format_pass': fmt, 'answer_pass': value == case['expected'],
            'pass': ok and fmt and value == case['expected']}


def launch_args(name, model):
    template = str(ROOT / 'frozen-template.jinja')
    args = [str(BUILD / 'dflash_server'), model,
        '--prefix-cache-slots', '0', '--max-ctx', '65536', '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
        '--host', '127.0.0.1', '--port', str(PORT), '--model-name', 'comparison',
        '--chat-template-file', template, '--default-max-tokens', '64000', '--think-max-tokens', '64000',
        '--reasoning-effort-x-high', '64000', '--reasoning-effort-max', '64000', '--hard-limit-reply-budget', '0']
    if name.endswith('-dflash2'):
        args += ['--draft', '/code/models/qwen38/qwen38-dflash2-q8_0.gguf', '--draft-block-size', '16']
    return args


def drain_gpu():
    for _ in range(150):
        if int(Path('/sys/class/drm/card5/device/mem_info_vram_used').read_text()) < 1536 * 1024**2:
            return
        time.sleep(.2)
    raise RuntimeError('GPU allocations did not drain; refusing concurrent benchmark')


def stop_process(p):
    if p is None or p.poll() is not None:
        return
    p.terminate()
    try:
        p.wait(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()


def main():
    qualification = json.loads(Path('/root/bonsai2-qualification/results.json').read_text())
    assert {q['model'] for q in qualification} == {'pq2', 'ptq1', 'q2'}
    assert all(q['reference']['passed'] and q['chunking']['passed'] for q in qualification)
    save('qualification.json', qualification)
    suite_bytes = (ROOT / 'suite.json').read_bytes()
    assert hashlib.sha256(suite_bytes).hexdigest() == SUITE_HASH
    suite = json.loads(suite_bytes)
    assert not (ROOT / 'results.json').exists(), 'Keep previous results; use a new run directory'
    health = call('/health', port=8216, timeout=10)
    assert not health.get('busy') and not health.get('active_requests') and not health.get('pending_requests'), health
    assert subprocess.run(['systemctl', 'is-active', '--quiet', 'lucebox.service']).returncode == 0
    args = {n: launch_args(n, m) for n, m in MODELS.items()}
    save('launch.json', args)
    save('provenance.json', dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        oracle_prism_revision=PRISM_REV, suite_sha256=SUITE_HASH, repetitions_tasks=1,
        native_executable_sha256=hashlib.sha256((BUILD/'dflash_server').read_bytes()).hexdigest(),
        native_source_revision=(ROOT/'source-revision.txt').read_text().strip(),
        template_sha256=hashlib.sha256((ROOT/'frozen-template.jinja').read_bytes()).hexdigest(),
        initial_health=health, models={n:dict(path=m,bytes=Path(m).stat().st_size) for n,m in MODELS.items()},
        verified_bonsai=json.loads(Path('/root/bonsai2-models/verified-models.json').read_text())))
    rows, failures = [], []
    p = None
    subprocess.run(['systemctl', 'stop', 'lucebox.service'], check=True)
    try:
        drain_gpu()
        for name, model in MODELS.items():
            save('progress.json', dict(backend=name, phase='loading', completed=len(rows)))
            try:
                with (ROOT / (name + '.log')).open('w') as log:
                    p = subprocess.Popen(args[name], env=ENV, stdout=log, stderr=subprocess.STDOUT)
                    started = time.monotonic()
                    for _ in range(180):
                        if p.poll() is not None:
                            raise RuntimeError('startup failed: ' + name)
                        try:
                            if call('/health', timeout=2).get('status') == 'ok':
                                break
                        except Exception:
                            pass
                        time.sleep(1)
                    else:
                        raise RuntimeError('startup timeout: ' + name)
                    load_seconds = time.monotonic() - started
                    props = call('/props')
                    save(name + '-props.json', props)
                    assert props['default_generation_settings']['n_ctx'] == 65536, 'Unexpected context capacity'
                    envelope = props['budget_envelope']
                    assert envelope['default_max_tokens'] == 64000
                    assert envelope['think_max_tokens'] == 64000
                    assert envelope['hard_limit_reply_budget'] == 0
                    call('/v1/chat/completions', dict(model='comparison', messages=[dict(role='user', content='Reply only: ready')],
                         temperature=0, max_tokens=16, reasoning_effort='none', cache_prompt=False))
                    for case in suite['cases']:
                        save('progress.json', dict(backend=name, phase=case['id'], completed=len(rows)))
                        body = dict(model='comparison', messages=case['messages'], temperature=0, seed=42,
                                    max_tokens=64000, reasoning_effort='xhigh', cache_prompt=False)
                        if 'tools' in case:
                            body['tools'] = case['tools']
                        t = time.monotonic()
                        response = call('/v1/chat/completions', body)
                        wall = time.monotonic() - t
                        usage = response['usage']
                        timing = response.get('timings', usage.get('timings', {}))
                        message = response['choices'][0]['message']
                        reason = message.get('reasoning_content') or message.get('reasoning') or ''
                        row = dict(backend=name, case=case['id'], suite=case['suite'], rep=1, wall_seconds=wall,
                            load_seconds=load_seconds, prefill_ms=timing.get('prefill_ms', timing.get('prompt_ms')),
                            decode_ms=timing.get('decode_ms', timing.get('predicted_ms')),
                            prompt_tokens=usage['prompt_tokens'], total_tokens=usage['completion_tokens'],
                            reasoning_tokens_native=usage.get('completion_tokens_details', {}).get('reasoning_tokens'),
                            reasoning_text=reason, score=score(case, response), request=body, response=response,
                            vram_bytes_after=int(Path('/sys/class/drm/card5/device/mem_info_vram_used').read_text()))
                        assert not timing.get('cache_hit'), 'Unexpected warm cache hit'
                        assert timing.get('cached_prefix_tokens', 0) == 0, 'Unexpected cached prefix'
                        rows.append(row)
                        save('results.json', rows)
                        print(json.dumps({k:v for k,v in row.items() if k not in ('request','response','reasoning_text')}), flush=True)
            except Exception as e:
                failures.append(dict(backend=name, error=str(e)))
                save('failures.json', failures)
                print(name, str(e), flush=True)
            finally:
                stop_process(p)
                p = None
                drain_gpu()
    finally:
        stop_process(p)
        subprocess.run(['systemctl', 'start', 'lucebox.service'], check=True)
        save('progress.json', dict(phase='finished', completed=len(rows), failures=failures))


if __name__ == '__main__':
    main()
