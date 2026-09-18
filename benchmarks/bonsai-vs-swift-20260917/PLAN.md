# Execution gate: native Lucebox integration first

User correction: do not run the reference-runtime benchmark matrix below. It is retained as historical setup only. `run.py` is disabled until its model entries use the qualified Lucebox backend. Prism may be used for numerical correctness checks, never as a substitute for the requested Lucebox performance comparison. No measured benchmark was started.

# Bonsai packing versus Swift: frozen comparison

## Scope

Prism `prism-v7` at `c1abda39458458ebfb4ec0722bd2224aab26e680`, compiled for gfx1201, runs Swift IQ4_XS and Bonsai PQ2_0, PTQ1_0 and Q2_0. This isolates packing/model differences under the same engine. A fifth entry measures the current Swift model with Lucebox and its resident DFlash2 drafter, the practical baseline. This is **not** a Bonsai-on-Lucebox or Bonsai-with-DFlash2 result; that integration is unfinished.

## Frozen inputs and rubrics

Reuse `swift-controlled-v1/suite.json` byte for byte (SHA256 `f0b9120d5643f58ea6f40e9cdd9f183ff0e5f745317d49d838e59eae8fe85925`) and its frozen template. Six quality tasks retain exact JSON/type/value and tool-call checks. The ten article speed tasks retain their original completion-only criterion: their code correctness is not scored. No changed rubric or selected successful retry replaces a failure.

- One first-pass run of all 16 tasks per entry, labelled preliminary rather than a statistical median.
- Thinking enabled, requested effort xhigh, temperature 0, seed 42; 65,536 context and 64,000 output ceiling from the frozen suite. This ceiling is a context safety bound, not an early throughput cutoff. Any length finish fails normal-completion checks. Prism uses unlimited reasoning budget; effort labels do not guarantee identical thinking behavior across models.
- Same prompt template, batch/microbatch 512, GPU Q8 K/V, one active stream. Record actual prompt counts and reject an equal-input claim if they differ.
- Cold prompt cache for each measured task; model-load and warmup outside task timing. Record request/response bodies, finish reasons, native timing, usage and visible reasoning.
- Report native reasoning counts where present and separately labelled re-tokenized reasoning-text estimates otherwise. Never subtract estimated text tokens from native totals and present the result as exact answer-token accounting.
- Three synthetic `llama-bench` repetitions for 512/2048-token prefill and 128-token decode in each Prism entry; use medians of individual samples. These have fixed token counts, unlike natural task completion.

## Execution

Use private port 18217. Require production idle before pausing its service. Run the benchmark under a systemd unit with an independent `ExecStopPost` restoring `lucebox.service`, plus Python `finally` restoration and a bounded runtime. Preserve existing service configuration, models and executable. No simultaneous generation or fitting both production and benchmark models into VRAM.

Store immutable model-source hashes, runtime identity, exact arguments, logs, raw results and failure records. Each backend's task failure is recorded; continue other backends after verified GPU memory drainage. Never claim missing timing as zero or a failed startup as a speed result. Compare task-level wall time as well as generation rate, because shorter reasoning can lower time without faster kernels.
