"""Mundo procedural estilo Terraria: relieve, biomas, cuevas, minerales,
arboles y estructuras (casa en ruinas, mina, altar, cabana, cofres).

Que hace:
    Genera el tilemap jugable con 6 fases (ver generate()): relieve con
    ruido fractal, capas por bioma, vetas de mineral en blobs, cuevas
    talladas con ruido 'cresta' + gusanos, vegetacion y estructuras con loot.

Con que conecta:
    - noise.py  -> Noise().fbm1/ridged/warp2/fbm2 (todo el relieve y cuevas).
    - config.py -> WORLD_W/H, WG_* (amplitudes y umbrales ajustables).
    - blocks.py -> ids de bloque que se colocan (1 tierra, 2 piedra...).
    - game.py   -> usa get/set/solid, spawn, chest_loot, time; guarda con
      save()/load(). physics.py solo necesita world.solid().
    - saves/    -> save()/load() en JSON incluyeloot de cofres y la semilla.

Como tocarlo luego:
    Llama generate(seed=1234, caves=False) para un mundo sin cuevas, o
    generate(seed=1, tree_density=0.3) para mas bosque. Los parametros de
    config.py (WG_HILLS_AMP, WG_CAVE_SIZE...) son los mandos principales.

Uso *args/**kwargs:
    generate() y las fases _fase_*() aceptan **opts para activar/apagar
    partes sin cambiar las llamadas existentes en game.py.
"""
import json
import random
from blocks import BLOCKS
from noise import Noise


class World:
    # Fuentes de luz puntuales: bid -> (r, g, b, radio_tiles).
    # Colores estilo Terraria (cada antorcha tine distinto).
    LIGHT_SOURCES = {
        14: (255, 190, 90, 12),   # antorcha calida
        29: (255, 200, 115, 11),  # farol calido
        19: (170, 130, 255, 10),  # flor abisal violeta
        25: (120, 255, 190, 9),   # seta verde
    }

    def __init__(self, w, h):
        self.w = w
        self.h = h
        # OPT: bytearray por fila (1 byte/tile, ids < 256) en vez de
        # list[int]: 1.5M tiles pasan de ~50MB a ~1.5MB -> evita el OOM-kill.
        self.tiles = [bytearray(w) for _ in range(h)]
        # Mapa de luz estilo Terraria (0..255 por tile): sol de dia
        # completo + RGB de antorchas. Se calcula al generar/cargar
        # (no se guarda: se recomputa, como hace Terraria).
        self.sun = [bytearray(b"\xff" * w) for _ in range(h)]
        self.lr = [bytearray(w) for _ in range(h)]
        self.lg = [bytearray(w) for _ in range(h)]
        self.lb = [bytearray(w) for _ in range(h)]
        self.spawn = (w // 2, 10)
        self.chest_loot = {}   # (x,y) -> lista items al romper cofre
        self.time = 0.25       # 0-1 (0.25 = manana)
        self.seed = 0
        self.heights = [h // 3] * w  # superficie por columna (se rellena al generar)
        self.abyss_x = w // 4        # centro de la fosa (fase abismo)
        self.abyss_top = h // 3

    # ---------- acceso (API que usa game.py y physics.py) ----------
    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x, y):
        if not self.in_bounds(x, y):
            return 10  # bedrock fuera del mundo
        return self.tiles[y][x]

    def set(self, x, y, v):
        if self.in_bounds(x, y):
            self.tiles[y][x] = v

    def solid(self, x, y):
        b = BLOCKS.get(self.get(x, y), BLOCKS[0])
        return b["solid"]

    # ---------- luz estilo Terraria (sol + antorchas RGB por tile) ----------
    def _light_luts(self):
        """LUTs planas solido/fondo/cristal para el trace y el flood."""
        sol = bytearray(256)
        bg = bytearray(256)
        trs = bytearray(256)
        for bid, info in BLOCKS.items():
            if 0 <= bid < 256:
                if info.get("solid"):
                    sol[bid] = 1
                if info.get("background"):
                    bg[bid] = 1
                if info.get("glass"):
                    trs[bid] = 1
        return sol, bg, trs

    def compute_sun(self, progress=None):
        """Luz solar por columna: 255 al aire, x0.9 por solido (el
        cristal no tapa), x0.995 por fondo. Solo bajo la superficie."""
        sol, bg, trs = self._light_luts()
        tiles, sun, heights = self.tiles, self.sun, self.heights
        W, H = self.w, self.h
        for x in range(W):
            lvl = 255
            sy = heights[x]
            for y in range(sy, H):
                b = tiles[y][x]
                sun[y][x] = lvl
                if sol[b] and not trs[b]:
                    if lvl > 6:
                        lvl = max(6, (lvl * 9) // 10)
                elif bg[b]:
                    if lvl > 6:
                        lvl = max(6, (lvl * 995) // 1000)
            if progress and (x & 127) == 0:
                progress(x / W)

    def _sun_column(self, x):
        """Re-traza el sol de una columna (tras picar/colocar)."""
        if not (0 <= x < self.w):
            return
        sol, bg, trs = self._light_luts()
        tiles, sun = self.tiles, self.sun
        lvl = 255
        for y in range(self.heights[x], self.h):
            b = tiles[y][x]
            sun[y][x] = lvl
            if sol[b] and not trs[b]:
                if lvl > 6:
                    lvl = max(6, (lvl * 9) // 10)
            elif bg[b]:
                if lvl > 6:
                    lvl = max(6, (lvl * 995) // 1000)

    def _torch_flood(self, sx, sy, r, g, b):
        """Flood fill de una fuente: atenua x0.90 en aire, x0.85 en fondo
        y x0.72 en solido (la luz muere en los muros, como en Terraria).
        Combina por maximo (no suma)."""
        from collections import deque
        sol, bg, trs = self._light_luts()
        tiles = self.tiles
        lr, lg, lb = self.lr, self.lg, self.lb
        W, H = self.w, self.h
        if lr[sy][sx] >= r and lg[sy][sx] >= g and lb[sy][sx] >= b:
            return
        lr[sy][sx] = max(lr[sy][sx], r)
        lg[sy][sx] = max(lg[sy][sx], g)
        lb[sy][sx] = max(lb[sy][sx], b)
        dq = deque()
        dq.append((sx, sy, 255))
        while dq:
            x, y, inten = dq.popleft()
            for nx, ny in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                nb = tiles[ny][nx]
                att = 72 if (sol[nb] and not trs[nb]) else (85 if bg[nb] else 90)
                ni = (inten * att) // 100
                if ni < 8:
                    continue
                nr, ng, nbl = (ni * r) // 255, (ni * g) // 255, (ni * b) // 255
                if nr <= lr[ny][nx] and ng <= lg[ny][nx] and nbl <= lb[ny][nx]:
                    continue
                if nr > lr[ny][nx]:
                    lr[ny][nx] = nr
                if ng > lg[ny][nx]:
                    lg[ny][nx] = ng
                if nbl > lb[ny][nx]:
                    lb[ny][nx] = nbl
                dq.append((nx, ny, ni))

    def compute_torch_full(self, progress=None):
        """Escanea todas las fuentes y las inunda (una vez por mundo)."""
        self.lr = [bytearray(self.w) for _ in range(self.h)]
        self.lg = [bytearray(self.w) for _ in range(self.h)]
        self.lb = [bytearray(self.w) for _ in range(self.h)]
        SRC = World.LIGHT_SOURCES
        tiles = self.tiles
        W, H = self.w, self.h
        n = 0
        for y in range(H):
            row = tiles[y]
            for x in range(W):
                s = SRC.get(row[x])
                if s:
                    self._torch_flood(x, y, s[0], s[1], s[2])
                    n += 1
            if progress and (y & 127) == 0:
                progress(y / H)
        return n

    def recalc_light_box(self, tx, ty, R=28):
        """Tras picar/colocar: re-traza el sol de la columna y rehace las
        antorchas de la caja (sincrono, unos ms: caja pequena)."""
        self._sun_column(tx)
        SRC = World.LIGHT_SOURCES
        tiles = self.tiles
        W, H = self.w, self.h
        x0, x1 = max(0, tx - R), min(W - 1, tx + R)
        y0, y1 = max(0, ty - R), min(H - 1, ty + R)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.lr[y][x] = 0
                self.lg[y][x] = 0
                self.lb[y][x] = 0
        sx0, sx1 = max(0, tx - R - 14), min(W - 1, tx + R + 14)
        sy0, sy1 = max(0, ty - R - 14), min(H - 1, ty + R + 14)
        for y in range(sy0, sy1 + 1):
            row = tiles[y]
            for x in range(sx0, sx1 + 1):
                s = SRC.get(row[x])
                if s:
                    self._torch_flood(x, y, s[0], s[1], s[2])

    def is_night(self):
        t = self.time % 1.0
        return t < 0.20 or t > 0.78

    def daylight(self):
        """0 (noche) a 1 (dia). Lo usa game.py para el cielo y la luz."""
        t = self.time % 1.0
        if 0.25 <= t <= 0.70:
            return 1.0
        if t < 0.20 or t > 0.80:
            return 0.0
        if 0.20 <= t < 0.25:
            return (t - 0.20) / 0.05
        return 1.0 - (t - 0.70) / 0.10

    # ---------- generacion ----------
    def generate(self, seed=None, progress=None, **opts):
        """Genera un mundo completo. **opts: overrides de config.

        Opts: hills_amp, cave_size, ore_richness, tree_density,
              do_caves, do_ores, do_trees, do_structures (True/False).
        progress(frac, label): callback para la pantalla de carga.
        """
        from config import WG_HILLS_AMP, WG_CAVE_SIZE, WG_ORE_RICHNESS, WG_TREE_DENSITY
        if seed is None:
            seed = random.randint(0, 999999)
        rng = random.Random(seed)
        self.seed = seed
        self.chest_loot = {}
        nz = Noise(seed)
        W, H = self.w, self.h
        hills_amp = opts.get("hills_amp", WG_HILLS_AMP)
        cave_size = opts.get("cave_size", WG_CAVE_SIZE)
        richness = opts.get("ore_richness", WG_ORE_RICHNESS)
        tree_density = opts.get("tree_density", WG_TREE_DENSITY)

        def _pb(f, label):
            if progress:
                progress(f, label)

        _pb(0.02, "Relieve del continente...")
        self._fase_relieve(nz, rng, hills_amp)
        _pb(0.15, "Capas de tierra y piedra...")
        self._fase_capas(nz, rng)
        if opts.get("do_ores", True):
            _pb(0.30, "Vetas de mineral...")
            self._fase_menas(nz, richness)
        if opts.get("do_caves", True):
            _pb(0.45, "Tallando cuevas...")
            self._fase_cuevas(nz, rng, cave_size, progress=lambda f: _pb(0.45 + f * 0.20, "Tallando cuevas..."))
        if opts.get("do_structures", True):
            _pb(0.66, "Abriendo el Abismo...")
            self._fase_abismo(nz, rng)  # antes que bedrock y estructuras
        if opts.get("do_biomes", True):
            _pb(0.78, "Biomas profundos...")
            self._fase_biomas_profundos(nz, rng)  # hongos, ruinas, bosques
        _pb(0.88, "Bordes de bedrock...")
        self._fase_bedrock(rng)
        if opts.get("do_trees", True):
            _pb(0.92, "Plantando bosques...")
            self._fase_arboles(nz, rng, tree_density)
        if opts.get("do_structures", True):
            _pb(0.96, "Ruinas y cofres...")
            self._fase_estructuras(nz, rng)
        # spawn seguro en el centro, con plataforma limpia
        sx = W // 2
        self._limpiar_zona(sx - 12, self.heights[sx] - 16, 26, 18)
        for dx in range(-12, 13):
            if self.in_bounds(sx + dx, self.heights[sx]):
                self.tiles[self.heights[sx]][sx + dx] = 18
        self.spawn = (sx, self.heights[sx] - 2)
        self._choza_liora(rng, sx)
        _pb(0.968, "Luz del sol...")
        self.compute_sun(progress=lambda f: _pb(0.968 + f * 0.012, "Luz del sol..."))
        _pb(0.982, "Encendiendo antorchas...")
        self.compute_torch_full(progress=lambda f: _pb(0.982 + f * 0.014, "Encendiendo antorchas..."))
        _pb(1.0, "Listo!")

    # ----- fase 1: relieve con ruido fractal (continente + colinas) -----
    def _fase_relieve(self, nz, rng, hills_amp, **kwargs):
        """Altura por columna: continente suave + colinas con detalle.

        Conecta con: todas las fases (heights[] dice donde esta la superficie).
        """
        W, H = self.w, self.h
        base = H // 3
        for x in range(W):
            continente = nz.fbm1(x * 0.012, octaves=3)      # -1..1, valles/montes
            colinas = nz.fbm1(x * 0.06 + 100.0, octaves=3)  # detalle fino
            hgt = base + int(continente * 9 + colinas * hills_amp)
            self.heights[x] = max(8, min(H // 2, hgt))

    # ----- fase 2: capas de tierra/piedra + playas y desiertos -----
    def _fase_capas(self, nz, rng, **kwargs):
        """Rellena cada columna: hierba/arena, tierra, piedra. Playas abajo,
        manchas de desierto donde la humedad es alta. Conecta con: fase 1."""
        W, H = self.w, self.h
        base = H // 3
        for x in range(W):
            sy = self.heights[x]
            humedad = nz.fbm1(x * 0.02 + 500.0, octaves=2)
            desierto = humedad > 0.35
            playa = sy >= base + 4
            grosor_tierra = 4 + int((nz.n1(x * 0.09 + 7.0) * 0.5 + 0.5) * 3)
            for y in range(H):
                if y < sy:
                    self.tiles[y][x] = 0
                elif y == sy:
                    self.tiles[y][x] = 5 if (playa or desierto) else 18
                elif y < sy + grosor_tierra:
                    self.tiles[y][x] = 5 if desierto else 1
                else:
                    self.tiles[y][x] = 2

    # ----- fase 3: vetas de mineral en blobs de ruido (por profundidad) -----
    def _fase_menas(self, nz, richness=1.0, **kwargs):
        """Vetas organicas: cada mineral tiene su campo de ruido y su banda
        de profundidad. richness>1 = mas mineral (umbral mas bajo).

        OPT: solo filas bajo tierra (desde min(heights)), un solo campo
        de ruido por banda y octaves=2 -> ~3x mas rapido con igual aspecto.
        """
        from noise import fbm2
        W, H = self.w, self.h
        tiles = self.tiles
        pa, pb, pc = nz.perm, nz.perm_b, nz.perm_c
        y_start = max(12, min(self.heights) - 1)
        for y in range(y_start, H):
            depth = y / H
            row = tiles[y]
            if depth > 0.72:
                th_d, th_g = 0.62 / richness, 0.58 / richness
                for x in range(W):
                    if row[x] != 2:
                        continue
                    if fbm2(x * 0.15, y * 0.15, pc, octaves=2) > th_d:
                        row[x] = 9    # diamante
                    elif fbm2(x * 0.12 + 31, y * 0.12, pb, octaves=2) > th_g:
                        row[x] = 8    # oro tambien al fondo
            elif depth > 0.55:
                th_g, th_i = 0.58 / richness, 0.48 / richness
                for x in range(W):
                    if row[x] != 2:
                        continue
                    if fbm2(x * 0.12 + 31, y * 0.12, pb, octaves=2) > th_g:
                        row[x] = 8    # oro
                    elif fbm2(x * 0.10 + 77, y * 0.10, pa, octaves=2) > th_i:
                        row[x] = 7    # hierro
            elif depth > 0.38:
                th_i, th_c = 0.48 / richness, 0.40 / richness
                for x in range(W):
                    if row[x] != 2:
                        continue
                    if fbm2(x * 0.10 + 77, y * 0.10, pa, octaves=2) > th_i:
                        row[x] = 7    # hierro
                    elif fbm2(x * 0.09 + 133, y * 0.09, pa, octaves=2) > th_c:
                        row[x] = 6    # carbon
            elif y > 12:
                th_c = 0.40 / richness
                for x in range(W):
                    if row[x] != 2:
                        continue
                    if fbm2(x * 0.09 + 133, y * 0.09, pa, octaves=2) > th_c:
                        row[x] = 6    # carbon

    # ----- fase 4: cuevas (crestas retorcidas + bolsillos + gusanos) -----
    def _fase_cuevas(self, nz, rng, cave_size=0.06, progress=None, **kwargs):
        """Talla galerias donde el ruido 'cresta' ~0 (tuneles conectados),
        bolsillos donde fbm2 es alto, y gusanos que garantizan entradas.

        No toca la superficie (y < sy+3) ni el bedrock. Conecta con: fase 1
        (heights) y fase 3 (puede atravesar vetas, como en Terraria).

        OPT: warp barato (2 noise2 en vez de 2 fbm2), ridged/fbm de
        2 octavas, arranque desde min(heights) y mascara a media
        resolucion (bloques 2x2): ~4x menos ruido con tuneles iguales.
        """
        from noise import noise2, fbm2, ridged2
        W, H = self.w, self.h
        tiles = self.tiles
        heights = self.heights
        perm, perm_b, perm_c = nz.perm, nz.perm_b, nz.perm_c
        y_start = max(2, min(heights) + 3)
        _carve = (1, 2, 5, 6, 7, 8, 9)
        y2_start, y2_end = y_start // 2, H // 2
        for y2 in range(y2_start, y2_end):
            y = y2 * 2
            for x2 in range(W // 2):
                x = x2 * 2
                # rechazo rapido del bloque 2x2
                t00 = tiles[y][x]
                t10 = tiles[y][x + 1]
                if y + 1 < H:
                    t01 = tiles[y + 1][x]
                    t11 = tiles[y + 1][x + 1]
                    if (t00 not in _carve and t10 not in _carve
                            and t01 not in _carve and t11 not in _carve):
                        continue
                    if (y < heights[x] + 3 and y < heights[x + 1] + 3
                            and y + 1 < heights[x] + 3 and y + 1 < heights[x + 1] + 3):
                        continue
                else:
                    if t00 not in _carve and t10 not in _carve:
                        continue
                    if y < heights[x] + 3 and y < heights[x + 1] + 3:
                        continue
                # warp barato: 1 octava por eje (antes fbm 2 octavas x2)
                ox = noise2(x * 0.05 + 13.7, y * 0.05 + 91.2, perm_b)
                oy = noise2(x * 0.05 + 47.3, y * 0.05 + 17.9, perm_c)
                wx = x + ox * 0.9
                wy = y + oy * 0.9
                carve = ridged2(wx * 0.09, wy * 0.09, perm, octaves=2) < cave_size
                if not carve and (y / H) > 0.35:
                    carve = fbm2(x * 0.05 + 9, y * 0.05, perm_c, octaves=2) > 0.48
                if not carve:
                    continue
                for dy in (0, 1):
                    ny = y + dy
                    if ny >= H:
                        break
                    row = tiles[ny]
                    for dx in (0, 1):
                        nx = x + dx
                        if row[nx] in _carve and ny >= heights[nx] + 3:
                            row[nx] = 0
            if progress and (y2 & 63) == 0:
                progress((y2 - y2_start) / max(1, y2_end - y2_start))
        # gusanos: 20 tuneles (antes 10) para el mundo grande
        for i in range(20):
            x = rng.randint(5, W - 5)
            y = rng.randint(self.heights[x] + 4, H - 8)
            pasos = rng.randint(120, 300)
            ang = rng.uniform(0, 6.28)
            for _ in range(pasos):
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-2, -1, 0, 1, 2):
                        nx, ny = x + dx, y + dy
                        if 1 <= nx < W - 1 and 1 <= ny < H - 1:
                            if self.tiles[ny][nx] != 10 and ny > self.heights[nx] + 2:
                                self.tiles[ny][nx] = 0
                ang += rng.uniform(-0.5, 0.5)
                x += int(round(__import__("math").cos(ang)))
                y += int(round(__import__("math").sin(ang) * 0.7))
                x = max(2, min(W - 3, x))
                y = max(5, min(H - 4, y))

    # ----- fase 6b: EL ABISMO (fosa enorme estilo Made in Abyss) -----
    # Temas por capa DENTRO del hueco (muro/suelo/luz/deco distintos):
    #  1 Borde = piedra + losa + antorcha | 2 Tentaculos = micelio + setas
    #  3 Falla = pizarra + losa + antorcha | 4 Copas = ladrillo + farol
    #  5 Cadaveres = hueso + flor | 6 Capital = roca + ladrillo + farol.
    ABYSS_THEME = {
        1: dict(wall=2, back=21, floor=23, light=14, deco=(4, 14)),
        2: dict(wall=24, back=22, floor=24, light=25, deco=(25, 4)),
        3: dict(wall=27, back=22, floor=23, light=14, deco=(19, 4)),
        4: dict(wall=15, back=21, floor=15, light=29, deco=(14, 29)),
        5: dict(wall=28, back=22, floor=28, light=19, deco=(19, 28)),
        6: dict(wall=20, back=22, floor=15, light=29, deco=(29, 19)),
        7: dict(wall=27, back=22, floor=28, light=29, deco=(28, 19)),
    }

    def _fase_abismo(self, nz, rng, **kwargs):
        """El Abismo como en Made in Abyss: un CRATER-campana enorme, muy
        ancho en la boca (~76 tiles) que se ESTRECHA al bajar (~20 en el
        fondo), con terrazas para descender, paredes de roca TEMATICA por
        capa, campamento del Vigia en el borde y santuario con cofre abajo.

        Guarda abyss_x/top (los usan game.py y Bruno).
        Conecta con: abyss.py (capas para decorar), fase 1 (heights).
        """
        import abyss
        W, H = self.w, self.h
        sx = W // 2
        ax = self._sitio_superficie(rng, lejos_de=sx, margen=70, ancho=80)
        # La boca (±55) y el campamento (+63) deben caber en el mundo.
        ax = max(60, min(W - 70, ax))
        top = self.heights[ax]
        self.abyss_x, self.abyss_top = ax, top
        # boca del crater ancha y escalonada
        for dy in range(0, 12):
            w = 44 - dy * 3
            for dx in range(-w, w + 1):
                nx, ny = ax + dx, top + dy
                if self.in_bounds(nx, ny) and abs(dx) <= w - 1:
                    if self.tiles[ny][nx] != 10:
                        self.tiles[ny][nx] = 0
        # anillo del borde: losas + antorchas (como Orth mirando al agujero)
        for dx in list(range(-46, -38)) + list(range(39, 47)):
            if self.in_bounds(ax + dx, top):
                self.tiles[top][ax + dx] = 23
            if self.in_bounds(ax + dx, top - 1) and rng.random() < 0.4:
                self.tiles[top - 1][ax + dx] = 14
        # campamento del Vigia al borde (Bruno vive aqui)
        camp = ax + 50
        for dx in range(14):
            if self.in_bounds(camp + dx, top):
                self.tiles[top][camp + dx] = 11
        for dy in range(1, 7):
            if self.in_bounds(camp, top - dy):
                self.tiles[top - dy][camp] = 11
            if self.in_bounds(camp + 13, top - dy):
                self.tiles[top - dy][camp + 13] = 11
        for dx in range(14):
            if self.in_bounds(camp + dx, top - 7):
                self.tiles[top - 7][camp + dx] = 11
        for dx in range(1, 13):
            for dy in range(1, 7):
                if self.in_bounds(camp + dx, top - dy) and self.tiles[top - dy][camp + dx] == 0:
                    self.tiles[top - dy][camp + dx] = 21
        self.tiles[top - 1][camp] = 32  # puerta del vigia
        self.tiles[top - 2][camp] = 32
        self.tiles[top - 4][camp + 13] = 34  # ventana
        self.tiles[top - 1][camp + 2] = 30  # cama del vigia
        self.tiles[top - 1][camp + 3] = 30
        self.tiles[top - 1][camp + 6] = 12  # mesa
        self.tiles[top - 1][camp + 8] = 31  # silla
        self.tiles[top - 4][camp + 7] = 29  # farol colgado
        lado = 1
        centro_x = float(ax)
        y_end = H - 4
        for y in range(top + 3, y_end):
            capa = abyss.layer_at(y, H, top)
            th = self.ABYSS_THEME.get(max(1, capa),
                                      self.ABYSS_THEME[1])
            # CAMPANA: de ~38 arriba a ~10 abajo + ondulacion leve
            d = (y - top) / max(1, y_end - top)
            half_base = 38 + (10 - 38) * d
            centro_x += nz.fbm1(y * 0.06 + 900.0, octaves=2) * 0.15
            centro_x = max(ax - 2, min(ax + 2, centro_x))
            cx = int(round(centro_x))
            half = int(half_base + nz.fbm1(y * 0.04 + 901.0, octaves=2) * 2)
            half = max(8, half)
            for dx in range(-half - 4, half + 5):
                nx = cx + dx
                if not self.in_bounds(nx, y):
                    continue
                adx = abs(dx)
                if adx <= half:
                    if self.tiles[y][nx] != 10:
                        self.tiles[y][nx] = 0  # aire del pozo
                elif adx in (half + 1, half + 2, half + 3):
                    # muralla triple con la roca TEMATICA de la capa
                    if self.tiles[y][nx] in (2, 7, 8, 1, 5, 6, 9, 20, 24, 27, 28):
                        self.tiles[y][nx] = th["wall"] if capa >= 1 else 2
                elif adx == half + 4 and capa >= 1:
                    # fondo decorativo tras la muralla
                    if self.tiles[y][nx] in (2, 1, 5):
                        self.tiles[y][nx] = th["back"]
            # terrazas anchas cada 12 tiles (alternan lado, 18 de ancho)
            if (y - top) % 12 == 7:
                lado *= -1
                for dx in range(18):
                    nx = cx + lado * (half - 1) + (dx if lado > 0 else -dx)
                    if self.in_bounds(nx, y):
                        self.tiles[y][nx] = th["floor"]
                # luz tematica en el extremo interior
                farol = cx + lado * (half - 3)
                if self.in_bounds(farol, y - 1):
                    self.tiles[y - 1][farol] = th["light"]
                farol2 = cx + lado * (half - 14)
                if self.in_bounds(farol2, y - 1) and self.tiles[y - 1][farol2] == 0:
                    self.tiles[y - 1][farol2] = th["light"]
                # barandilla de losa en el borde
                edge = cx + lado * half
                if self.in_bounds(edge, y - 1) and self.tiles[y - 1][edge] == 0:
                    if rng.random() < 0.7:
                        self.tiles[y - 1][edge] = 23
            # decoracion colgante del borde interior, tematica por capa
            if rng.random() < 0.30 + capa * 0.03:
                for sgn in (-1, 1):
                    nx = cx + sgn * half
                    if self.in_bounds(nx, y) and self.tiles[y][nx] == 0:
                        r = rng.random()
                        d0, d1 = th["deco"]
                        self.tiles[y][nx] = d0 if r < 0.7 else d1
            # vetas de pared tras la muralla de roca
            if capa in (1, 2) and rng.random() < 0.06:
                nx = cx + rng.choice([-1, 1]) * (half + 1)
                if self.in_bounds(nx, y) and self.tiles[y][nx] == 20:
                    self.tiles[y][nx] = 21
        # santuario del fondo: sala amplia + pilares + luces + cofre
        fondo = H - 5
        for dx in range(-18, 19):
            if self.in_bounds(ax + dx, fondo + 1):
                self.tiles[fondo + 1][ax + dx] = 15
            for dy in range(-6, 1):
                nx, ny = ax + dx, fondo + dy
                if self.in_bounds(nx, ny) and abs(dx) > 1:
                    if self.tiles[ny][nx] == 20:
                        self.tiles[ny][nx] = 0
        for dx in (-15, 15):
            for dy in range(-6, 1):
                if self.in_bounds(ax + dx, fondo + dy):
                    self.tiles[fondo + dy][ax + dx] = 15
            if self.in_bounds(ax + dx, fondo - 7):
                self.tiles[fondo - 7][ax + dx] = 29
        for dx in (-7, 7):
            if self.in_bounds(ax + dx, fondo) and self.tiles[fondo][ax + dx] == 0:
                self.tiles[fondo][ax + dx] = 29
        self.tiles[fondo][ax] = 16
        self.chest_loot[(ax, fondo)] = [
            ("reliquia_orbe", 1),
            ("diamante", rng.randint(3, 5)),
            ("pocion_vida_mayor", 2),
            ("baya_luminosa", rng.randint(3, 6)),
            ("moneda_oro", rng.randint(2, 5)),
        ]

    def layer_at(self, tx, ty, *args, **kwargs):
        """Capa del Abismo 0..6 en ese tile (para game.py y spawns)."""
        import abyss
        sy = self.heights[tx] if 0 <= tx < self.w else ty
        return abyss.layer_at(ty, self.h, sy, *args, **kwargs)

    # ----- fase 6c: BIOMAS PROFUNDOS (hongos, civilizaciones, bosques) -----
    def _fase_biomas_profundos(self, nz, rng, **kwargs):
        """Biomas bajo la superficie para el mundo 3x profundo:

        - Hongos brillantes (prof 0.35-0.65): salas con suelo de micelio,
          setas gigantes (tallo + sombrero luminoso) y setas pequenas.
        - Civilizaciones (prof 0.30-0.75): salas de ladrillo con pilares,
          mesa, cofre con loot y antorchas; 2 templos con altar.
        - Bosques subterraneos (prof >0.65): tierra con hierba, arboles
          Arboles y flores abisales que dan luz.

        Evitan el Abismo (+-22). Mas biomas y mas grandes.
        Conecta con: blocks (24/25/26), abyss.
        """
        W, H = self.w, self.h
        abx = getattr(self, "abyss_x", None)

        def lejos_abismo(x, r=44):
            return abx is None or abs(x - abx) >= r

        def elipse(cx, cy, rx, ry):
            pts = []
            for dy in range(-ry, ry + 1):
                for dx in range(-rx, rx + 1):
                    if (dx / max(1, rx)) ** 2 + (dy / max(1, ry)) ** 2 <= 1.0:
                        nx, ny = cx + dx, cy + dy
                        if self.in_bounds(nx, ny):
                            pts.append((nx, ny))
            return pts

        # ---- 1) hongos brillantes (12 salas, antes 7) ----
        for _ in range(12):
            my = rng.randint(int(H * 0.35), int(H * 0.65))
            mx = rng.randint(20, W - 20)
            if not lejos_abismo(mx):
                continue
            rx, ry = rng.randint(20, 32), rng.randint(12, 18)
            for nx, ny in elipse(mx, my, rx, ry):
                if self.tiles[ny][nx] != 10:
                    self.tiles[ny][nx] = 0
            # suelo de micelio
            for sx in range(mx - rx, mx + rx + 1):
                for yy in range(my - ry, my + ry + 1):
                    if not self.in_bounds(sx, yy):
                        break
                    if (self.tiles[yy][sx] == 0
                            and self.in_bounds(sx, yy + 1)
                            and self.tiles[yy + 1][sx] in (1, 2, 5)):
                        self.tiles[yy + 1][sx] = 24
            # setas gigantes (3-5, antes 2-4)
            for _ in range(rng.randint(3, 5)):
                sx = mx + rng.randint(-rx + 2, rx - 2)
                base = None
                for yy in range(my + ry, my - ry, -1):
                    if not self.in_bounds(sx, yy):
                        break
                    if self.tiles[yy][sx] == 24 and self.tiles[yy - 1][sx] == 0:
                        base = yy - 1
                        break
                if base is None:
                    continue
                tall = rng.randint(6, 12)
                for i in range(tall):
                    if self.in_bounds(sx, base - i) and self.tiles[base - i][sx] == 0:
                        self.tiles[base - i][sx] = 26
                capy = base - tall
                for dx in range(-4, 5):
                    for dy in (0, 1):
                        nx, ny = sx + dx, capy + dy
                        if self.in_bounds(nx, ny) and self.tiles[ny][nx] == 0:
                            if abs(dx) <= 4 - dy:
                                self.tiles[ny][nx] = 25
            # setas pequenas sueltas
            for _ in range(rng.randint(6, 12)):
                sx = mx + rng.randint(-rx, rx)
                for yy in range(my + ry, my - ry, -1):
                    if not self.in_bounds(sx, yy):
                        break
                    if self.tiles[yy][sx] in (24, 1, 2) and self.tiles[yy - 1][sx] == 0:
                        self.tiles[yy - 1][sx] = 25
                        break

        # ---- 2) civilizaciones (8 salas, antes 6) ----
        for r in range(8):
            hondo = (r >= 6)  # las ultimas 2 son templos con altar
            if hondo:
                my = rng.randint(int(H * 0.65), H - 16)
            else:
                my = rng.randint(int(H * 0.30), int(H * 0.65))
            mx = rng.randint(20, W - 25)
            if not lejos_abismo(mx, 44):
                continue
            rw, rh = (30, 20) if hondo else (rng.randint(22, 32), rng.randint(12, 16))
            for dy in range(rh):
                for dx in range(rw):
                    nx, ny = mx + dx, my + dy
                    if self.in_bounds(nx, ny) and self.tiles[ny][nx] != 10:
                        self.tiles[ny][nx] = 0
            for dx in range(rw):
                self.set(mx + dx, my + rh - 1, 15)
                self.set(mx + dx, my, 15)
            for dy in range(rh):
                self.set(mx, my + dy, 15)
                self.set(mx + rw - 1, my + dy, 15)
            for px in range(mx + 6, mx + rw - 1, 6):
                for dy in range(1, rh - 1):
                    self.set(px, my + dy, 15)
            self.set(mx + 2, my + rh - 2, 12)
            self.set(mx + rw - 3, my + rh - 2, 16)
            self.set(mx + 1, my + rh - 3, 14)
            self.set(mx + rw - 2, my + rh - 3, 14)
            if hondo:
                self.set(mx + rw // 2, my + rh - 2, 17)
                self.set(mx + rw // 2, my + rh - 3, 14)
                loot = [("reliquia_orbe", 1), ("diamante", rng.randint(2, 4)),
                        ("moneda_oro", rng.randint(3, 8)), ("pocion_vida_mayor", 2)]
            else:
                loot = [("moneda_plata", rng.randint(8, 20)),
                        ("moneda_oro", rng.randint(1, 3)),
                        ("lingote_hierro", rng.randint(3, 8)),
                        ("pocion_vida_menor", rng.randint(1, 3)),
                        ("antorcha", rng.randint(4, 10))]
            self.chest_loot[(mx + rw - 3, my + rh - 2)] = loot

        # ---- 3) bosques subterraneos (7, antes 5) ----
        for _ in range(7):
            my = rng.randint(int(H * 0.65), H - 14)
            mx = rng.randint(22, W - 22)
            if not lejos_abismo(mx):
                continue
            rx, ry = rng.randint(24, 36), rng.randint(14, 20)
            for nx, ny in elipse(mx, my, rx, ry):
                if self.tiles[ny][nx] != 10:
                    self.tiles[ny][nx] = 0
            # suelo de tierra con hierba
            for sx in range(mx - rx, mx + rx + 1):
                for yy in range(my - ry, my + ry + 1):
                    if not self.in_bounds(sx, yy):
                        break
                    if (self.tiles[yy][sx] == 0
                            and self.in_bounds(sx, yy + 1)
                            and self.tiles[yy + 1][sx] == 2):
                        self.tiles[yy + 1][sx] = 1 if rng.random() < 0.4 else 18
            # arboles subterraneos (4-8, antes 3-6)
            for _ in range(rng.randint(6, 12)):
                sx = mx + rng.randint(-rx + 2, rx - 2)
                base = None
                for yy in range(my + ry, my - ry, -1):
                    if not self.in_bounds(sx, yy):
                        break
                    if self.tiles[yy][sx] in (1, 18) and self.tiles[yy - 1][sx] == 0:
                        base = yy - 1
                        break
                if base is None:
                    continue
                tall = rng.randint(6, 12)
                for i in range(tall):
                    if self.in_bounds(sx, base - i) and self.tiles[base - i][sx] == 0:
                        self.tiles[base - i][sx] = 3
                for dx in range(-3, 4):
                    for dy in range(-3, 3):
                        nx, ny = sx + dx, base - tall + dy
                        if (self.in_bounds(nx, ny) and self.tiles[ny][nx] == 0
                                and abs(dx) + abs(dy) <= 5 and rng.random() < 0.85):
                            self.tiles[ny][nx] = 4
            # flores abisales para luz
            for _ in range(rng.randint(6, 14)):
                sx = mx + rng.randint(-rx, rx)
                for yy in range(my + ry, my - ry, -1):
                    if not self.in_bounds(sx, yy):
                        break
                    if self.tiles[yy][sx] in (1, 18) and self.tiles[yy - 1][sx] == 0:
                        if rng.random() < 0.7:
                            self.tiles[yy - 1][sx] = 19
                        break
    # ----- fase 5: bedrock bordes y fondo -----
    def _fase_bedrock(self, rng, **kwargs):
        W, H = self.w, self.h
        for x in range(W):
            self.tiles[H - 1][x] = 10
            if rng.random() < 0.5:
                self.tiles[H - 2][x] = 10
        for y in range(H):
            self.tiles[y][0] = 10
            self.tiles[y][W - 1] = 10

    # ----- fase 6: arboles donde el bosque es denso -----
    def _fase_arboles(self, nz, rng, density=0.12, **kwargs):
        """Bosques en manchas (ruido 1D) en vez de uniforme. Mas arboles para el mundo grande."""
        W = self.w
        for x in range(5, W - 5):
            sy = self.heights[x]
            if self.tiles[sy][x] != 18:
                continue
            bosque = nz.fbm1(x * 0.03 + 300.0, octaves=2)
            if bosque < 0.0 or rng.random() > density + bosque * 0.30:
                continue
            tronco = rng.randint(8, 13)
            if sy - tronco - 2 < 0:
                continue
            if any(self.tiles[sy - i][x] == 3 for i in range(1, 4)):
                continue
            for i in range(1, tronco + 1):
                self.tiles[sy - i][x] = 3
            copa = sy - tronco
            for dx in range(-3, 4):
                for dy in range(-3, 3):
                    nx, ny = x + dx, copa + dy
                    if self.in_bounds(nx, ny) and self.tiles[ny][nx] == 0:
                        if abs(dx) + abs(dy) <= 5 and rng.random() < 0.85:
                            self.tiles[ny][nx] = 4

    # ----- fase 7: estructuras con loot -----
    def _fase_estructuras(self, nz, rng, **kwargs):
        """Casas amuebladas (cama, mesa, silla, farol, paredes), minas con
        galerias y faroles, altares de Underdown iluminados, cabanas subterraneas
        completas y cofres de cueva. Todo x2 en tiles (TILE=6)."""
        W, H = self.w, self.h
        sx = W // 2
        abx = getattr(self, "abyss_x", None)
        # 2 casas amuebladas: suelo, paredes, techo con puerta, interior
        # con cama + mesa + silla + farol + paredes de fondo y cofre.
        for _ in range(2):
            hx = self._sitio_superficie(rng, lejos_de=sx, margen=30, ancho=26,
                                        avoid_x=abx, avoid_r=60)
            hy = self.heights[hx]
            self._limpiar_zona(hx, hy - 10, 26, 10)
            for dx in range(26):  # suelo de tablones
                self.tiles[hy][hx + dx] = 11
            for dy in range(1, 10):  # paredes
                self.tiles[hy - dy][hx] = 11
                self.tiles[hy - dy][hx + 25] = 11
            for dx in range(26):  # techo con puerta de 4
                if dx not in (11, 12, 13, 14):
                    self.tiles[hy - 10][hx + dx] = 11
            for dx in range(1, 25):  # paredes de fondo del interior
                for dy in range(1, 10):
                    if self.tiles[hy - dy][hx + dx] == 0:
                        self.tiles[hy - dy][hx + dx] = 21
            # puerta en la pared izquierda + ventanas de cristal
            self.tiles[hy - 1][hx] = 32
            self.tiles[hy - 2][hx] = 32
            self.tiles[hy - 5][hx + 25] = 34
            self.tiles[hy - 7][hx + 25] = 34
            self.tiles[hy - 6][hx] = 34
            fy = hy - 1
            self.tiles[fy][hx + 3] = 30      # cama
            self.tiles[fy][hx + 4] = 30
            self.tiles[fy][hx + 8] = 12      # mesa de trabajo
            self.tiles[fy][hx + 10] = 31     # silla
            self.tiles[fy - 3][hx + 9] = 29  # farol colgado
            self.tiles[fy][hx + 14] = 13     # horno
            self.tiles[fy - 1][hx + 14] = 14  # antorcha sobre el horno
            self.tiles[fy][hx + 20] = 16     # cofre
            self.tiles[fy - 3][hx + 20] = 29  # farol sobre el cofre
            self.chest_loot[(hx + 20, fy)] = [
                ("moneda_plata", rng.randint(5, 15)),
                ("pocion_vida_menor", rng.randint(1, 3)),
                ("lingote_hierro", rng.randint(2, 6)),
                ("antorcha", rng.randint(5, 12)),
                ("cama", 1),
            ]
        # 2 minas: pozo ancho con travesanos, galerias y faroles
        for _ in range(2):
            mx = self._sitio_superficie(rng, lejos_de=sx, margen=20, ancho=6,
                                        avoid_x=abx, avoid_r=60)
            my_top = self.heights[mx]
            fondo = min(H - 8, my_top + 84)
            for y in range(my_top, fondo):
                for dx in (-2, -1, 0, 1, 2):
                    if self.in_bounds(mx + dx, y):
                        self.tiles[y][mx + dx] = 0
                if (y - my_top) % 8 == 0:
                    self.set(mx - 2, y, 3)
                    self.set(mx + 2, y, 3)
                    self.set(mx - 2, y - 1, 29)
                if (y - my_top) % 10 == 0:
                    self.set(mx + 2, y, 29)
            for gy in (my_top + 28, my_top + 56):
                if gy < fondo:
                    for dx in range(-18, 19):
                        if self.in_bounds(mx + dx, gy):
                            self.tiles[gy][mx + dx] = 0
                            self.tiles[gy - 3][mx + dx] = 0
                            self.tiles[gy - 4][mx + dx] = 0
                        if dx % 6 == 0 and self.in_bounds(mx + dx, gy - 1):
                            self.set(mx + dx, gy - 1, 3)
                    self.set(mx - 16, gy - 1, 29)
                    self.set(mx + 16, gy - 1, 29)
            self.tiles[fondo][mx] = 16
            self.chest_loot[(mx, fondo)] = [
                ("moneda_oro", rng.randint(1, 3)),
                ("pocion_vida_mayor", 1),
                ("diamante", rng.randint(1, 3)),
            ]
        # 2 altares de Underdown con faroles
        for _ in range(2):
            ax = self._sitio_superficie(rng, lejos_de=sx, margen=16, ancho=16,
                                        avoid_x=abx, avoid_r=60)
            ay = self.heights[ax]
            for dx in range(-7, 8):
                if self.in_bounds(ax + dx, ay):
                    self.tiles[ay][ax + dx] = 15
            self.tiles[ay - 1][ax] = 17
            self.tiles[ay - 2][ax] = 29
            for dx in (-6, 6):
                if self.in_bounds(ax + dx, ay - 1):
                    self.tiles[ay - 1][ax + dx] = 29
        # 3 cabanas subterraneas
        for _ in range(3):
            self._cabana_subterranea(rng)
        # cofres sueltos en cuevas (10, antes 6)
        puestos = 0
        for _ in range(120):
            if puestos >= 14:
                break
            x = rng.randint(2, W - 3)
            y = rng.randint(H // 2, H - 4)
            if self.tiles[y][x] == 0 and self.solid(x, y + 1):
                self.tiles[y][x] = 16
                self.chest_loot[(x, y)] = [
                    ("moneda_plata", rng.randint(3, 10)),
                    ("carbon", rng.randint(3, 8)),
                    ("pocion_vida_menor", rng.randint(1, 2)),
                    ("gel", rng.randint(2, 6)),
                ]
                puestos += 1

    def _choza_liora(self, rng, sx, **kwargs):
        """Choza de Liora junto al spawn: suelo, paredes, techo, puerta
        ABIERTA hacia el jugador, ventana, cama, mesa, silla y farol.
        Liora (game.py) aparece al lado de la puerta."""
        hy = self.heights[sx + 8]
        hx = sx + 8
        self._limpiar_zona(hx, hy - 8, 16, 8)
        for dx in range(16):
            self.tiles[hy][hx + dx] = 11
        for dy in range(1, 8):
            self.tiles[hy - dy][hx] = 11
            self.tiles[hy - dy][hx + 15] = 11
        for dx in range(16):
            if dx not in (6, 7, 8, 9):
                self.tiles[hy - 8][hx + dx] = 11
        for dx in range(1, 15):
            for dy in range(1, 8):
                if self.tiles[hy - dy][hx + dx] == 0:
                    self.tiles[hy - dy][hx + dx] = 21
        fy = hy - 1
        self.tiles[fy][hx] = 33      # puerta abierta (hacia el spawn)
        self.tiles[fy - 1][hx] = 33
        self.tiles[fy - 4][hx + 15] = 34  # ventana
        self.tiles[fy][hx + 3] = 30  # cama
        self.tiles[fy][hx + 4] = 30
        self.tiles[fy][hx + 7] = 12  # mesa
        self.tiles[fy][hx + 9] = 31  # silla
        self.tiles[fy - 3][hx + 8] = 29  # farol

    def _sitio_superficie(self, rng, lejos_de, margen, ancho, avoid_x=None, avoid_r=0, **kwargs):
        """Columna libre para una estructura: dentro del mundo, separada
        `margen` del punto lejos_de (spawn) y `avoid_r` del Abismo.
        **kwargs: ignora extras."""
        W = self.w
        for _ in range(80):
            x = rng.randint(5, W - 5 - ancho)
            if abs(x - lejos_de) >= margen:
                if avoid_x is None or abs(x - avoid_x) >= avoid_r:
                    return x
        return 10

    def _limpiar_zona(self, x, y, w, h, **kwargs):
        """Vacía un rectangulo de tiles (para interiores y spawn)."""
        for dy in range(h):
            for dx in range(w):
                if self.in_bounds(x + dx, y + dy):
                    self.tiles[y + dy][x + dx] = 0

    def _cabana_subterranea(self, rng, **kwargs):
        """Cabana minera completa: paredes de tablon, cama, mesa, silla,
        faroles y cofre con loot. Si no encuentra sitio, no pasa nada."""
        W, H = self.w, self.h
        abx = getattr(self, "abyss_x", None)
        for _ in range(120):
            x = rng.randint(4, W - 26)
            y = rng.randint(int(H * 0.35), H - 14)
            if abx is not None and abs(x + 8 - abx) < 44:
                continue  # no dentro del Abismo
            if self.tiles[y + 4][x + 8] == 0 or not self.solid(x + 8, y + 5):
                continue
            self._limpiar_zona(x, y - 2, 18, 9)
            for dx in range(18):  # suelo y techo
                self.set(x + dx, y + 6, 11)
                self.set(x + dx, y - 2, 11)
            for dy in range(-2, 7):  # paredes
                self.set(x, y + dy, 11)
                self.set(x + 17, y + dy, 11)
            for dx in range(1, 17):  # fondo rustico
                for dy in range(-1, 6):
                    if self.tiles[y + dy][x + dx] == 0:
                        self.tiles[y + dy][x + dx] = 21
            fy = y + 5
            self.set(x, fy, 32)   # puerta en la pared izquierda
            self.set(x, fy - 1, 32)
            self.set(x + 17, fy - 2, 34)  # ventana en la derecha
            self.set(x + 2, fy, 30)   # cama
            self.set(x + 3, fy, 30)
            self.set(x + 6, fy, 12)   # mesa de trabajo
            self.set(x + 8, fy, 31)   # silla
            self.set(x + 7, fy - 3, 29)  # farol colgado
            self.set(x + 12, fy, 16)  # cofre
            self.set(x + 12, fy - 3, 29)
            self.set(x + 15, fy, 13)  # horno pequeno
            self.chest_loot[(x + 12, fy)] = [
                ("moneda_plata", rng.randint(5, 12)),
                ("lingote_hierro", rng.randint(3, 7)),
                ("pocion_vida_menor", rng.randint(1, 2)),
                ("hierro_crudo", rng.randint(2, 5)),
            ]
            return

    # ---------- ayuda fisica ----------
    def find_ground(self, tx, ty):
        while ty < self.h - 1 and not self.solid(tx, ty + 1) and self.get(tx, ty + 1) != 10:
            ty += 1
        return ty

    # ---------- biomas (para fondos + transiciones en game.py) ----------
    def biome_at(self, tx, ty):
        """Bioma en el tile: bosque | pradera | desierto | cielo |
        cuevas | abismo. Lo usa game.py para el fondo parallax.
        Transiciones suaves: las franjas de 6 tiles en bordes las
        resuelve game.py mezclando colores (ver bg_blend)."""
        import abyss
        if not self.in_bounds(tx, ty):
            return "pradera"
        # Abismo: dentro de la fosa y bajo su boca
        ax = getattr(self, "abyss_x", None)
        atop = getattr(self, "abyss_top", 0)
        if ax is not None and abs(tx - ax) <= 12 and ty >= atop - 2:
            return "abismo"
        sy = self.heights[tx] if 0 <= tx < self.w else ty
        depth = ty / max(1, self.h)
        if ty < sy - 8:
            return "cielo"
        if depth > 0.55 or ty > sy + 18:
            return "cuevas"
        surf = self.get(tx, sy) if self.in_bounds(tx, sy) else 18
        if surf == 5:
            return "desierto"
        # bosque: hay troncos cerca de la superficie en +-6 columnas
        for dx in range(-6, 7):
            nx = tx + dx
            if not (0 <= nx < self.w):
                continue
            nsy = self.heights[nx]
            for dy in range(1, 8):
                if self.get(nx, nsy - dy) == 3:
                    return "bosque"
        return "pradera"

    # ---------- guardado ----------
    def save(self, path):
        # OPT v2: tiles como bytes comprimidos (zlib+base64) en vez de
        # lista JSON de 1.5M ints: el save pasa de ~5MB/10s a ~300KB/<1s.
        import base64
        import zlib
        raw = b"".join(bytes(row) for row in self.tiles)
        data = {
            "v": 2,
            "w": self.w, "h": self.h,
            "tiles_b64": base64.b64encode(zlib.compress(raw, 6)).decode("ascii"),
            "spawn": self.spawn,
            "time": self.time,
            "chest_loot": {f"{x},{y}": v for (x, y), v in self.chest_loot.items()},
            "seed": getattr(self, "seed", 0),
            "abyss_x": getattr(self, "abyss_x", self.w // 4),
            "abyss_top": getattr(self, "abyss_top", self.h // 3),
            "heights": getattr(self, "heights", [self.h // 3] * self.w),
        }
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path, w, h):
        import base64
        import zlib
        with open(path) as f:
            data = json.load(f)
        world = cls(data.get("w", w), data.get("h", h))
        if data.get("v") == 2 and "tiles_b64" in data:
            raw = zlib.decompress(base64.b64decode(data["tiles_b64"]))
            W, H = world.w, world.h
            assert len(raw) == W * H, "save corrupto"
            world.tiles = [bytearray(raw[y * W:(y + 1) * W]) for y in range(H)]
        else:
            # saves viejos v1: lista de listas -> bytearray
            world.tiles = [bytearray(row) for row in data["tiles"]]
        world.spawn = tuple(data["spawn"])
        world.time = data.get("time", 0.3)
        world.chest_loot = {}
        for k, v in data.get("chest_loot", {}).items():
            x, y = map(int, k.split(","))
            world.chest_loot[(x, y)] = v
        world.seed = data.get("seed", 0)
        world.abyss_x = data.get("abyss_x", world.w // 4)
        world.abyss_top = data.get("abyss_top", world.h // 3)
        # heights: vital para biome_at/spawn/layer (los saves viejos no lo tienen)
        heights = data.get("heights")
        if isinstance(heights, list) and len(heights) == world.w:
            world.heights = [int(v) for v in heights]
        else:
            # reconstruir superficie escaneando la primera columna solida
            world.heights = []
            for x in range(world.w):
                sy = 0
                for y in range(world.h):
                    if world.tiles[y][x] != 0:
                        sy = y
                        break
                world.heights.append(sy)
        # La luz no se guarda: se recomputa al cargar (como Terraria).
        world.compute_sun()
        world.compute_torch_full()
        return world
