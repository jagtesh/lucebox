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

## Current validation boundary

- CPU packing round trips, independent wire-layout checks, and GGUF type-42 disambiguation pass. The codec test is registered as `bonsai_codecs`.
- GPU dequantization functions and the three conversion registrations are ported from Prism `prism-v7`, commit `c1abda39458458ebfb4ec0722bd2224aab26e680`. Their numerical function bodies match that reference. HIP compilation and GPU execution are still pending; conversion support alone does not provide packed matrix multiplication.
- Packed GPU matrix multiplication and Bonsai activation/embedding transforms remain to be integrated. The loader intentionally rejects Prism rotation metadata until that integration is complete.
- No Bonsai inference correctness or performance result is claimed, and production is unchanged.

## Deployment constraints

- Production remains unchanged until the implementation is validated.
- Download formats sequentially into `/root/bonsai2-models`, as requested; retain existing models. Run `python3 scripts/bonsai/download_models.py /root/bonsai2-models` to fetch pinned revisions and verify their published SHA256 hashes before using them.
- Packed weights must remain packed in GPU memory for a meaningful packing performance comparison.
- Architecture compatibility is not proof of drafter acceptance or exact sampled-output parity.
