# Maze3D title artwork

`title.hgr` is the unmodified 8192-byte HGR image copied from A2FC:
`a2filecmd/data/IMGHGR/MAZE3D#062000`, used in its DEMO image collection.

SHA-256: `bfb19ace71d5337207d7b8189eb50018f04a6148b007e3f0f763577bf866af5e`.

The DOS 3.3 disk stores it as `MAZETITLE`. It is compressed losslessly with
fhpack (8,192 → 3,249 bytes), loaded at $1100 and decompressed into the
hidden HGR page. The build verifies the full byte-for-byte round trip.
Three footer rows display profiles, controls and the record; the first
168 scanlines and the source image remain unchanged.

`FDRAW-NOTICE.txt` and `FHPACK-NOTICE.txt` document the rendering and
compression source provenance; `FDRAW-LICENSE.txt` contains their Apache-2.0
license.
