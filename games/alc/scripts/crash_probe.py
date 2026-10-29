"""lldb-driven crash inspection for the Astral Chain stage-3 boot.

Run (from AC_build):
  lldb -b build/alc-native -o "command script import ../scripts/crash_probe.py" -o alcprobe -o quit

Waits for main's seal, reads the module base dynamically (it is not stable across runs), arms a write
watchpoint on the BSS object field the game dereferences (base+0xcc9cd98+0x28), breaks once at the crash
function's entry (base+0x9c0cd0), then continues to the SIGSEGV and dumps guest registers, the object and
the pointer table.
"""
import lldb
import struct
import sys
import time


def out(msg):
    print(msg)
    sys.stdout.flush()


def alcprobe(debugger, command, exe_ctx, result, _dict):
    target = debugger.GetSelectedTarget()
    out("alcprobe: arming")
    bp_seal = target.BreakpointCreateByName('seal')
    si = lldb.SBLaunchInfo(['rewritten/v101', 'boot'])
    si.SetWorkingDirectory('/Volumes/bit2t/switch/MacNativeGames/games/alc/AC_build')
    err = lldb.SBError()
    process = target.Launch(si, err)
    if not process or not process.IsValid():
        out(f"launch failed: {err}"); return
    waited = 0
    while process.GetState() in (lldb.eStateRunning, lldb.eStateLaunching, lldb.eStateAttaching):
        time.sleep(0.1); waited += 0.1
        if waited > 60: break
    frame = process.GetSelectedThread().GetFrameAtIndex(0)
    base_v = frame.EvaluateExpression('(uint8_t*)modules[0].base')
    base = int(base_v.GetValueAsUnsigned() or 0)
    out(f"alcprobe: main base = {base:#x}")
    if not base:
        out("no base"); return
    try:
        bp_seal.SetEnabled(False)
        field = base + 0xcc9cd98 + 0x28
        obj = base + 0xcc9cd98
        wp = target.WatchAddress(field, 8, False, True, err)   # read=off, write=on
        out(f"watchpoint on {field:#x}: valid={wp.IsValid()} err={err}")
        bp_crash = target.BreakpointCreateAtAddress(lldb.SBAddress(base + 0x9c0cd0, target))
        bp_crash.SetOneShot(True)
    except Exception as e:
        out(f"arm failed: {e!r}"); return

    def dump(tag):
        try:
            _dump(tag)
        except Exception as e:
            out(f"dump failed: {e!r}")

    def _dump(tag):
        th = process.GetSelectedThread()
        f = th.GetFrameAtIndex(0)
        regs = {}
        for r in ('x0', 'x1', 'x2', 'x3', 'x8', 'x9', 'x10', 'x21', 'x23', 'x24', 'pc', 'lr'):
            v = f.FindRegister(r)
            regs[r] = v.GetValueAsUnsigned() if v else 0
        out(f"[{tag}] stop={th.GetStopDescription(120)}")
        out(f"[{tag}] " + ' '.join(f"{k}={v:#x}" for k, v in regs.items()))
        for name, addr, n in (('object', obj, 10), ('ptrtable', base + 0xdc2688, 6)):
            data = process.ReadMemory(addr, 8 * n, err)
            if data:
                vals = struct.unpack(f'<{n}Q', data)
                out(f"[{tag}] {name} @{addr:#x}: " + ' '.join(f"{v:#x}" for v in vals))
            else:
                out(f"[{tag}] {name} read failed: {err}")

    for round_i in range(6):
        process.Continue()
        if process.GetState() != lldb.eStateStopped:
            out(f"state {process.GetState()}"); return
        th = process.GetSelectedThread()
        reason = th.GetStopReason()
        if reason == lldb.eStopReasonWatchpoint:
            dump(f"watch#{round_i}")
        elif reason == lldb.eStopReasonBreakpoint:
            dump(f"entry#{round_i}")
        elif reason == lldb.eStopReasonSignal:
            dump("SEGV"); return
        else:
            dump(f"other#{round_i}({reason})")
    out("alcprobe: rounds exhausted")


def __lldb_init_module(debugger, _dict):
    debugger.HandleCommand('command script add -f crash_probe.alcprobe alcprobe')
