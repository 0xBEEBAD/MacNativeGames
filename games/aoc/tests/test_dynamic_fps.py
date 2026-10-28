"""Execute AoC's generated ARM64 timing stubs against synthetic game objects.

Install the optional test dependency `unicorn` to run these instruction-level
checks. No game binaries or renderer are used.
"""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
from types import SimpleNamespace

try:
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import *
except ImportError:
    Uc = None

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME / 'runtime/tools'))
spec = importlib.util.spec_from_file_location('aoc_patches_test', GAME / 'runtime/games/01002B00111A2000/patches.py')
patches = importlib.util.module_from_spec(spec); spec.loader.exec_module(patches)

@unittest.skipUnless(Uc, 'install unicorn for instruction-level AoC timing tests')
class DynamicTimingTests(unittest.TestCase):
    BASE=0x10000000
    STATE=0x3000000
    def setUp(self):
        self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.u.mem_map(self.BASE,0x4000000)
        pc=0x3100000;self.sites={};self.originals={}
        def emit(word):
            nonlocal pc
            self.u.mem_write(self.BASE+pc,struct.pack('<I',word));pc+=4
        def put(off,words,reason):
            self.sites[off]=off+4
            self.u.mem_write(self.BASE+off,struct.pack('<'+'I'*len(words),*words))
        ctx=SimpleNamespace(here=lambda:pc,emit=emit,state=self.STATE,site=lambda off,orig:self.originals.update({off:orig}),put=put)
        patches.frame_step(ctx)
        self.assertEqual(ctx.aoc_timing_abi,3)
        self.assertEqual(self.originals[0x166dc60],'e83640b9681a00b9e04640bd')
        self.sites[0x166dc60]=0x166dc6c
        self.u.reg_write(UC_ARM64_REG_X19,self.BASE+0x3500000)
        self.u.reg_write(UC_ARM64_REG_X27,self.BASE+0x3501000)
        self.u.reg_write(UC_ARM64_REG_X23,self.BASE+0x3502000)
        self.write(0x1ef5f3c,'f',59.94)
        self.write(0x2bac798,'Q',self.BASE+0x3503000)
        self.write(0x3502048,'I',30)
        self.write(0x3502034,'f',1/30)
        self.write(0x3502044,'f',1/30)
        self.write(self.STATE+0x50,'f',.1)
        self.write(self.STATE+0x54,'f',.001)
        self.write(self.STATE+0x60,'f',1e-9)
        self.native_ticks=1000000000
        def counter(uc,address,size,user):
            if bytes(uc.mem_read(address,4))==bytes.fromhex('51e03bd5'):
                uc.reg_write(UC_ARM64_REG_X17,self.native_ticks);uc.reg_write(UC_ARM64_REG_PC,address+4)
        self.u.hook_add(UC_HOOK_CODE,counter)
    def write(self,off,fmt,value):self.u.mem_write(self.BASE+off,struct.pack('<'+fmt,value))
    def read(self,off,fmt):return struct.unpack('<'+fmt,self.u.mem_read(self.BASE+off,struct.calcsize(fmt)))[0]
    def configure(self,target,dynamic=True):
        self.write(self.STATE,'f',target);self.write(self.STATE+0x38,'I',int(dynamic))
    def run_site(self,site):self.u.emu_start(self.BASE+site,self.BASE+self.sites[site],count=500)
    def update(self,dt):
        self.run_site(0x166dab4)
        # s1 is work before the wait; it is deliberately much shorter.
        self.u.reg_write(UC_ARM64_REG_S1,int.from_bytes(struct.pack('<f',.0001),'little'))
        self.u.reg_write(UC_ARM64_REG_X21,10000000)
        self.u.reg_write(UC_ARM64_REG_X0,10000000+round(dt*19200000))
        self.u.reg_write(UC_ARM64_REG_X24,19200000)
        self.run_site(0x166dc60)
        return self.read(0x3500018,'f')
    def test_30_60_120_keep_clock_battle_and_events_in_sync(self):
        for target in (30,60,120):
            self.configure(target)
            before=self.read(self.STATE+0x40,'d')
            for i in range(target*2):
                self.assertAlmostEqual(self.update(1/target),1/target,places=7)
            self.assertAlmostEqual(self.read(self.STATE+0x40,'d')-before,2,places=5)
            self.assertEqual(self.read(0x3500030,'I'),target)
            self.assertAlmostEqual(self.read(0x269e15c,'f'),target,places=3)
            self.assertAlmostEqual(self.read(0x35062d0,'f'),target*59.94/60,places=3)
            self.assertEqual(self.read(0x269e154,'I'),2 if target==30 else 1)
    def test_variable_intervals_preserve_elapsed_time(self):
        self.configure(120)
        route=[1/120,1/60,1/45,.040,1/90]*60
        for dt in route:self.assertAlmostEqual(self.update(dt),dt,places=7)
        self.assertAlmostEqual(self.read(self.STATE+0x40,'d'),sum(route),places=5)
        # Battle/event rate consumes the preceding measured step, not cap 120.
        self.run_site(0x166dab4)
        self.assertAlmostEqual(self.read(0x269e15c,'f'),90,places=3)
    def test_live_switches_and_original_mode_restore_30(self):
        for target in (120,30,60,0,120,0):
            self.configure(target)
            self.update(1/(target or 30))
            self.assertEqual(self.read(0x3500030,'I'),target or 30)
            self.assertAlmostEqual(self.read(0x269e15c,'f'),target or 30,places=3)
            self.assertEqual(self.read(0x3505aa4,'I'),2 if target<=30 else 1)
        self.assertAlmostEqual(self.read(0x3500018,'f'),1/30,places=7)
    def test_fixed_mode_and_long_pause_are_bounded(self):
        self.configure(120,False)
        self.assertAlmostEqual(self.update(.025),1/120,places=7)
        self.configure(120,True)
        self.assertAlmostEqual(self.update(5),.1,places=6)
        self.assertAlmostEqual(self.update(0),.001,places=7)
    def test_original_object_timescale_is_preserved(self):
        self.configure(60)
        self.write(0x3502034,'f',.5/30)
        self.write(0x3502044,'f',.25/30)
        self.assertAlmostEqual(self.update(.02),.01,places=7)
        value=self.u.reg_read(UC_ARM64_REG_S0)
        self.assertAlmostEqual(struct.unpack('<f',value.to_bytes(4,'little'))[0],.005,places=7)
    def test_scene_clock_follows_48hz_when_task_target_is_120(self):
        self.configure(120)
        self.update(1/120)
        self.u.reg_write(UC_ARM64_REG_X8,0x12345678)
        self.u.reg_write(UC_ARM64_REG_X9,self.BASE+0x269e000)
        self.run_site(0x8c3610)
        before=self.read(self.STATE+0x80,'d')
        for i in range(96):
            self.update(1/120)
            self.native_ticks+=round(1e9/48)
            self.u.reg_write(UC_ARM64_REG_X8,0x12345678)
            self.run_site(0x8c3610)
            self.assertEqual(self.u.reg_read(UC_ARM64_REG_X8),0x12345678)
        self.assertAlmostEqual(self.read(self.STATE+0x80,'d')-before,2,places=5)
        self.assertAlmostEqual(self.read(0x269e15c,'f'),48,places=3)
        self.update(1/120)
        self.assertAlmostEqual(self.read(0x269e15c,'f'),48,places=3)
        self.assertEqual(self.read(0x3500030,'I'),120)
        self.assertEqual(self.read(self.STATE+0x78,'Q'),97)
    def test_scene_original_and_long_gap(self):
        self.configure(0);self.write(0x269e15c,'f',30)
        self.u.reg_write(UC_ARM64_REG_X9,self.BASE+0x269e000);self.run_site(0x8c3610)
        self.assertEqual(self.u.reg_read(UC_ARM64_REG_S9),int.from_bytes(struct.pack('<f',30),'little'))
        self.configure(60);self.run_site(0x8c3610)
        self.native_ticks+=5_000_000_000;self.run_site(0x8c3610)
        self.assertAlmostEqual(self.read(self.STATE+0x70,'f'),.1,places=6)
    def test_device_interval_and_absent_device(self):
        for target in (0,30,60,120):
            self.configure(target);self.u.reg_write(UC_ARM64_REG_X9,0)
            self.run_site(0x8d94b0)
            self.assertEqual(self.u.reg_read(UC_ARM64_REG_X9)>>32,2 if target<=30 else 1)
        self.write(0x2bac798,'Q',0)
        self.configure(120);self.run_site(0x166dab4)

if __name__=='__main__':unittest.main()
