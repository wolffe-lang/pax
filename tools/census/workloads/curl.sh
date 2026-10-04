# curl as the network floor: https (TLS, the threaded resolver), an
# http-to-https redirect, and a 30 MB release download. Scope: curl.
SCOPE='/usr/bin/curl'
workload() {
    T /usr/bin/curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' https://archlinux.org/
    T /usr/bin/curl -sSL -o /dev/null -w '%{http_code} %{num_redirects}\n' http://github.com/
    T /usr/bin/curl -sSL -o /work/wolf.tar.gz -w '%{http_code} %{size_download}\n' \
        https://github.com/wolffe-lang/wolf-lang/releases/download/v0.2.22/wolf-0.2.22-x86_64-unknown-linux-gnu.tar.gz
    sha256sum /work/wolf.tar.gz
}
