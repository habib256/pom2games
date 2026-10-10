#!/usr/bin/env python3
"""Small synthetic PCM effect, no external asset or audio package."""
import math
import struct
import sys
import wave

with wave.open(sys.argv[1], 'wb') as wav:
    wav.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
    wav.writeframes(b''.join(struct.pack('<h', int(22000 * math.sin(
        2 * math.pi * (440*i/8000 + 800*(i/8000)**2)))) for i in range(320)))
