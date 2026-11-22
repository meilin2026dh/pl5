"""Real loopback HTTP read-only test, no simulated endpoint logic."""
import json,os,sqlite3,threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from integration_server import BridgeHandler
from autoresearch.council_v21 import ResearchCouncil
from autoresearch.paper_factory_v20 import offline_blueprint

def test_http_council_status(tmp_path,monkeypatch):
    target=str(tmp_path/'research.sqlite')
    with sqlite3.connect(target) as db:
        c=ResearchCouncil(db)
        body='We measure the likelihood of each model against a uniform distribution and apply external validation on future periods.'
        c.paper.documents.add_document('paper','A bounded method',body,kind='local')
        b=c.paper.register_blueprint('paper',offline_blueprint(c.paper.documents.get_document('paper')))
        c.create(b['blueprint_id'],goal='Create an independently testable model research plan')
        c.auto_plan(maximum=3)
    monkeypatch.setenv('PL5_PAPER_FACTORY_DB',target)
    server=ThreadingHTTPServer(('127.0.0.1',0),BridgeHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with urlopen(f'http://127.0.0.1:{server.server_port}/api/esse/research-council',timeout=3) as response:
            payload=json.load(response)
        assert payload['version']=='2.1.0'
        assert payload['total']==2
        assert not payload['auto_publish']
        assert payload['projects'][0]['prediction_advantage']=='NOT_ESTABLISHED'
    finally:
        server.shutdown();thread.join(timeout=3);server.server_close()
