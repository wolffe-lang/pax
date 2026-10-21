#!/bin/bash
# px58 on kasumi: what yew asks of Linux under its own goldens, black-box.
# The oracle (C yew at sagitta.pin's 9ace98c2, tools/oracle --cc gcc
# --build-only) and yew's tools/goldens run in localhost/px13-ubuntu; the
# static yew (tools/mkyew's, bin/yew) is given to the goldens as a wrapper
# that execs `strace -D -f`, so the pid the PTY runner spawned and
# signals stays yew's (strace is the grandchild). The suites: version,
# help, and campaign 03's 62 editor cases by name (yew's CI gate, M-YW3);
# each case's trace is tr.<pid> under OUTDIR, the runner's verdict in
# OUTDIR/verdicts.txt.   census-goldens.sh OUTDIR
L=$HOME/lanes/px58
O=$1
mkdir -p "$O"
cases="notepad_open notepad_move notepad_insert notepad_escape notepad_save notepad_save_error notepad_dirty_write notepad_dirty_discard notepad_dirty_cancel notepad_recover_apply notepad_recover_discard notepad_recover_escape notepad_preserve_lf notepad_preserve_crlf notepad_preserve_bom notepad_preserve_no_final_nl notepad_preserve_invalid notepad_preserve_unicode notepad_burst_keys notepad_burst_paste notepad_restore_term notepad_restore_segv notepad_restore_suspend notepad_restore_kill notepad_quit_force"
cases="$cases s15_degenerate s15_gutter_abs_1 s15_gutter_hybrid_10 s15_gutter_hybrid_100 s15_gutter_rel_9 s15_metadata_binary_invalid s15_metadata_bom s15_metadata_crlf s15_metadata_mixed s15_mode_i s15_mode_l s15_nowrap_cjk s15_position_unicode s15_resize_roundtrip s15_wrap_cjk"
cases="$cases s16_block_c_expand s16_block_prose_expand s16_word_emoji s16_word_han_first s16_word_han_second s16_word_tail"
cases="$cases s17_char_delete_matches_highlight s17_char_selection_unicode_tab s17_h_b_extends_by_block s17_h_c_extends_by_character s17_h_l_extends_by_line s17_h_w_extends_by_word s17_h_w_keyboard_entry s17_lift_ends_draws_two_cursors s17_lift_lines_draws_seven_cursors s17_lift_lines_draws_thousand_cursors s17_line_selection_unicode_tab s17_modal_milestone_saves s17_multicursor_typing_is_simultaneous s17_one_undo_reverts_multicursor_typing s17_rect_selection_unicode_tab s17_secondary_cursors_draw_at_eol"
podman run --rm --cap-add SYS_PTRACE --security-opt seccomp=unconfined --network none --ulimit core=0:0 \
    --cpuset-cpus 4-15 -v "$L:$L:Z" localhost/px13-ubuntu bash -c "
set -u
strace -V | head -n 1
cd $L/yew && git log --oneline -1
tools/oracle --cc gcc --build-only --jobs 12 || exit 1
cat > $L/bin/yew-traced <<W
#!/bin/sh
exec /usr/bin/strace -D -f -qq -n -v -xx -s 1048576 -o $O/tr.\\\$\\\$ -- $L/bin/yew \"\\\$@\"
W
chmod +x $L/bin/yew-traced
cat $L/bin/yew-traced
: > $O/verdicts.txt
tools/goldens --yew $L/bin/yew-traced --suite version,help | tee -a $O/verdicts.txt
for c in $cases; do
    tools/goldens --yew $L/bin/yew-traced --demo target/oracle/sagitta/build/demo_paint --suite pty --case \$c > /dev/null 2>&1
    v=\$(grep -E \"^pty: \$c: \" target/oracle/goldens/pty.log | head -n 1)
    echo \"\${v:-pty: \$c: no verdict}\" | tee -a $O/verdicts.txt
done
echo \"traces: \$(ls $O | grep -c '^tr\\.')\"
"
