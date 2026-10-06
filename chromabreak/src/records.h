#ifndef CHROMA_RECORDS_H
#define CHROMA_RECORDS_H
typedef struct {
    unsigned score;
    char initials[3];
    unsigned char mode;
} ChromaRecord;
extern ChromaRecord records[5];
void records_load(void);
unsigned char __fastcall__ records_rank(unsigned score);
unsigned char records_submit(unsigned score, const char *initials, unsigned char mode);
unsigned char records_save(void);
/* Farthest sector reached (0..CB_LEVELS-1), saved with the records. */
extern unsigned char records_progress;
unsigned char records_load_overlay(void *dest, unsigned size);
#endif
