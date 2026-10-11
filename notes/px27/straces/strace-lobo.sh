#!/bin/bash
# px27: lobo (static, b256d2e) under strace -f on Linux, its file tree on
# a tmpfs of a throwaway container. Mounted from the host: /lobo
# read-only (the binary) and /out (the straces). The file-side calls
# are what this lane reads; the request set is small on purpose.
set -u
LOBO=/lobo/lobo
[ "$(stat -f -c %T /t)" = tmpfs ] || { echo "/t is not a tmpfs"; exit 2; }
uname -r > /out/uname.txt; strace -V | head -n 1 >> /out/uname.txt; sha256sum $LOBO >> /out/uname.txt
one() { # workers
    local n=$1 d=/t/w$1 o=/out/w$1 port=$((8080 + $1))
    mkdir -p "$d/conf" "$d/html" "$d/logs" "$o"
    printf '<!doctype html><title>px27</title><p>the page</p>\n' > "$d/html/index.html"
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
    }
}
CONF
    (cd "$d" && strace -f -s 96 -o "$o/t.strace" "$LOBO" -t -c conf/lobo.conf) > "$o/t.out" 2>&1; echo "-t rc=$?" >> "$o/t.out"
    ls -la "$d" "$d/logs" > "$o/tree-after-t.txt" 2>&1
    (cd "$d" && exec strace -f -s 96 -o "$o/serve.strace" "$LOBO" -c conf/lobo.conf serve) > "$o/serve.out" 2>&1 &
    local sp=$! k=0
    while [ $k -lt 100 ] && ! curl -s -o /dev/null "http://127.0.0.1:$port/"; do sleep 0.1; k=$((k + 1)); done
    {
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/"
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/small.txt"
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/none"
        ls -la "$d/logs"
        echo "== status, reload, a request after it"
        (cd "$d" && strace -f -s 96 -o "$o/status.strace" "$LOBO" -c conf/lobo.conf status); echo "status rc=$?"
        (cd "$d" && strace -f -s 96 -o "$o/reload.strace" "$LOBO" -s reload -c conf/lobo.conf); echo "reload rc=$?"
        sleep 1
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/"
        echo "== the logs moved aside, reopen, a request after it"
        mv "$d/logs/access.log" "$d/logs/access.log.1"
        (cd "$d" && strace -f -s 96 -o "$o/reopen.strace" "$LOBO" -s reopen -c conf/lobo.conf); echo "reopen rc=$?"
        sleep 1
        curl -s -w '%{http_code} %{size_download}\n' -o /dev/null "http://127.0.0.1:$port/"
        ls -la "$d/logs"
        echo "== stop"
        (cd "$d" && strace -f -s 96 -o "$o/stop.strace" "$LOBO" -s stop -c conf/lobo.conf); echo "stop rc=$?"
    } > "$o/requests.out" 2>&1
    local w=0
    while kill -0 $sp 2>/dev/null && [ $w -lt 100 ]; do sleep 0.1; w=$((w + 1)); done
    kill -0 $sp 2>/dev/null && { echo "serve did not end; killed" >> "$o/requests.out"; kill $sp; }
    wait $sp; echo "serve rc=$?" >> "$o/requests.out"
    ls -la "$d/logs" >> "$o/requests.out" 2>&1
    cat "$d/logs/error.log" > "$o/error.log" 2>&1
    cat "$o/requests.out"
}
one 1
one 2
echo done
