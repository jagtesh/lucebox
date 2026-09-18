# Bonsai 2 integration

Scope: Qwen3.8-derived Bonsai 2 27B GGUF in PQ2_0, PTQ1_0 and upstream Q2_0 packing. Preserve the existing production deployment while developing an isolated HIP build.

## Commit and validation sequence

1. Record implementation scope and upstream provenance.
2. Add packing support and validate quantization/dequantization and GPU operations.
3. Read and validate rotation metadata; implement transforms in target inference, embedding lookup and the shared draft output head. Reject unsupported metadata rather than silently generating incorrect output.
4. Validate target-only inference against Prism's reference implementation, including batched prefill versus incremental decoding.
5. Compare the three packings using fixed prompts/settings, separate prefill/decode timing and GPU memory measurements.
6. Test the existing Qwen DFlash2 drafter separately, measuring acceptance and output correctness before claiming acceleration.

Each coherent implementation step is committed after its checks. Do not replace the vendored GGML tree wholesale: Lucebox has independent kernels, type IDs and graph operations to preserve. Do not reuse old-model cache state or timing calibration for Bonsai.

## Native integration and qualification

- CPU wire-layout/round-trip tests preserve Lucebox TurboQuant's existing type 42. Prism wire type 42 is mapped to an internal Q2_0 type only with Prism metadata; PQ2_0/PTQ1_0 have separate internal IDs.
- The loader validates version, block size, transform/axis, explicit signs and named transformed tensors. Signed normalized Hadamard is applied before folded projections; embedding inversion applies Hadamard then signs. Grouped GDN value channels are reordered before their output projection.
- HIP decode uses packed matrix-vector kernels. Prefill unpacks only the current matrix tile to shared-memory int8 and uses the existing Q8 matrix machinery. There is no persistent FP16-expanded copy of packed model weights.
- Graph-local transformed inputs are shared across compatible projections. Ordinary model projections retain their existing path. Bonsai disables stacked aliases that would bypass per-weight transform metadata.
- Tests pass on R9700/gfx1201: independent dense Hadamard oracle, signed/grouped projections, inverse embedding, malformed metadata rejection, and 12 packed matrix cases (three formats, 1/2/16/64 columns).
- All three complete 27B models pass fixed-token final-logit comparison with Prism: cosine >= 0.99998, normalized RMSE <= 0.00613, same top five tokens. Incremental versus batched execution also passes. These are finite numerical tests, not bit-identical generation guarantees.
- Qualification source: `scripts/bonsai/qualify_models.py`; results: `benchmarks/bonsai-vs-swift-20260917/qualification/numerical-results.json`.
- A first qualification attempt encountered a stale private loader object. Its failed log was retained; the complete committed tree was synchronized and rebuilt before the successful run. Production was automatically restored after both attempts.
- Benchmarks use native Lucebox for every timed entry. Prism is an independent numerical oracle only. The report records the exact binary and shared GGML hashes.

## Remaining validation boundaries

This qualification covers single-GPU dense Qwen35 inference on gfx1201 with Q8 K/V. Multi-GPU placement, other architectures/devices, long-context cache behavior and all optional KV formats are not qualified by this work. The private build sets FA_ALL_QUANTS=OFF to avoid recompiling unused attention combinations; production has not been replaced. Bonsai DFlash2 is now measured for all three packings: 16 identical tasks per configuration, with all six strict quality checks passing. This is finite functional validation, not proof of bit-identical speculative generation. The full eight-configuration comparison is in `benchmarks/bonsai-vs-swift-20260917/REPORT.md`. PTQ1 with DFlash2 is slower than target-only and is not recommended with the current kernels/defaults. Production was restored to Swift with DFlash2; its executable and configuration remain unchanged.

## Deployment constraints

- Production remains unchanged until the implementation is validated.
- Download formats sequentially into `/root/bonsai2-models`, as requested; retain existing models. Run `python3 scripts/bonsai/download_models.py /root/bonsai2-models` to fetch pinned revisions and verify their published SHA256 hashes before using them.
- Packed weights must remain packed in GPU memory for a meaningful packing performance comparison.
- Architecture compatibility is not proof of drafter acceptance or exact sampled-output parity.
