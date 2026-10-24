#!/usr/bin/env python3
"""The measured VT rows held to screen-ref independently of the kernel."""
import pathlib
import runpy
import unittest
Term = runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / 'tools/screen-ref'))['Term']

def term(data, cols=80, rows=25):
    t=Term(cols,rows)
    for b in data: t.feed(b)
    return t

class Cursor(unittest.TestCase):
    def test_cup_hvp(self):
        t=term(b'\33[3;5HX\33[4;7fY')
        self.assertEqual(t.cells[2][4],(88,7,0)); self.assertEqual(t.cells[3][6],(89,7,0))
        self.assertEqual((t.cy,t.cx),(3,7))
    def test_relative(self):
        t=term(b'\33[5;5H\33[2A\33[3C\33[B\33[DX')
        self.assertEqual(t.cells[3][6],(88,7,0)); self.assertEqual((t.cy,t.cx),(3,7))
    def test_hpa_vpa(self):
        t=term(b'\33[9G\33[4dX'); self.assertEqual(t.cells[3][8],(88,7,0))
    def test_defaults_and_clamps(self):
        t=term(b'\33[999;999HX\33[0;0HY')
        self.assertEqual(t.cells[-1][-1],(88,7,0)); self.assertEqual(t.cells[0][0],(89,7,0))
        self.assertEqual((t.cy,t.cx,t.wrap),(0,1,False))
    def test_negative_clamps(self):
        t=term(b'\33[999A\33[999DX'); self.assertEqual(t.cells[0][0],(88,7,0))
    def test_private_is_not_cup(self):
        t=term(b'\33[?5;5HX'); self.assertEqual(t.cells[0][0],(88,7,0))
    def test_parameter_capacity(self):
        for n in (8, 9, 15, 16):
            with self.subTest(n=n):
                t=term(('\33[3;4' + ';0'*(n-2) + 'HX').encode())
                self.assertEqual(t.cells[2][3],(88,7,0))
    def test_parameter_overflow_is_ignored(self):
        for n in (17, 18, 32):
            with self.subTest(n=n):
                t=term(('\33[3;4' + ';0'*(n-2) + 'HX').encode())
                self.assertEqual(t.cells[0][0],(88,7,0))

class Erase(unittest.TestCase):
    def test_ed(self):
        for mode,want in [(0,[(0,0,97)]),(1,[(0,2,99),(1,0,100),(1,1,101),(1,2,102)]),(2,[])]:
            t=term(b'abc\33[2;1Hdef\33[1;2H'+f'\33[{mode}J'.encode())
            got=[(y,x,c[0]) for y,row in enumerate(t.cells) for x,c in enumerate(row) if c[0]!=32]
            self.assertEqual(got,want); self.assertEqual((t.cy,t.cx),(0,1))
    def test_el(self):
        for mode,want in [(0,'ab   '),(1,'   de'),(2,'     ')]:
            t=term(b'abcde\33[1;3H'+f'\33[{mode}K'.encode())
            self.assertEqual(''.join(chr(c[0]) for c in t.cells[0][:5]),want)
            self.assertEqual((t.cy,t.cx),(0,2))
    def test_invalid_mode(self):
        t=term(b'abc\33[9J\33[9K'); self.assertEqual(t.cells[0][:3],[(97,7,0),(98,7,0),(99,7,0)])

class Rendition(unittest.TestCase):
    def test_reset_parts(self):
        t=term(b'\33[1mA\33[22mB\33[7mC\33[27mD')
        self.assertEqual(t.cells[0][:4],[(65,15,0),(66,7,0),(67,0,7),(68,7,0)])
    def test_bright_background(self):
        t=term(b'\33[101mA'); self.assertEqual(t.cells[0][0],(65,7,9))
    def test_indexed(self):
        t=term(b'\33[38;5;196mR\33[48;5;46mG\33[38;5;244mX')
        self.assertEqual(t.cells[0][:3],[(82,9,0),(71,9,2),(88,7,2)])
    def test_palette(self):
        rows=(pathlib.Path(__file__).resolve().parent/'vt.rows').read_text().splitlines()
        swap=lambda v: (v&10)|((v&1)<<2)|((v&4)>>2)
        for bg in (False,True):
            line=next(l for l in rows if l.startswith('PALETTE '+('BG' if bg else 'FG')+' '))
            values=[int(x,16) for x in line.split()[2:]]
            for i,v in enumerate(values):
                t=term(f'\33[{48 if bg else 38};5;{i}mX'.encode())
                self.assertEqual(t.cells[0][0][2 if bg else 1],swap(v>>4 if bg else v&15),(bg,i))

class Truecolour(unittest.TestCase):
    def test_measured_rgb_cube(self):
        rows=(pathlib.Path(__file__).resolve().parent/'rgb70.rows').read_text().splitlines()
        self.assertEqual(len(rows), 19683)
        swap=lambda v: (v&10)|((v&1)<<2)|((v&4)>>2)
        for line in rows:
            _,r,g,b,fg,bg=line.split()
            t=term(('\33[38;2;%s;%s;%smX\33[0;48;2;%s;%s;%smX' % (r,g,b,r,g,b)).encode())
            self.assertEqual((t.cells[0][0][1],t.cells[0][1][2]),
                             (swap(int(fg,16)&15),swap((int(bg,16)>>4)&7)),line)

class Editing(unittest.TestCase):
    def test_character_edits_clamp_and_keep_cursor(self):
        for op,want in [('@','ab  c'),('P','abe  '),('X','ab  e')]:
            t=term(('abcde\33[1;3H\33[2'+op).encode(),5,3)
            self.assertEqual(''.join(chr(c[0]) for c in t.cells[0]),want)
            self.assertEqual((t.cx,t.cy),(2,0))
    def test_region_rejects_one_line_and_out_of_range(self):
        for margin in ('2;2','2;999','3;2'):
            t=term(('\33[3;4H\33['+margin+'r').encode(),8,5)
            self.assertEqual((t.top,t.end,t.cx,t.cy),(0,5,3,2))
    def test_region_scroll_keeps_surroundings(self):
        t=term(b'a\r\nb\r\nc\r\nd\33[2;3r\33[3;1HX\nY',4,4)
        self.assertEqual([r[0][0] for r in t.cells],[97,88,32,100])
        self.assertEqual(t.cells[2][1][0],89)
    def test_line_edit_above_top_and_at_bottom(self):
        t=term(b'a\r\nb\r\nc\r\nd\33[2;3r\33[1;2H\33[2L',4,4)
        self.assertEqual([r[0][0] for r in t.cells],[32,32,97,100])
        t=term(b'a\r\nb\r\nc\33[2;3r\33[3;2H\33[M',4,4)
        self.assertEqual([r[0][0] for r in t.cells],[97,98,99,32])

class Attributes(unittest.TestCase):
    def test_precedence_and_inverse(self):
        t=term(b'\33[31;44;1;7mA\33[0;31;44;2;7mB')
        self.assertEqual(t.cells[0][:2],[(65,12,1),(66,12,0)])
    def test_record_blink_without_animation(self):
        t=term(b'\33[5mA\33[25mB')
        self.assertEqual(t.cells[0][:2],[(65,7,16),(66,7,0)])
    def test_truecolour_intensity_survives_foreground(self):
        t=term(b'\33[38:2::10:200:30mA')
        self.assertEqual(t.cells[0][0],(65,8,0))
    def test_save_rendition_flags(self):
        t=term(b'\33[31;2;3;4;5m\33' b'7\33[0m\33' b'8A')
        self.assertEqual(t.cells[0][0],(65,2,16))

class Osc(unittest.TestCase):
    def test_bel_and_st(self):
        for end in (b'\7',b'\33\\'):
            t=term(b'A\33]52;c;eA=='+end+b'B')
            self.assertEqual(t.cells[0][:3],[(65,7,0),(66,7,0),(32,7,0)])
    def test_any_esc_ends_it(self):
        # the VT's OSC-ESC and OSC-C0 rows: a C0 byte inside is consumed,
        # any ESC ends the string and starts the next sequence
        t=term(b'A\33]52;ignored\n\33[31mZ')
        self.assertEqual((t.cy,t.cx),(0,2)); self.assertEqual(t.cells[0][1],(90,1,0))
    def test_palette_string(self):
        t=term(b'A\33]P1ff0000B\33]RC'); self.assertEqual(''.join(chr(c[0]) for c in t.cells[0][:3]),'ABC')

class Save(unittest.TestCase):
    def test_position_and_attributes(self):
        t=term(b'\33[31m\33[3;5H\0337\33[32m\33[H\0338X')
        self.assertEqual(t.cells[2][4],(88,1,0)); self.assertEqual((t.cy,t.cx),(2,5))

class Alternate(unittest.TestCase):
    def test_restore(self):
        t=term(b'MAIN\33[?1049h\33[Halt\33[?1049lX')
        self.assertEqual(''.join(chr(c[0]) for c in t.cells[0][:6]),'MAINX ')
    def test_entry_and_nested(self):
        t=term(b'MAIN\33[?1049hA\33[?1049hB')
        self.assertEqual(''.join(chr(c[0]) for c in t.cells[0][:7]),'    AB ')
        self.assertEqual((t.cy,t.cx),(0,6))
    def test_restore_attributes(self):
        t=term(b'\33[31mMAIN\33[?1049h\33[32mA\33[?1049lB')
        self.assertEqual(t.cells[0][4],(66,1,0))
    def test_scroll_both(self):
        t=term(b'A\r\nB\r\nC\r\nD',4,3)
        saved=[row[:] for row in t.cells]
        for b in b'\33[?1049h\33[HX\r\nY\r\nZ\r\nW': t.feed(b)
        self.assertEqual([row[0][0] for row in t.cells],[89,90,87])
        for b in b'\33[?1049l': t.feed(b)
        self.assertEqual(t.cells,saved)
        for b in b'\r\nE': t.feed(b)
        self.assertEqual([row[0][0] for row in t.cells],[67,68,69])

class Cursor2(unittest.TestCase):
    def test_visibility(self):
        t=term(b'\33[?25lA'); self.assertFalse(t.visible)
        for b in b'\33[?25h': t.feed(b)
        self.assertTrue(t.visible)
    def test_shape_recorded(self):
        t=term(b'\33[6 qA'); self.assertEqual(t.shape,6); self.assertEqual(t.cells[0][0],(65,7,0))
        for b in b'\33[7 q\33[2;3 q': t.feed(b)
        self.assertEqual(t.shape,6)
    def test_backspace_at_the_margin(self):
        t=term(b'\33[1;79HAB\10C',80,25)
        self.assertEqual([c[0] for c in t.cells[0][78:]],[67,66]); self.assertEqual((t.cx,t.wrap),(79,False))
    def test_next_previous_line(self):
        t=term(b'\33[3;5H\33[2EX\33[1FY'); self.assertEqual((t.cells[4][0][0],t.cells[3][0][0]),(88,89))

class Answers(unittest.TestCase):
    def test_queries(self):
        t=term(b'\33[c\33Z\33[5n\33[3;5H\33[6n\33[?6n\33[>c')
        self.assertEqual(bytes(t.answers),b'\33[?6c\33[?6c\33[0n\33[3;5R\33[3;5R')
    def test_wrap_report(self):
        t=term(b'\33[1;80HX\33[6n',80,25); self.assertEqual(bytes(t.answers),b'\33[1;80R')

class Scroll(unittest.TestCase):
    def test_new_row_in_the_background(self):
        t=term(b'\33[3;1H\33[44mA\r\nB',4,3)
        self.assertEqual(t.cells[2],[(66,7,4),(32,7,4),(32,7,4),(32,7,4)])

if __name__=='__main__': unittest.main(verbosity=2)
