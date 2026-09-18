// Numerical qualification utility: fixed tokens -> final vocabulary logits.
// No sampling or throughput measurement. Compare chunked/incremental execution
// and Prism's independent runtime using exactly the same input IDs.
#include "internal.h"
#include "qwen35/graph_builders.h"
#include "qwen35/prefill_helpers.h"
#include "ggml-cuda.h"
#include <algorithm>
#include <fstream>
#include <iostream>
using namespace dflash::common;
static void require(bool ok,const char * message) {
    if (!ok) { std::cerr<<message<<": "<<dflash27b_last_error()<<'\n'; std::exit(1); }
}
int main(int argc,char **argv) {
    if(argc!=5) {std::cerr<<"model tokens.txt chunk-size logits.f32\n";return 2;}
    std::ifstream f(argv[2]);std::vector<int32_t> tokens;int32_t id;
    while(f>>id)tokens.push_back(id);
    const int chunk=std::stoi(argv[3]);
    require(!tokens.empty() && tokens.size()<=256 && chunk>0 && chunk<=256,"input bounds");
    auto backend=ggml_backend_cuda_init(0);require(backend!=nullptr,"GPU init");
    TargetWeights w;require(load_target_gguf(argv[1],backend,w),"load target");
    TargetCache cache;require(create_target_cache(w,512,0,backend,cache,false,0,false,1,false,GGML_TYPE_Q8_0,GGML_TYPE_Q8_0),"create cache");
    StepGraph sg;
    for(int start=0;start<int(tokens.size());start+=chunk) {
        const int n=std::min(chunk,int(tokens.size())-start);
        require(build_target_step(sg,w,cache,backend,start,n,true,false,false,0,1),"build graph");
        std::vector<float> embeds(w.n_embd*n);
        require(w.embedder.embed(tokens.data()+start,n,embeds.data()),"embed");
        ggml_backend_tensor_set(sg.inp_embed,embeds.data(),0,embeds.size()*sizeof(float));
        std::vector<int32_t> positions(4*n);
        fill_qwen35_mrope_positions(positions.data(),start,n);
        ggml_backend_tensor_set(sg.positions,positions.data(),0,positions.size()*sizeof(int32_t));
        upload_qwen35_causal_mask(sg.attn_mask,start,n,KQ_MASK_PAD);
        require(ggml_backend_graph_compute(backend,sg.gf)==GGML_STATUS_SUCCESS,"compute");
    }
    std::vector<float> logits(w.n_vocab);
    ggml_backend_tensor_get(sg.logits,logits.data(),0,logits.size()*sizeof(float));
    for(float value:logits)require(std::isfinite(value),"nonfinite logits");
    std::ofstream out(argv[4],std::ios::binary);out.write((const char *)logits.data(),logits.size()*sizeof(float));
    require(bool(out),"write logits");
    std::cout<<"vocab="<<w.n_vocab<<" argmax="<<(std::max_element(logits.begin(),logits.end())-logits.begin())<<'\n';
    step_graph_free(sg);free_target_cache(cache);free_target_weights(w);ggml_backend_free(backend);
}
