"""px113: one mpx5-yew or mpx5-screen job log -> its phases, in seconds, from
the log's own line timestamps. Prints one JSON object.

    python3 -I phases.py JOB_NAME LOGFILE

Phases (each from the end of the one before):
  setup     job start (first line) -> the main step's `##[group]Run tests/<suite>`
  yew       `mkyew: yew <sha>` -> the next tool's first line (yew's build alone)
  programs  the main step's start -> the first `program:` line, all builds (yew's in it)
  native    -> `built native ...` (kmain_console, native)
  release   -> `built release ...` (kmain_console, release; all tier only)
  s0        -> `PASS|FAIL Y0:`/`S0:` (the Linux side, screen-ref's rows)
  <tier> <fw>  -> the last row line naming that leg, in boot order
  tail      -> the main step's end (the next `##[group]Run`), or the log's end
A leg is `complete` when a later leg or the suite's verdict line follows it.
"""
import datetime
import json
import re
import sys

job, path = sys.argv[1], sys.argv[2]
suite = job
TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+)Z (.*)$")


def ts(s):
    return datetime.datetime.strptime(s[:26], "%Y-%m-%dT%H:%M:%S.%f")


lines = []
for raw in open(path, "rb").read().decode("utf-8", "replace").splitlines():
    m = TS.match(raw.lstrip("\ufeff"))
    if m:
        lines.append((ts(m.group(1)), m.group(2)))
if not lines:
    print(json.dumps({"error": "no timestamped lines"}))
    sys.exit(0)

out = {"first": lines[0][0].isoformat(), "last": lines[-1][0].isoformat()}
marks = {}


def first(pred, start=0):
    for i in range(start, len(lines)):
        if pred(lines[i][1]):
            return i
    return None


i_step = first(lambda t: t.startswith("##[group]Run tests/%s" % suite))
if i_step is None:
    print(json.dumps(dict(out, error="no main step")))
    sys.exit(0)
i_next = first(lambda t: t.startswith("##[group]Run "), i_step + 1)
i_endstep = (i_next - 1) if i_next is not None else len(lines) - 1
t0 = lines[0][0]
t_step = lines[i_step][0]
t_end = lines[i_endstep][0]
out["setup"] = (t_step - t0).total_seconds()
out["step"] = (t_end - t_step).total_seconds()
# after the main step: the artifact upload and the runner's cleanup, to the log's end
out["post"] = (lines[-1][0] - t_end).total_seconds()
out["job"] = (lines[-1][0] - t0).total_seconds()
out["exceeded"] = any("exceeded the maximum execution time" in t for _, t in lines)
body = range(i_step, i_endstep + 1)
pre = "%s: " % suite

i_yew = first(lambda t: t.startswith("mkyew: yew "), i_step)
if i_yew is not None and i_yew <= i_endstep:
    i_after = first(lambda t: re.match(r"^(build|mkpelt|mkboreutils|mkas|mkvtcases|%s): " % re.escape(suite), t) is not None, i_yew + 1)
    if i_after is not None and i_after <= i_endstep:
        out["yew"] = (lines[i_after][0] - lines[i_yew][0]).total_seconds()
    else:
        out["yew_open"] = (t_end - lines[i_yew][0]).total_seconds()
    m = re.match(r"mkyew: yew ([0-9a-f]{8})[0-9a-f]* pins wolf (\S+)", lines[i_yew][1])
    if m:
        out["yew_pin"], out["yew_wolf"] = m.group(1), m.group(2)

prev = t_step
for key, pat in (("programs", pre + "  program: "), ("native", pre + "built native "), ("release", pre + "built release ")):
    i = first(lambda t: t.startswith(pat), i_step)
    if i is not None and i <= i_endstep:
        # the last line of that kind ends the phase (both images built)
        j = i
        while j + 1 <= i_endstep and lines[j + 1][1].startswith(pat):
            j += 1
        out[key] = (lines[j][0] - prev).total_seconds()
        prev = lines[j][0]
i0 = first(lambda t: re.match(re.escape(pre) + r"(PASS|FAIL) [YS]0[ :]", t) is not None, i_step)
if i0 is not None and i0 <= i_endstep:
    out["s0"] = (lines[i0][0] - prev).total_seconds()
    prev = lines[i0][0]
legs = []
for fw in ("bios", "uefi"):
    for tier in ("native", "release"):
        pat = re.compile(re.escape(pre) + r"\s*(PASS |FAIL |SKIP )?[YS]\d+ %s %s\b" % (tier, fw))
        rows = re.compile(re.escape(pre) + r"(PASS|FAIL) [YS]\d+ %s %s\b" % (tier, fw))
        idx = [i for i in body if pat.match(lines[i][1])]
        if idx:
            legs.append(("%s %s" % (tier, fw), idx[-1], sum(1 for i in body if rows.match(lines[i][1]))))
verdict = first(lambda t: re.match(re.escape(pre) + r"(%s: )?(PASS|FAIL)$" % re.escape(suite), t) is not None, i_step)
out["verdict"] = lines[verdict][1][len(pre):] if verdict is not None and verdict <= i_endstep else None
out["legs"] = {}
for n, (name, i, nrows) in enumerate(legs):
    # the last leg reached is whole when the verdict follows it, or when it
    # printed as many PASS/FAIL rows as the run's first leg (whole, since a
    # later leg began)
    complete = n + 1 < len(legs) or out["verdict"] is not None or (n > 0 and nrows >= legs[0][2])
    out["legs"][name] = {"seconds": (lines[i][0] - prev).total_seconds(), "complete": complete, "rows": nrows}
    prev = lines[i][0]
out["tail"] = (t_end - prev).total_seconds()
# a red row: the run is a red of its own (a build or a session that failed),
# never a timing sample of a green leg
out["fails"] = [lines[i][1][len(pre):][:100] for i in body if lines[i][1].startswith(pre + "FAIL")]
print(json.dumps(out))
