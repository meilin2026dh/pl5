"""V3.4 research-only Streamlit. Input uploads are never executed."""
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pailie5.parameter_hub_v34 import inventory,fit_step_constraint,fit_lift_moduli
from pailie5.operator_metalearning_v33 import fixtures,learn
from pailie5.transfer_evolution_v34 import transfer,public_result

st.set_page_config(page_title='PL5 V3.4 · 参数注册与迁移',layout='wide')
st.title('PL5 V3.4 · 统一参数注册与跨算子迁移')
st.caption('科研沙箱：参数登记≠全部可学习；数学证明≠彩票预测能力；不会自动改变ESSE生产规则。')
a,b,c=st.tabs(['可学习参数清单','历史数据：参数学习','数学表：迁移与进化'])
with a:
    item=inventory()
    st.dataframe(pd.DataFrame(item['parameters']),hide_index=True,use_container_width=True)
    st.json(item['counts'])
with b:
    st.caption('仅支持用户核实的、按开奖时间由早到晚排列的CSV；至少180期。未来测试区间不参与模型选择。')
    f=st.file_uploader('上传历史CSV',type='csv')
    method=st.selectbox('训练项目',['V2.7 步长阈值与约束权重','V2.8 高维Lift两个模参数'])
    first=st.selectbox('第一位置（0表示万位）',list(range(5)),index=0) if method.startswith('V2.8') else 0
    second=st.selectbox('第二位置',list(range(5)),index=1) if method.startswith('V2.8') else 1
    if st.button('执行时间切分实验',type='primary'):
        try:
            if f is None:raise ValueError('请先提供CSV')
            if f.size>3_000_000:raise ValueError('CSV过大')
            from research_v24 import read_history
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'official.csv';p.write_bytes(f.getvalue());hist=[int(x) for x in read_history(p)]
            if method.startswith('V2.7'):res=fit_step_constraint(hist)
            else:res=fit_lift_moduli(hist,{'op':'digit','pos':first},{'op':'digit','pos':second})
            st.json({k:v for k,v in res.items() if k not in ('threshold_candidates','trials')})
            st.dataframe(pd.DataFrame(res.get('threshold_candidates',res.get('trials',[]))),use_container_width=True)
            st.download_button('下载研究报告',json.dumps(res,ensure_ascii=False,indent=2),'v34_parameter_result.json')
        except (ValueError,KeyError,TypeError,UnicodeError) as e:st.error(str(e))
with c:
    f=st.selectbox('原始数学运算表',list(fixtures()))
    m=st.slider('修改单元个数',1,6,2)
    if st.button('基于原算子迁移学习'):
        try:
            base=learn(fixtures()[f],source_id='synth_seed')['abilities']
            if not base:raise ValueError('原始表没有找到可压缩算子，请更换演示表')
            op=next((x for x in base if x.family=='affine_orbit'),base[0])
            target=op.table().copy()
            for j in range(m):
                x=(j*3+1)%10;y=(j*5+2)%10
                target[x,y]=(int(target[x,y])+1)%op.levels
            result=public_result(transfer(op,target))
            st.json(result)
            st.warning('这里的留出是数学表单元，不是未来彩票开奖。')
        except (ValueError,TypeError) as e:st.error(str(e))
