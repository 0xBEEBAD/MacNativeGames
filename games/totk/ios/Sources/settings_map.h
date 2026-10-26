#pragma once

/* The iPad Settings pane as the environment the runtime reads at launch. Kept free of UIKit so
   tests/test_ios_settings.py checks the tables on a Mac.
   Two layers, chosen by the pane's "Use custom settings" switch (TOTK_CUSTOM_PICTURE):
   - presets (off, the default): Full HD (TOTK_DOCKED) and the frame-rate row (TOTK_PHONE_FPS);
   - custom (on): the picture mode, the scene resolution and the frame-rate cap.
   A layer owns its keys completely, so the two never write the same environment variable. */
typedef struct {
    const char *drawable;        /* TOTK_IOS_DRAWABLE_H: rows, "0" = the panel's native pixels */
    const char *output_upscale;  /* TOTK_MFX_OUTPUT: MetalFX spatial scaling of the canvas into the drawable */
    const char *operation;       /* TOTK_OPERATION_MODE: "handheld" or "docked" (the 1080 mode uses the docked settings) */
} totk_picture_env;

typedef struct {
    const char *present_hz;      /* DM_PRESENT_HZ, NULL: leave unset */
    const char *phone_fps;       /* TOTK_PHONE_FPS, NULL: leave unset */
} totk_frame_env;

/* The Full HD preset (docked 1 / 0): its own drawable, scene and output upscale; the operation mode follows. */
typedef struct {
    const char *operation;
    const char *drawable;        /* NULL: leave the runtime's handheld default */
    const char *scene;           /* TOTK_RENDER_RES, NULL: leave the runtime's default */
    const char *output_upscale;
} totk_preset_env;

/* mode is one of the pane's picture values; 0 when it is not (out is untouched). */
int totk_picture_env_build(const char *mode, totk_picture_env *out);
/* cap is "30", "60" or "120". 0 when cap is not a pane value (out is untouched). */
int totk_frame_env_build(const char *cap, totk_frame_env *out);
/* docked: the pane's Full HD switch. Always succeeds. */
int totk_preset_env_build(int docked, totk_preset_env *out);
/* fps is the pane's preset row, "60" (up to the display's rate) or "30" (held). 0 for anything else. */
int totk_preset_frame_env_build(const char *fps, totk_frame_env *out);

const char *totk_picture_mode_default(void);
const char *totk_frame_cap_default(void);
