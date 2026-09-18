// Build separately against the pinned Prism llama library, never Lucebox GGML.
#include "llama.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <vector>
int main(int argc,char **argv) {
    if(argc!=5)return 2;
    std::ifstream f(argv[2]);std::vector<llama_token> tokens;llama_token id;
    while(f>>id)tokens.push_back(id);
    const int chunk=std::stoi(argv[3]);
    if(tokens.empty() || tokens.size()>256 || chunk<=0 || chunk>256)return 2;
    llama_backend_init();
    auto mp=llama_model_default_params();mp.n_gpu_layers=99;
    auto * model=llama_model_load_from_file(argv[1],mp);if(!model)return 1;
    auto cp=llama_context_default_params();cp.n_ctx=512;cp.n_batch=256;cp.n_ubatch=256;cp.n_seq_max=1;
    cp.type_k=GGML_TYPE_Q8_0;cp.type_v=GGML_TYPE_Q8_0;cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_ENABLED;
    auto * ctx=llama_init_from_model(model,cp);if(!ctx)return 1;
    auto batch=llama_batch_init(256,0,1);
    for(int start=0;start<int(tokens.size());start+=chunk) {
        batch.n_tokens=std::min(chunk,int(tokens.size())-start);
        for(int i=0;i<batch.n_tokens;++i) {
            batch.token[i]=tokens[start+i];batch.pos[i]=start+i;batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;
            batch.logits[i]=(i==batch.n_tokens-1);
        }
        if(llama_decode(ctx,batch))return 1;
    }
    const int n=llama_vocab_n_tokens(llama_model_get_vocab(model));
    const float * logits=llama_get_logits_ith(ctx,-1);
    for(int i=0;i<n;++i)if(!std::isfinite(logits[i]))return 1;
    std::ofstream out(argv[4],std::ios::binary);out.write((const char *)logits,n*sizeof(float));if(!out)return 1;
    std::cout<<"vocab="<<n<<" argmax="<<(std::max_element(logits,logits+n)-logits)<<'\n';
    llama_batch_free(batch);llama_free(ctx);llama_model_free(model);llama_backend_free();
}
