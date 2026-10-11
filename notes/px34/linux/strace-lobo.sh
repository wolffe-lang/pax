#!/usr/bin/env bash
# px34: lobo (static, trunk pin) under strace -f on Linux with a
# request set: keepalive, close, a proxied request, a static file, a
# reload; one worker and four. Runs INSIDE px13-ubuntu; /w is ~/lanes/px34.
set -uo pipefail
W=/w/st
# px34: -yy names each socket's path; -s status beside status.
LOBO=$W/bin/lobo
out=$W/lobo-strace
rm -rf "$out"; mkdir -p "$out"
uname -r > "$out/uname.txt"
strace -V | head -n 1 >> "$out/uname.txt"
sha256sum "$LOBO" >> "$out/uname.txt"

cat > "$out/upstream.py" <<'PY'
import http.server, sys
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_GET(self):
        body = ("upstream saw %s\n" % self.path).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        got = self.rfile.read(n)
        body = ("upstream got %d bytes\n" % len(got)).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", 9000), H).serve_forever()
PY
python3 "$out/upstream.py" &
up=$!

one() { # workers
    local n=$1 d=$out/w$1 port=$((8080 + $1))
    mkdir -p "$d/conf" "$d/html" "$d/logs"
    printf '<!doctype html><title>px34</title><p>the page</p>\n' > "$d/html/index.html"
    head -c 300000 /dev/zero | tr '\0' 'x' > "$d/html/big.txt"
    printf 'small\n' > "$d/html/small.txt"
    cat > "$d/conf/lobo.conf" <<CONF
worker_processes $n;
pid logs/lobo.pid;
error_log logs/error.log;
control unix:logs/control.sock;
events {
    worker_connections 1024;
}
http {
    types {
        text/html  html htm;
        text/plain txt;
    }
    default_type application/octet-stream;
    access_log logs/access.log;
    server {
        listen 127.0.0.1:$port;
        server_name localhost;
        root html;
        index index.html;
        location /api/ {
            proxy_pass http://127.0.0.1:9000;
        }
    }
}
CONF
    (cd "$d" && "$LOBO" -t -c conf/lobo.conf) > "$d/t.out" 2>&1; echo "-t rc=$?" >> "$d/t.out"
    (cd "$d" && exec strace -f -s 256 -yy -o "$d/serve.strace" "$LOBO" -c conf/lobo.conf serve) > "$d/serve.out" 2>&1 &
    local sp=$! k=0
    while [ $k -lt 100 ] && ! curl -s -o /dev/null "http://127.0.0.1:$port/"; do sleep 0.1; k=$((k + 1)); done
    {
        echo "== keepalive: three requests on one connection"
        curl -s -w '%{http_code} %{size_download} conns=%{num_connects}\n' -o /dev/null "http://127.0.0.1:$port/" -o /dev/null "http://127.0.0.1:$port/small.txt" -o /dev/null "http://127.0.0.1:$port/index.html"
        echo "== close"
        curl -s -H 'Connection: close' -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/"
        echo "== http/1.0"
        curl -s -0 -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/small.txt"
        echo "== a static file of 300000 bytes"
        curl -s -w '%{http_code} %{size_download}\n' -o "$d/big.got" "http://127.0.0.1:$port/big.txt"; cmp "$d/big.got" "$d/html/big.txt" && echo same
        echo "== a range, a HEAD, a 404, a conditional"
        curl -s -r 10-19 -w ' %{http_code} %{size_download}\n' "http://127.0.0.1:$port/big.txt"
        curl -s -I -w '%{http_code}\n' -o /dev/null "http://127.0.0.1:$port/big.txt"
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/none"
        curl -s -z 'Jan 1 2037' -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/small.txt"
        echo "== proxied: a GET, a POST, two on one connection"
        curl -s -w ' %{http_code}\n' "http://127.0.0.1:$port/api/one"
        curl -s -d 'hello=world' -w ' %{http_code}\n' "http://127.0.0.1:$port/api/post"
        curl -s -w ' %{http_code} conns=%{num_connects}\n' "http://127.0.0.1:$port/api/a" "http://127.0.0.1:$port/api/b"
        echo "== eight at once"
        cp=(); for i in 1 2 3 4 5 6 7 8; do curl -s -o /dev/null -w '%{http_code} ' "http://127.0.0.1:$port/big.txt" & cp+=($!); done; wait "${cp[@]}"; echo
        echo "== status, reload, a request after it"
        (cd "$d" && strace -f -s 256 -yy -o "$d/status.strace" "$LOBO" -c conf/lobo.conf status); echo "status rc=$?"
        (cd "$d" && strace -f -s 256 -yy -o "$d/s-status.strace" "$LOBO" -s status -c conf/lobo.conf); echo "-s status rc=$?"
        (cd "$d" && strace -f -s 256 -yy -o "$d/reload.strace" "$LOBO" -s reload -c conf/lobo.conf); echo "reload rc=$?"
        sleep 1
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/"
        curl -s -w ' %{http_code}\n' "http://127.0.0.1:$port/api/after"
        echo "== an idle second, then stop"
        sleep 1.5
        (cd "$d" && strace -f -s 256 -yy -o "$d/stop.strace" "$LOBO" -s stop -c conf/lobo.conf); echo "stop rc=$?"
    } > "$d/requests.out" 2>&1
    local w=0
    while kill -0 $sp 2>/dev/null && [ $w -lt 100 ]; do sleep 0.1; w=$((w + 1)); done
    kill -0 $sp 2>/dev/null && { echo "serve did not end; killed" >> "$d/requests.out"; kill $sp; }
    wait $sp; echo "serve rc=$?" >> "$d/requests.out"
    cat "$d/requests.out"
    tail -n 5 "$d/logs/error.log" 2>/dev/null
    wc -l "$d"/*.strace
}
one 1
one 4
kill $up
echo done
