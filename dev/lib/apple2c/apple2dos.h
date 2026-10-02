/* apple2dos.h — DOS 3.3 commands from Apple II C programs (cc65).
 *
 * Link apple2dos_asm.s (assembled with -I dev/lib/apple2) and start from
 * dev/cc65/crt0_apple2.s, whose zero-page snapshot DOS gets back while it
 * runs a command (the same code as the asm module ../apple2/dos.asm).
 *
 *     a2_dos_cmd("BLOAD HISCORE,A$1000");
 *
 *     a2_dos_new();                       // "BSAVE HISCORE,A$1000,L$0004"
 *     a2_dos_add("BSAVE HISCORE,A$");
 *     a2_dos_hex(0x10); a2_dos_hex(0x00);
 *     a2_dos_add(",L$");
 *     a2_dos_hex(0x00); a2_dos_hex(0x04);
 *     if (!a2_disk_protected()) a2_dos_run();
 *
 * DOS reports errors itself (FILE NOT FOUND, WRITE PROTECTED...) by stopping
 * the program at the BASIC prompt: put the files on the disk beforehand and
 * test a2_disk_protected() before a write. Commands hold 39 characters. */
#ifndef APPLE2DOS_H
#define APPLE2DOS_H

void a2_dos_cmd(const char *cmd);        /* run one complete command          */
void a2_dos_new(void);                   /* start building a command          */
void a2_dos_add(const char *s);          /* append a string                   */
void a2_dos_hex(unsigned char b);        /* append b as two hex digits        */
void a2_dos_run(void);                   /* run the command built so far      */
unsigned char a2_disk_protected(void);   /* 1 if the slot 6 disk is protected */

#endif /* APPLE2DOS_H */
