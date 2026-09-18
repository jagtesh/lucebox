// Independent wire-pattern checks for Prism's group-128 ternary packings.
#include "ggml.h"
#include "ggml-quants.h"
#include "gguf.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
static void require(bool ok, const char * msg) { if (!ok) { std::fprintf(stderr, "%s\n", msg); std::exit(1); } }
int main() {
    ggml_init_params p = {1024*1024, nullptr, true};
    auto * ctx = ggml_init(p);
    require(ctx != nullptr, "ggml init");
    for (int kind=0; kind<3; ++kind) {
        const ggml_type type = kind==0 ? GGML_TYPE_Q2_0 : kind==1 ? GGML_TYPE_PQ2_0 : GGML_TYPE_PTQ1_0;
        const int n = kind==0 ? 64 : 128;
        std::vector<float> x(n), out(n);
        std::vector<unsigned char> packed(ggml_row_size(type,n));
        // Distinct groups, scales and lane patterns catch packing/ordering errors.
        for (int shift=0; shift<n; ++shift) {
            for (int j=0;j<n;++j) x[j] = ((j+shift)%3-1)*0.5f;
            if (kind==0) quantize_row_q2_0_ref(x.data(),(block_q2_0 *)packed.data(),n);
            if (kind==1) quantize_row_pq2_0_ref(x.data(),(block_pq2_0 *)packed.data(),n);
            if (kind==2) quantize_row_ptq1_0_ref(x.data(),(block_ptq1_0 *)packed.data(),n);
            if (kind==0) dequantize_row_q2_0((block_q2_0 *)packed.data(),out.data(),n);
            if (kind==1) dequantize_row_pq2_0((block_pq2_0 *)packed.data(),out.data(),n);
            if (kind==2) dequantize_row_ptq1_0((block_ptq1_0 *)packed.data(),out.data(),n);
            require(x==out,"ternary round trip");
            if (kind<2) {
                for(int j=0;j<n;++j) require(((packed[2+j/4]>>(2*(j%4)))&3)==(j+shift)%3,"2-bit wire code");
            } else {
                // Independently reconstruct each base-3 byte in logical lane order.
                for (int b=0;b<26;++b) {
                    int v=0;
                    const int count=b<24?5:4;
                    for(int t=0;t<count;++t) {
                        int pos=b<16?b+t*16:b<24?80+(b-16)+t*8:120+(b-24)+t*2;
                        v=3*v+(pos+shift)%3;
                    }
                    if(count==4) v*=3;
                    require(packed[b]==(v*256+242)/243,"base-3 wire code");
                }
            }
        }
        require(ggml_blck_size(type)==n,"block size");
    }
    require(GGML_TYPE_TQ3_0==42 && GGML_TYPE_Q2_0!=42,"legacy TurboQuant type preserved");
    // Actual GGUF parsing must disambiguate wire id 42 without changing legacy KV.
    for (bool prism : {false, true}) {
        auto * file = std::tmpfile();
        require(file != nullptr, "temporary GGUF file");
        auto * metadata = gguf_init_empty();
        if (prism) gguf_set_val_u32(metadata, "prism.hadamard.version", 1);
        auto * tensor = ggml_new_tensor_1d(ctx, GGML_TYPE_TQ3_0, 128);
        ggml_set_name(tensor, "wire42.weight");
        gguf_add_tensor(metadata, tensor);
        require(gguf_write_to_file_ptr(metadata, file, true), "write wire fixture");
        std::rewind(file);
        gguf_init_params read_params = {true, nullptr};
        auto * parsed = gguf_init_from_file_ptr(file, read_params);
        require(parsed != nullptr, "parse wire fixture");
        require(gguf_get_tensor_type(parsed, 0) == (prism ? GGML_TYPE_Q2_0 : GGML_TYPE_TQ3_0),
                "wire 42 must follow Prism metadata and preserve legacy files");
        gguf_free(parsed);
        gguf_free(metadata);
        std::fclose(file);
    }
    ggml_free(ctx);
    std::puts("Bonsai codec wire patterns and round trips passed");
}
