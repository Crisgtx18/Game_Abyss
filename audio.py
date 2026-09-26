# Sonidos procedurales (sin archivos externos). Si no hay audio, se desactiva solo.
import math
import pygame


class Audio:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.ok = True
        except Exception:
            self.ok = False

    def _tone(self, freq, ms=120, vol=0.25, slide=0):
        if not self.ok:
            return
        try:
            rate = 22050
            n = int(rate * ms / 1000)
            buf = bytearray()
            import struct
            for i in range(n):
                t = i / rate
                f = freq + slide * (i / max(1, n))
                s = int(vol * 32767 * math.sin(2 * math.pi * f * t) * (1 - i / n))
                buf += struct.pack("<h", max(-32767, min(32767, s)))
            snd = pygame.mixer.Sound(buffer=bytes(buf))
            snd.play()
        except Exception:
            pass

    def hit(self):
        self._tone(220, 90, 0.3, -80)

    def pickup(self):
        self._tone(660, 90, 0.2, 300)

    def break_block(self):
        self._tone(150, 140, 0.3, -60)

    def craft(self):
        self._tone(520, 120, 0.25, 200)

    def hurt(self):
        self._tone(180, 200, 0.35, -100)

    def potion(self):
        self._tone(440, 200, 0.25, 250)

    def boss(self):
        self._tone(90, 500, 0.4, 40)
