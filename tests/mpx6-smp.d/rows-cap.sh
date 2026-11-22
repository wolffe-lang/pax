# tests/mpx6-smp.d/rows-cap.sh — SMP_ROWS_CAP=N, a development knob of tests/mpx6-smp (sourced by it and by
# knob-selftest.sh). Until the release step every processor but CPU 0 runs no thread by default, so the kinds
# that boot at that default (rows, stress and the three ends) are red at their gate `active 1 of N`; with the
# knob they boot with `pax.cpus=N` and their rows can be read before the release. It is never the gate: the
# hosted run refuses it, a record's manifest never sets it, a take that sets it says `NOT-A-GATE` first, and
# it goes, with its rows, in the release step. Unset, every image's command line is byte-identical.

rows_cap_check() { # CAP: '' (unset) or 1-64; 0 when it may be used, else 2 and why on stderr
    local c=$1
    [ -n "$c" ] || return 0
    case $c in *[!0-9]*|0*) echo "SMP_ROWS_CAP takes a count of processors, 1 to 64, not '$c'" >&2; return 2 ;; esac
    [ "$c" -le 64 ] || { echo "SMP_ROWS_CAP takes a count of processors, 1 to 64, not '$c'" >&2; return 2; }
    [ "${GITHUB_ACTIONS:-}" != true ] || { echo "SMP_ROWS_CAP is a development knob: the hosted run never sets it" >&2; return 2; }
    return 0
}

rows_cap_spec() { # CAP SPEC: an image's NAME:CMDLINE-WORDS:RUN-LINE, with ` pax.cpus=CAP` on a default-cap kind
    local c=$1 spec=$2
    local name=${spec%%:*} rest=${spec#*:}
    local words=${rest%%:*} line=${rest#*:}
    case $name in rows|stress|end-*) [ -z "$c" ] || words="$words pax.cpus=$c" ;; esac
    printf '%s:%s:%s\n' "$name" "$words" "$line"
}
