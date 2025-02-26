/*
 * This file is part of the OpenMV project.
 * Copyright (c) 2013/2014 Ibrahim Abdelkader <i.abdalkader@gmail.com>
 * This work is licensed under the MIT license, see the file LICENSE for details.
 *
 * Sensor Python module.
 *
 */
#include "mp.h"
#include "sccb.h"
#include "sensor.h"
#include "py_assert.h"
#include "py_image.h"
#include "py_sensor.h"

static mp_obj_t py_sensor_reset() {
    sensor_reset();
    sensor_set_pixformat(PIXFORMAT_RGB565);
    sensor_set_framesize(FRAMESIZE_QQVGA);
    sensor_set_framerate(FRAMERATE_30FPS);
    sensor_set_gainceiling(GAINCEILING_8X);
    sensor_set_contrast(0);
    sensor_set_brightness(0);
    sensor_set_saturation(0);
    return mp_const_none;
}

static mp_obj_t py_sensor_snapshot() {
    mp_obj_t image = py_image(0, 0, 0, 0);
    if (sensor_snapshot((struct image*) py_image_cobj(image))==-1) {
        nlr_jump(mp_obj_new_exception_msg(&mp_type_RuntimeError, "Sensor Timeout!!"));
        return mp_const_false;
    }
    return image;
}

static mp_obj_t py_sensor_set_pixformat(mp_obj_t pixformat) {
    if (sensor_set_pixformat(mp_obj_get_int(pixformat)) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_framerate(mp_obj_t framerate) {
    enum sensor_framerate fr;
    switch (mp_obj_get_int(framerate)) {
        case 2:
            fr = FRAMERATE_2FPS;
            break;
        case 8:
            fr = FRAMERATE_8FPS;
            break;
        case 15:
            fr = FRAMERATE_15FPS;
            break;
        case 30:
            fr = FRAMERATE_30FPS;
            break;
        case 60:
            fr = FRAMERATE_60FPS;
            break;
        default:
            nlr_jump(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid framerate"));
            break;
    }

    if (sensor_set_framerate(fr) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_framesize(mp_obj_t framesize) {
    if (sensor_set_framesize(mp_obj_get_int(framesize)) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_gainceiling(mp_obj_t gainceiling) {
    enum sensor_gainceiling gain;
    switch (mp_obj_get_int(gainceiling)) {
        case 2:
            gain = GAINCEILING_2X;
            break;
        case 4:
            gain = GAINCEILING_4X;
            break;
        case 8:
            gain = GAINCEILING_8X;
            break;
        case 16:
            gain = GAINCEILING_16X;
            break;
        case 32:
            gain = GAINCEILING_32X;
            break;
        case 64:
            gain = GAINCEILING_64X;
            break;
        case 128:
            gain = GAINCEILING_128X;
            break;
        default:
            nlr_jump(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid gainceiling"));
            break;
    }

    if (sensor_set_gainceiling(gain) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_brightness(mp_obj_t brightness) {
    if (sensor_set_brightness(mp_obj_get_int(brightness)) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_contrast(mp_obj_t contrast) {
    if (sensor_set_contrast(mp_obj_get_int(contrast)) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_saturation(mp_obj_t saturation) {
    if (sensor_set_saturation(mp_obj_get_int(saturation)) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_quality(mp_obj_t qs) {
    int q = mp_obj_get_int(qs);
    PY_ASSERT_TRUE((q >= 0 && q <= 100));

    q = 100-q; //invert quality
    q = 255*q/100; //map to 0->255
    if (sensor_set_quality(q) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_set_colorbar(mp_obj_t enable) {
    if (sensor_set_colorbar(mp_obj_is_true(enable)) != 0) {
        return mp_const_false;
    }
    return mp_const_true;
}

static mp_obj_t py_sensor_write_reg(mp_obj_t addr, mp_obj_t val) {
    SCCB_Write(mp_obj_get_int(addr), mp_obj_get_int(val));
    return mp_const_none;
}

static mp_obj_t py_sensor_read_reg(mp_obj_t addr) {
    return mp_obj_new_int(SCCB_Read(mp_obj_get_int(addr)));
}

//static void py_sensor_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
//    mp_printf(print, "<Sensor MID:0x%.2X%.2X PID:0x%.2X VER:0x%.2X>",
//            sensor.id.MIDH, sensor.id.MIDL, sensor.id.PID, sensor.id.VER);
//}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(py_sensor_reset_obj,           py_sensor_reset);
STATIC MP_DEFINE_CONST_FUN_OBJ_0(py_sensor_snapshot_obj,        py_sensor_snapshot);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_pixformat_obj,   py_sensor_set_pixformat);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_framerate_obj,   py_sensor_set_framerate);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_framesize_obj,   py_sensor_set_framesize);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_gainceiling_obj, py_sensor_set_gainceiling);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_contrast_obj,    py_sensor_set_contrast);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_brightness_obj,  py_sensor_set_brightness);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_saturation_obj,  py_sensor_set_saturation);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_quality_obj,     py_sensor_set_quality);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_set_colorbar_obj,    py_sensor_set_colorbar);
STATIC MP_DEFINE_CONST_FUN_OBJ_2(py_sensor_write_reg_obj,       py_sensor_write_reg);
STATIC MP_DEFINE_CONST_FUN_OBJ_1(py_sensor_read_reg_obj,        py_sensor_read_reg);

STATIC const mp_map_elem_t globals_dict_table[] = {
    { MP_OBJ_NEW_QSTR(MP_QSTR___name__),    MP_OBJ_NEW_QSTR(MP_QSTR_sensor) },
    /* Pixel format */
    { MP_OBJ_NEW_QSTR(MP_QSTR_RGB565),      MP_OBJ_NEW_SMALL_INT(PIXFORMAT_RGB565)},   /* 2BPP/RGB565*/
    { MP_OBJ_NEW_QSTR(MP_QSTR_YUV422),      MP_OBJ_NEW_SMALL_INT(PIXFORMAT_YUV422)},   /* 2BPP/YUV422*/
    { MP_OBJ_NEW_QSTR(MP_QSTR_GRAYSCALE),   MP_OBJ_NEW_SMALL_INT(PIXFORMAT_GRAYSCALE)},/* 1BPP/GRAYSCALE*/
    { MP_OBJ_NEW_QSTR(MP_QSTR_JPEG),        MP_OBJ_NEW_SMALL_INT(PIXFORMAT_JPEG)},     /* JPEG/COMPRESSED*/
    /* Frame size */
    { MP_OBJ_NEW_QSTR(MP_QSTR_QQCIF),       MP_OBJ_NEW_SMALL_INT(FRAMESIZE_QQCIF)},    /* 88x72     */
    { MP_OBJ_NEW_QSTR(MP_QSTR_QQVGA),       MP_OBJ_NEW_SMALL_INT(FRAMESIZE_QQVGA)},    /* 160x120   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_QQVGA2),      MP_OBJ_NEW_SMALL_INT(FRAMESIZE_QQVGA2)},   /* 128x160   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_QCIF),        MP_OBJ_NEW_SMALL_INT(FRAMESIZE_QCIF)},     /* 176x144   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_QVGA),        MP_OBJ_NEW_SMALL_INT(FRAMESIZE_QVGA)},     /* 320x240   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_CIF),         MP_OBJ_NEW_SMALL_INT(FRAMESIZE_CIF)},      /* 352x288   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_VGA),         MP_OBJ_NEW_SMALL_INT(FRAMESIZE_VGA)},      /* 640x480   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_SVGA),        MP_OBJ_NEW_SMALL_INT(FRAMESIZE_SVGA)},     /* 800x600   */
    { MP_OBJ_NEW_QSTR(MP_QSTR_SXGA),        MP_OBJ_NEW_SMALL_INT(FRAMESIZE_SXGA)},     /* 1280x1024 */
    { MP_OBJ_NEW_QSTR(MP_QSTR_UXGA),        MP_OBJ_NEW_SMALL_INT(FRAMESIZE_UXGA)},     /* 1600x1200 */

    /* Sensor functions */
    { MP_OBJ_NEW_QSTR(MP_QSTR_reset),           (mp_obj_t)&py_sensor_reset_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_snapshot),        (mp_obj_t)&py_sensor_snapshot_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_pixformat),   (mp_obj_t)&py_sensor_set_pixformat_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_framerate),   (mp_obj_t)&py_sensor_set_framerate_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_framesize),   (mp_obj_t)&py_sensor_set_framesize_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_gainceiling), (mp_obj_t)&py_sensor_set_gainceiling_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_contrast),    (mp_obj_t)&py_sensor_set_contrast_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_brightness),  (mp_obj_t)&py_sensor_set_brightness_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_saturation),  (mp_obj_t)&py_sensor_set_saturation_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_quality),     (mp_obj_t)&py_sensor_set_quality_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_set_colorbar),    (mp_obj_t)&py_sensor_set_colorbar_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR___write_reg),     (mp_obj_t)&py_sensor_write_reg_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR___read_reg),      (mp_obj_t)&py_sensor_read_reg_obj },
};

STATIC MP_DEFINE_CONST_DICT(globals_dict, globals_dict_table);

const mp_obj_module_t sensor_module = {
    .base = { &mp_type_module },
    .name = MP_QSTR_sensor,
    .globals = (mp_obj_t)&globals_dict,
};
