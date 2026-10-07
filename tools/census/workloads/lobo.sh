# lobo 0.1.1 (the release archive) serving its demo site, as the
# site's own scripts drive it: lobo -t, serve, pages, the 1.3 MB file, a
# range, a 404, /metrics, the control socket, then a reload
# with a slow download held across it, the old generation retired, and
# a stop over the control socket. Scope: every lobo process (the server,
# its threads, and the lobo control clients); curl is the untraced driver.
SCOPE='/stage/lobo/lobo'
workload() {
    cp -R /stage/lobo-site /work/lobo-site
    cd /work/lobo-site
    mkdir -p logs
    PATH=/stage/lobo:$PATH
    T /stage/lobo/lobo -t
    T /stage/lobo/lobo serve > logs/serve.out 2>&1 &
    i=0
    until curl -s -o /dev/null http://127.0.0.1:8088/; do
        i=$((i + 1)); [ $i -ge 100 ] && { echo "lobo never answered"; return 1; }
        sleep 0.1
    done
    for u in / /index.html /files/big.bin /metrics /nope; do
        curl -s -o /dev/null -w "$u %{http_code} %{size_download}\n" "http://127.0.0.1:8088$u"
    done
    curl -s -o /dev/null -r 0-99 -w "range %{http_code} %{size_download}\n" http://127.0.0.1:8088/files/big.bin
    curl -s -I -o /dev/null -w "head %{http_code}\n" http://127.0.0.1:8088/
    curl -s -o /dev/null -o /dev/null -o /dev/null -w "keepalive %{http_code}\n" \
        http://127.0.0.1:8088/ http://127.0.0.1:8088/index.html http://127.0.0.1:8088/metrics
    T /stage/lobo/lobo control ping
    T /stage/lobo/lobo status
    curl -s --limit-rate 128k -o logs/dl.bin http://127.0.0.1:8088/files/big.bin &
    dl=$!
    sleep 2
    cp -R html html-v2
    sed -i 's/hello from/v2: hello from/' html-v2/index.html
    sed -i 's/root html;/root html-v2;/' conf/site.conf
    T /stage/lobo/lobo -s reload
    sleep 1
    curl -s http://127.0.0.1:8088/ | grep -o '<h1>.*</h1>'
    T /stage/lobo/lobo status
    wait $dl
    cmp html/files/big.bin logs/dl.bin && echo "download intact across the reload"
    i=0
    until grep -q 'generation-retired' logs/serve.out; do
        i=$((i + 1)); [ $i -ge 60 ] && { echo "old generation never retired"; break; }
        sleep 1
    done
    T /stage/lobo/lobo -s stop
    wait
    grep -E 'generation-(draining|retired)' logs/serve.out | head -4
}
