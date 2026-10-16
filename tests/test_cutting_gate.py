import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

p=Path(__file__).resolve().parents[1]/'src/sim_evals/environments/cutting_physics.py'
spec=importlib.util.spec_from_file_location('cutting_gate_test_module',p)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class GateTests(unittest.TestCase):
    def stroke(self,g,x=0,y=0,axis=(0,1,0)):
        return [g.update([x,y,z],axis) for z in np.linspace(.035,-.023,20)]
    def test_valid(self):
        g=m.CutGate(); self.assertEqual(sum(self.stroke(g)),1);self.assertTrue(g.cut)
        self.assertFalse(g.update([0,0,-.03],[0,1,0]))
    def test_wrong_side(self):
        self.assertFalse(any(self.stroke(m.CutGate(),x=.04)))
    def test_wrong_direction(self):
        self.assertFalse(any(self.stroke(m.CutGate(),axis=(1,0,0))))
    def test_misses_width(self):
        self.assertFalse(any(self.stroke(m.CutGate(),y=.08)))
    def test_teleport(self):
        g=m.CutGate();g.update([0,0,.035],[0,1,0]);self.assertFalse(g.update([0,0,-.03],[0,1,0]))
    def test_below_without_entry(self):
        self.assertFalse(m.CutGate().update([0,0,-.025],[0,1,0]))
    def test_upward(self):
        g=m.CutGate();self.assertFalse(any(g.update([0,0,z],[0,1,0]) for z in np.linspace(-.03,.035,20)))
    def test_leaves_seam(self):
        g=m.CutGate();g.update([0,0,.035],[0,1,0]);g.update([.1,0,.01],[0,1,0]);self.assertFalse(g.update([0,0,-.021],[0,1,0]))
    def test_nan(self):
        self.assertFalse(m.CutGate().update([float('nan'),0,0],[0,1,0]))

if __name__=='__main__':unittest.main()
