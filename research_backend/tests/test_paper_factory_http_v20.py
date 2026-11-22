import json
import sqlite3
from unittest.mock import patch
from test_bridge_server_v12 import HandlerHarness
from autoresearch.paper_factory_v20 import PaperFactory, offline_blueprint

BODY='A probability model is used to evaluate a predeclared statistical hypothesis on separate test data, so unseen samples remain independent of the method selection process.'

def test_paper_factory_status_requires_explicit_db(tmp_path):
    with patch.dict('os.environ',{'PL5_PAPER_FACTORY_DB':str(tmp_path/'missing.sqlite')}):
        h=HandlerHarness(method='GET',path='/api/esse/paper-factory');h.do_GET()
        out=json.loads(h.wfile.getvalue())
        assert h.status==200 and out['status']=='not_initialized'
        assert not (tmp_path/'missing.sqlite').exists()

def test_status_shows_only_grounded_cards(tmp_path):
    path=tmp_path/'paper.sqlite'
    with sqlite3.connect(path) as db:
        lab=PaperFactory(db)
        lab.documents.add_document('doc', 'Independent models', BODY,kind='local')
        lab.register_blueprint('doc',offline_blueprint(lab.documents.get_document('doc')))
    with patch.dict('os.environ',{'PL5_PAPER_FACTORY_DB':str(path)}):
        h=HandlerHarness(method='GET',path='/api/esse/paper-factory');h.do_GET()
        out=json.loads(h.wfile.getvalue())
        assert h.status==200 and out['total_blueprints']==1
        assert out['cards'][0]['source']['source_quote'] in BODY
        assert out['cards'][0]['official_approval'] is False
