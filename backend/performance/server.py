"""Loopback-only HTTP test harness. Not a Cloud Run or production server."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac,os
from run import decode,execute,canonical,VERSION
MAX_BODY=1048576

def create_server(token, port=0):
    if not isinstance(token,str) or len(token)<32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('local token must be at least 32 ASCII characters without whitespace')
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup(); self.connection.settimeout(5)
        def log_message(self,*args): pass # Do not log authorization or case data.
        def send_json(self,status,data):
            raw=canonical(data).encode()
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)))
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if self.path=='/healthz':
                return self.send_json(200,{'status':'UP','engine_version':VERSION,'scope':'LOCAL_SYNTHETIC_ONLY','persistence':'NOT_SAVED'})
            self.send_json(404,{'error':'NOT_FOUND'})
        def do_POST(self):
            if self.path!='/v1/performance/run':return self.send_json(404,{'error':'NOT_FOUND'})
            auth=self.headers.get_all('Authorization',[])
            if len(auth)!=1 or not hmac.compare_digest(auth[0].encode(),('Bearer '+token).encode()):
                return self.send_json(401,{'error':'UNAUTHORIZED'})
            if self.headers.get('Origin') is not None:return self.send_json(403,{'error':'BROWSER_ORIGIN_NOT_ALLOWED'})
            if self.headers.get('Transfer-Encoding') is not None:return self.send_json(400,{'error':'TRANSFER_ENCODING_NOT_SUPPORTED'})
            if self.headers.get_content_type()!='application/json':return self.send_json(415,{'error':'JSON_REQUIRED'})
            lengths=self.headers.get_all('Content-Length',[])
            if len(lengths)!=1 or not lengths[0].isdigit():return self.send_json(411,{'error':'CONTENT_LENGTH_REQUIRED'})
            size=int(lengths[0])
            if size>MAX_BODY:return self.send_json(413,{'error':'BODY_TOO_LARGE'})
            try:
                raw=self.rfile.read(size)
                if len(raw)!=size:raise ValueError('truncated input')
                payload=decode(raw)
                if not isinstance(payload,dict):raise ValueError('object required')
                if payload.get('evidence_class')!='SYNTHETIC_TEST_ONLY':return self.send_json(422,{'error':'SYNTHETIC_ONLY'})
                result=execute(payload)
                # Serialize before headers, so nonfinite arithmetic cannot produce half a response.
                canonical(result)
            except TimeoutError:return self.send_json(408,{'error':'READ_TIMEOUT'})
            except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):
                return self.send_json(400,{'error':'INVALID_INPUT'})
            return self.send_json(200,result)
    return HTTPServer(('127.0.0.1',port),Handler)

if __name__=='__main__':
    if os.environ.get('K_SERVICE'):raise SystemExit('Local harness must not run on Cloud Run')
    server=create_server(os.environ.get('BARYON_LOCAL_TOKEN'),int(os.environ.get('PORT','8080')))
    print('Local synthetic API listening on 127.0.0.1:'+str(server.server_port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
