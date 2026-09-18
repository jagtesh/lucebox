#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "gguf.h"
#include <cmath>
#include <cstdio>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace dflash::common {

struct BonsaiMetadata {
    int block = 0;
    bool grouped_v = false;
    bool inverse_embedding = false;
    std::set<std::string> weights;
    std::map<int, std::vector<float>> signs;
};

inline bool read_bonsai_metadata(const gguf_context * g, ggml_context * tensors,
                                 BonsaiMetadata & out, std::string & error) {
    out = {};
    try {
        auto key = [&](const char * name, gguf_type type) {
            const auto id = gguf_find_key(g, name);
            if (id < 0 || gguf_get_kv_type(g, id) != type)
                throw std::runtime_error(std::string("missing or invalid ") + name);
            return id;
        };
        auto str = [&](const char * name) { return std::string(gguf_get_val_str(g, key(name, GGUF_TYPE_STRING))); };
        auto arr = [&](const char * name, gguf_type type) {
            auto id = key(name, GGUF_TYPE_ARRAY);
            if (gguf_get_arr_type(g, id) != type) throw std::runtime_error(std::string("invalid array type: ")+name);
            return id;
        };
        if (gguf_find_key(g, "prism.hadamard.version") < 0) {
            for (int64_t i=0; i<gguf_get_n_kv(g); ++i)
                if (std::string(gguf_get_key(g,i)).find("prism.hadamard.")==0)
                    throw std::runtime_error("Prism metadata without version");
            for (auto * t=ggml_get_first_tensor(tensors); t; t=ggml_get_next_tensor(tensors,t))
                if (t->type==GGML_TYPE_Q2_0 || t->type==GGML_TYPE_PQ2_0 || t->type==GGML_TYPE_PTQ1_0)
                    throw std::runtime_error("Bonsai packing without activation metadata");
            return true;
        }
        if (gguf_get_val_u32(g,key("prism.hadamard.version",GGUF_TYPE_UINT32))!=1)
            throw std::runtime_error("unsupported Prism metadata version");
        if (str("general.architecture")!="qwen35")
            throw std::runtime_error("Bonsai integration currently supports dense qwen35 only");
        const auto block=gguf_get_val_u32(g,key("prism.hadamard.block_size",GGUF_TYPE_UINT32));
        if (block<2 || block>1024 || (block&(block-1))) throw std::runtime_error("unsupported Hadamard block size");
        out.block=int(block);
        if (str("prism.hadamard.transform")!="normalized-sylvester-walsh-hadamard" ||
            str("prism.hadamard.axis")!="input-last-dimension") throw std::runtime_error("unsupported Hadamard transform/axis");
        const auto mode=str("prism.hadamard.sign_mode");
        if (mode=="explicit") {
            const auto widths=arr("prism.hadamard.sign_widths",GGUF_TYPE_INT32);
            const auto values=arr("prism.hadamard.sign_values",GGUF_TYPE_INT32);
            const auto * ww=(const int32_t *)gguf_get_arr_data(g,widths);
            const auto * vv=(const int32_t *)gguf_get_arr_data(g,values);
            const size_t count=gguf_get_arr_n(g,values);
            size_t off=0;
            if (!gguf_get_arr_n(g,widths)) throw std::runtime_error("empty explicit signs");
            for (size_t i=0; i<gguf_get_arr_n(g,widths); ++i) {
                const int width=ww[i];
                if (width<=0 || width%out.block || size_t(width)>count-off || out.signs.count(width))
                    throw std::runtime_error("invalid or duplicate sign width");
                auto & signs=out.signs[width];
                for (int j=0; j<width; ++j) {
                    const int value=vv[off++];
                    if (value!=1 && value!=-1) throw std::runtime_error("signs must be +/-1");
                    signs.push_back(float(value));
                }
            }
            if (off!=count) throw std::runtime_error("sign length mismatch");
        } else if (mode!="identity") throw std::runtime_error("unsupported sign mode");
        auto validate_tensor=[&](const std::string & name) {
            auto * t=ggml_get_tensor(tensors,name.c_str());
            if (!t || t->ne[0]%out.block || ggml_n_dims(t)!=2 ||
                (mode=="explicit" && !out.signs.count(int(t->ne[0]))))
                throw std::runtime_error("missing/incompatible transformed tensor: "+name);
        };
        const auto names=arr("prism.hadamard.weight_names",GGUF_TYPE_STRING);
        if (!gguf_get_arr_n(g,names)) throw std::runtime_error("empty folded weight list");
        const std::set<std::string> kinds={"attn_q.weight","attn_k.weight","attn_v.weight","attn_qkv.weight",
            "attn_gate.weight","attn_output.weight","ffn_gate.weight","ffn_up.weight","ffn_down.weight","ssm_out.weight"};
        for (size_t i=0; i<gguf_get_arr_n(g,names); ++i) {
            std::string name=gguf_get_arr_str(g,names,i);
            if (name!="output.weight") {
                const auto dot=name.find('.',4);
                if (name.find("blk.")!=0 || dot==std::string::npos || dot==4 ||
                    name.substr(4,dot-4).find_first_not_of("0123456789")!=std::string::npos || !kinds.count(name.substr(dot+1)))
                    throw std::runtime_error("unhandled folded tensor: "+name);
            }
            validate_tensor(name);
            if (!out.weights.insert(name).second) throw std::runtime_error("duplicate folded tensor");
        }
        if (gguf_find_key(g,"prism.hadamard.inverse_weight_names")>=0) {
            const auto inverse=arr("prism.hadamard.inverse_weight_names",GGUF_TYPE_STRING);
            for (size_t i=0; i<gguf_get_arr_n(g,inverse); ++i) {
                std::string name=gguf_get_arr_str(g,inverse,i);
                if (name!="token_embd.weight" || out.inverse_embedding) throw std::runtime_error("unhandled/duplicate inverse tensor");
                validate_tensor(name);
                out.inverse_embedding=true;
            }
        }
        if (gguf_find_key(g,"prism.hadamard.gdn_v_grouped")>=0)
            out.grouped_v=gguf_get_val_bool(g,key("prism.hadamard.gdn_v_grouped",GGUF_TYPE_BOOL));
        return true;
    } catch (const std::exception & e) {
        error=e.what(); out={}; return false;
    }
}

inline void bonsai_inverse_embedding(float * row, int width, int block, const std::vector<float> & signs) {
    GGML_ASSERT(block>0 && width%block==0 && (signs.empty() || int(signs.size())==width));
    const float scale=1.0f/std::sqrt(float(block));
    for (int start=0; start<width; start+=block) {
        for (int stride=1; stride<block; stride*=2)
            for (int base=0; base<block; base+=stride*2)
                for (int j=0; j<stride; ++j) {
                    const int a=start+base+j,b=a+stride;
                    const float x=row[a],y=row[b]; row[a]=x+y; row[b]=x-y;
                }
        for (int j=0; j<block; ++j) row[start+j]*=scale;
    }
    if (!signs.empty()) for (int i=0; i<width; ++i) row[i]*=signs[i];
}

struct BonsaiState {
    BonsaiMetadata meta;
    ggml_context * ctx=nullptr;
    ggml_backend_buffer_t buffer=nullptr;
    std::map<int,ggml_tensor *> signs;
    ~BonsaiState() {
        if (buffer) ggml_backend_buffer_free(buffer);
        if (ctx) ggml_free(ctx);
    }
    bool allocate(ggml_backend_t backend) {
        if (meta.signs.empty()) return true;
        ctx=ggml_init({(meta.signs.size()+1)*ggml_tensor_overhead(),nullptr,true});
        if (!ctx) return false;
        for (const auto & kv:meta.signs) signs[kv.first]=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,kv.first);
        buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);
        if (!buffer) return false;
        for (const auto & kv:meta.signs) ggml_backend_tensor_set(signs.at(kv.first),kv.second.data(),0,kv.second.size()*sizeof(float));
        return true;
    }
};

inline ggml_tensor * bonsai_matmul(ggml_context * ctx, const BonsaiState * state,
    ggml_tensor * weight, ggml_tensor * input, int head_dim=0, int nk=0, int rep=0) {
    if (!state || !state->meta.weights.count(ggml_get_name(weight))) return ggml_mul_mat(ctx,weight,input);
    // Reuse within this graph context only. No stale pointers survive graph rebuilds.
    char name[GGML_MAX_NAME];
    std::snprintf(name,sizeof(name),"bonsai.%p.%d.%d.%d",(void *)input,head_dim,nk,rep);
    ggml_tensor * transformed=ggml_get_tensor(ctx,name);
    if (!transformed) {
        auto * x=ggml_is_contiguous(input)?input:ggml_cont(ctx,input);
        if (state->meta.grouped_v && rep>1) {
            GGML_ASSERT(head_dim>0 && nk>0 && head_dim*nk*rep==input->ne[0]);
            x=ggml_reshape_4d(ctx,x,head_dim,nk,rep,ggml_nelements(input)/input->ne[0]);
            x=ggml_cont(ctx,ggml_permute(ctx,x,0,2,1,3));
            x=ggml_reshape_4d(ctx,x,input->ne[0],input->ne[1],input->ne[2],input->ne[3]);
        }
        const auto signs=state->signs.find(int(input->ne[0]));
        if (signs!=state->signs.end()) x=ggml_mul(ctx,x,signs->second);
        transformed=ggml_bonsai_wht(ctx,x,state->meta.block);
        ggml_set_name(transformed,name);
    }
    return ggml_mul_mat(ctx,weight,transformed);
}
} // namespace dflash::common
