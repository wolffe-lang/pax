#!/usr/bin/env bash
# notes/px125/rig/engine.sh — the container engine as tools/linux-tree calls it (PAX_ENGINE) in the
# linux step: ENGINE_P (the host's engine) with ENGINE_MEM's memory cap and a process limit on each
# `run`, and the take's CPUs (ENGINE_CPUS) inside the container, before linux-tree's own runner.
if [ "${1:-}" = run ]; then
    shift
    args=(run --memory "${ENGINE_MEM:-12g}" --pids-limit 16384)
    while [ $# -gt 0 ]; do
        if [ "$1" = sh ] && [ "${2:-}" = /x/run.sh ]; then args+=(taskset -c "${ENGINE_CPUS:?}"); fi
        args+=("$1"); shift
    done
    exec "${ENGINE_P:?}" "${args[@]}"
fi
exec "${ENGINE_P:?}" "$@"
