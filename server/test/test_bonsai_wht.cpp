#include "ggml.h"
#include "common/bonsai.h"
#include "ggml-backend.h"
#include "ggml-cpu.h"
#ifdef GGML_USE_CUDA
#include "ggml-cuda.h"
#endif
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

static void check(bool ok, const char * message) {
    if (!ok) { std::fprintf(stderr, "%s\n", message); std::exit(1); }
}

int main(int argc, char ** argv) {
    ggml_backend_t backend = nullptr;
    if (argc > 1 && std::strcmp(argv[1], "--gpu") == 0) {
#ifdef GGML_USE_CUDA
        backend = ggml_backend_cuda_init(0);
#endif
    } else {
        backend = ggml_backend_cpu_init();
        ggml_backend_cpu_set_n_threads(backend, 4);
    }
    check(backend != nullptr, "requested backend unavailable");
    for (int width : {2, 32, 128, 1024}) {
        auto * ctx = ggml_init({4*1024*1024, nullptr, true});
        auto * input = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 5*width, 3);
        auto * once = ggml_bonsai_wht(ctx, input, width);
        auto * twice = ggml_bonsai_wht(ctx, once, width);
        auto * graph = ggml_new_graph(ctx);
        ggml_build_forward_expand(graph, twice);
        auto buffer = ggml_backend_alloc_ctx_tensors(ctx, backend);
        check(buffer != nullptr, "allocate graph");
        std::vector<float> x(15*width), actual(x.size()), inverse(x.size());
        for (size_t i=0; i<x.size(); ++i) x[i] = std::sin(i*0.271) + (int(i)%7-3)*0.125f;
        ggml_backend_tensor_set(input, x.data(), 0, x.size()*sizeof(float));
        check(ggml_backend_graph_compute(backend, graph) == GGML_STATUS_SUCCESS, "compute WHT");
        ggml_backend_tensor_get(once, actual.data(), 0, actual.size()*sizeof(float));
        ggml_backend_tensor_get(twice, inverse.data(), 0, inverse.size()*sizeof(float));
        // Independent dense Sylvester matrix: H[i,j]=(-1)^popcount(i&j)/sqrt(N).
        for (size_t base=0; base<x.size(); base+=width) {
            for (int i=0; i<width; ++i) {
                double expected = 0;
                for (int j=0; j<width; ++j) {
                    unsigned bits = unsigned(i&j), parity = 0;
                    while (bits) { parity ^= bits&1; bits >>= 1; }
                    expected += (parity ? -1.0 : 1.0)*x[base+j];
                }
                expected /= std::sqrt(double(width));
                check(std::abs(actual[base+i]-expected) < 3e-5*(1+std::abs(expected)), "dense Hadamard oracle mismatch");
                check(std::abs(inverse[base+i]-x[base+i]) < 5e-6, "H(H(x)) must equal x");
            }
        }
        ggml_backend_buffer_free(buffer);
        ggml_free(ctx);
    }
    for (bool grouped : {false, true}) {
        using namespace dflash::common;
        auto * ctx = ggml_init({4*1024*1024, nullptr, true});
        BonsaiState state;
        state.meta.block = 4;
        state.meta.grouped_v = grouped;
        state.meta.weights.insert("output.weight");
        state.meta.signs[8] = {1,-1,-1,1,-1,1,1,-1};
        check(state.allocate(backend), "allocate signs");
        auto * input = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 8, 3);
        auto * weights = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 8, 5);
        ggml_set_name(weights, "output.weight");
        auto * result = bonsai_matmul(ctx, &state, weights, input, 2, 2, 2);
        auto * repeated = bonsai_matmul(ctx, &state, weights, input, 2, 2, 2);
        check(result->src[1] == repeated->src[1], "reuse identical transform within graph");
        auto * graph = ggml_new_graph(ctx);
        ggml_build_forward_expand(graph, result);
        auto buffer = ggml_backend_alloc_ctx_tensors(ctx, backend);
        check(buffer != nullptr, "allocate signed transform graph");
        std::vector<float> x(24), w(40), actual(15);
        for (size_t i=0; i<x.size(); ++i) x[i] = (int(i)%11-5)*0.25f;
        for (size_t i=0; i<w.size(); ++i) w[i] = (int(i)%7-3)*0.125f;
        ggml_backend_tensor_set(input, x.data(), 0, x.size()*sizeof(float));
        ggml_backend_tensor_set(weights, w.data(), 0, w.size()*sizeof(float));
        check(ggml_backend_graph_compute(backend, graph) == GGML_STATUS_SUCCESS, "signed transform matmul");
        ggml_backend_tensor_get(result, actual.data(), 0, actual.size()*sizeof(float));
        for (int col=0; col<3; ++col) {
            double transformed[8] = {};
            for (int i=0; i<8; ++i) {
                for (int j=0; j<4; ++j) {
                    const int logical=(i/4)*4+j;
                    // Explicit tiled-to-grouped reindex, independent of ggml_permute.
                    const int source=grouped ? logical%2 + 2*((logical/4)%2) + 4*((logical/2)%2) : logical;
                    unsigned bits=unsigned((i%4)&j), parity=0;
                    while (bits) { parity ^= bits&1; bits >>= 1; }
                    transformed[i] += (parity?-1.0:1.0)*x[col*8+source]*state.meta.signs.at(8)[logical]/2;
                }
            }
            for (int row=0; row<5; ++row) {
                double expected=0;
                for (int k=0; k<8; ++k) expected+=w[row*8+k]*transformed[k];
                check(std::abs(actual[col*5+row]-expected)<2e-5,"signed/grouped projection oracle mismatch");
            }
        }
        ggml_backend_buffer_free(buffer);
        ggml_free(ctx);
    }
    ggml_backend_free(backend);
    std::puts("Bonsai normalized WHT: dense oracle and inverse passed");
}
