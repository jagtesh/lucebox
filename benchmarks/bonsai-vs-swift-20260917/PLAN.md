# Bonsai packing versus Swift: native Lucebox comparison

## Integration gate passed

PQ2_0, PTQ1_0 and Q2_0 run inside Lucebox, including packed HIP decode/prefill, signed Hadamard activation transforms, inverse embeddings, grouped GDN output and output projection. CPU independent-oracle tests and all 12 packed GPU matrix cases pass. Full-model final logits pass the frozen comparison thresholds against Prism, and batched versus incremental execution passes for all three formats (see `qualification/numerical-results.json`). This is numerical qualification, not proof of identical long-generation behavior.

Prism prism-v7 at c1abda39458458ebfb4ec0722bd2224aab26e680 is a correctness oracle only. Every timed configuration uses the same private Lucebox executable: Swift IQ4_XS target-only, Bonsai PQ2_0/PTQ1_0/Q2_0 target-only, and Swift IQ4_XS with DFlash2. Bonsai DFlash2 is a later experiment.

## Frozen inputs and rubrics

Reuse swift-controlled-v1/suite.json byte for byte (SHA256 f0b9120d5643f58ea6f40e9cdd9f183ff0e5f745317d49d838e59eae8fe85925) and its frozen template. Six quality tasks retain exact JSON/type/value and tool-call checks. The ten article speed tasks retain completion-only criteria: code correctness is not scored. No changed rubric or successful retry replaces a failure.

- One first-pass run of all 16 tasks per entry. This run overrides the historical suite's repetition/order metadata, preserves its inputs and rubrics, and is preliminary rather than a statistical comparison.
- Thinking enabled, xhigh requested, temperature 0, seed 42; 65,536 context and 64,000 output ceiling. The ceiling is a context safety bound; a length finish fails normal completion. Record actual thinking tokens, since labels do not ensure equal reasoning length.
- Identical frozen template, 512-token idle prefill batches, GPU Q8 K/V, one stream. Record prompt counts and flag differences.
- Prefix slots disabled and hybrid cache off. Verify zero cached prefix in each timed response. Loading and short warmup are excluded.
- Save raw requests/responses, native prefill/decode timing, total output tokens and native thinking-token counts. No re-tokenization estimates are needed.
- This first pass measures natural task completion only. The earlier proposed Prism synthetic microbenchmark is removed; it would not measure native Lucebox inference.
- The private HIP build uses FA_ALL_QUANTS=OFF; all entries use the same Q8 K/V kernels. This is not a production deployment or general multi-GPU qualification.

## Execution and reporting

Private port 18217. Require production idle before stopping it. Independent systemd ExecStopPost plus Python finally restore lucebox.service, with a bounded runtime. Preserve production configuration, models and executable. Never overlap GPU workloads.

Store model hashes, executable/source identities, exact arguments, logs, responses and errors. Record failures and continue remaining entries only after verified memory drainage. Never treat missing timing as zero or compare partial totals against complete suites. Report quality and speed subsets separately, thinking/output counts and task-level wall time alongside generation throughput.
