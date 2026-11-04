"""Loopback-only JSON bridge service; not publicly exposed, no model code execution."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pailie5.integration_bridge import ContractError, SCHEMA, run_bridge
from pailie5.algorithm_registry_v14 import Registry
from status_v151 import status
from pailie5.capability_network import CapabilityRegistry
from pailie5.ability_lab_v19 import AbilityLab
from autoresearch.paper_factory_v20 import PaperFactory
from autoresearch.council_v21 import ResearchCouncil
from autoresearch.collaboration_v22 import V22ResearchLab
import sqlite3
from pailie5.nine_spaces_v24 import capability_cards, Rule as V24Rule, TemporalSpec, compose_temporal
from pailie5.representation_v25 import propose as propose_spaces_v25, audit as audit_spaces_v25, study as study_spaces_v25
from pailie5.representation_registry_v25 import status as representation_v25_status
from pailie5.highdim_v26 import capabilities as hdse_v26_capabilities, proposals as hdse_v26_proposals, study as hdse_v26_study
from pailie5.hdse_registry_v26 import status as hdse_v26_status
from pailie5.bcse_v27 import capabilities as bcse_v27_capabilities, study as bcse_v27_study
from pailie5.autolift_v28 import invent as autolift_v28_invent, study as autolift_v28_study

from pailie5.operator_metalearning_v33 import learn as metalearn_v33, FAMILIES as v33_families, PROPERTIES as v33_properties

from pailie5.parameter_hub_v34 import inventory as parameter_hub_inventory, fit_step_constraint as hub_fit_step, fit_lift_moduli as hub_fit_lift
MAX_BODY = 700_000
class BridgeHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == '/api/esse/parameters-v34/catalog':
            return self._json(200,parameter_hub_inventory())
        if self.path == '/api/esse/meta-v33/capabilities':
            return self._json(200,{'version':'v3.3','families':list(v33_families),
                    'properties':list(v33_properties),'status':'research_only',
                    'official_prediction_advantage':'unverified'})
        if self.path == "/api/esse/autolift-v28/capabilities":
            return self._json(200, {'version':'2.8.0','status':'research_only',
                'cards':[x.card() for x in autolift_v28_invent(maximum=12)],
                'promotion':'manual_approval_only','prediction_advantage':'unverified'})
        if self.path == "/api/esse/bcse-v27/capabilities":
            return self._json(200,{"version":"bcse-v27","status":"research_only",
                "constraints":bcse_v27_capabilities(),"prediction_advantage":"UNVERIFIED"})
        if self.path == "/api/esse/hdse-v26/registry":
            return self._json(200,hdse_v26_status(os.environ.get("PL5_HDSE_DB","runtime/hdse_v26.sqlite")))
        if self.path == "/api/esse/hdse-v26/capabilities":
            return self._json(200, {"version":"2.6.0","status":"research_only",
                "capabilities":hdse_v26_capabilities(),"predictive_advantage":"unverified"})
        if self.path == "/api/esse/spaces-v25/capabilities":
            inventory=representation_v25_status(os.environ.get('PL5_REPRESENTATION_DB','runtime/representation_v25.sqlite'))
            return self._json(200, {'version':'v2.5','inventory':inventory,'operators':['weighted_mod','pair_sum_mod',
                'signed_difference','cross_term_mod','combination_mod','affine_relabel'],
                'status':'research_only','automatic_promotion':False,
                'predictive_advantage':'unverified'})
        if self.path == "/api/esse/spaces-v24/capabilities":
            return self._json(200, {"version":"v2.4", "status":"exploratory",
                "capabilities":capability_cards(),"predictive_advantage":"UNVERIFIED"})
        if self.path == "/api/esse/research-v22":
            path=os.environ.get('PL5_PAPER_FACTORY_DB')
            if not path or not os.path.isfile(path):
                return self._json(200, {'version':'2.2.0','status':'not_initialized',
                                        'projects':[],'total_generated':0,'total_evaluated':0,
                                        'automatic_execution':False,'automatic_release':False})
            try:
                with sqlite3.connect(path) as db:
                    lab=V22ResearchLab(db)
                    rows=db.execute('SELECT project_id FROM v22_generated ORDER BY created_at DESC LIMIT 25').fetchall()
                    items=[lab.status(row[0]) for row in rows]
                    generated=db.execute('SELECT COUNT(*) FROM v22_generated').fetchone()[0]
                    evaluated=db.execute('SELECT COUNT(*) FROM v22_evaluations').fetchone()[0]
                return self._json(200, {'version':'2.2.0','status':'research_only',
                                        'projects':items,'total_generated':generated,'total_evaluated':evaluated,
                                        'automatic_execution':False,'automatic_release':False})
            except (ValueError,sqlite3.DatabaseError):
                return self._json(503,{'error':'v22_research_invalid','message':'研究记录校验失败'})
        if self.path == "/api/esse/research-council":
            path=os.environ.get('PL5_PAPER_FACTORY_DB')
            if not path or not os.path.isfile(path):
                return self._json(200, {'version':'2.1.0','status':'not_initialized',
                    'total':0,'projects':[], 'automatic_execution':False,'auto_publish':False})
            try:
                with sqlite3.connect(path) as db:
                    items=ResearchCouncil(db).status(limit=25)
                return self._json(200,{'status':'experimental_only',**items})
            except (ValueError,sqlite3.DatabaseError):
                return self._json(503,{'error':'research_registry_invalid','message':'研究库校验失败，停止读取'})
        if self.path == "/api/esse/paper-factory":
            path=os.environ.get('PL5_PAPER_FACTORY_DB')
            if not path or not os.path.isfile(path):
                return self._json(200,{'version':'2.0','status':'not_initialized',
                                       'total_blueprints':0,'total_studies':0,'cards':[],
                                       'approved_predictive_algorithms':0})
            with sqlite3.connect(path) as db:
                items=PaperFactory(db).status(limit=25)
            return self._json(200,{'status':'experimental_only',**items})
        if self.path == "/api/esse/ability-lab":
            path=os.environ.get('PL5_AAN_DB')
            if not path or not os.path.isfile(path):
                return self._json(200,{'status':'not_initialized','total':0,'proposals':[],
                                       'prediction_advantage':'UNVERIFIED'})
            with AbilityLab(path) as lab:
                state=lab.latest(limit=24)
            return self._json(200,{'status':'experimental_only',**state})
        if self.path == "/api/esse/capabilities":
            path=os.environ.get('PL5_AAN_DB')
            if not path or not os.path.isfile(path):
                return self._json(200, {'status':'not_initialized','count':0,'nodes':[],
                    'message':'请先运行 capability_cli_v18.py bootstrap/grow'})
            db=CapabilityRegistry(path)
            try:
                graph=db.graph()
                return self._json(200, {'status':'experimental_only','count':graph['count'],
                        'nodes':graph['nodes'][:100], 'edges':graph['edges'][:200],
                        'truncated':graph['count']>100,
                        'predictive_advantage':'NOT_ESTABLISHED'})
            finally: db.close()
        if self.path == "/api/esse/status":
            return self._json(200, status(registry_path=os.environ.get('PL5_REGISTRY_PATH'),
                official_cache_path=os.environ.get('PL5_OFFICIAL_CACHE'),
                forward_db_path=os.environ.get('PL5_FORWARD_DB')))
        if self.path != "/api/esse/health":
            return self._json(404,{"error":"not_found"})
        return self._json(200,{"ok":True,"schema":SCHEMA,"status":"research_only"})
    def do_POST(self):
        if self.path == '/api/esse/parameters-v34/fit':
            if 'application/json' not in self.headers.get('Content-Type',''):
                return self._json(415,{'error':'json_required'})
            size=self.headers.get('Content-Length','')
            if not size.isdigit() or not 1<=int(size)<=100_000:
                return self._json(413,{'error':'invalid_length'})
            try:
                payload=json.loads(self.rfile.read(int(size)))
                if type(payload) is not dict or set(payload)-{'kind','history','first_pos','second_pos'}:
                    raise ValueError('未知参数或请求结构无效')
                if payload.get('kind') not in ('step','lift'):
                    raise ValueError('仅支持step/lift科研适配')
                draws=payload.get('history')
                if type(draws) is not list or not 180<=len(draws)<=1800:
                    raise ValueError('历史必须是180..1800个0..99999整数')
                if payload['kind']=='step':
                    if set(payload)-{'kind','history'}:raise ValueError('step不接受位置参数')
                    output=hub_fit_step(draws)
                else:
                    p=payload.get('first_pos',0);q=payload.get('second_pos',1)
                    if type(p) is not int or type(q) is not int or not(0<=p<=4 and 0<=q<=4):
                        raise ValueError('位置参数应为0..4整数')
                    output=hub_fit_lift(draws,{'op':'digit','pos':p},{'op':'digit','pos':q})
                    # Keep HTTP response bounded and disclose summary counts.
                    output['trial_count']=len(output.pop('trials'))
                return self._json(200,output)
            except (ValueError,TypeError,KeyError) as exc:
                return self._json(422,{'error':'validation','message':str(exc)[:320]})
            except Exception:
                return self._json(500,{'error':'internal','message':'参数训练失败'})
        if self.path == '/api/esse/meta-v33/learn':
            if 'application/json' not in self.headers.get('Content-Type',''):
                return self._json(415,{'error':'json_required'})
            size=self.headers.get('Content-Length','')
            if not size.isdigit() or not 1<=int(size)<=200_000:
                return self._json(413,{'error':'invalid_length'})
            try:
                payload=json.loads(self.rfile.read(int(size)))
                if type(payload) is not dict or set(payload)-{'table','seed','required_properties','maximum'}:
                    raise ValueError('字段不合法')
                import numpy as np
                t=payload['table']
                if type(t) is not list or len(t)!=10 or any(type(row) is not list or len(row)!=10 or any(type(v) is not int for v in row) for row in t):
                    raise ValueError('输入必须是10x10整数表')
                r=metalearn_v33(np.asarray(t),seed=payload.get('seed',20261102),
                      required_properties=payload.get('required_properties',[]),
                      maximum=payload.get('maximum',5),source_id='api_user_table')
                r['abilities']=[ability.card() for ability in r['abilities']]
                return self._json(200,r)
            except (ValueError,TypeError,KeyError) as exc:
                return self._json(422,{'error':'validation','message':str(exc)[:320]})
            except Exception:
                return self._json(500,{'error':'internal','message':'元学习研究计算失败'})
        if self.path == "/api/esse/autolift-v28/research":
            if 'application/json' not in self.headers.get('Content-Type',''):
                return self._json(415, {'error':'json_required'})
            raw=self.headers.get('Content-Length','')
            if not raw.isdigit() or not 1<=int(raw)<=MAX_BODY:
                return self._json(413, {'error':'invalid_length'})
            try:
                payload=json.loads(self.rfile.read(int(raw)))
                if not isinstance(payload,dict):raise ValueError('JSON应为对象')
                fields={'history','seed','maximum','validation_periods','test_periods','budget','alpha','gate_alpha'}
                if set(payload)-fields:raise ValueError('包含未知字段')
                if 'history' not in payload:
                    return self._json(200, {'cards':[v.card() for v in autolift_v28_invent(maximum=8)],'status':'research_only'})
                if not isinstance(payload['history'],list) or len(payload['history'])>2000:
                    raise ValueError('HTTP最多2000期历史')
                # User-controlled HTTP calls never write the local research registry.
                result=autolift_v28_study(**payload)
                result['operator_cards']=result['operator_cards'][:8]
                result['experiments']=result['experiments'][:20]
                result['experimental_top_k']=result['experimental_top_k'][:30]
                result['equal_budget_random_control']=result['equal_budget_random_control'][:30]
                return self._json(200,result)
            except (ValueError,TypeError,KeyError) as exc:
                return self._json(422,{'error':'validation','message':str(exc)[:320]})
            except Exception:
                return self._json(500,{'error':'internal','message':'自主升维科研失败'})
        if self.path == "/api/esse/bcse-v27/research":
            if "application/json" not in self.headers.get("Content-Type", ""):
                return self._json(415,{"error":"json_required"})
            size=self.headers.get("Content-Length", "")
            if not size.isdigit() or not 1<=int(size)<=MAX_BODY:
                return self._json(413,{"error":"invalid_length"})
            try:
                body=json.loads(self.rfile.read(int(size)))
                if not isinstance(body,dict):raise ValueError('需要JSON对象')
                keys={'history','constraints','seed','test_periods','validation_periods',
                      'budget','dirichlet_alpha','null_trials'}
                if set(body)-keys:raise ValueError('存在未知请求字段')
                if 'history' not in body:
                    return self._json(200,{'version':'bcse-v27','status':'research_hypotheses_only',
                         'capabilities':bcse_v27_capabilities()})
                if not isinstance(body['history'],list) or len(body['history'])>2000:
                    raise ValueError('HTTP历史最多2000期')
                if body.get('null_trials',0)>1 or type(body.get('null_trials',0)) is not int:
                    raise ValueError('HTTP随机模拟最多1次')
                result=bcse_v27_study(**body)
                return self._json(200,result)
            except (ValueError,TypeError,KeyError) as e:
                return self._json(422,{'error':'validation','message':str(e)[:320]})
            except Exception:
                return self._json(500,{'error':'internal','message':'BCSE科研计算失败'})
        if self.path == "/api/esse/hdse-v26/research":
            if "application/json" not in self.headers.get("Content-Type", ""):
                return self._json(415,{"error":"json_required"})
            content_size=self.headers.get('Content-Length','')
            if not content_size.isdigit() or not 1<=int(content_size)<=MAX_BODY:
                return self._json(413,{"error":"invalid_length"})
            try:
                payload=json.loads(self.rfile.read(int(content_size)))
                if not isinstance(payload,dict):raise ValueError('必须传JSON对象')
                seed=payload.get('seed',20261102)
                maximum=payload.get('maximum',7)
                budget=payload.get('budget',100)
                test_periods=payload.get('test_periods',30)
                null_trials=payload.get('null_trials',0)
                if (type(seed) is not int or not 0<=seed<2**32 or
                    type(maximum) is not int or not 1<=maximum<=12 or
                    type(budget) is not int or not 1<=budget<=100 or
                    type(test_periods) is not int or not 20<=test_periods<=200 or
                    type(null_trials) is not int or not 0<=null_trials<=2):
                    raise ValueError('参数范围不合法')
                history=payload.get('history')
                if history is None:
                    result={'version':'hdse-v26','status':'research_hypotheses_only',
                            'proposals':[s.capability() for s in hdse_v26_proposals(seed,maximum)]}
                else:
                    if not isinstance(history,list) or len(history)>2000:
                        raise ValueError('HTTP历史最多2000期')
                    result=hdse_v26_study(history,seed=seed,maximum=maximum,budget=budget,
                                            test_periods=test_periods,null_trials=null_trials)
                return self._json(200,result)
            except (ValueError,TypeError,KeyError) as e:
                return self._json(422,{'error':'validation','message':str(e)[:320]})
            except Exception:
                return self._json(500,{'error':'internal','message':'高维研究计算失败'})
        if self.path == "/api/esse/spaces-v25/discover":
            if "application/json" not in self.headers.get("Content-Type", ""):
                return self._json(415,{"error":"json_required"})
            raw_length=self.headers.get('Content-Length','')
            if not raw_length.isdigit() or not 1<=int(raw_length)<=MAX_BODY:
                return self._json(413,{"error":"invalid_length"})
            try:
                payload=json.loads(self.rfile.read(int(raw_length)))
                if not isinstance(payload,dict):raise ValueError('需要JSON对象')
                seed=payload.get('seed',20261102)
                count=payload.get('count',16)
                if type(seed) is not int or type(count) is not int or not 0<=seed<2**32 or not 1<=count<=40:
                    raise ValueError('seed/count不合法')
                history=payload.get('history')
                if history is None:
                    result={'version':'representation-v25','candidate_audit':audit_spaces_v25(propose_spaces_v25(seed,count)),
                            'status':'engineering_discovery_only'}
                else:
                    if not isinstance(history,list) or len(history)>2000:
                        raise ValueError('历史必须是最多2000期的数组')
                    periods=payload.get('test_periods',30)
                    alpha=payload.get('alpha',100.)
                    if type(periods) is not int or type(alpha) not in (int,float):
                        raise ValueError('测试区间/先验强度非法')
                    result=study_spaces_v25(history,seed=seed,count=count,test_periods=periods,alpha=alpha)
                return self._json(200,result)
            except (ValueError,TypeError,KeyError) as e:
                return self._json(422,{'error':'validation','message':str(e)[:320]})
            except Exception:
                return self._json(500,{'error':'internal','message':'表示空间研究执行失败'})
        if self.path == "/api/esse/spaces-v24/evaluate":
            if "application/json" not in self.headers.get("Content-Type", ""):
                return self._json(415,{"error":"json_required"})
            size=self.headers.get("Content-Length")
            if not size or not size.isdigit() or not 1<=int(size)<=MAX_BODY:
                return self._json(413,{"error":"invalid_length"})
            try:
                payload=json.loads(self.rfile.read(int(size)))
                if not isinstance(payload,dict): raise ValueError('请求必须为JSON对象')
                history=payload.get('history',[])
                rules=payload.get('rules',[])
                temporal=payload.get('temporal_specs',[])
                budget=payload.get('budget',100)
                seed=payload.get('seed',42)
                if (not isinstance(history,list) or len(history)>10000 or
                        not isinstance(rules,list) or len(rules)>24 or
                        not isinstance(temporal,list) or len(temporal)>12 or
                        type(budget) is not int or not 1<=budget<=100 or
                        type(seed) is not int or not 0<=seed<=4294967295):
                    raise ValueError('历史最多10000期、静态规则最多24条、时序规则最多12条、目标1..100注')
                result=compose_temporal(history,[V24Rule(**r) for r in rules],
                    [TemporalSpec(**x) for x in temporal],budget=budget,seed=seed,
                    base_numbers=payload.get('base_numbers'))
                return self._json(200,result)
            except (TypeError,ValueError,KeyError) as e:
                return self._json(422,{"error":"validation","message":str(e)[:320]})
            except Exception:
                return self._json(500,{"error":"internal","message":"多空间研究服务计算失败"})
        if self.path != "/api/esse/sculpt":
            return self._json(404,{"error":"not_found"})
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self._json(415,{"error":"json_required"})
        size = self.headers.get("Content-Length")
        if not size or not size.isdigit() or not 1 <= int(size) <= MAX_BODY:
            return self._json(413,{"error":"invalid_length"})
        try:
            body=json.loads(self.rfile.read(int(size)))
            registry_path=os.environ.get('PL5_REGISTRY_PATH')
            if registry_path:
                db=Registry(registry_path)
                try: response=run_bridge(body,registry=db)
                finally: db.close()
            else:
                response=run_bridge(body)
            return self._json(200,response)
        except (ValueError, TypeError, ContractError) as exc:
            return self._json(422,{"error":"validation","message":str(exc)[:400]})
        except Exception:
            return self._json(500,{"error":"internal","message":"内部计算异常，请检查服务日志"})
    def log_message(self, fmt, *args):
        # Do not print user-provided JSON bodies, even on failure.
        print("[bridge]",fmt%args)

def serve():
    port=int(os.environ.get("PL5_BRIDGE_PORT","8765"))
    if not 1024 <= port <= 65535: raise ValueError("无效端口")
    server=ThreadingHTTPServer(("127.0.0.1",port), BridgeHandler)
    print(f"PL5 ESSE bridge listening on 127.0.0.1:{port}",flush=True)
    server.serve_forever()
if __name__=="__main__": serve()
