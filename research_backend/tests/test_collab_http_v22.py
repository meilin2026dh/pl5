import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from integration_server import BridgeHandler
from autoresearch.collaboration_v22 import V22ResearchLab
from autoresearch.paper_factory_v20 import offline_blueprint


def test_v22_http_reports_generated_only(tmp_path,monkeypatch):
    path=str(tmp_path/'research.sqlite')
    with sqlite3.connect(path) as db:
        lab=V22ResearchLab(db)
        doc='Empirical frequency modeling can be compared to independent uniform baselines with frozen historical evaluation.'
        lab.council.paper.documents.add_document('document','Frequency methods for digit counts',doc,kind='local')
        b=lab.council.paper.register_blueprint('document',offline_blueprint(lab.council.paper.documents.get_document('document')))
        p=lab.council.create(b['blueprint_id'],goal='Evaluate generated digit-frequency research ability and cross-platform score stability')
        lab.generate(p['project_id'])
    monkeypatch.setenv('PL5_PAPER_FACTORY_DB',path)
    server=ThreadingHTTPServer(('127.0.0.1',0),BridgeHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with urlopen(f'http://127.0.0.1:{server.server_port}/api/esse/research-v22',timeout=3) as res:
            payload=json.load(res)
        assert payload['version']=='2.2.0'
        assert payload['total_generated']==1
        assert payload['total_evaluated']==0
        assert payload['projects'][0]['generated']
        assert payload['automatic_release'] is False
    finally:
        server.shutdown();thread.join(timeout=3);server.server_close()
