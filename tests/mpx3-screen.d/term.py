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

if __name__=='__main__': unittest.main(verbosity=2)
