"""lldb-driven crash inspection for the Astral Chain stage-3 boot.

Run:  lldb -b build/alc-native -o "command script import ../scripts/crash_probe.py" -o "alcprobe" -o quit
(from AC_build). Waits for main's seal, arms a write watchpoint on the BSS object field the game
dereferences (base+0xcc9cd98+0x28), breaks at the crash function entry once, continues to the crash and
dumps guest registers, the object, and the pointer table.
"""
import lldb
import struct


def alcprobe(debugger, command, exe_ctx, result, _dict):
    target = debugger.GetSelectedTarget()
    print("alcprobe: arming\n")
    bp_seal = target.BreakpointCreateByName('seal')
    si = lldb.SBLaunchInfo(['rewritten/v101', 'boot'])
    si.SetWorkingDirectory('/Volumes/bit2t/switch/MacNativeGames/games/alc/AC_build')
    err = lldb.SBError()
    process = target.Launch(si, err)
    if not process or not process.IsValid():
        print(f"launch failed: {err}\n"); return
    # wait for the first seal stop
    import time
    waited = 0
    while process.GetState() in (lldb.eStateRunning, lldb.eStateLaunching, lldb.eStateAttaching):
        time.sleep(0.1); waited += 0.1
        if waited > 60: break
    frame = process.GetSelectedThread().GetFrameAtIndex(0)
    base_v = frame.EvaluateExpression('(uint8_t*)modules[0].base')
    base = int(base_v.GetValueAsUnsigned() or 0)
    print(f"alcprobe: main base = {base:#x}\n")
    if not base:
        print("no base\n"); return
    bp_seal.SetEnabled(False)
    field = base + 0xcc9cd98 + 0x28
    obj = base + 0xcc9cd98
    wp = target.WatchAddress(field, 8, lldb.eWatchpointModeWrite, lldb.eWatchpointKindWrite, err)
    print(f"watchpoint on {field:#x}: {err}\n" if False else f"watchpoint on {field:#x}: valid={wp.IsValid()}\n")
    bp_crash = target.BreakpointCreateAtAddress(lldb.SBAddress(base + 0x9c0cd0, target))
    bp_crash.SetOneShot(True)

    def dump(tag):
        th = process.GetSelectedThread()
        f = th.GetFrameAtIndex(0)
        regs = {}
        for r in ('x0', 'x1', 'x2', 'x3', 'x8', 'x9', 'x10', 'x21', 'x23', 'x24', 'pc', 'lr'):
            v = f.FindRegister(r)
            regs[r] = v.GetValueAsUnsigned() if v else 0
        print(f"[{tag}] stop={th.GetStopDescription(120)}\n")
        print(f"[{tag}] " + ' '.join(f"{k}={v:#x}" for k, v in regs.items()) + "\n")
        for name, addr, n in (('object', obj, 10), ('ptrtable', base + 0xdc2688, 6)):
            data = process.ReadMemory(addr, 8 * n, err)
            if data:
                vals = struct.unpack(f'<{n}Q', data)
                print(f"[{tag}] {name} @{addr:#x}: " + ' '.join(f"{v:#x}" for v in vals) + "\n")
            else:
                print(f"[{tag}] {name} read failed: {err}\n")

    # continue; watchpoint stops come first (if any), then the crash-fn entry, then the SIGSEGV
    for round_i in range(6):
        process.Continue()
        if process.GetState() != lldb.eStateStopped:
            print(f"state {process.GetState()}\n"); return
        th = process.GetSelectedThread()
        reason = th.GetStopReason()
        if reason == lldb.eStopReasonWatchpoint:
            dump(f"watch#{round_i}")
            continue
        if reason == lldb.eStopReasonBreakpoint:
            dump(f"entry#{round_i}")
            continue
        if reason == lldb.eStopReasonSignal:
            dump("SEGV")
            return
        dump(f"other#{round_i}({reason})")
        continue
    print("alcprobe: rounds exhausted\n")


def __lldb_init_module(debugger, _dict):
    debugger.HandleCommand('command script add -f crash_probe.alcprobe alcprobe')
