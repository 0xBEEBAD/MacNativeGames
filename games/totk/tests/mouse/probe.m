/* runtime/gamepad.m's mouse mode: buttons to the keyboard and mouse layout (runtime/input.c, here a stand-in) and, for
   mouse lines in controls.txt, the controller layout; movement as the right stick and the gyro; the sensitivity slider;
   release, and the saved on / off. The real file is compiled in; the 10 ms ticks are driven here (mouseTicksByHand). */
#include "../../runtime/gamepad.m"

_Noreturn void runtime_fail(const char *message) { fprintf(stderr, "FAIL: %s\n", message); exit(1); }
static uint64_t clockNow = 1000000000ull;
uint64_t runtime_now_ns(void) { return clockNow; }
void runtime_feedback_attach(GCController *controller) { (void)controller; }
void runtime_feedback_detach(GCController *controller) { (void)controller; }
void runtime_feedback_quiet(void) {}
static int gyroOn = 1, motionMouse = -1, feeds, hookCalls;
static double lastYaw, lastAcc;
int runtime_gyro_enabled(void) { return gyroOn; }
void runtime_motion_mouse(int on) { motionMouse = on; }
void runtime_motion_feed_mouse(const double acc[3], const double gyro[3], uint64_t now) { (void)now; feeds++; lastYaw = gyro[2]; lastAcc = acc[2]; }
static void hook(void) { hookCalls++; }
static unsigned layoutHeld; static int layoutCalls;   /* runtime/input.c's mouse buttons: what reached the layout */
void runtime_input_mouse(int button, int down) { layoutCalls++; layoutHeld = down ? layoutHeld | 1u << button : layoutHeld & ~(1u << button); }

static int failures, checked;
static void check(int ok, const char *what) { checked++; if (!ok) { failures++; fprintf(stderr, "FAIL: %s\n", what); } }
static int file_says(const char *path, const char *text) {
    char got[64] = {0}; FILE *f = fopen(path, "r"); if (!f) return 0;
    size_t n = fread(got, 1, sizeof got - 1, f); fclose(f); got[n] = 0; return !strcmp(got, text);
}
static RuntimeGamepadState settle(void) { RuntimeGamepadState s; runtime_gamepad_read(&s); runtime_gamepad_read(&s); return s; }   /* past latched presses */
static void spin(void) { [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.02]]; }
enum { Y = 1 << 3, ZL = 1 << 8, ZR = 1 << 9 };

int main(int argc, char **argv) { @autoreleasepool {
    if (argc != 2) { fprintf(stderr, "usage: probe <empty folder>\n"); return 2; }
    char controls[1024], saved[1100];
    snprintf(controls, sizeof controls, "%s/controls.txt", argv[1]);
    snprintf(saved, sizeof saved, "%s/mouse.txt", argv[1]);
    setenv("TOTK_CONTROLS", controls, 1);
    mouseTicksByHand = 1;
    controller_map_default(controllerMap, controllerModes);
    runtime_mouse_set_hook(hook);

    check(!runtime_mouse_enabled(), "mouse mode starts off");
    runtime_mouse_button(0, 1); runtime_mouse_move(10, 0); mouse_tick();
    RuntimeGamepadState s = settle();
    check(!s.buttons && !s.rx && !s.ry, "mouse mode off: clicks and movement do nothing");
    runtime_mouse_button(0, 0);

    check(runtime_mouse_set(1) == 1 && runtime_mouse_enabled() && file_says(saved, "on\n") && motionMouse == 1, "settings: on, saved, the mouse takes the gyro");
    check(runtime_mouse_set(1) == 1 && motionMouse == 1, "on again: no change");
    spin(); check(hookCalls == 1, "the window is told (to capture the pointer)");
    runtime_mouse_button(0, 1); s = settle(); check(layoutHeld == 1 && !s.buttons, "left button: to the keyboard and mouse layout, nothing from the controller's");
    runtime_mouse_button(0, 1); check(layoutCalls == 1, "a button already down: no second call");
    runtime_mouse_button(0, 0); runtime_mouse_button(1, 1); runtime_mouse_button(2, 1); check(layoutHeld == 6, "right and middle reach the layout");
    runtime_mouse_button(1, 0); runtime_mouse_button(2, 0); runtime_mouse_button(9, 1); check(!layoutHeld, "a button number out of range is ignored");
    /* A mouse line in controls.txt still drives its Switch button, the bow's aim included. */
    const char *error = NULL;
    check(!controller_map_parse("mouse_left = y\nmouse_right = zr aim mouse_left\nmouse_middle = zl\n", controllerMap, controllerModes, &error), "mouse lines parse");
    runtime_mouse_button(0, 1); s = settle(); check(s.buttons == Y, "left button: attack (Y)");
    runtime_mouse_button(0, 0); s = settle(); check(!s.buttons, "left button up");
    runtime_mouse_button(1, 1); s = settle(); check(s.buttons == ZR, "right button held: draw the bow (ZR)");
    runtime_mouse_button(0, 1); s = settle(); check(!s.buttons, "left click while drawing: ZR let go (the shot), no attack");
    runtime_mouse_button(0, 0); s = settle(); check(s.buttons == ZR, "left up, right still held: drawing again");
    runtime_mouse_button(1, 0); runtime_mouse_button(2, 1); s = settle(); check(s.buttons == ZL, "middle button: target (ZL)");
    runtime_mouse_button(2, 0); s = settle(); check(!s.buttons, "middle up");
    controller_map_default(controllerMap, controllerModes);
    runtime_mouse_move(10, 0); mouse_tick(); s = settle();
    check(abs(s.rx - 16384) <= 1 && !s.ry, "10 points right: half the right stick right");
    check(feeds == 1 && lastYaw < 0 && lastAcc == -1, "and the gyro turns clockwise, lying flat");
    mouse_tick(); s = settle(); check(s.rx > 0 && s.rx < 16384 && feeds == 2, "it decays tick by tick, the gyro keeps sampling");
    runtime_mouse_button(0, 1); runtime_mouse_release(); mouse_tick(); s = settle();
    check(!s.buttons && !s.rx && !s.ry && !layoutHeld, "release (the window lost the pointer): buttons up, also in the layout, stick centred");

    /* The settings panel's sensitivity: at once, saved, read at the next start; TOTK_MOUSE_SENSITIVITY decides over it. */
    char sensitivity[1100]; snprintf(sensitivity, sizeof sensitivity, "%s/mouse-sensitivity.txt", argv[1]);
    check(runtime_mouse_sensitivity() == 50 && !runtime_mouse_sensitivity_locked(), "sensitivity 50 by default");
    runtime_mouse_sensitivity_set(80); mouse_tick(); mouse_tick(); mouse_tick(); mouse_look_reset(&mouseLook);
    runtime_mouse_move(10, 0); mouse_tick(); s = settle();
    check(runtime_mouse_sensitivity() == 80 && file_says(sensitivity, "80\n") && abs(s.rx - 26214) <= 1, "80: 10 points are 0.8 of the stick, saved");
    runtime_mouse_sensitivity_set(500); check(runtime_mouse_sensitivity() == 100 && file_says(sensitivity, "100\n"), "kept within 1-100");
    FILE *g = fopen(sensitivity, "w"); fputs("35\n", g); fclose(g);
    load_mouse_sensitivity(); check(runtime_mouse_sensitivity() == 35, "the next start reads it");
    g = fopen(sensitivity, "w"); fputs("fast\n", g); fclose(g);
    load_mouse_sensitivity(); check(runtime_mouse_sensitivity() == 35, "a word that is no number keeps it");
    setenv("TOTK_MOUSE_SENSITIVITY", "20", 1); load_mouse_sensitivity();
    runtime_mouse_sensitivity_set(90); check(runtime_mouse_sensitivity() == 20 && runtime_mouse_sensitivity_locked(), "the variable decides");
    unsetenv("TOTK_MOUSE_SENSITIVITY"); mouseSensitivityLocked = 0; runtime_mouse_sensitivity_set(50);

    check(runtime_mouse_set(0) == 0 && file_says(saved, "off\n") && motionMouse == 0, "settings: off, saved, the gyro back to the controller");
    spin(); check(hookCalls == 2, "the window is told again (to free the pointer)");
    FILE *f = fopen(saved, "w"); fputs("on\n", f); fclose(f);
    load_mouse_mode(); check(runtime_mouse_enabled() && motionMouse == 1, "the next start reads mouse mode on");
    runtime_mouse_set(0); f = fopen(saved, "w"); fputs("maybe\n", f); fclose(f);
    load_mouse_mode(); check(!runtime_mouse_enabled(), "a word other than on / off: off");

    setenv("TOTK_MOUSE_GYRO", "0", 1); motionMouse = -1;
    int before = feeds; runtime_mouse_set(1); runtime_mouse_move(10, 0); mouse_tick(); s = settle();
    check(motionMouse == 0 && feeds == before && s.rx > 0, "TOTK_MOUSE_GYRO=0: the stick only, the controller keeps the gyro");
    runtime_mouse_set(0); unsetenv("TOTK_MOUSE_GYRO");
    gyroOn = 0; motionMouse = -1; before = feeds; runtime_mouse_set(1); mouse_tick();
    check(motionMouse == 0 && feeds == before, "TOTK_GYRO=0 (no six-axis device for the game): no mouse gyro either");
    runtime_mouse_set(0);

    printf("{\"status\":\"%s\",\"probe\":\"mouse\",\"checked\":%d,\"failures\":%d}\n", failures ? "fail" : "pass", checked, failures);
    return failures != 0;
}}
