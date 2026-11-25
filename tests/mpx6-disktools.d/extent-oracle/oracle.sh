#!/bin/sh
# Black-box oracle identity is checked before every command, not just at image build.
set -eu
version=$(dpkg-query -W -f='${Version}' e2fsprogs)
if [ "$version" != '1.47.0-2.4~exp1ubuntu4.1' ]; then
    printf '%s\n' "REFUSED oracle-version found=$version expected=1.47.0-2.4~exp1ubuntu4.1" >&2
    exit 75
fi
sha256sum -c "$(dirname "$0")/binaries.sha256" >&2 || {
    printf '%s\n' 'REFUSED oracle-binary-digest' >&2
    exit 75
}
case ${1:-} in
    --identity)
        printf '%s\n' "e2fsprogs=$version"
        sha256sum /usr/sbin/mke2fs /usr/sbin/e2fsck /usr/sbin/debugfs
        ;;
    e2fsck|debugfs|mke2fs)
        program=$1
        shift
        exec "/usr/sbin/$program" "$@"
        ;;
    *) printf '%s\n' 'REFUSED oracle-command' >&2; exit 75 ;;
esac
