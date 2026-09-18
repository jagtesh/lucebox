#include "ggml.h"
#include "ggml-quants.h"
#include "ggml-backend.h"
#include "ggml-cuda.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
static void check(bool ok,const char * message) { if(!ok){std::fprintf(stderr,"%s\n",message);std::exit(1);} }
int main() {
    auto backend=ggml_backend_cuda_init(0);
    check(backend!=nullptr,"GPU required");
    const int k=1024, rows=65;
    for(auto type:{GGML_TYPE_Q2_0,GGML_TYPE_PQ2_0,GGML_TYPE_PTQ1_0}) {
        for(int cols:{1,2,16,64}) {
            auto * ctx=ggml_init({8*1024*1024,nullptr,true});
            auto * w=ggml_new_tensor_2d(ctx,type,k,rows);
            auto * x=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,k,cols);
            auto * y=ggml_mul_mat(ctx,w,x);
            check(ggml_backend_supports_op(backend,y),"packed GPU matrix operation unsupported");
            auto * graph=ggml_new_graph(ctx);ggml_build_forward_expand(graph,y);
            auto buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);check(buffer!=nullptr,"GPU allocation");
            std::vector<float> weights(k*rows),input(k*cols),actual(rows*cols),decoded(k*rows);
            std::vector<unsigned char> packed(ggml_nbytes(w));
            for(int r=0;r<rows;++r) for(int i=0;i<k;++i) weights[r*k+i]=((i*17+r*11)%3-1)*(r%2?0.125f:0.25f);
            for(int c=0;c<cols;++c) for(int i=0;i<k;++i) input[c*k+i]=i%32==0 ? 127/32.0f : ((i*19+c*13)%255-127)/32.0f;
            // Q8 input scales are exact powers of two in this fixture, allowing
            // comparison with the unquantized dot oracle without masking errors.
            check(ggml_quantize_chunk(type,weights.data(),packed.data(),0,rows,k,nullptr)==packed.size(),"packed length");
            ggml_get_type_traits(type)->to_float(packed.data(),decoded.data(),decoded.size());
            check(decoded==weights,"CPU packed weights differ");
            ggml_backend_tensor_set(w,packed.data(),0,packed.size());
            ggml_backend_tensor_set(x,input.data(),0,input.size()*sizeof(float));
            check(ggml_backend_graph_compute(backend,graph)==GGML_STATUS_SUCCESS,"packed matmul compute");
            ggml_backend_tensor_get(y,actual.data(),0,actual.size()*sizeof(float));
            for(int c=0;c<cols;++c) for(int r=0;r<rows;++r) {
                double expected=0;
                for(int i=0;i<k;++i) expected+=double(decoded[r*k+i])*input[c*k+i];
                if(std::abs(actual[c*rows+r]-expected)>0.001) {
                    std::fprintf(stderr,"%s cols=%d row=%d col=%d actual=%.8f expected=%.8f\n",ggml_type_name(type),cols,r,c,actual[c*rows+r],expected);
                    check(false,"packed GPU dot oracle mismatch");
                }
            }
            std::printf("%s columns=%d passed\n",ggml_type_name(type),cols);
            ggml_backend_buffer_free(buffer);ggml_free(ctx);
        }
    }
    ggml_backend_free(backend);
}
