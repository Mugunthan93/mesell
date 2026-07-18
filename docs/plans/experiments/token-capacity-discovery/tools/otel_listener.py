import http.server, json, datetime, gzip
CAP='/tmp/tokcap-poc/otel-capture.ndjson'
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _read(self):
        cl=self.headers.get('Content-Length')
        if cl is not None: return self.rfile.read(int(cl))
        if 'chunked' in (self.headers.get('Transfer-Encoding') or '').lower():
            buf=b''
            while True:
                ln=self.rfile.readline().strip()
                try: sz=int(ln,16)
                except: break
                if sz==0: self.rfile.readline(); break
                buf+=self.rfile.read(sz); self.rfile.readline()
            return buf
        return b''
    def do_POST(self):
        body=self._read()
        hdrs={k:self.headers.get(k) for k in ('Content-Length','Content-Encoding','Transfer-Encoding','Content-Type')}
        if (self.headers.get('Content-Encoding') or '')=='gzip' and body:
            try: body=gzip.decompress(body)
            except Exception: pass
        rec={'t':datetime.datetime.now().isoformat(),'path':self.path,'blen':len(body),'hdrs':hdrs}
        try: rec['json']=json.loads(body.decode('utf-8'))
        except Exception as e: rec['raw']=body[:300].decode('latin1','replace'); rec['err']=str(e)
        open(CAP,'a').write(json.dumps(rec)+'\n')
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{}')
    def do_GET(self): self.send_response(200); self.end_headers()
print("listener v2 on :4318", flush=True)
http.server.HTTPServer(('127.0.0.1',4318),H).serve_forever()
