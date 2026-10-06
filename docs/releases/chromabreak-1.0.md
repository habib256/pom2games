# ChromaBreak 1.0 — Apple //e and //c

ChromaBreak is a free, open-source brick-breaker in double hi-res for the enhanced Apple //e (128 KB, extended 80-column card) and the Apple //c. It comes as a single 140 KB ProDOS disk image: download `CHROMABREAK.po`, mount it as a 5¼-inch disk, and boot it. The image starts ProDOS 2.4.3 and the game; no installation is needed. A 65C02 is required; an original //e with a 6502 gets a message and returns to ProDOS.

## What's in it

- **Double hi-res, 16 colours, steady frame rate:** 30 frames per second on NTSC machines, 25 on PAL ones, with up to three balls, lasers, a capsule, shards and enemies on screen.
- **Sixty boards**, from PRISM to OMEGA: patterns, figures, mazes and fortresses, with tiles that take one, two or three hits, and steel that never breaks.
- **Six bonus capsules:** Enlarge, Slow, Catch, Disrupt (three balls), Laser and Pierce.
- **Enemies** that come through gates and slide around the tiles, combos up to ×8, an extra life every 1,000 points.
- **A paddle that also moves up and down**, and puts spin on the ball.
- **Mouse, keyboard, joystick or paddles:** AppleMouse II card on the //e, the built-in mouse on the //c.
- **Two-voice music on the built-in speaker:** a title theme, ten different endings for cleared boards, and a fanfare after the sixtieth. No sound card is needed.
- **Three difficulty levels**, five high scores with initials and the farthest board reached saved on the disk, a board selector, an attract mode, and a help page (`?` on the title) that shows every capsule and tile.
- **RGB cards:** on Le Chat Mauve, the //c RGB adapter and Video-7, text is drawn in sharp 560-dot monochrome over the 140-colour graphics.

## Screenshots

![ChromaBreak title screen](https://raw.githubusercontent.com/habib256/pom2games/chromabreak-1.0/chromabreak/screenshots/title.png)

| Sector 1, PRISM | Sector 2 |
|:--:|:--:|
| ![ChromaBreak sector 1 with a falling Slow capsule](https://raw.githubusercontent.com/habib256/pom2games/chromabreak-1.0/chromabreak/screenshots/game.png) | ![ChromaBreak sector 2](https://raw.githubusercontent.com/habib256/pom2games/chromabreak-1.0/chromabreak/screenshots/game-sector-2.png) |

![Help page: capsules, tiles and points](https://raw.githubusercontent.com/habib256/pom2games/chromabreak-1.0/chromabreak/screenshots/help.png)

The title and the two boards are POM2 captures with its colour-monitor rendering; the help page is a plain 560 × 384 render.

## Playing

A click, **SPACE** or **RETURN** on the title starts a game and launches the ball. Without a mouse the keyboard works at once.

| Control | Action |
|---|---|
| **1** / **2** / **3** on the title | Relax, Arcade or Expert |
| Mouse left and right | Place the paddle |
| Mouse up and down | Raise or lower the paddle, up to mid-field |
| Click, **SPACE** or **RETURN** in play | Launch a caught ball; fire with the Laser bonus |
| **M** / **K** / **J** | Play with the mouse, the keyboard, or a joystick or paddles |
| **A** / **D** or the left and right arrows | Move the paddle with the keyboard |
| **W** / **X** or the up and down arrows | Raise or lower it |
| **S** | Stop the keyboard paddle |
| Joystick or paddle 0 and 1, buttons 0 and 1 | Paddle position and height; launch and fire |
| **P** | Pause and resume |
| **ESC** | Menu: resume, choose a board already reached, sound on or off, title, quit to ProDOS |
| **H** on the title | High scores |
| **?** on the title | Help page |
| Ctrl-RESET | Clean return to ProDOS |

| Mode | Lives | Paddle | Ball speed | A capsule every |
|---|:--:|:--:|:--:|:--:|
| Relax | 5 | wide | slow | 4 tiles |
| Arcade | 3 | medium | medium | 5 tiles |
| Expert | 2 | narrow | fast | 6 tiles |

| Capsule | Effect |
|---|---|
| **E** Enlarge, orange | A wider paddle |
| **S** Slow, pink | A slower ball |
| **C** Catch, red | The ball sticks where it meets the paddle |
| **D** Disrupt, purple | Three balls |
| **L** Laser, blue | Two cannons on the paddle; hold the click to keep firing |
| **P** Pierce, light blue | Red balls that break any tile but steel in one hit |

A bonus lasts until another capsule is caught, a life is lost or the board is cleared. Destroying tiles without touching the paddle raises the multiplier every three tiles, up to ×8. An enemy is worth 100 points. A life is lost only when the last ball falls.

## Validation and credits

The release disk was rebuilt from a clean tree and compared byte-for-byte with the committed image. Automated tests run the game in the POM2 emulator core with the real //e and //c ROMs and both AppleMouse models: boot and exit, mouse, keyboard and joystick play, frame intervals in the busiest scenes on NTSC and PAL, collisions against a reference model, every board transition, the finale, high-score files (missing, corrupt, write-protected), the help page and both voices of the tunes. These checks validate emulated execution: the game has not yet run on real hardware, and reports from a real //e or //c are welcome.

Code and boards: **VERHILLE Arnaud**. Beautiful Boot font: **Michael Pohoreski**. ProDOS keeps its own credits and rights. [Source code](https://github.com/habib256/pom2games/tree/chromabreak-1.0/chromabreak) is available under [GPL-3.0](https://github.com/habib256/pom2games/blob/chromabreak-1.0/LICENSE). The [design notes](https://github.com/habib256/pom2games/blob/chromabreak-1.0/chromabreak/README.md) in the repository are in French.
