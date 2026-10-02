# lib.sh — shared by tools/* and tests/*. Source it; never run it.
# shellcheck shell=bash

PAX_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PAX_BUILD=${PAX_BUILD:-$PAX_ROOT/build}
PAX_CACHE=${PAX_CACHE:-$PAX_ROOT/.pax-cache}

die() { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 2; }
say() { printf '%s: %s\n' "${0##*/}" "$*" >&2; }

need() {
    local t
    for t in "$@"; do
        command -v "$t" >/dev/null 2>&1 || die "missing tool: $t (this harness never installs anything; see README.md, 'Hosts')"
    done
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

# Load boot/limine.pin into LIMINE_VERSION / LIMINE_URL / LIMINE_SHA256.
load_limine_pin() {
    local pin=$PAX_ROOT/boot/limine.pin
    [ -f "$pin" ] || die "no $pin"
    # shellcheck disable=SC1090
    . "$pin"
    [ -n "${LIMINE_VERSION:-}" ] && [ -n "${LIMINE_URL:-}" ] && [ -n "${LIMINE_SHA256:-}" ] \
        || die "$pin must set LIMINE_VERSION, LIMINE_URL and LIMINE_SHA256"
    LIMINE_DIR=$PAX_CACHE/limine-$LIMINE_VERSION
}

# The UEFI firmware for QEMU: PAX_OVMF_CODE (and optionally
# PAX_OVMF_VARS) win; otherwise the first known distro path that exists.
# Prints "code vars" (vars may be empty) or nothing.
find_ovmf() {
    if [ -n "${PAX_OVMF_CODE:-}" ]; then
        printf '%s %s\n' "$PAX_OVMF_CODE" "${PAX_OVMF_VARS:-}"
        return
    fi
    local pair code vars
    for pair in \
        /usr/share/OVMF/OVMF_CODE_4M.fd:/usr/share/OVMF/OVMF_VARS_4M.fd \
        /usr/share/OVMF/OVMF_CODE.fd:/usr/share/OVMF/OVMF_VARS.fd \
        /usr/share/edk2/x64/OVMF_CODE.4m.fd:/usr/share/edk2/x64/OVMF_VARS.4m.fd \
        /usr/share/edk2-ovmf/x64/OVMF_CODE.fd:/usr/share/edk2-ovmf/x64/OVMF_VARS.fd \
        /usr/share/edk2/ovmf/OVMF_CODE.fd:/usr/share/edk2/ovmf/OVMF_VARS.fd \
        /usr/share/qemu/edk2-x86_64-code.fd:/usr/share/qemu/edk2-i386-vars.fd \
        /opt/homebrew/share/qemu/edk2-x86_64-code.fd:/opt/homebrew/share/qemu/edk2-i386-vars.fd \
        /usr/local/share/qemu/edk2-x86_64-code.fd:/usr/local/share/qemu/edk2-i386-vars.fd
    do
        code=${pair%%:*}; vars=${pair#*:}
        if [ -f "$code" ]; then
            [ -f "$vars" ] || vars=
            printf '%s %s\n' "$code" "$vars"
            return
        fi
    done
}
