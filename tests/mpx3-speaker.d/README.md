# Speaker timing

K2 measures pitch from QEMU's WAV capture, but onset and hold durations from
the guest's speaker-event ring. The capture follows host scheduling and is
not an independent guest clock. Positive, finite capture durations remain
visible in every verdict; frequencies must remain within **1%**.

Guest timing bounds are unchanged: adjacent onsets **50 ± 3 ticks**, total
span **350 ± 3 ticks**, holds **48 ± 3 ticks**. The event ring is read only
after the machine has halted. No fixed host delay is used to infer completion.

Twenty native-BIOS speaker-row boots before and twenty after, each under
four host CPUs, used the same image. Before: **1/20 failures**, a 589.2 ms
capture duration against the old 576 ms upper limit, while the guest had
onsets `51 50 50 50 50 50 50`, span `351`, and holds `49 48 48 48 48 48 48 48`.
After: **0/20 failures**. Whole-take elapsed times were 12–15 s on both sides.
The corrected judge still rejects bad pitch, nonfinite capture values,
wrong onset/hold times and missing evidence.

CI issue [#202](https://github.com/wolffe-lang/pax/issues/202) records the
same distinction at 651.8 ms. No capture-duration margin is claimed after
retiring that invalid host-clock assertion. Across all 40 timelines, onsets were 50–51 ticks and holds 48–49 ticks;
spans were 351 ticks before and 350–351 after. Capture durations ranged
449.4–589.2 ms before and 449.4–540.9 ms after. Thus the observed guest onset,
span and hold maxima each have **2 ticks of margin** to their existing upper
bounds; per-take timelines preserve the underlying observations.

These measurements target the `speaker` row. The local container lacks
strace, so K9 printed its named skip in each take; this is not a claim of
full-suite coverage. CI still requires K9 independently.
