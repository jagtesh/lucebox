#include "bonsai-wht.cuh"

// One cooperative block per independent Hadamard block. No subgroup-width
// assumptions: the same butterfly works on CUDA and AMD wave32/wave64.
static __global__ void bonsai_wht_kernel(const float * src, float * dst, int width) {
    __shared__ float values[1024];
    const int64_t offset = (int64_t) blockIdx.x * width;
    for (int j = threadIdx.x; j < width; j += blockDim.x) values[j] = src[offset+j];
    __syncthreads();
    for (int stride = 1; stride < width; stride *= 2) {
        for (int pair = threadIdx.x; pair < width/2; pair += blockDim.x) {
            const int i = (pair / stride) * (2*stride) + pair % stride;
            const float a = values[i], b = values[i+stride];
            values[i] = a+b;
            values[i+stride] = a-b;
        }
        __syncthreads();
    }
    const float scale = rsqrtf((float) width);
    for (int j = threadIdx.x; j < width; j += blockDim.x) dst[offset+j] = values[j] * scale;
}

void ggml_cuda_op_bonsai_wht(ggml_backend_cuda_context & ctx, ggml_tensor * dst) {
    const auto * src = dst->src[0];
    const int width = ggml_get_op_params_i32(dst, 0);
    GGML_ASSERT(src->type == GGML_TYPE_F32 && ggml_is_contiguous(src));
    GGML_ASSERT(width >= 2 && width <= 1024 && (width & (width-1)) == 0 && src->ne[0] % width == 0);
    const int64_t blocks = ggml_nelements(src) / width;
    GGML_ASSERT(blocks > 0 && blocks <= INT32_MAX);
    bonsai_wht_kernel<<<(unsigned) blocks, 256, 0, ctx.stream()>>>(
        (const float *) src->data, (float *) dst->data, width);
    CUDA_CHECK(cudaGetLastError());
}
