"""VT key measurements; labels preserve NumLock transitions and duplicates."""
KEYS = [(f'off-{n}',f'kp_{n}') for n in range(10)] + [('off-dot','kp_decimal')]
KEYS += [(f'shift-{n}',f'shift-kp_{n}') for n in range(10)]
KEYS += [(f'ctrl-{n}',f'ctrl-kp_{n}') for n in (1,2,4,5,6,7,8,9)]
KEYS += [(f'alt-{n}',f'alt-kp_{n}') for n in range(10)]
KEYS += [('alt-65','alt-kp_6-kp_5'),('alt-97','alt-kp_9-kp_7'),
         ('alt-128','alt-kp_1-kp_2-kp_8'),('alt-256','alt-kp_2-kp_5-kp_6'),
         ('alt-emoji','alt-kp_1-kp_2-kp_8-kp_5-kp_0'),('alt-shift-1','alt-shift-kp_1')]
KEYS += [(f'altgr-{n}',f'alt_r-{n}') for n in '0123456789abcdefgz']
KEYS += [('altgr-41','alt_r-4-1'),('altgr-80','alt_r-8-0'),
         ('altgr-20ac','alt_r-2-0-a-c'),('altgr-kp1','alt_r-kp_1'),
         ('altgr-shift-a','alt_r-shift-a'),('altgr-ctrl-a','alt_r-ctrl-a')]
KEYS += [('num-on','num_lock')] + [(f'on-{n}',f'kp_{n}') for n in range(10)]
KEYS += [('on-shift-1','shift-kp_1'),('on-alt65','alt-kp_6-kp_5'),('num-off','num_lock')]
KEYS += [('hex-41','alt_r-kp_4-kp_1'),('hex-euro','alt_r-kp_2-kp_0-a-c'),
         ('hex-emoji','alt_r-kp_1-f-kp_6-kp_4-kp_2'),('hex-a1b','alt_r-a-kp_1-b')]
