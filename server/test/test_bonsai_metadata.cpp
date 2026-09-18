#include "common/bonsai.h"
#include <cstdlib>
#include <iostream>
using namespace dflash::common;
static void check(bool ok,const char * what) { if (!ok) { std::cerr<<what<<'\n'; std::exit(1); } }
int main(int argc,char **argv) {
    if (argc>1) {
        ggml_context * ctx=nullptr;
        auto * g=gguf_init_from_file(argv[1],{true,&ctx});
        check(g!=nullptr,"read GGUF");
        BonsaiMetadata m; std::string error;
        check(read_bonsai_metadata(g,ctx,m,error),error.c_str());
        std::cout<<"block="<<m.block<<" weights="<<m.weights.size()<<" sign_widths="<<m.signs.size()<<" inverse_embedding="<<m.inverse_embedding<<'\n';
        ggml_free(ctx);gguf_free(g);return 0;
    }
    for (int fault=0; fault<10; ++fault) {
        auto * ctx=ggml_init({1024*1024,nullptr,true});
        auto * w=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,8,3);ggml_set_name(w,"output.weight");
        auto * e=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,8,3);ggml_set_name(e,"token_embd.weight");
        auto * g=gguf_init_empty();
        gguf_set_val_str(g,"general.architecture",fault==1?"qwen35moe":"qwen35");
        gguf_set_val_u32(g,"prism.hadamard.version",fault==2?2:1);
        gguf_set_val_u32(g,"prism.hadamard.block_size",fault==3?3:4);
        gguf_set_val_str(g,"prism.hadamard.transform","normalized-sylvester-walsh-hadamard");
        gguf_set_val_str(g,"prism.hadamard.axis",fault==4?"wrong-axis":"input-last-dimension");
        gguf_set_val_str(g,"prism.hadamard.sign_mode","explicit");
        int32_t width=8;std::vector<int32_t> signs={1,-1,1,-1,-1,1,-1,1};
        if(fault==5) signs[3]=0;
        gguf_set_arr_data(g,"prism.hadamard.sign_widths",GGUF_TYPE_INT32,&width,fault==6?0:1);
        gguf_set_arr_data(g,"prism.hadamard.sign_values",GGUF_TYPE_INT32,signs.data(),fault==7?7:8);
        const char * names[]={fault==8?"output.missing":"output.weight"};
        gguf_set_arr_str(g,"prism.hadamard.weight_names",names,1);
        const char * inverse[]={fault==9?"output.weight":"token_embd.weight"};
        gguf_set_arr_str(g,"prism.hadamard.inverse_weight_names",inverse,1);
        BonsaiMetadata meta;std::string error;
        check(read_bonsai_metadata(g,ctx,meta,error)==(fault==0),"metadata validation mismatch");
        if(!fault) {
            check(meta.weights.count("output.weight")==1 && meta.inverse_embedding,"parsed names");
            std::vector<float> x={1,2,-3,4,5,-6,7,8}, actual=x;
            bonsai_inverse_embedding(actual.data(),8,4,meta.signs.at(8));
            for(int i=0;i<8;++i) {
                float oracle=0;
                for(int j=0;j<4;++j) {int n=(i%4)&j;const int parity=(n&1)^((n>>1)&1);oracle+=(parity?-1:1)*x[(i/4)*4+j]/2;}
                oracle*=signs[i];
                check(std::abs(oracle-actual[i])<1e-6,"embedding inverse order mismatch");
            }
        }
        gguf_free(g);ggml_free(ctx);
    }
    std::cout<<"Bonsai metadata rejection and inverse embedding oracle passed\n";
}
