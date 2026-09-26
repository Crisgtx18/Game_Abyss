"""Ruido procedural con seed (alternativa a Perlin noise, sin dependencias).

Que hace:
    Genera ruido suave y determinista en 1D/2D: value-noise con interpolacion
    quintica + fBm (varias octavas) + ridged (para cuevas) + domain warp
    (para que las formas se vean organicas y no rectas).

Por que no Perlin clasico ni librerias:
    - Sin dependencias: no hay que instalar `noise`/`numpy`; el juego corre
      con solo pygame.
    - Determinista por seed: el mismo seed genera el mismo mundo (ideal
      para guardar/compartir semillas en saves/).
    - Suficiente para un tilemap: el value-noise con fade quintico se ve
      igual de bien que Perlin a esta escala y es mas corto de entender.

Con que conecta:
    - world.py -> usa Noise().fbm1() para el relieve, .moisture para biomas,
      .ridged2() + .warp2() para tallar cuevas y .fbm2() para vetas de mineral.
    - config.py -> WG_* aporta amplitudes y umbrales por defecto.
    - saves/ -> world.seed permite regenerar el mismo mundo.

Como tocarlo luego:
    Sube `octaves` para mas detalle (mas lento) o baja `lacunarity`.
    `warp2()` con mas `strength` retuerce mas las cuevas.

Uso *args/**kwargs:
    Todas las funciones aceptan *args/**kwargs extra para no romper llamadas
    si luego anades parametros (ej. n2(x, y, perm, debug=True)).
"""
import math
import random


def make_perm(seed, *args, **kwargs):
    """Permutacion de 512 valores derivada del seed. Base de todo el ruido."""
    rng = random.Random(seed)
    p = list(range(256))
    rng.shuffle(p)
    return p + p


def _fade(t):
    """Curva quintica: el valor cambia suave, sin picos en los bordes."""
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a, b, t):
    return a + (b - a) * t


def noise1(x, perm, *args, **kwargs):
    """Value-noise 1D en [-1, 1]. Para relieve y humedad por columna."""
    xi = math.floor(x)
    xf = x - xi
    h0 = perm[xi & 255] / 255.0 * 2 - 1
    h1 = perm[(xi + 1) & 255] / 255.0 * 2 - 1
    return _lerp(h0, h1, _fade(xf))


def noise2(x, y, perm, *args, **kwargs):
    """Value-noise 2D en [-1, 1]. Para cuevas, menas y manchas de bioma."""
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    X, Y = xi & 255, yi & 255
    v00 = perm[(perm[X] + Y) & 255] / 255.0 * 2 - 1
    v10 = perm[(perm[X + 1] + Y) & 255] / 255.0 * 2 - 1
    v01 = perm[(perm[X] + Y + 1) & 255] / 255.0 * 2 - 1
    v11 = perm[(perm[X + 1] + Y + 1) & 255] / 255.0 * 2 - 1
    u, v = _fade(xf), _fade(yf)
    return _lerp(_lerp(v00, v10, u), _lerp(v01, v11, u), v)


def fbm1(x, perm, *args, octaves=4, lacunarity=2.0, gain=0.5, **kwargs):
    """Ruido fractal 1D: suma octavas (montanas grandes + detalle fino)."""
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += noise1(x * freq, perm) * amp
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm if norm else 0.0


def fbm2(x, y, perm, *args, octaves=4, lacunarity=2.0, gain=0.5, **kwargs):
    """Ruido fractal 2D en [-1, 1]. Para menas y bolsillos de caverna."""
    total, amp, fx, fy, norm = 0.0, 1.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += noise2(x * fx, y * fy, perm) * amp
        norm += amp
        amp *= gain
        fx *= lacunarity
        fy *= lacunarity
    return total / norm if norm else 0.0


def ridged2(x, y, perm, *args, octaves=4, lacunarity=2.1, gain=0.5, **kwargs):
    """Ruido 'cresta' en [0, 1]: vale ~0 sobre lineas finas -> tuneles.

    Las cuevas se tallan donde ridged < umbral: salen galerias conectadas
    en vez de agujeros sueltos. Es la pieza clave del sistema de cuevas.
    """
    total, amp, fx, fy, norm = 0.0, 1.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        n = 1.0 - abs(noise2(x * fx, y * fy, perm))
        total += n * amp
        norm += amp
        amp *= gain
        fx *= lacunarity
        fy *= lacunarity
    return total / norm if norm else 0.0


class Noise:
    """Campos de ruido con seed. Una instancia por mundo generado.

    Ejemplo:
        nz = Noise(seed=1234)
        altura = nz.fbm1(x * 0.03, octaves=4)   # relieve
        cueva  = nz.ridged(x*0.08, y*0.08)      # ~0 => tallar tunel
    """

    def __init__(self, seed=0, *args, **kwargs):
        self.seed = seed
        self.perm = make_perm(seed)
        # permutaciones desplazadas = campos independientes baratos
        self.perm_b = make_perm(seed + 101)
        self.perm_c = make_perm(seed + 707)

    # --- atajos 1D/2D (reenvian *args/**kwargs a las funciones) ---
    def n1(self, x, *args, **kwargs):
        """Relieve/humedad base. Conecta con: alturas y biomas en world.py."""
        return noise1(x, self.perm, *args, **kwargs)

    def fbm1(self, x, *args, **kwargs):
        """Relieve fractal (continent + colinas). Ver world.py fase 1."""
        return fbm1(x, self.perm, *args, **kwargs)

    def n2(self, x, y, *args, **kwargs):
        return noise2(x, y, self.perm, *args, **kwargs)

    def fbm2(self, x, y, *args, field="a", **kwargs):
        """Manchas organicas. field a/b/c = mapas independientes (menas)."""
        perm = {"a": self.perm, "b": self.perm_b, "c": self.perm_c}[field]
        return fbm2(x, y, perm, *args, **kwargs)

    def ridged(self, x, y, *args, **kwargs):
        """Crestas para tuneles. Ver world.py fase 4 (cuevas)."""
        return ridged2(x, y, self.perm, *args, **kwargs)

    def warp2(self, x, y, *args, strength=0.6, scale=0.05, **kwargs):
        """Domain warp: retuerce coordenadas con otro ruido.

        Devuelve (wx, wy). Usalo antes de ridged/fbm para que cuevas y
        vetas se curven de forma natural en vez de salir rectas.
        """
        ox = fbm2(x * scale + 13.7, y * scale + 91.2, self.perm_b, octaves=2)
        oy = fbm2(x * scale + 47.3, y * scale + 17.9, self.perm_c, octaves=2)
        return x + ox * strength / scale * 0.05, y + oy * strength / scale * 0.05
