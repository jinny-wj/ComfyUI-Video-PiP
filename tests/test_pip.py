import unittest
import torch
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("pip_engine", Path(__file__).resolve().parents[1]/"pip.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
composite_frames, SHAPES = module.composite_frames, module.SHAPES


class PiPTests(unittest.TestCase):
    def test_shapes_and_input_immutability(self):
        bg = torch.zeros(3, 64, 96, 3)
        fg = torch.ones(2, 30, 40, 3)
        masks = []
        for shape in SHAPES:
            out, mask = composite_frames(bg, fg, 24, 24, shape=shape, width=40, height=30,
                                         position='居中', corner_radius=8, border_width=0)
            self.assertEqual(out.shape, bg.shape)
            self.assertEqual(mask.shape, (1, 64, 96))
            self.assertTrue(torch.isfinite(out).all())
            self.assertEqual(float(out[0, 32, 48, 0]), 1.)
            self.assertEqual(float(out[0, 0, 0, 0]), 0.)
            masks.append(mask)
        self.assertEqual(len({m.numpy().tobytes() for m in masks}), 5)
        self.assertEqual(float(bg.sum()), 0.)
        self.assertTrue(torch.all(fg == 1))

    def test_timeline_fps_and_end_modes(self):
        bg = torch.zeros(6, 8, 8, 3)
        fg = torch.stack([torch.full((8, 8, 3), .2), torch.full((8, 8, 3), .8)])
        for mode, values in [('循环', [.2,.2,.8,.8,.2,.2]), ('保持末帧', [.2,.2,.8,.8,.8,.8]),
                             ('结束后隐藏', [.2,.2,.8,.8,0,0])]:
            out, _ = composite_frames(bg, fg, 4, 2, shape='矩形', width=8, height=8,
                                      position='自定义', border_width=0, short_video=mode)
            torch.testing.assert_close(out[:,4,4,0], torch.tensor(values))

    def test_offscreen_clipping_and_opacity(self):
        bg, fg = torch.zeros(1,16,16,3), torch.ones(1,8,8,3)
        out, mask = composite_frames(bg,fg,24,24,shape='矩形',position='自定义',x=-4,y=-4,
                                      width=8,height=8,opacity=.5,border_width=0)
        self.assertAlmostEqual(float(out[0,1,1,0]), .5)
        self.assertEqual(float(out[0,8,8,0]), 0.)
        out, mask = composite_frames(bg,fg,24,24,position='自定义',x=99,width=8,height=8)
        self.assertTrue(torch.equal(out,bg))
        self.assertEqual(float(mask.sum()),0.)

    def test_border_and_bad_color(self):
        bg, fg = torch.zeros(1,32,32,3), torch.ones(1,32,32,3)
        out, _ = composite_frames(bg,fg,24,24,shape='矩形',position='自定义',width=32,height=32,
                                   border_width=4,border_color='#FF0000')
        torch.testing.assert_close(out[0,1,16],torch.tensor([1.,0.,0.]))
        torch.testing.assert_close(out[0,16,16],torch.ones(3))
        with self.assertRaises(ValueError):
            composite_frames(bg,fg,24,24,border_color='bad')

if __name__ == '__main__':
    unittest.main()
