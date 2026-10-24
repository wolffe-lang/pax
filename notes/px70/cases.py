"""Fresh black-box VT inputs; no expected results are generated here."""
CLEAR = b'\33[0m\33[r\33[?25l\33]R\33[2J\33[H'
CASES = []
def case(name, data, pixels=False):
    CASES.append((name, CLEAR + data, pixels))

for p in (2, 3, 4, 5, 21):
    case('attr-%d' % p, ('\33[%dmA\33[0mA' % p).encode(), True)
case('plain', b'AA', True)
case('italic-green', b'\33[32mA\33[0mA', True)
case('underline-cyan', b'\33[36mA\33[0mA', True)
for seq in ('1;2', '2;1', '2;3', '3;2', '3;4', '4;3', '2;4', '4;2',
            '1;3', '1;4', '3;23', '4;24', '5;25', '2;22', '1;22',
            '31;3;23', '31;4;24', '31;2;22', '3;39', '4;39', '2;39',
            '3;31', '4;31', '2;31', '3;7', '4;7', '2;7'):
    case('flags-' + seq.replace(';', '-'), ('\33[%smA' % seq).encode())
for seq in ('38;2;255;0;0', '38:2:255:0:0', '38:2::255:0:0',
            '38:2:0:255:0:0', '48:2::0:0:255', '38:5:196',
            '38;2;10;200;30', '38;2;128;128;128', '38;2;256;0;0',
            '38;2;999;0;0', '38;2;255;0', '38;2', '38:2::10:200:30'):
    case('colour-' + seq.replace(';', '-').replace(':', '_'), ('\33[%smA' % seq).encode())
for count in (8, 9, 15, 16, 17, 18, 32):
    case('cup-%d' % count, ('\33[3;4' + ';0' * (count - 2) + 'HX').encode())
    case('sgr-%d' % count, ('\33[' + '0;' * (count - 1) + '31mX').encode())
for op in ('@', 'P', 'X'):
    for count in ('', '0', '1', '2', '80', '9999'):
        case('char-%s-%s' % ({'@':'ich','P':'dch','X':'ech'}[op], count or 'default'),
             ('abcde\33[1;2H\33[44m\33[%s%s' % (count,op)).encode())
    case('char-%s-margin' % ord(op), ('\33[1;79HAB\33[%s' % op).encode())
for region in ('2;3', '2;2', '0;0', '3;2', '2;999', '999;999', '25;25', '24;25'):
    case('region-' + region.replace(';', '-'),
         ('a\r\nb\r\nc\r\nd\33[5;5H\33[%srX\33[6n' % region).encode())
for op in ('L', 'M'):
    for row in (1, 2, 3, 4, 25):
        case('line-%s-row%d' % (op, row),
             ('a\r\nb\r\nc\r\nd\33[2;3r\33[%d;2H\33[44m\33[2%s' % (row, op)).encode())
case('region-scroll', b'outside\33[2;4r\33[4;1Hone\r\ntwo\r\nthree\33[r')
case('region-outside-lf', b'\33[2;3r\33[25;1HA\nB\33[r')
case('palette-set', b'\33[31mAA\33]P1123456\33[H', True)
case('palette-reset', b'\33[31mAA\33]P1123456\33]R\33[H', True)
for p in range(7):
    case('cursor-%d' % p, ('\33[3;3H\33[?25h\33[%d q' % p).encode(), True)
case('cursor-hidden', b'\33[3;3H', True)
for seq in ('31;44;1;7', '31;44;2;7', '31;44;3;7', '31;44;4;7',
            '31;44;1;3;7', '31;44;2;3;7', '31;44;1;4;7', '31;44;2;4;7',
            '3;4;23', '3;4;24', '1;2;22', '2;1;22', '5;7', '1;5;7',
            '2;5;7', '3;5;7', '31;44;2', '31;44;1'):
    case('combined-' + seq.replace(';', '-'), ('\33[%smA' % seq).encode())
case('save-attributes', b'\33[31;2;3;4;5m\33\x37\33[0m\33\x38A')
