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
    def test_parameter_overflow_is_ignored(self):
        t=term(b'\33[3;4;0;0;0;0;0;0;0HX'); self.assertEqual(t.cells[0][0],(88,7,0))

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
        rows=(pathlib.Path(__file__).resolve().parents[2]/'notes/px59/vt.rows').read_text().splitlines()
        swap=lambda v: (v&10)|((v&1)<<2)|((v&4)>>2)
        for bg in (False,True):
            line=next(l for l in rows if l.startswith('PALETTE '+('BG' if bg else 'FG')+' '))
            values=[int(x,16) for x in line.split()[2:]]
            for i,v in enumerate(values):
                t=term(f'\33[{48 if bg else 38};5;{i}mX'.encode())
                self.assertEqual(t.cells[0][0][2 if bg else 1],swap(v>>4 if bg else v&15),(bg,i))

class Osc(unittest.TestCase):
    def test_bel_and_st(self):
        for end in (b'\7',b'\33\\'):
            t=term(b'A\33]52;c;eA=='+end+b'B')
            self.assertEqual(t.cells[0][:3],[(65,7,0),(66,7,0),(32,7,0)])
    def test_unterminated(self):
        t=term(b'A\33]52;ignored\n\33[31mZ'); self.assertEqual((t.cy,t.cx),(0,1))

if __name__=='__main__': unittest.main(verbosity=2)
