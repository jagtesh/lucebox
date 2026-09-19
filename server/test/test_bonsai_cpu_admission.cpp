#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-cpu.h"

#include <cstdio>
#include <cstdlib>
#include <initializer_list>

static void require(bool value, const char * message) {
    if (!value) {
        std::fprintf(stderr, "%s\n", message);
        std::exit(1);
    }
}

int main() {
    ggml_init_params params{};
    params.mem_size = 1024 * 1024;
    params.no_alloc = true;
    ggml_context * ctx = ggml_init(params);
    require(ctx != nullptr, "ggml init failed");

    ggml_backend_t cpu = ggml_backend_cpu_init();
    require(cpu != nullptr, "CPU backend init failed");
    ggml_backend_dev_t device = ggml_backend_get_device(cpu);

    for (ggml_type type : {GGML_TYPE_Q2_0, GGML_TYPE_PQ2_0, GGML_TYPE_PTQ1_0}) {
        const int64_t width = ggml_blck_size(type);
        ggml_tensor * weights = ggml_new_tensor_2d(ctx, type, width, 4);
        ggml_tensor * input = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, width, 2);
        ggml_tensor * product = ggml_mul_mat(ctx, weights, input);
        require(!ggml_backend_dev_supports_op(device, product),
                "CPU admitted Bonsai packed matmul without a vec-dot kernel");
    }

    ggml_tensor * weights = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 32, 4);
    ggml_tensor * input = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 32, 2);
    require(ggml_backend_dev_supports_op(device, ggml_mul_mat(ctx, weights, input)),
            "CPU rejected an ordinary F32 matmul");

    ggml_backend_free(cpu);
    ggml_free(ctx);
    std::puts("Bonsai CPU admission checks passed");
}
