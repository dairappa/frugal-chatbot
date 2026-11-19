"""Static server for the WebLLM demo. POST /log appends smoke-test events to smoke.log."""
import http.server, json, sys, time
class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length", 0)))
        with open("smoke.log", "a") as f:
            f.write(json.dumps({"at": time.strftime("%H:%M:%S"), **json.loads(body)}) + "\n")
        self.send_response(204); self.end_headers()
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8000), H).serve_forever()
