/* Robot Space Station — the test zone: missions, room, drones, objects,
 * technician (tools/model.py Zone). */
#ifndef ZONE_H
#define ZONE_H

#define ROOM_Y 10u              /* screen row of room row 0 */
#define ROOM_H 144u
#define DRONE_W 10u
#define DRONE_H 12u
#define OBJ_W 7u
#define OBJ_H 8u
#define OBJECTS 4u
#define DRONES 2u

extern unsigned char mission;
extern unsigned char drone_n;                     /* 1 or 2 in this mission */
extern unsigned char drone_x[DRONES], drone_y[DRONES];   /* room pixels */
extern unsigned char holding[DRONES];             /* held object, or 0xFF */
extern unsigned char thrust[DRONES][6];           /* sinks 0-5: thrusters, claw, radio */
extern unsigned char obj_n, obj_kind[OBJECTS], obj_x[OBJECTS], obj_y[OBJECTS];
extern unsigned char door_open[2];                /* groups '_'/'|' and ','/'!' */

void zone_init(void);
unsigned char mission_count(void);
const char *__fastcall__ mission_name_of(unsigned char m);
/* Room (read from RSS.ROOMS), drones, objects, technician; 0: disk error. */
unsigned char __fastcall__ zone_load(unsigned char m);
/* One turn of every drone (tools/model.py Zone.tick); drone B's board is
 * swapped in for its turn. Bit d set: drone d must be redrawn. */
unsigned char zone_tick(void);
unsigned char zone_won(void);
/* Doors from what presses the plates; 1 if they changed (then redraw). */
unsigned char zone_doors(void);
void zone_draw_doors(void);
void zone_draw(void);
void __fastcall__ drone_draw(unsigned char d);
/* Technician (act_x, act_y on screen): one pixel towards x,y; 0 if not moved. */
unsigned char tech_step(unsigned char x, unsigned char y);
/* The drone he touches + 1, or 0. */
unsigned char tech_touches_drone(void);
void __fastcall__ tech_beside_drone(unsigned char d);

#endif
