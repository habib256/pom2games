#include "dhgr.h"
#include "hgr_layout.h"
extern const unsigned char hgr_font[768];
extern unsigned char dhgr_base, dhgr_aux, dhgr_mask, dhgr_bits;
extern unsigned char *dhgr_addr;
unsigned char dhgr_text_phase, dhgr_text_row[6];
void __fastcall__ dhgr_glyph_row_asm(unsigned char glyph);
void dhgr_write_asm(void);
void dhgr_puts(const char *s, unsigned char x, unsigned char y)
{
    unsigned char ch, row, byte, first, count, left_mask, right_mask;
    unsigned xpos=x, pos, addr;
    while ((ch=(unsigned char)*s++)!=0) {
        if (ch<32u || ch>127u) ch='?';
        if (xpos+8u>140u || y>184u) return;
        pos=xpos*4u;
        first=(unsigned char)(pos/7u);
        dhgr_text_phase=(unsigned char)(pos%7u);
        count=(unsigned char)((dhgr_text_phase+32u+6u)/7u);
        left_mask=(unsigned char)((0x7Fu<<dhgr_text_phase)&0x7Fu);
        right_mask=(unsigned char)((dhgr_text_phase+32u)%7u);
        right_mask=right_mask ? (1u<<right_mask)-1u : 0x7Fu;
        for (row=0; row<8u; ++row) {
            dhgr_glyph_row_asm(hgr_font[(unsigned)(ch-32u)*8u+row]);
            addr=HGR_ROW_ADDR(dhgr_base,y+row);
            for (byte=0; byte<count; ++byte) {
                dhgr_addr=(unsigned char *)(addr+((first+byte)>>1));
                dhgr_aux=((first+byte)&1u)^1u;
                dhgr_mask=byte==0 ? left_mask : byte==count-1u ? right_mask : 0x7Fu;
                dhgr_bits=dhgr_text_row[byte]&dhgr_mask;
                dhgr_write_asm();
            }
        }
        xpos+=8u;
    }
}
