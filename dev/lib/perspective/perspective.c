/* GPL-3.0. Table-driven projection inspired by Colin Leroy-Mira's
 * Shufflepuck (see README.md). Full 280-pixel HGR input, 16-bit products.
 */
#include "perspective.h"

unsigned char __fastcall__ a2_perspective_project(
    const a2_perspective_t *camera, unsigned x, unsigned char y,
    a2_projected_t *out)
{
    unsigned projected, shift;
    unsigned char scale, screen_y;
    if (!camera || !out || !camera->scale || !camera->shift ||
        !camera->screen_y || !camera->rows || camera->rows > 192u ||
        x > 279u || y >= camera->rows) return 0;
    scale = camera->scale[y];
    if (scale) {
        /* Splitting X avoids a 32-bit product (279*255 exceeds 65535).
         * The high byte is at most one and its contribution needs no mul.
         */
        projected = ((x & 255u) * scale) >> 8;
        if (x > 255u) projected += scale;
    } else projected = x;
    shift = camera->shift[y];
    screen_y = camera->screen_y[y];
    if (shift > 279u || projected > 279u - shift || screen_y > 191u)
        return 0;
    out->x = projected + shift;
    out->y = screen_y;
    return 1;
}
