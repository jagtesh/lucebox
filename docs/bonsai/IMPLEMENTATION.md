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

## Deployment constraints

- Production remains unchanged until the implementation is validated.
- Download formats sequentially because /code currently has limited capacity; retain existing models.
- Packed weights must remain packed in GPU memory for a meaningful packing performance comparison.
- Architecture compatibility is not proof of drafter acceptance or exact sampled-output parity.
