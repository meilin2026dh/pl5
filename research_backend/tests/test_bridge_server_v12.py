"""In-process HTTP protocol test, avoiding external network and OS ports."""
import io
import json
from unittest.mock import Mock
from integration_server import BridgeHandler
from test_integration_bridge_v12 import payload

class HandlerHarness(BridgeHandler):
    def __init__(self, *, method, path, body=b'', ctype='application/json'):
        self.path=path
        self.command=method
        self.rfile=io.BytesIO(body)
        self.wfile=io.BytesIO()
        self.headers={"Content-Type":ctype,"Content-Length":str(len(body))}
        self.status=None
        self.response_headers={}
        self.client_address=('127.0.0.1',1234)
    def send_response(self,status): self.status=status
    def send_header(self,k,v): self.response_headers[k]=v
    def end_headers(self): pass
    def log_message(self,*args): pass

def test_health_and_json_roundtrip():
    h=HandlerHarness(method='GET',path='/api/esse/health')
    h.do_GET()
    assert h.status==200 and json.loads(h.wfile.getvalue())['ok']
    body=json.dumps(payload()).encode()
    h=HandlerHarness(method='POST',path='/api/esse/sculpt',body=body)
    h.do_POST()
    assert h.status==200
    response=json.loads(h.wfile.getvalue())
    assert response['strict_keep_count']==250 and response['source_guard']

def test_reject_bad_endpoint_or_type():
    h=HandlerHarness(method='POST',path='/api/esse/other',body=b'{}')
    h.do_POST()
    assert h.status==404
    h=HandlerHarness(method='POST',path='/api/esse/sculpt',body=b'{}',ctype='text/plain')
    h.do_POST()
    assert h.status==415
