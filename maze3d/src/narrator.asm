; Narrator lines loaded from DOS 3.3 into $1100 before MAZE3D starts.
.segment "NARRATOR"
str_empty: .byte 0
ph_idle0: .byte "THE SHADOWS WHISPER YOUR NAME",0
ph_idle1: .byte "THE DUNGEON HOLDS ITS BREATH",0
ph_idle2: .byte "THE DARK AWAITS YOUR FATE",0
ph_idle3: .byte "STEP BY STEP, A LEGEND GROWS",0
ph_idle4: .byte "DEEPER! THE LEGEND DESCENDS",0
ph_idle5: .byte "DEEPER STILL, MORE HEROIC",0
ph_idle6: .byte "THE ABYSS OPENS ITS ARMS!",0
ph_idle7: .byte "ANOTHER STEP TOWARD GLORY",0
ph_idle8: .byte "BATS FLEE AT YOUR APPROACH",0
ph_idle9: .byte "EVEN THE WALLS ADMIRE YOU",0
ph_idle10: .byte "DESTINY SMELLS FAINTLY DAMP",0
ph_idle11: .byte "YOUR BOOTS ECHO LIKE THUNDER",0
ph_idle12: .byte "THE MAP FEARS YOUR FOOTSTEPS",0
ph_idle13: .byte "ONWARD, O RADIANT ONE!",0
ph_idle14: .byte "SUCH POISE! SUCH DIRECTION!",0
ph_idle15: .byte "A HERO WALKS. SLOWLY. BUT YES",0
ph_idle16: .byte "THE GLOOM PARTS FOR YOU",0
ph_idle17: .byte "LEGENDS ARE MADE OF WALKING",0
ph_idle18: .byte "MIND THE MOSS, GREAT ONE",0
ph_idle19: .byte "THE EXIT DREADS YOUR ARRIVAL",0
ph_idle20: .byte "DUST SETTLES IN YOUR HONOUR",0
ph_idle21: .byte "YOUR SHADOW LOOKS HEROIC TOO",0
ph_idle22: .byte "COBWEBS PART IN REVERENCE",0
ph_idle23: .byte "THE SILENCE APPLAUDS YOU",0
ph_idle24: .byte "A DRAFT! AN OMEN! OR A GAP",0
ph_idle25: .byte "YOU STRIDE WITH PURPOSE-ISH",0
ph_idle26: .byte "THE STONES REMEMBER GIANTS",0
ph_idle27: .byte "FORWARD, INTO SLIGHT DANGER!",0
ph_idle28: .byte "THE TORCHES ENVY YOUR GLOW",0
ph_idle29: .byte "EACH STEP, A VERSE UNWRITTEN",0
ph_idle30: .byte "THE MAZE TREMBLES POLITELY",0
ph_idle31: .byte "DOOM HUMS A CHEERFUL TUNE",0
ph_win0: .byte "A FOE PERISHES. GLORY!",0
ph_win1: .byte "THE BARDS WILL SING OF THIS",0
ph_win2: .byte "SLAIN! THE HALL ACCLAIMS YOU",0
ph_win3: .byte "ONE LESS FOR THE LEGEND",0
ph_win4: .byte "TREASURE WORTHY OF YOUR QUEST",0
ph_win5: .byte "LOOT FIT FOR THE CHOSEN",0
ph_win6: .byte "YOUR GLORY GROWS HEAVIER",0
ph_win7: .byte "TAKEN, WITH FLAIR INTACT",0
ph_win8: .byte "IT NEVER STOOD A CHANCE",0
ph_win9: .byte "SPLAT! MOST MAJESTIC, THAT",0
ph_win10: .byte "ANOTHER STAT FOR THE EPICS",0
ph_win11: .byte "THE CROWD OF ONE GOES WILD",0
ph_win12: .byte "SMOTE! A FINE WORD, NOW",0
ph_win13: .byte "GORGEOUS AND DEADLY. RUDE.",0
ph_win14: .byte "IT REGRETS EVERYTHING NOW",0
ph_win15: .byte "CLEAN KILL. POETS WEEP.",0
ph_win16: .byte "VANQUISHED WITH GOOD POSTURE",0
ph_win17: .byte "GOLD! SHINY! MINE! ...YOURS",0
ph_win18: .byte "COINS FOR THE HERO FUND",0
ph_win19: .byte "PILLAGE BECOMES YOU",0
ph_win20: .byte "THAT WILL BUFF THE LEGEND",0
ph_win21: .byte "A TROPHY FOR THE MANTLE",0
ph_win22: .byte "THE ABYSS COUGHS UP LOOT",0
ph_win23: .byte "RICHER, AND STILL HANDSOME",0
ph_win24: .byte "DISPATCHED. NEXT VICTIM?",0
ph_win25: .byte "HEROIC. ALSO MILDLY MESSY.",0
ph_win26: .byte "THE MONSTER FILED A COMPLAINT",0
ph_win27: .byte "ONE SWING, ONE SONNET",0
ph_win28: .byte "BEHOLD, THE SPOILS OF FATE",0
ph_win29: .byte "VICTORY TASTES LIKE DUST. YAY",0
ph_win30: .byte "ANOTHER BEAST, A NEW BALLAD",0
ph_win31: .byte "IT WILL NOT BE MISSED",0
ph_peril0: .byte "YOUR BREATH FAILS, ALAS",0
ph_peril1: .byte "DEATH LURKS... STAY NOBLE",0
ph_peril2: .byte "ONE STEP FROM AN EPIC END!",0
ph_peril3: .byte "HOLD ON, FALTERING LEGEND",0
ph_peril4: .byte "OUCH! YET YOU STAY SUBLIME",0
ph_peril5: .byte "A BITE UNWORTHY OF YOU",0
ph_peril6: .byte "PAIN FORGES THE HEROES",0
ph_peril7: .byte "YOU STAGGER, MAJESTIC",0
ph_peril8: .byte "MAYBE... RUN? HEROICALLY?",0
ph_peril9: .byte "THAT ONE STUNG THE LEGEND",0
ph_peril10: .byte "BLEEDING, BUT FASHIONABLY",0
ph_peril11: .byte "THE END NEARS. POSTURE!",0
ph_peril12: .byte "PERHAPS A HEALER? A PRAYER?",0
ph_peril13: .byte "STILL PRETTY. LESS ALIVE.",0
ph_peril14: .byte "YOUR EPILOGUE LOOMS CLOSE",0
ph_peril15: .byte "DIGNITY OVER LONGEVITY!",0
ph_peril16: .byte "WOUNDED, YET PHOTOGENIC",0
ph_peril17: .byte "THE GRAVE CLEARS ITS THROAT",0
ph_peril18: .byte "TEETERING ON GLORY'S EDGE",0
ph_peril19: .byte "I'D FLEE. GENTLY. JUST SAYING",0
ph_peril20: .byte "ONE MORE HIT ENDS THE SAGA",0
ph_peril21: .byte "COURAGE! ALSO, BANDAGES!",0
ph_peril22: .byte "THE REAPER TAPS HIS WATCH",0
ph_peril23: .byte "FADING, BUT WITH FLOURISH",0
ph_peril24: .byte "A NOBLE SHADE YOU WILL MAKE",0
ph_peril25: .byte "HP LOW, EGO INTACT",0
ph_peril26: .byte "DEATH IS SO INCONVENIENT",0
ph_peril27: .byte "CLING ON, O SPLENDID ONE",0
ph_peril28: .byte "THE TOMB WARMS UP FOR YOU",0
ph_peril29: .byte "ALMOST A MARTYR. ALMOST.",0
ph_peril30: .byte "GASP! DRAMATIC, YET DIRE",0
ph_peril31: .byte "SURVIVE, FOR THE FANS!",0
msg_ptr_lo:
        .byte <ph_idle0,<ph_idle1,<ph_idle2,<ph_idle3,<ph_idle4,<ph_idle5,<ph_idle6,<ph_idle7
        .byte <ph_idle8,<ph_idle9,<ph_idle10,<ph_idle11,<ph_idle12,<ph_idle13,<ph_idle14,<ph_idle15
        .byte <ph_idle16,<ph_idle17,<ph_idle18,<ph_idle19,<ph_idle20,<ph_idle21,<ph_idle22,<ph_idle23
        .byte <ph_idle24,<ph_idle25,<ph_idle26,<ph_idle27,<ph_idle28,<ph_idle29,<ph_idle30,<ph_idle31
        .byte <ph_win0,<ph_win1,<ph_win2,<ph_win3,<ph_win4,<ph_win5,<ph_win6,<ph_win7
        .byte <ph_win8,<ph_win9,<ph_win10,<ph_win11,<ph_win12,<ph_win13,<ph_win14,<ph_win15
        .byte <ph_win16,<ph_win17,<ph_win18,<ph_win19,<ph_win20,<ph_win21,<ph_win22,<ph_win23
        .byte <ph_win24,<ph_win25,<ph_win26,<ph_win27,<ph_win28,<ph_win29,<ph_win30,<ph_win31
        .byte <ph_peril0,<ph_peril1,<ph_peril2,<ph_peril3,<ph_peril4,<ph_peril5,<ph_peril6,<ph_peril7
        .byte <ph_peril8,<ph_peril9,<ph_peril10,<ph_peril11,<ph_peril12,<ph_peril13,<ph_peril14,<ph_peril15
        .byte <ph_peril16,<ph_peril17,<ph_peril18,<ph_peril19,<ph_peril20,<ph_peril21,<ph_peril22,<ph_peril23
        .byte <ph_peril24,<ph_peril25,<ph_peril26,<ph_peril27,<ph_peril28,<ph_peril29,<ph_peril30,<ph_peril31
msg_ptr_hi:
        .byte >ph_idle0,>ph_idle1,>ph_idle2,>ph_idle3,>ph_idle4,>ph_idle5,>ph_idle6,>ph_idle7
        .byte >ph_idle8,>ph_idle9,>ph_idle10,>ph_idle11,>ph_idle12,>ph_idle13,>ph_idle14,>ph_idle15
        .byte >ph_idle16,>ph_idle17,>ph_idle18,>ph_idle19,>ph_idle20,>ph_idle21,>ph_idle22,>ph_idle23
        .byte >ph_idle24,>ph_idle25,>ph_idle26,>ph_idle27,>ph_idle28,>ph_idle29,>ph_idle30,>ph_idle31
        .byte >ph_win0,>ph_win1,>ph_win2,>ph_win3,>ph_win4,>ph_win5,>ph_win6,>ph_win7
        .byte >ph_win8,>ph_win9,>ph_win10,>ph_win11,>ph_win12,>ph_win13,>ph_win14,>ph_win15
        .byte >ph_win16,>ph_win17,>ph_win18,>ph_win19,>ph_win20,>ph_win21,>ph_win22,>ph_win23
        .byte >ph_win24,>ph_win25,>ph_win26,>ph_win27,>ph_win28,>ph_win29,>ph_win30,>ph_win31
        .byte >ph_peril0,>ph_peril1,>ph_peril2,>ph_peril3,>ph_peril4,>ph_peril5,>ph_peril6,>ph_peril7
        .byte >ph_peril8,>ph_peril9,>ph_peril10,>ph_peril11,>ph_peril12,>ph_peril13,>ph_peril14,>ph_peril15
        .byte >ph_peril16,>ph_peril17,>ph_peril18,>ph_peril19,>ph_peril20,>ph_peril21,>ph_peril22,>ph_peril23
        .byte >ph_peril24,>ph_peril25,>ph_peril26,>ph_peril27,>ph_peril28,>ph_peril29,>ph_peril30,>ph_peril31
