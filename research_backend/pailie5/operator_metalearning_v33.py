"""V3.3 bounded operator meta-learning (mathematics, not lottery prediction).

Learn representations of a frozen 10x10 0..k-1 operation table. All candidates
must EXACTLY reconstruct the full truth table before they become research-only
capabilities. Holdout-of-cells is a model-selection diagnostic, not a lottery
out-of-sample test. No code execution of user-provided formulae.
"""
from __future__ import annotations
import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from .primitive_categories_v31 import _validated_table, _sha, GRID_A, GRID_B

VERSION='v33-meta-learner-1'
FAMILIES=('affine_orbit','piecewise_orbit','sparse_exceptions','decision_tree','quantized_linear')
FEATURES=('a','b','sum10','diff10','absdiff')
PROPERTIES=('commutative','shift_both_invariant','shift_opposite_invariant',
            'independent_of_a','independent_of_b','subdomain_associative')

def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def _bits(n):return max(1,(n-1).bit_length())
def _major(v,k):
    vals=np.bincount(np.asarray(v,dtype=np.int64),minlength=k)
    return int(np.argmax(vals))
def _axis(a,b,u,v):return (u*a+v*b)%10

def props(table):
    t,_=_validated_table(table)
    r={
        'commutative':bool(np.array_equal(t,t.T)),
        'shift_both_invariant':bool(all(int(t[a,b])==int(t[(a+1)%10,(b+1)%10]) for a in range(10) for b in range(10))),
        'shift_opposite_invariant':bool(all(int(t[a,b])==int(t[(a+1)%10,(b-1)%10]) for a in range(10) for b in range(10))),
        'independent_of_a':bool(np.all(t==t[[0],:])),
        'independent_of_b':bool(np.all(t==t[:,[0]])),
        'subdomain_associative':bool(all(int(t[int(t[a,b]),c])==int(t[a,int(t[b,c])])
                       for a in range(int(t.max())+1) for b in range(int(t.max())+1)
                       for c in range(int(t.max())+1))),
    }
    return r

def _feature(name,a,b):
    if name=='a':return a
    if name=='b':return b
    if name=='sum10':return (a+b)%10
    if name=='diff10':return (a-b)%10
    if name=='absdiff':return abs(a-b)
    raise ValueError('不支持的分支特征')

def scalar(family,p,a,b,k):
    if type(a) is not int or type(b) is not int or not (0<=a<=9 and 0<=b<=9):
        raise ValueError('必须输入0..9整数')
    if family in ('affine_orbit','sparse_exceptions'):
        if family=='sparse_exceptions':
            for x,y,z in p['exceptions']:
                if a==x and b==y:return z
        return p['orbit'][_axis(a,b,p['u'],p['v'])]
    if family=='piecewise_orbit':
        ix=(a-b)%10 if p['direction']=='difference' else (a+b)%10
        return p['orbits'][p['classes'][a]][ix]
    if family=='decision_tree':
        node=p['tree']
        while 'leaf' not in node:
            node=node['left'] if _feature(node['feature'],a,b)<=node['threshold'] else node['right']
        return node['leaf']
    if family=='quantized_linear':
        coeff=p['coefficients']
        val=coeff[0]+coeff[1]*a+coeff[2]*b+coeff[3]*abs(a-b)
        return int(np.clip(np.floor(val+0.5),0,k-1))
    raise ValueError('未知运算家族')

def _all_table(family,p,k):
    return np.asarray([[scalar(family,p,a,b,k) for b in range(10)] for a in range(10)],dtype=np.uint8)

def _validate(family,p,k):
    if family not in FAMILIES or type(p) is not dict or k not in (3,4):raise ValueError('无效家族或输出域')
    if family in ('affine_orbit','sparse_exceptions'):
        keys={'u','v','orbit'}|({'exceptions'} if family=='sparse_exceptions' else set())
        if set(p)!=keys or any(type(p[z]) is not int or not 1<=p[z]<=9 for z in ('u','v')):
            raise ValueError('非法模轨道参数')
        if type(p['orbit']) is not list or len(p['orbit'])!=10 or any(type(z) is not int or not 0<=z<k for z in p['orbit']):raise ValueError('非法轨道')
        if family=='sparse_exceptions':
            e=p['exceptions']
            if type(e) is not list or not 1<=len(e)<=6:raise ValueError('非法例外点数量')
            if (any(type(z) is not list or len(z)!=3 or any(type(x) is not int for x in z) or
                   not(0<=z[0]<=9 and 0<=z[1]<=9 and 0<=z[2]<k) for z in e) or
                   [(z[0],z[1]) for z in e]!=sorted(set((z[0],z[1]) for z in e))):raise ValueError('非法例外坐标')
    elif family=='piecewise_orbit':
        if set(p)!={'direction','classes','orbits'} or p['direction'] not in ('sum','difference'):
            raise ValueError('非法分段参数')
        cl=p['classes']; orbs=p['orbits']
        if (type(cl) is not list or len(cl)!=10 or type(orbs) is not list or not 1<=len(orbs)<=3 or
            any(type(x) is not int for x in cl) or set(cl)!=set(range(len(orbs))) or
            any(type(row) is not list or len(row)!=10 or any(type(z) is not int or not 0<=z<k for z in row) for row in orbs)):
            raise ValueError('非法分段类或轨道')
    elif family=='decision_tree':
        if set(p)!={'tree'}:raise ValueError('非法决策树字段')
        def walk(node,depth):
            if type(node) is not dict or depth>3:raise ValueError('树深超限')
            if set(node)=={'leaf'}:
                if type(node['leaf']) is not int or not 0<=node['leaf']<k:raise ValueError('非法叶节点')
                return
            if set(node)!={'feature','threshold','left','right'} or depth==3 or node['feature'] not in FEATURES or type(node['threshold']) is not int or not 0<=node['threshold']<=8:raise ValueError('非法决策树节点')
            walk(node['left'],depth+1);walk(node['right'],depth+1)
        walk(p['tree'],0)
    else:
        if set(p)!={'coefficients'} or type(p['coefficients']) is not list or len(p['coefficients'])!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>20 for v in p['coefficients']):raise ValueError('非法连续系数')

def code_bits(family,p,k):
    if family=='affine_orbit':return 24+8+10*_bits(k)
    if family=='sparse_exceptions':return 24+8+10*_bits(k)+len(p['exceptions'])*(7+_bits(k))
    if family=='piecewise_orbit':return 24+1+10*_bits(len(p['orbits']))+10*len(p['orbits'])*_bits(k)
    if family=='quantized_linear':return 24+4*26 # 26-bit signed fixed-point coefficients at 1e-6 resolution
    def tree_bits(node):
        return _bits(k) if 'leaf' in node else 13+tree_bits(node['left'])+tree_bits(node['right'])
    return 24+tree_bits(p['tree'])

@dataclass(frozen=True)
class LearnedOperator:
    id:str; family:str; payload:dict; levels:int; source_sha256:str
    description_bits:int; source_id:str; properties:dict; version:str=VERSION
    def __post_init__(self):
        _validate(self.family,self.payload,self.levels)
        if self.version!=VERSION or type(self.source_id) is not str or not 1<=len(self.source_id)<=1024:raise ValueError('版本或来源非法')
        if self.description_bits!=code_bits(self.family,self.payload,self.levels) or self.description_bits>=100*_bits(self.levels):raise ValueError('无压缩优势')
        if set(self.properties)!=set(PROPERTIES) or any(type(v) is not bool for v in self.properties.values()):raise ValueError('性质声明非法')
        if type(self.source_sha256) is not str or len(self.source_sha256)!=64 or any(c not in '0123456789abcdef' for c in self.source_sha256):raise ValueError('源指纹非法')
        signature={'family':self.family,'payload':self.payload,'levels':self.levels,'sha':self.source_sha256,'version':VERSION}
        if self.id!='pl5.v33.'+hashlib.sha256(canon(signature).encode()).hexdigest()[:24]:raise ValueError('算子ID校验失败')
    def call(self,a,b):return scalar(self.family,self.payload,a,b,self.levels)
    def vector(self,a,b):
        x,y=np.asarray(a),np.asarray(b)
        if (x.shape!=y.shape or not np.issubdtype(x.dtype,np.integer) or not np.issubdtype(y.dtype,np.integer)
            or np.any(x<0) or np.any(x>9) or np.any(y<0) or np.any(y>9)):
            raise ValueError('必须同形整数数组，数字在0..9')
        return np.asarray([self.call(int(u),int(v)) for u,v in zip(x.flat,y.flat)],dtype=np.uint8).reshape(x.shape)
    def table(self):return self.vector(GRID_A,GRID_B)
    def certify(self):
        table=self.table()
        if _sha(table)!=self.source_sha256:raise ValueError('源数学表指纹不一致')
        if props(table)!=self.properties:raise ValueError('数学性质与实际不一致')
        for a in range(10):
            for b in range(10):
                if self.call(a,b)!=int(table[a,b]):raise ValueError('批量与标量计算不一致')
        return {'checked_pairs':100,'sha256':self.source_sha256,'scalar_vector_agree':True,'exact':True}
    def card(self):
        return {'id':self.id,'version':VERSION,'family':self.family,'parameters':self.payload,
                'learnable_layers':['structure','parameters','property_requirements'],
                'property_checks':self.properties,'proof':self.certify(),
                'description_bits_proxy':self.description_bits,'raw_bits_proxy':100*_bits(self.levels),
                'source_id':self.source_id,'status':'research_only','predictive_advantage':'unverified'}


def _affine(t,mask,k,top=3):
    a,b=GRID_A,GRID_B
    results=[]
    for u in range(1,10):
        for v in range(1,10):
            idx=_axis(a,b,u,v)
            orbit=[]
            for z in range(10):
                vals=t[(idx==z)&mask]
                orbit.append(_major(vals,k) if len(vals) else 0)
            p={'u':u,'v':v,'orbit':orbit}
            pred=np.asarray(orbit)[idx]
            err=int(np.count_nonzero(pred[mask]!=t[mask]))
            results.append((err,code_bits('affine_orbit',p,k),p))
    results.sort(key=lambda z:(z[0],z[1],z[2]['u'],z[2]['v']))
    return [v[2] for v in results[:top]]

def _piecewise(t,mask,k):
    ret=[]
    for direction in ('difference','sum'):
        # Profile indexed by orbit position (each physical row is shifted).
        order=np.array([[(a-j)%10 if direction=='difference' else (j-a)%10 for j in range(10)] for a in range(10)])
        z=t[np.arange(10)[:,None],order]
        m=mask[np.arange(10)[:,None],order]
        for count in (1,2,3):
            seeds=[0]
            while len(seeds)<count:
                idx=max((i for i in range(10) if i not in seeds),key=lambda i:
                        (min(int(np.count_nonzero((z[i]!=z[s])&m[i]&m[s])) for s in seeds),-i))
                seeds.append(idx)
            centers=[z[i].copy() for i in seeds]
            classes=np.zeros(10,dtype=int)
            for _ in range(8):
                for i in range(10):
                    classes[i]=min(range(count),key=lambda c:(int(np.count_nonzero((z[i]!=centers[c])&m[i])),c))
                for c in range(count):
                    for j in range(10):
                        observed=z[(classes==c)&m[:,j],j]
                        centers[c][j]=_major(observed,k) if len(observed) else int(centers[c][j])
            used=sorted(set(int(x) for x in classes))
            mapper={c:i for i,c in enumerate(used)}
            p={'direction':direction,'classes':[mapper[int(x)] for x in classes],
               'orbits':[list(map(int,centers[c])) for c in used]}
            ret.append(p)
    return ret

def _grow_tree(t,mask,k,maxdepth=3):
    aa,bb=GRID_A.ravel(),GRID_B.ravel()
    y=t.ravel(); m=mask.ravel()
    def make(ids,depth):
        vals=y[ids&m]
        label=_major(vals,k) if len(vals) else 0
        if depth==maxdepth or len(vals)==0 or np.all(vals==vals[0]):return {'leaf':label}
        baseline=len(vals)-int(np.max(np.bincount(vals,minlength=k)))
        best=None
        for f in FEATURES:
            fvals=np.asarray([_feature(f,int(a),int(b)) for a,b in zip(aa,bb)])
            for threshold in range(9):
                left=ids&(fvals<=threshold);right=ids&(fvals>threshold)
                lv=y[left&m];rv=y[right&m]
                if len(lv)==0 or len(rv)==0:continue
                error=(len(lv)-np.max(np.bincount(lv,minlength=k)))+(len(rv)-np.max(np.bincount(rv,minlength=k)))
                gain=baseline-int(error)
                if gain>0 and (best is None or gain>best[0]):best=(gain,f,threshold,left,right)
        if best is None:return {'leaf':label}
        return {'feature':best[1],'threshold':best[2],
                'left':make(best[3],depth+1),'right':make(best[4],depth+1)}
    return {'tree':make(np.ones(100,dtype=bool),0)}

def _linear(t,mask,k):
    """Learn continuous coefficients by bounded linear feasibility and then quantize.

    A minimum 0.01 bin-boundary margin makes 1e-6 storage rounding safe.
    If the model is inconsistent, revert to bounded least squares.
    """
    a,b=GRID_A,GRID_B
    X=np.column_stack([np.ones(100),a.ravel(),b.ravel(),np.abs(a-b).ravel()])
    y=t.ravel().astype(int)
    rows=X[mask.ravel()]
    targets=y[mask.ravel()]
    constraints=[];bounds=[]
    for row,label in zip(rows,targets):
        if label<k-1:
            constraints.append(row);bounds.append(label+0.49)
        if label>0:
            constraints.append(-row);bounds.append(-(label-0.49))
    res=linprog(np.zeros(4),A_ub=np.asarray(constraints),b_ub=np.asarray(bounds),
                bounds=[(-20,20)]*4,method='highs')
    if res.success:
        coeff=np.asarray(res.x)
    else:
        try:coeff=np.linalg.lstsq(rows,targets,rcond=None)[0]
        except np.linalg.LinAlgError:coeff=np.zeros(4)
    best=None
    for scale in (0.9,1.0,1.1):
        for bias in (-0.1,0,0.1):
            d=np.asarray(coeff*scale).copy();d[0]+=bias
            d=np.round(d,6)
            if np.any(np.abs(d)>20):continue
            pred=np.clip(np.floor(X@d+0.5),0,k-1).astype(int)
            error=int(np.count_nonzero((pred!=y)&mask.ravel()))
            p={'coefficients':[float(x) for x in d]}
            cand=(error,sum(abs(v) for v in p['coefficients']),p)
            if best is None or cand[:2]<best[:2]:best=cand
    return best[2]

def _candidates(t,mask,k,max_exceptions):
    affine=_affine(t,mask,k,top=5)
    out=[('affine_orbit',p) for p in affine]
    out.extend(('piecewise_orbit',p) for p in _piecewise(t,mask,k))
    for base in affine:
        pred=_all_table('affine_orbit',base,k)
        exception_coords=np.argwhere(mask&(pred!=t))
        if 1<=len(exception_coords)<=max_exceptions:
            p={**base,'exceptions':[[int(a),int(b),int(t[a,b])] for a,b in exception_coords]}
            out.append(('sparse_exceptions',p))
    out.append(('decision_tree',_grow_tree(t,mask,k)))
    out.append(('quantized_linear',_linear(t,mask,k)))
    return [(f,p) for f,p in out if code_bits(f,p,k)<100*_bits(k)]

def learn(table,*,source_id='math_fixture',seed=20261102,holdout_cells=20,
          max_exceptions=6,required_properties=(),maximum=5):
    t,k=_validated_table(table)
    if (type(seed) is not int or not 0<=seed<2**32 or type(holdout_cells) is not int or not 5<=holdout_cells<=35
        or type(max_exceptions) is not int or not 0<=max_exceptions<=6
        or type(maximum) is not int or not 1<=maximum<=10
        or type(source_id) is not str or not 1<=len(source_id)<=1024):raise ValueError('学习参数超限')
    if not isinstance(required_properties,(tuple,list)) or any(type(p) is not str or p not in PROPERTIES for p in required_properties):raise ValueError('非法性质要求')
    claims=props(t)
    unmet=[p for p in required_properties if not claims[p]]
    if unmet:return {'version':VERSION,'status':'rejected_property_requirements','unmet':unmet,'properties':claims,'abilities':[],'trials':[]}
    rng=np.random.default_rng(seed); m=np.ones(100,dtype=bool);m[rng.choice(100,size=holdout_cells,replace=False)]=False
    train=m.reshape(10,10)
    trials=[]
    for fam,p in _candidates(t,train,k,max_exceptions):
        pred=_all_table(fam,p,k)
        trials.append({'family':fam,'train_errors':int(np.count_nonzero((pred!=t)&train)),
                       'cell_holdout_errors':int(np.count_nonzero((pred!=t)&~train)),
                       'code_bits':code_bits(fam,p,k)})
    trials.sort(key=lambda z:(z['cell_holdout_errors'],z['train_errors'],z['code_bits'],z['family']))
    valid=[]; seen=set()
    for fam,p in _candidates(t,np.ones((10,10),dtype=bool),k,max_exceptions):
        _validate(fam,p,k)
        reconstructed=_all_table(fam,p,k)
        if not np.array_equal(reconstructed,t):continue
        bits=code_bits(fam,p,k)
        sig={'family':fam,'payload':p,'levels':k,'sha':_sha(t),'version':VERSION}
        identifier='pl5.v33.'+hashlib.sha256(canon(sig).encode()).hexdigest()[:24]
        if identifier in seen:continue
        seen.add(identifier)
        op=LearnedOperator(identifier,fam,p,k,_sha(t),bits,source_id,claims)
        op.certify();valid.append(op)
    valid.sort(key=lambda op:(op.description_bits,op.family,op.id))
    abilities=valid[:maximum]
    return {'version':VERSION,'status':'exact_compressed' if abilities else 'no_exact_compressed_representation',
            'source_sha256':_sha(t),'properties':claims,
            'raw_bits_proxy':100*_bits(k),'cell_holdout_count':holdout_cells,
            'trials':trials,'abilities':abilities,'predictive_advantage':'NOT_ESTABLISHED',
            'holdout_meaning':'Held-out TABLE CELLS, not lottery future draws'}

class MetaRegistry:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS operator_v33 (id TEXT PRIMARY KEY, record TEXT NOT NULL, hash TEXT NOT NULL)')
    def register(self,ability):
        ability.certify();rec=canon(ability.__dict__);digest=hashlib.sha256(rec.encode()).hexdigest()
        with sqlite3.connect(self.path) as db:
            cur=db.execute('INSERT OR IGNORE INTO operator_v33 VALUES (?,?,?)',(ability.id,rec,digest))
            if cur.rowcount==0:
                self.get(ability.id)
            return cur.rowcount==1
    def get(self,identifier):
        with sqlite3.connect(self.path) as db:row=db.execute('SELECT record,hash FROM operator_v33 WHERE id=?',(identifier,)).fetchone()
        if row is None:raise KeyError(identifier)
        if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('能力注册记录篡改')
        item=LearnedOperator(**json.loads(row[0]));item.certify();return item
    def summary(self):
        with sqlite3.connect(self.path) as db:ids=[row[0] for row in db.execute('SELECT id FROM operator_v33 ORDER BY id')]
        return [self.get(x).card() for x in ids]

def fixtures(seed=9):
    a,b=GRID_A,GRID_B
    return {
        'affine_modular':np.array([0,2,1,0,2,1,1,0,2,1],dtype=np.uint8)[(3*a+2*b)%10],
        'two_state_piecewise':np.where(a<5, np.array([0,1,2,1,0,2,0,1,2,0])[(a-b)%10],np.array([2,2,1,0,1,2,0,2,1,0])[(a-b)%10]).astype(np.uint8),
        'sparse_exception':_make_sparse(a,b),
        'small_tree':np.where(a<=4,np.where(b<=3,0,1),2).astype(np.uint8),
        'linear_quantized':np.clip(np.floor(.3*a+.15*b+.5),0,3).astype(np.uint8),
        'unstructured_random':np.random.default_rng(seed).integers(0,3,size=(10,10),dtype=np.uint8),
    }
def _make_sparse(a,b):
    t=np.array([0,2,1,0,2,1,1,0,2,1],dtype=np.uint8)[(3*a+2*b)%10].copy()
    t[1,7]=(int(t[1,7])+1)%3;t[8,2]=(int(t[8,2])+1)%3
    return t
