"""Texturas y sprites 100% pixelart procedurales (sin PNG externos).

Estilo: todo se dibuja en un lienzo pequeno (PIXELES gordos, paleta
limitada, sin circulos suaves ni degradados) y se escala a su tamano
final con NEAREST, asi cada pixel se ve cuadrado y nitido, como debe
ser en pixelart.

Que hace:
    - Texturas de bloques en 16x16 -> 32 (clusters 2x2, dithering,
      bisel de 1px, brillos cuadrados).
    - SPRITES de personajes con animacion: Kael (idle/run/jump/fall),
      mobs (slime/walker/skeleton/bat/golem/king) y NPCs. Cada sprite
      es un frame cacheado; draw_player/draw_enemy solo eligen el
      frame segun el estado (igual que un spritesheet).
    - Si en el futuro pones PNGs en assets/ (p. ej.
      assets/mobs/player/run_0.png), load_sprite_file() los usa como
      override; si no existen, se usa el pixelart procedural.

Con que conecta:
    - game.py  -> get_tile_texture() para pintar el mundo.
    - ui.py    -> draw_item_icon() delega en get_item_icon().
    - entities/player.py -> Player.draw() delega en draw_player().
    - entities/mobs/enemies.py -> Enemy.draw() delega en draw_enemy().
    - entities/npc.py -> NPC.draw() delega en draw_npc().
    - blocks.py / items.py -> aportan los ids y nombres que aqui se dibujan.

Como tocarlo luego:
    Cada bloque tiene SU funcion _tex_* y cada personaje su _spr_*.
    Cambia la PALETA o los pixeles ahi. Todo acepta *args/**kwargs
    para anadir variantes sin romper llamadas viejas.
"""
import math
import os
import random
import pygame
from config import TILE

# Lienzo base pixelart: 16px -> 32px (pixel gordo de 2x2).
PB = 16

_cache_tiles = {}
_cache_icons = {}
_cache_sprites = {}
_file_cache = {}

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ---------------------------------------------------------------- utilidades
def shade(color, amt):
    """Aclara/oscurece un color RGB. amt>0 aclara, <0 oscurece."""
    return tuple(max(0, min(255, c + amt)) for c in color)


def _small(w=PB, h=PB):
    """Lienzo pequeno con alfa para dibujar pixel a pixel."""
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _up(small, size):
    """Escala NEAREST: el pixel gordo se conserva nitido (sin difuminar)."""
    if small.get_size() == (size, size):
        return small
    return pygame.transform.scale(small, (size, size))


def px(s, x, y, c):
    """Pinta 1 pixel del lienzo pequeno (respeta limites)."""
    w, h = s.get_size()
    if 0 <= x < w and 0 <= y < h:
        s.fill(c, (x, y, 1, 1))


def rect_px(s, x, y, w, h, c):
    """Rectangulo alineado a la rejilla de pixeles."""
    s.fill(c, pygame.Rect(x, y, w, h))


def bevel_px(s, light, dark):
    """Bisel pixelart de 1px: fila superior clara, inferior oscura."""
    w, h = s.get_size()
    for x in range(w):
        px(s, x, 0, light)
        px(s, x, h - 1, dark)


def cluster_noise(s, rng, n, colors, area=None, block=2):
    """Ruido en bloques de `block` px (clusters, no puntitos sueltos)."""
    W, H = s.get_size()
    ax, ay, aw, ah = area if area else (0, 0, W, H)
    for _ in range(n):
        x = rng.randint(ax, max(ax, ax + aw - block))
        y = rng.randint(ay, max(ay, ay + ah - block))
        rect_px(s, x, y, block, block, rng.choice(colors))


def dither_px(s, rng, n, color, area=None):
    """Dithering: pixeles sueltos dispersos (textura retro)."""
    W, H = s.get_size()
    ax, ay, aw, ah = area if area else (0, 0, W, H)
    for _ in range(n):
        px(s, rng.randint(ax, ax + aw - 1), rng.randint(ay, ay + ah - 1), color)


def speckle(surf, rng, n, colors, size=3, area=None):
    """Compat: ruido en bloques (antes eran puntitos sueltos)."""
    block = max(1, size // 2)
    cluster_noise(surf, rng, n, colors, area=area, block=block)


def edge_highlight(surf, light=(255, 255, 255), dark=(0, 0, 0), alpha=40):
    """Compat: bisel. En pixelart se aplica ANTES de escalar (ver bevel_px)."""
    pass


def load_sprite_file(*parts):
    """Override con PNG real si existe en assets/. Devuelve Surface o None.

    Ej: load_sprite_file("mobs", "player", "run_0.png"). Cachea el intento
    para no tocar disco cada frame. Asi los personajes YA tienen sistema
    de sprites: hoy procedurales, manana PNGs dibujados a mano.
    """
    key = tuple(parts)
    if key in _file_cache:
        return _file_cache[key]
    p = os.path.join(ASSETS, *parts)
    surf = None
    try:
        if os.path.isfile(p):
            surf = pygame.image.load(p).convert_alpha()
    except Exception:
        surf = None
    _file_cache[key] = surf
    return surf


def _blit_center(dst, src, x, y, w, h):
    """Centra src en el rect (x,y,w,h) con NEAREST si hay que reescalar."""
    sw, sh = src.get_size()
    if (sw, sh) != (w, h):
        src = pygame.transform.scale(src, (w, h))
    dst.blit(src, (x + (w - src.get_width()) // 2,
                   y + (h - src.get_height()) // 2))


# ------------------------------------------------------- texturas de bloques
def _tex_tierra(s, rng, *args, **kwargs):
    # Retro chunky estilo Terraria: manchas GORDAS (4-5px) de 2 tonos,
    # dithering en pares y SIN bisel por tile (el bisel marcaba la
    # cuadricula y rompia la conexion; los bordes los pone el autotile).
    base = (150, 98, 48)
    s.fill(base)
    cluster_noise(s, rng, 4, [(132, 84, 40), (168, 116, 62)], block=5)
    cluster_noise(s, rng, 5, [(120, 76, 36), (160, 108, 56)], block=4)
    _checker(s, rng, 7, (108, 68, 30))


def _tex_hierba(s, rng, *args, **kwargs):
    _tex_tierra(s, rng)
    # capa de hierba viva con borde dentado pixelart (3px + dientes)
    for x in range(16):
        depth = 3 + (1 if (x * 7 + rng.randint(0, 2)) % 3 == 0 else 0)
        for y in range(depth):
            px(s, x, y, (80, 172, 66))
    for x in range(16):
        px(s, x, 0, (118, 218, 102))
    # briznas: cruces de 1px, no lineas diagonales
    for _ in range(7):
        x = rng.randint(0, 15)
        px(s, x, 3, (64, 148, 58))
        px(s, x, 2, (96, 196, 90))


def _tex_piedra(s, rng, *args, **kwargs):
    # Retro chunky: manchas gordas + grieta gruesa ocasional (2px, no
    # fina de 1px) + dithering. Sin bisel: conecta con sus vecinas.
    s.fill((135, 135, 145))
    cluster_noise(s, rng, 4, [(112, 112, 122), (155, 155, 165)], block=5)
    cluster_noise(s, rng, 5, [(120, 120, 130), (148, 148, 158)], block=4)
    if rng.random() < 0.6:  # grieta gruesa en L
        gx, gy = rng.randint(1, 10), rng.randint(1, 10)
        rect_px(s, gx, gy, 5, 2, (95, 95, 105))
        rect_px(s, gx + 3, gy, 2, 5, (95, 95, 105))
    _checker(s, rng, 6, (105, 105, 115))


def _tex_tronco(s, rng, *args, **kwargs):
    # Tronco de fondo: marco oscuro para que se lea sin colision.
    s.fill((112, 74, 36))
    for x in (2, 5, 8, 11, 14):  # vetas verticales de 1px con ritmo
        for y in range(0, 16):
            px(s, x, y, (72, 46, 20) if (y + x) % 3 else (138, 96, 52))
    px(s, 7, 5, (58, 36, 15))  # nudo 2x2 con brillo
    rect_px(s, 6, 4, 3, 3, (80, 52, 24))
    px(s, 8, 5, (140, 100, 55))
    px(s, 6, 4, (160, 120, 70))
    dither_px(s, rng, 6, (95, 62, 30))
    # borde lateral oscuro = "esta detras"
    for y in range(16):
        px(s, 0, y, (50, 32, 14))
        px(s, 15, y, (50, 32, 14))
    bevel_px(s, (150, 105, 58), (55, 35, 15))


def _tex_hojas(s, rng, *args, **kwargs):
    # Copa organica: parches grandes + huecos y brillos aleatorios por variante.
    s.fill((30, 125, 34))
    cluster_noise(s, rng, 5, [(38, 155, 40), (50, 185, 55), (22, 100, 26)], block=3)
    cluster_noise(s, rng, 8, [(38, 155, 40), (50, 185, 55), (22, 100, 26)], block=2)
    for _ in range(rng.randint(2, 5)):  # huecos cuadrados
        rect_px(s, rng.randint(0, 14), rng.randint(0, 14), 2, 2, (14, 70, 16))
    for _ in range(rng.randint(2, 4)):  # brillos
        hx, hy = rng.randint(0, 14), rng.randint(0, 14)
        px(s, hx, hy, (140, 240, 140))


def _tex_arena(s, rng, *args, **kwargs):
    # Retro: dunas en bandas gruesas onduladas + dithering. Sin bisel.
    s.fill((233, 214, 150))
    cluster_noise(s, rng, 4, [(205, 185, 120), (245, 228, 170)], block=5)
    for y in (4, 10):  # veta de duna gruesa
        for x in range(16):
            if (x + y) % 3:
                px(s, x, y, (220, 200, 135))
    _checker(s, rng, 6, (210, 190, 128))


def _tex_mena(s, rng, base, gem, n=4, *args, **kwargs):
    # Mena retro estilo Terraria: base de piedra chunky + pepitas gordas
    # 3x2 con brillo blanco en posiciones aleatorias (2-4 por tile).
    s.fill(base)
    cluster_noise(s, rng, 4, [shade(base, -18), shade(base, +14)], block=5)
    cluster_noise(s, rng, 4, [shade(base, -22), shade(base, +10)], block=4)
    pts = [(2, 2), (11, 2), (2, 11), (11, 11), (6, 6)][:n]
    rng.shuffle(pts)
    for ox, oy in pts[:rng.randint(2, max(2, n))]:
        rect_px(s, ox, oy, 3, 2, shade(gem, -40))
        rect_px(s, ox, oy, 3, 1, gem)
        px(s, ox, oy, (255, 255, 255))


def _tex_bedrock(s, rng, *args, **kwargs):
    s.fill((35, 35, 44))
    for _ in range(3):  # bloques cuadrados con borde, nada redondo
        x, y = rng.randint(0, 10), rng.randint(0, 10)
        w, h = rng.randint(3, 6), rng.randint(3, 5)
        rect_px(s, x, y, w, h, (50, 50, 62))
        for ix in range(x, x + w):
            px(s, ix, y, (70, 70, 85))
        for ix in range(x, x + w):
            px(s, ix, y + h - 1, (22, 22, 30))


def _tex_tablones(s, rng, *args, **kwargs):
    s.fill((160, 115, 60))
    for y in (4, 8, 12):  # separacion entre tablas (2px)
        for x in range(16):
            px(s, x, y, (110, 75, 35))
    for y in (2, 6, 10, 14):  # veta punteada
        for x in range(0, 16, 2):
            px(s, x + (y % 3 == 0), y, (175, 130, 75))
    for x, y in [(2, 2), (13, 6), (2, 10), (13, 14)]:  # clavos cuadrados
        px(s, x, y, (80, 70, 60))
        px(s, x, y - 1, (200, 190, 170))
    bevel_px(s, (190, 145, 85), (95, 62, 28))


def _tex_mesa(s, rng, *args, **kwargs):
    s.fill((60, 45, 30))
    rect_px(s, 1, 2, 14, 4, (170, 125, 70))  # tablero
    for x in range(1, 15):
        px(s, x, 2, (190, 145, 85))
    rect_px(s, 2, 6, 2, 10, (120, 85, 45))   # patas
    rect_px(s, 12, 6, 2, 10, (120, 85, 45))
    rect_px(s, 6, 3, 3, 2, (200, 200, 210))  # plano
    px(s, 6, 3, (255, 255, 255))


def _tex_horno(s, rng, *args, **kwargs):
    s.fill((85, 85, 95))
    cluster_noise(s, rng, 5, [(70, 70, 80), (100, 100, 110)], block=2)
    rect_px(s, 4, 6, 8, 9, (45, 45, 55))     # boca
    # fuego en pixeles escalonados
    for x, y in ((6, 13), (7, 12), (8, 11), (8, 13), (9, 12), (7, 13), (9, 13)):
        px(s, x, y, (255, 120, 20))
    px(s, 8, 13, (255, 220, 100))
    px(s, 8, 12, (255, 220, 100))
    for x in range(4, 12):  # marco superior claro
        px(s, x, 6, (120, 120, 135))
    bevel_px(s, (120, 120, 135), (50, 50, 60))


def _tex_antorcha(s, rng, *args, **kwargs):
    # Antorcha al tamano correcto: palito fino centrado + llama, resto
    # transparente (ya no es un cuadrado macizo estilo bloque).
    # La llama ladea segun la variante (rng) para que no sean identicas.
    lean = rng.choice((-1, 0, 1))
    rect_px(s, 7, 7, 2, 9, (139, 90, 43))    # palo
    px(s, 7, 7, (160, 110, 55))
    px(s, 7, 15, (100, 62, 28))
    # llama en 3 capas cuadradas, ladeada
    rect_px(s, 5 + lean, 2, 6, 5, (255, 140, 20))
    rect_px(s, 6 + lean, 3, 4, 3, (255, 215, 90))
    rect_px(s, 7 + lean, 4, 2, 2, (255, 245, 180))
    px(s, 7 + lean, 4, (255, 255, 255))


def _tex_ladrillo(s, rng, *args, **kwargs):
    s.fill((150, 70, 60))
    for y in (5, 11):  # mortero horizontal 1px
        for x in range(16):
            px(s, x, y, (210, 200, 190))
    for x in (8, 4, 12):  # mortero vertical alterno
        y0 = 0 if x == 8 else (6 if x in (4, 12) else 12)
        for y in range(y0, y0 + 5):
            px(s, x, y, (210, 200, 190))
    dither_px(s, rng, 10, (135, 60, 52))
    px(s, 1, 1, (190, 110, 100))
    bevel_px(s, (185, 120, 110), (110, 45, 38))


def _tex_cofre(s, rng, *args, **kwargs):
    s.fill((70, 55, 35))
    rect_px(s, 1, 5, 14, 10, (140, 100, 45))
    rect_px(s, 1, 5, 14, 3, (165, 120, 60))  # tapa
    for x in range(1, 15):
        px(s, x, 5, (190, 150, 80))
    for y in range(5, 15):  # refuerzos
        px(s, 2, y, (80, 60, 40))
        px(s, 13, y, (80, 60, 40))
    rect_px(s, 7, 8, 2, 4, (255, 215, 60))   # cerradura
    px(s, 7, 8, (255, 240, 150))
    bevel_px(s, (190, 150, 80), (50, 38, 22))


def _tex_altar(s, rng, *args, **kwargs):
    s.fill((40, 38, 55))
    rect_px(s, 1, 9, 14, 7, (80, 70, 140))
    for x in range(1, 15):
        px(s, x, 9, (100, 90, 165))
    rect_px(s, 5, 3, 6, 6, (150, 60, 220))   # gema cuadrada
    rect_px(s, 6, 4, 4, 4, (200, 150, 255))
    px(s, 7, 5, (255, 255, 255))
    px(s, 2, 12, (120, 220, 255))  # runas 1px
    px(s, 13, 12, (120, 220, 255))


def _tex_flor(s, rng, *args, **kwargs):
    """Flor abisal (19) al tamano correcto: tallo fino + petalos que
    brillan, resto transparente (ya no es un cuadrado macizo)."""
    bend = rng.choice((-1, 0, 1))
    for y in range(7, 16):  # tallo 1px, algo ladeado por variante
        px(s, 8 + (bend if y < 11 else 0), y, (40, 120, 70))
    px(s, 6, 12, (40, 120, 70))  # hojas en L
    px(s, 7, 12, (40, 120, 70))
    px(s, 9, 12, (40, 120, 70))
    px(s, 10, 12, (40, 120, 70))
    hx, hy = 8 + bend, 4
    for ox, oy in ((hx, hy - 1), (hx - 3, hy + 1), (hx + 2, hy + 1),
                   (hx - 2, hy + 3), (hx + 1, hy + 3)):  # petalos 2x2
        rect_px(s, ox - 1, oy - 1, 2, 2, (150, 100, 255))
    rect_px(s, hx - 1, hy, 3, 3, (230, 220, 255))
    px(s, hx - 1, hy, (255, 255, 255))


def _tex_rocaabisal(s, rng, *args, **kwargs):
    """Roca abisal (20): base oscura con manchas gordas + cristales 2x2
    morados. Sin bisel: natural y conectada."""
    s.fill((48, 42, 78))
    cluster_noise(s, rng, 4, [(60, 52, 95), (36, 32, 60)], block=5)
    cluster_noise(s, rng, 4, [(66, 58, 102), (30, 26, 52)], block=4)
    for _ in range(rng.randint(2, 3)):
        vx, vy = rng.randint(0, 13), rng.randint(0, 13)
        rect_px(s, vx, vy, 2, 2, (145, 90, 220))
        px(s, vx, vy, (235, 205, 255))


def _tex_pared_rustica(s, rng, *args, **kwargs):
    """Pared rustica (21): fondo de madera cruzada, mas apagada."""
    s.fill((110, 86, 58))
    for y in range(0, 16, 4):  # listones horizontales
        for x in range(16):
            px(s, x, y, (85, 64, 42))
    for x in range(0, 16, 4):  # listones verticales tenues
        for y in range(16):
            if (x + y) % 8 == 0:
                px(s, x, y, (95, 72, 48))
    cluster_noise(s, rng, 4, [(125, 100, 68)], block=2)
    for x, y in [(3, 3), (12, 7), (6, 12)]:  # clavos
        px(s, x, y, (60, 50, 45))
        px(s, x, y - 1, (180, 170, 150))
    bevel_px(s, (140, 112, 78), (70, 52, 34))


def _tex_pared_abisal(s, rng, *args, **kwargs):
    """Pared abisal (22): ladrillos morados de fondo con runa."""
    s.fill((50, 40, 82))
    for y in (5, 11):
        for x in range(16):
            px(s, x, y, (30, 24, 55))
    for x in (8, 4, 12):
        y0 = 0 if x == 8 else (6 if x in (4, 12) else 12)
        for y in range(y0, y0 + 5):
            px(s, x, y, (30, 24, 55))
    cluster_noise(s, rng, 4, [(62, 50, 100)], block=2)
    # runa central brillante
    px(s, 7, 7, (170, 130, 255))
    px(s, 8, 7, (170, 130, 255))
    px(s, 7, 8, (170, 130, 255))
    px(s, 8, 8, (230, 210, 255))
    bevel_px(s, (80, 65, 130), (28, 22, 50))


def _tex_losa(s, rng, *args, **kwargs):
    """Losa musgosa (23): piedra baja con musgo arriba."""
    s.fill((120, 120, 130))
    cluster_noise(s, rng, 6, [(105, 105, 115), (135, 135, 145)], block=2)
    for x in range(16):  # musgo superior dentado
        depth = 3 + (1 if x % 3 == 0 else 0)
        for y in range(depth):
            px(s, x, y, (95, 160, 70))
    for x in range(0, 16, 3):
        px(s, x, 0, (130, 200, 100))
    rect_px(s, 4, 8, 8, 2, (90, 90, 100))  # grieta
    bevel_px(s, (160, 160, 170), (75, 75, 85))


def _tex_micelio(s, rng, *args, **kwargs):
    """Micelio brillante (24): suelo fungico morado con manchas gordas y
    esporas brillantes 2x2. Sin bisel: funde con la tierra."""
    s.fill((70, 60, 130))
    cluster_noise(s, rng, 4, [(60, 50, 115), (85, 72, 150)], block=5)
    cluster_noise(s, rng, 4, [(55, 45, 105), (92, 80, 158)], block=4)
    for _ in range(rng.randint(3, 5)):  # esporas brillantes 2x2
        gx, gy = rng.randint(0, 14), rng.randint(0, 14)
        rect_px(s, gx, gy, 2, 2, (120, 255, 190))
        px(s, gx, gy, (230, 255, 240))


def _tex_seta(s, rng, *args, **kwargs):
    """Seta luminosa (25) al tamano correcto: tallo fino + sombrero con
    motas brillantes, resto transparente."""
    bend = rng.choice((-1, 0, 1))
    for y in range(6, 16):  # tallo palido
        px(s, 8 + (bend if y < 10 else 0), y, (210, 200, 215))
    px(s, 8 + bend, 12, (190, 180, 195))
    hx, hy = 8 + bend, 4
    # sombrero: disco escalonado cian
    for dx in range(-3, 4):
        px(s, hx + dx, hy, (90, 220, 160))
        px(s, hx + dx, hy + 1, (70, 190, 140))
    for dx in range(-2, 3):
        px(s, hx + dx, hy - 1, (110, 235, 175))
    for dx in (-1, 1):
        px(s, hx + dx, hy - 1, (230, 255, 240))  # motas
    px(s, hx, hy - 1, (255, 255, 255))


def _tex_tallo(s, rng, *args, **kwargs):
    """Tallo fungico (26): fibra vertical palida con nudos (conecta como
    madera en el autotile). Sin bisel: es natural y debe fundirse."""
    s.fill((200, 190, 200))
    cluster_noise(s, rng, 3, [(180, 170, 190), (215, 205, 215)], block=4)
    cluster_noise(s, rng, 4, [(180, 170, 190), (215, 205, 215)], block=3)
    for x in (4, 8, 12):  # fibras verticales gruesas
        for y in range(0, 16):
            if y % 2 == 0:
                px(s, x, y, (170, 160, 180))
    if rng.random() < 0.7:  # nudo
        nx, ny = rng.randint(2, 11), rng.randint(3, 12)
        rect_px(s, nx, ny, 3, 2, (170, 160, 180))
        px(s, nx, ny, (225, 215, 225))


def _checker(s, rng, n, color):
    """Dithering retro estilo Terraria: pares de pixeles sueltos."""
    for _ in range(n):
        x, y = rng.randint(0, 14), rng.randint(0, 15)
        px(s, x, y, color)
        px(s, x + 1, y, color)


def _tex_pizarra(s, rng, *args, **kwargs):
    """Pizarra abisal (27): lajas gruesas apiladas, tema de La Gran Falla.
    Natural: sin bisel para que conecte."""
    s.fill((72, 82, 112))
    cluster_noise(s, rng, 4, [(58, 66, 94), (88, 98, 128)], block=4)
    for y in (5, 11):  # grietas gruesas entre lajas
        for x in range(16):
            px(s, x, y, (40, 46, 68))
            if x % 4 == 0:
                px(s, x, y + 1, (40, 46, 68))
    _checker(s, rng, 6, (100, 112, 142))
    px(s, 2, 2, (120, 132, 162))  # lasca brillante


def _tex_hueso(s, rng, *args, **kwargs):
    """Hueso antiguo (28): marfil fosil del Mar de Cadaveres con grietas
    y un craneo. Natural: sin bisel para que conecte."""
    s.fill((214, 204, 178))
    cluster_noise(s, rng, 4, [(190, 178, 150), (228, 220, 196)], block=4)
    for x in (5, 11):  # grietas verticales
        for y in range(0, 16, 2):
            px(s, x, y, (170, 158, 130))
    _checker(s, rng, 5, (198, 186, 158))
    # craneo 5x4
    rect_px(s, 6, 6, 5, 4, (235, 228, 205))
    px(s, 7, 7, (60, 50, 45))
    px(s, 9, 7, (60, 50, 45))
    px(s, 8, 9, (60, 50, 45))


def _tex_farol(s, rng, *args, **kwargs):
    """Farol (29): marco de hierro con cristal calido. Solo el farolillo
    ocupa el centro; el resto transparente (no es bloque macizo)."""
    rect_px(s, 5, 2, 6, 2, (50, 50, 60))    # capucha
    rect_px(s, 5, 12, 6, 2, (50, 50, 60))   # base
    for y in range(4, 12):
        px(s, 5, y, (60, 60, 72))
        px(s, 10, y, (60, 60, 72))
    rect_px(s, 6, 4, 4, 8, (255, 190, 90))  # cristal
    rect_px(s, 7, 5, 2, 6, (255, 230, 160))
    px(s, 7, 5, (255, 255, 255))
    px(s, 7, 2, (40, 40, 50))  # gancho
    px(s, 8, 1, (40, 40, 50))


def _tex_cama(s, rng, *args, **kwargs):
    """Cama (30): cabecero de madera + manta roja. Rellena el tile
    (es solida) con marco de madera alrededor."""
    s.fill((120, 85, 45))
    rect_px(s, 1, 1, 2, 10, (150, 110, 60))   # cabecero
    px(s, 1, 1, (175, 130, 75))
    rect_px(s, 3, 5, 12, 7, (170, 60, 60))    # manta
    rect_px(s, 3, 5, 12, 2, (200, 90, 90))
    rect_px(s, 3, 10, 12, 2, (110, 40, 40))   # sombra manta
    rect_px(s, 4, 3, 8, 2, (220, 210, 190))   # almohada
    px(s, 4, 3, (255, 255, 255))
    for x in (1, 14):  # patas
        rect_px(s, x, 12, 1, 4, (90, 62, 32))


def _tex_silla(s, rng, *args, **kwargs):
    """Silla (31): respaldo alto + asiento + patas. Centrada con
    transparente alrededor (mueble, no bloque macizo)."""
    rect_px(s, 4, 2, 2, 8, (150, 110, 60))    # respaldo
    px(s, 4, 2, (175, 130, 75))
    rect_px(s, 4, 10, 8, 2, (165, 122, 68))   # asiento
    px(s, 4, 10, (190, 145, 85))
    rect_px(s, 5, 12, 1, 4, (110, 78, 40))    # patas
    rect_px(s, 10, 12, 1, 4, (110, 78, 40))
    px(s, 6, 4, (90, 64, 34))  # travesano
    px(s, 6, 5, (90, 64, 34))


def _tex_puerta(s, rng, *args, **kwargs):
    """Puerta cerrada (32): tablones verticales con marco y pomo."""
    s.fill((110, 78, 42))
    for x in (3, 7, 11):  # tablones verticales
        for y in range(16):
            if y % 2 == 0:
                px(s, x, y, (140, 100, 55))
    rect_px(s, 1, 1, 14, 2, (90, 62, 32))     # marco sup/inf
    rect_px(s, 1, 13, 14, 2, (90, 62, 32))
    px(s, 1, 1, (150, 110, 60))
    rect_px(s, 12, 7, 2, 2, (255, 215, 90))   # pomo
    px(s, 12, 7, (255, 240, 160))
    bevel_px(s, (160, 120, 70), (70, 48, 24))


def _tex_puerta_abierta(s, rng, *args, **kwargs):
    """Puerta abierta (33): solo la hoja plegada a un lado, el resto
    transparente (se atraviesa)."""
    rect_px(s, 1, 0, 4, 16, (140, 100, 55))   # hoja plegada
    for y in range(0, 16, 2):
        px(s, 2, y, (110, 78, 42))
        px(s, 4, y, (110, 78, 42))
    rect_px(s, 1, 0, 1, 16, (90, 62, 32))
    px(s, 3, 7, (255, 215, 90))  # pomo asomando


def _tex_ventana(s, rng, *args, **kwargs):
    """Ventana (34): marco de madera con cristal casi transparente
    (brillo diagonal). Bloquea el paso, no la luz."""
    rect_px(s, 0, 0, 16, 2, (120, 86, 46))
    rect_px(s, 0, 14, 16, 2, (120, 86, 46))
    rect_px(s, 0, 0, 2, 16, (120, 86, 46))
    rect_px(s, 14, 0, 2, 16, (120, 86, 46))
    rect_px(s, 7, 2, 2, 12, (120, 86, 46))    # cruceta
    rect_px(s, 2, 7, 12, 2, (120, 86, 46))
    for i in range(4):  # brillo diagonal del cristal
        px(s, 4 + i, 10 - i, (225, 245, 255))
        px(s, 9 + i, 12 - i, (200, 230, 245))


_TEX_FN = {
    1: _tex_tierra, 2: _tex_piedra, 3: _tex_tronco, 4: _tex_hojas,
    5: _tex_arena, 10: _tex_bedrock, 11: _tex_tablones, 12: _tex_mesa,
    13: _tex_horno, 14: _tex_antorcha, 15: _tex_ladrillo, 16: _tex_cofre,
    17: _tex_altar, 18: _tex_hierba, 19: _tex_flor, 20: _tex_rocaabisal,
    21: _tex_pared_rustica, 22: _tex_pared_abisal, 23: _tex_losa,
    24: _tex_micelio, 25: _tex_seta, 26: _tex_tallo,
    27: _tex_pizarra, 28: _tex_hueso, 29: _tex_farol, 30: _tex_cama,
    31: _tex_silla, 32: _tex_puerta, 33: _tex_puerta_abierta,
    34: _tex_ventana,
}
_MENA = {6: ((100, 100, 110), (25, 25, 30), 4), 7: ((150, 130, 120), (215, 150, 115), 4),
         8: ((150, 130, 120), (255, 215, 60), 4), 9: ((120, 130, 150), (120, 230, 255), 5)}


def get_tile_texture(bid, *args, variant=0, size=TILE, **kwargs):
    """Devuelve la Surface pixelart cacheada del bloque bid (NEAREST).

    Args:
        bid: id de blocks.py. variant: cambia la semilla del detalle.
        size: lado en px (casi siempre TILE). **kwargs: futuros (glow...).
    Conecta con: game.py (render del mundo).
    NOTA: para que las texturas CONECTEN usa get_tile_texture_auto()
    con mascaras de vecinos (bordes solo donde hay aire).
    """
    key = (bid, variant, size)
    if key in _cache_tiles:
        return _cache_tiles[key]
    small = _small(PB, PB)
    rng = random.Random(bid * 999 + variant)
    if bid in _MENA:
        base, gem, n = _MENA[bid]
        _tex_mena(small, rng, base, gem, n)
    else:
        fn = _TEX_FN.get(bid)
        if fn:
            fn(small, rng, *args, **kwargs)
        else:
            small.fill((0, 0, 0, 255))
    # Variantes invertidas: los bloques (menos la hierba, que tiene
    # arriba/abajo) salen espejados segun la variante -> mas variedad
    # sin romper la conexion (el espejo conserva los bordes del grupo).
    if variant and bid != 18:
        small = pygame.transform.flip(small, variant in (1, 3), variant in (2, 3))
    s = _up(small, size)
    _cache_tiles[key] = s
    return s


# ------------------------------------------------- autotile / conexion
# Grupos que conectan sin costura entre si (misma familia visual).
_AUTOTILE_GROUPS = {
    1: "tierra", 18: "tierra", 5: "tierra",
    2: "piedra", 6: "piedra", 7: "piedra", 8: "piedra", 9: "piedra",
    10: "piedra", 13: "piedra", 15: "piedra", 17: "piedra",
    20: "piedra", 23: "piedra",
    11: "madera", 12: "madera", 16: "madera", 3: "madera", 21: "madera",
    26: "madera",
    22: "abisal",
    4: "hoja", 19: "hoja",
    24: "tierra",  # el micelio funde con la tierra (borde de bioma suave)
    14: "deco", 25: "deco", 29: "deco",
    27: "pizarra",  # la pizarra conecta consigo misma (tema capa 3)
    28: "hueso",    # el hueso conecta consigo mismo (tema capa 5)
    30: "madera", 31: "madera",
    32: "madera", 33: "madera", 34: "madera",
}


# LUTs planas por id (0..255) para el autotile caliente: evitan
# world.get() + dict BLOCKS por vecino en cada fallo de cache.
_LUT_SOLID = None
_LUT_BG = None
_LUT_GRP = None


def _build_lut():
    """Construye las LUT una vez (lazy para evitar import circular)."""
    global _LUT_SOLID, _LUT_BG, _LUT_GRP
    if _LUT_SOLID is not None:
        return
    from blocks import BLOCKS
    sol = bytearray(256)
    bg = bytearray(256)
    grp = ["solo"] * 256
    for bid, info in BLOCKS.items():
        if 0 <= bid < 256:
            if info.get("solid"):
                sol[bid] = 1
            if info.get("background"):
                bg[bid] = 1
            grp[bid] = _AUTOTILE_GROUPS.get(bid, "solo")
    _LUT_SOLID, _LUT_BG, _LUT_GRP = sol, bg, grp


def autotile_group(bid):
    """Familia visual del bloque (para transiciones suaves entre biomas)."""
    if _LUT_GRP is not None and 0 <= bid < 256:
        return _LUT_GRP[bid]
    return _AUTOTILE_GROUPS.get(bid, "solo")


def autotile_masks(world, tx, ty):
    """Mascaras de 4 bits (1=arriba,2=abajo,4=izq,8=der) para el tile.

    exp: lados expuestos al aire/fondo (ahi va borde iluminado/sombra).
    seam: lados con solido de OTRO grupo (ahi va costura de transicion).
    Los solidos del mismo grupo conectan sin borde -> las texturas se funden.

    Via rapida con LUTs planas y acceso directo (sin world.get/dicts).
    """
    if _LUT_SOLID is None:
        _build_lut()
    sol, grp = _LUT_SOLID, _LUT_GRP
    tiles = world.tiles
    W, H = world.w, world.h
    my_group = grp[tiles[ty][tx]]
    exp = 0
    seam = 0
    # arriba (bit 1)
    if ty > 0:
        nb = tiles[ty - 1][tx]
        if not sol[nb]:
            exp |= 1
        elif grp[nb] != my_group:
            seam |= 1
    # abajo (bit 2)
    if ty < H - 1:
        nb = tiles[ty + 1][tx]
        if not sol[nb]:
            exp |= 2
        elif grp[nb] != my_group:
            seam |= 2
    # izquierda (bit 4)
    if tx > 0:
        nb = tiles[ty][tx - 1]
        if not sol[nb]:
            exp |= 4
        elif grp[nb] != my_group:
            seam |= 4
    # derecha (bit 8)
    if tx < W - 1:
        nb = tiles[ty][tx + 1]
        if not sol[nb]:
            exp |= 8
        elif grp[nb] != my_group:
            seam |= 8
    return exp, seam


def get_tile_texture_auto(bid, exp=0, seam=0, size=TILE, variant=0):
    """Textura con bordes autotile cacheada.

    exp/seam: mascaras de autotile_masks(). El interior (base) es identico
    a get_tile_texture(); solo se anaden bordes/transiciones encima,
    asi los bloques del mismo grupo se ven continuos y los bordes solo
    salen al aire -> las texturas "conectan".
    """
    key = ("auto", bid, exp, seam, variant, size)
    if key in _cache_tiles:
        return _cache_tiles[key]
    base = get_tile_texture(bid, variant=variant, size=PB).copy()
    # NOTA: Surface.fill() con alfa REEMPLAZA (transparentaria el tile).
    # Para luz/sombra se usa BLEND_RGBA_ADD/SUB (suma/resta RGB, alfa intacto).
    ADD, SUB = pygame.BLEND_RGBA_ADD, pygame.BLEND_RGBA_SUB
    # --- jitter de luz por variante: cada tile brilla un poco distinto ---
    if variant == 1:
        base.fill((8, 8, 8, 0), (0, 0, PB, PB), ADD)
    elif variant == 2:
        base.fill((9, 9, 9, 0), (0, 0, PB, PB), SUB)
    elif variant == 3:
        base.fill((5, 5, 5, 0), (0, 0, PB, PB // 2), ADD)
        base.fill((6, 6, 6, 0), (0, PB // 2, PB, PB - PB // 2), SUB)
    # --- bordes expuestos estilo Terraria: outline oscuro de 1px en el
    # filo + luz interior. Marca cada bloque abierto sin marcar rejilla
    # en el interior (ahi la textura base ya conecta sola). ---
    if exp & 1:  # arriba expuesto: outline + filo de luz
        base.fill((25, 25, 30, 0), (0, 0, PB, 1), SUB)
        base.fill((45, 45, 45, 0), (0, 1, PB, 1), ADD)
    if exp & 2:  # abajo: outline + sombra gruesa
        base.fill((30, 30, 35, 0), (0, PB - 1, PB, 1), SUB)
        base.fill((45, 45, 45, 0), (0, PB - 3, PB, 2), SUB)
    if exp & 4:  # izquierda: outline + luz lateral
        base.fill((25, 25, 30, 0), (0, 0, 1, PB), SUB)
        base.fill((28, 28, 28, 0), (1, 0, 1, PB), ADD)
    if exp & 8:  # derecha: outline + sombra lateral
        base.fill((25, 25, 30, 0), (PB - 1, 0, 1, PB), SUB)
        base.fill((30, 30, 30, 0), (PB - 3, 0, 2, PB), SUB)
    # esquinas exteriores: remate en L para que no se vea cortado
    if (exp & 1) and (exp & 4):
        base.fill((35, 35, 40, 0), (0, 0, 2, 2), SUB)
        base.fill((45, 45, 45, 0), (0, 0, 1, 1), ADD)
    if (exp & 1) and (exp & 8):
        base.fill((35, 35, 40, 0), (PB - 2, 0, 2, 2), SUB)
        base.fill((45, 45, 45, 0), (PB - 1, 0, 1, 1), ADD)
    if (exp & 2) and (exp & 4):
        base.fill((45, 45, 45, 0), (0, PB - 2, 2, 2), SUB)
    if (exp & 2) and (exp & 8):
        base.fill((45, 45, 45, 0), (PB - 2, PB - 2, 2, 2), SUB)
    # --- costuras entre grupos distintos (transicion tierra<->piedra...) ---
    if seam & 1:
        base.fill((36, 36, 36, 0), (0, 0, PB, 1), SUB)
    if seam & 2:
        base.fill((36, 36, 36, 0), (0, PB - 1, PB, 1), SUB)
    if seam & 4:
        base.fill((36, 36, 36, 0), (0, 0, 1, PB), SUB)
    if seam & 8:
        base.fill((36, 36, 36, 0), (PB - 1, 0, 1, PB), SUB)
    s = _up(base, size)
    _cache_tiles[key] = s
    return s


# ------------------------------------------------------------- iconos items
_TIER = {"madera": (160, 115, 60), "piedra": (130, 130, 140), "hierro": (190, 195, 210),
         "oro": (255, 210, 70), "diamante": (120, 230, 255), "cuero": (150, 110, 70)}


def _tier_of(item_id):
    for t in _TIER:
        if t in item_id:
            return _TIER[t]
    return (200, 200, 200)


def _icon_handle(s, cx, cy, length=7):
    """Mango de madera diagonal con contorno oscuro y brillo (Terraria)."""
    for i in range(length):
        x, y = cx - 5 + i, cy + 5 - i
        px(s, x, y, (139, 90, 43))
        px(s, x, y + 1, (100, 62, 28))
    for i in range(length):
        x, y = cx - 5 + i, cy + 5 - i
        if i % 2 == 0:
            px(s, x, y, (180, 130, 70))  # vetas claras
    px(s, cx - 5, cy + 6, (60, 38, 18))  # tope del mango
    px(s, cx - 5 + length - 1, cy + 5 - length + 1, (60, 38, 18))


def _icon_herramienta(s, item_id, cx, cy, es_hacha=False, es_martillo=False, *args, **kwargs):
    # Herramientas estilo Terraria: mango con contorno + cabeza metalica
    # grande con filo claro arriba y sombra abajo + 1px de brillo.
    col = _tier_of(item_id)
    dark = shade(col, -55)
    light = shade(col, 55)
    _icon_handle(s, cx, cy)
    if es_martillo:
        # cabeza 7x5 con contorno oscuro completo estilo Minecraft
        rect_px(s, cx - 1, cy - 10, 9, 6, (40, 30, 25))
        for x in range(cx + 0, cx + 7):
            for y in range(cy - 9, cy - 4):
                px(s, x, y, col)
        for x in range(cx + 0, cx + 7):
            px(s, x, cy - 9, light)
            px(s, x, cy - 5, dark)
        for y in range(cy - 9, cy - 4):
            px(s, cx + 0, y, dark)
            px(s, cx + 6, y, dark)
        px(s, cx + 1, cy - 9, (255, 255, 255))
        px(s, cx + 2, cy - 8, light)
        rect_px(s, cx - 2, cy - 8, 2, 3, (90, 70, 55))  # union/mango
        px(s, cx - 2, cy - 8, (150, 120, 85))
        return
    if es_hacha:
        # hoja de hacha: silueta oscura estilo Minecraft + filo claro
        blade = [(4, -6), (5, -6), (6, -6), (6, -5), (5, -5), (4, -5),
                 (4, -4), (5, -4), (6, -3), (5, -3), (4, -3)]
        for bx, by in blade:
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px(s, cx + bx + ox, cy + by + oy, (40, 30, 25))
        for bx, by in blade:
            px(s, cx + bx, cy + by, col)
        for bx, by in [(4, -6), (5, -6), (6, -6)]:
            px(s, cx + bx, cy + by, light)
        px(s, cx + 4, cy - 6, (255, 255, 255))
        for bx, by in [(4, -3), (5, -3)]:
            px(s, cx + bx, cy + by, dark)
        px(s, cx + 3, cy - 4, (90, 70, 55))  # cuna
        px(s, cx + 3, cy - 5, (150, 120, 85))
    else:
        # PICO estilo Terraria: mango diagonal + cabeza creciente ancha con
        # dos puntas afiladas curvadas hacia abajo, contorno oscuro,
        # filo claro arriba y remache en la union.
        # mango (un poco mas largo, de esquina a esquina)
        for i in range(9):
            x, y = cx - 6 + i, cy + 6 - i
            px(s, x, y, (139, 90, 43))
            px(s, x, y + 1, (100, 62, 28))
        for i in (1, 3, 5, 7):
            px(s, cx - 6 + i, cy + 6 - i, (180, 130, 70))
        px(s, cx - 6, cy + 7, (60, 38, 18))
        # cabeza creciente: arco ancho de 13px con silueta oscura + filo
        for x in range(-6, 7):
            y = cy - 7 + abs(x) * 2 // 3
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px(s, cx + x + ox, y + oy, (40, 30, 25))
        for x in range(-6, 7):
            y = cy - 7 + abs(x) * 2 // 3
            px(s, cx + x, y, col)
            px(s, cx + x, y - 1, light)
            px(s, cx + x, y + 1, dark)
        # puntas afiladas hacia abajo en ambos extremos
        px(s, cx - 6, cy - 3, col)
        px(s, cx - 6, cy - 2, dark)
        px(s, cx + 6, cy - 3, col)
        px(s, cx + 6, cy - 2, dark)
        # brillo en la cresta + remache
        px(s, cx - 1, cy - 8, (255, 255, 255))
        px(s, cx, cy - 8, light)
        px(s, cx, cy - 6, (150, 120, 85))
        px(s, cx, cy - 5, (90, 70, 55))


def _icon_espada(s, item_id, cx, cy, *args, **kwargs):
    # Espada estilo Terraria: hoja ancha 2px con filo claro, punta en
    # diagonal, guarda dorada con contorno y pomo redondo.
    col = _tier_of(item_id)
    dark = shade(col, -55)
    light = shade(col, 55)
    # silueta oscura estilo Minecraft detras de la hoja
    for i in range(9):
        x, y = cx - 4 + i, cy + 4 - i
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)):
            px(s, x + ox, y + oy, (40, 30, 25))
            px(s, x + 1 + ox, y + oy, (40, 30, 25))
    for i in range(9):  # hoja en escalera de 2px de ancho
        x, y = cx - 4 + i, cy + 4 - i
        px(s, x, y, dark)       # lomo
        px(s, x + 1, y, col)    # centro
        if i % 2 == 0:
            px(s, x + 1, y, light)  # filo que brilla
    px(s, cx + 5, cy - 5, light)  # punta
    px(s, cx + 4, cy - 4, (255, 255, 255))
    px(s, cx - 5, cy + 5, dark)
    # guarda dorada con contorno
    for x in range(-3, 3):
        px(s, cx - 3 + x, cy + 4 + (1 if x % 2 else 0), (255, 215, 60))
    px(s, cx - 6, cy + 4, (140, 100, 30))
    px(s, cx, cy + 5, (140, 100, 30))
    px(s, cx - 5, cy + 4, (255, 240, 170))
    # mango + pomo
    px(s, cx - 4, cy + 5, (90, 60, 30))
    px(s, cx - 4, cy + 6, (90, 60, 30))
    px(s, cx - 4, cy + 7, (150, 150, 160))  # pomo metalico
    px(s, cx - 4, cy + 7, shade(col, 30))


def _icon_armadura(s, item_id, cx, cy, *args, **kwargs):
    col = _tier_of(item_id)
    tipo = "casco" if "casco" in item_id else ("peto" if "peto" in item_id else "botas")
    if tipo == "casco":
        for x in range(-4, 5):
            px(s, cx + x, cy - 4 + abs(x) // 2, col)
            px(s, cx + x, cy - 5 + abs(x) // 2, shade(col, 45))
        for x in range(-4, 5):
            px(s, cx + x, cy, shade(col, -40))
    elif tipo == "peto":
        rect_px(s, cx - 4, cy - 5, 8, 9, col)
        for x in range(-4, 4):
            px(s, cx + x, cy - 5, shade(col, 45))
        rect_px(s, cx - 1, cy - 1, 2, 2, (60, 60, 80))
    else:
        rect_px(s, cx - 4, cy - 1, 3, 5, col)
        rect_px(s, cx + 1, cy - 1, 3, 5, col)
        px(s, cx - 4, cy - 1, shade(col, 45))
        px(s, cx + 1, cy - 1, shade(col, 45))


def _icon_pocion(s, item_id, cx, cy, *args, **kwargs):
    # Frasco estilo Terraria: cuello estrecho con corcho, cuerpo redondo,
    # liquido con burbujas y brillo.
    liquido = (220, 60, 60) if "vida" in item_id else ((150, 150, 160) if "hierro" in item_id
               else ((120, 220, 120) if "regen" in item_id else (120, 200, 255)))
    rect_px(s, cx - 1, cy - 8, 3, 2, (200, 170, 120))  # corcho
    rect_px(s, cx - 1, cy - 6, 3, 3, (190, 225, 245))  # cuello
    for x in range(-4, 5):  # cuerpo redondo
        w = 4 - abs(x) // 2
        for y in range(-3, w):
            px(s, cx + x, cy + y, (190, 225, 245))
    for x in range(-3, 4):  # liquido
        w = 3 - abs(x) // 2
        for y in range(-1, w):
            px(s, cx + x, cy + y, liquido)
    px(s, cx - 2, cy - 1, (255, 255, 255))  # burbujas + brillo
    px(s, cx + 1, cy + 1, shade(liquido, 60))
    px(s, cx - 3, cy - 3, (255, 255, 255))


def _icon_material(s, item_id, cx, cy, *args, **kwargs):
    if item_id == "gel":
        # Gel estilo Terraria: gota redonda con brillo grande.
        for x in range(-4, 5):
            w = 4 - abs(x) // 2
            for y in range(-4, w + 1):
                px(s, cx + x, cy + y, (90, 220, 130))
        rect_px(s, cx - 3, cy - 3, 3, 3, (170, 255, 195))
        px(s, cx - 3, cy - 3, (255, 255, 255))
        px(s, cx + 2, cy + 2, (60, 180, 100))
    elif "lingote" in item_id:
        col = (200, 150, 120) if "hierro" in item_id else (255, 215, 90)
        for i in range(5):
            for x in range(-3 + (i == 0), 4 - (i == 0)):
                px(s, cx + x, cy - 2 + i, col)
        for x in range(-2, 3):
            px(s, cx + x, cy - 2, (255, 255, 255))
    elif "crudo" in item_id or item_id == "carbon":
        col = (60, 60, 65) if item_id == "carbon" else ((170, 120, 100) if "hierro" in item_id else (220, 190, 90))
        for i in range(5):
            for x in range(-2 - i // 2, 3 + i // 2):
                px(s, cx + x, cy - 3 + i, col)
        px(s, cx - 1, cy - 2, shade(col, 60))
    elif item_id == "diamante":
        for i in range(5):
            for x in range(-2 - (2 - abs(i - 2)), 3 + (2 - abs(i - 2))):
                px(s, cx + x, cy - 2 + i, (120, 230, 255))
        px(s, cx - 1, cy - 1, (255, 255, 255))
    elif "moneda" in item_id:
        col = (200, 120, 60) if "cobre" in item_id else ((200, 200, 210) if "plata" in item_id else (255, 215, 60))
        rect_px(s, cx - 3, cy - 4, 7, 8, col)
        for x in range(-3, 4):
            px(s, cx + x, cy - 4, shade(col, 50))
            px(s, cx + x, cy + 3, shade(col, -40))
        px(s, cx - 1, cy - 2, shade(col, 60))
    elif item_id == "corazon":
        rect_px(s, cx - 4, cy - 3, 3, 3, (230, 40, 60))
        rect_px(s, cx + 1, cy - 3, 3, 3, (230, 40, 60))
        rect_px(s, cx - 3, cy - 1, 7, 4, (230, 40, 60))
        px(s, cx - 1, cy + 3, (230, 40, 60))
        px(s, cx - 3, cy - 3, (255, 150, 150))
    elif item_id == "palo":
        for i in range(6):
            px(s, cx - 4 + i, cy + 4 - i, (139, 90, 43))
    elif item_id == "corona_viscosa":
        rect_px(s, cx - 5, cy - 2, 10, 4, (255, 215, 60))
        for i in range(3):
            px(s, cx - 4 + i * 3, cy - 4, (255, 215, 60))
            px(s, cx - 3 + i * 3, cy - 5, (255, 215, 60))
        rect_px(s, cx - 1, cy - 1, 3, 3, (150, 60, 220))
    elif item_id == "reliquia_orbe":
        rect_px(s, cx - 4, cy - 4, 8, 8, (40, 20, 80))
        rect_px(s, cx - 3, cy - 3, 6, 6, (150, 60, 220))
        rect_px(s, cx - 1, cy - 1, 3, 3, (220, 180, 255))
        px(s, cx - 1, cy - 2, (255, 255, 255))
    elif item_id in ("manzana", "baya_luminosa", "seta_brillante"):
        if item_id == "seta_brillante":  # seta: sombrero + tallo
            for dx in range(-3, 4):
                px(s, cx + dx, cy - 1, (90, 220, 160))
                px(s, cx + dx, cy, (70, 190, 140))
            for dx in range(-2, 3):
                px(s, cx + dx, cy - 2, (110, 235, 175))
            px(s, cx - 1, cy - 2, (255, 255, 255))
            rect_px(s, cx - 1, cy + 1, 2, 4, (210, 200, 215))
            return
        col = (220, 60, 60) if item_id == "manzana" else (150, 120, 255)
        rect_px(s, cx - 3, cy - 3, 7, 7, col)
        rect_px(s, cx - 2, cy - 2, 3, 3, shade(col, 50))
        px(s, cx + 1, cy - 5, (60, 140, 60))
    elif item_id in ("carne_cruda", "carne_cocida"):
        col = (220, 140, 140) if item_id == "carne_cruda" else (150, 95, 60)
        rect_px(s, cx - 5, cy - 2, 9, 5, col)
        rect_px(s, cx + 4, cy - 3, 2, 2, (240, 240, 240))
        if item_id == "carne_cocida":
            px(s, cx - 2, cy, (110, 65, 40))
            px(s, cx + 1, cy + 1, (110, 65, 40))
    elif item_id in ("pan_hongo", "brocheta", "estofado_abismo"):
        if item_id == "pan_hongo":
            rect_px(s, cx - 4, cy - 3, 8, 5, (200, 160, 110))
            for x in range(-4, 4):
                px(s, cx + x, cy - 3, (220, 185, 135))
        elif item_id == "brocheta":
            for i in range(7):
                px(s, cx - 5 + i, cy + 5 - i, (139, 90, 43))
            for i, cc in enumerate([(150, 95, 60), (150, 120, 255), (150, 95, 60)]):
                rect_px(s, cx - 3 + i * 2 - 1, cy + 3 - i * 2 - 1, 2, 2, cc)
        else:
            rect_px(s, cx - 5, cy - 2, 10, 5, (90, 60, 50))
            rect_px(s, cx - 4, cy - 3, 8, 2, (200, 130, 60))
            px(s, cx - 1, cy - 2, (120, 220, 120))
    else:
        rect_px(s, cx - 4, cy - 4, 8, 8, (200, 200, 200))
        for x in range(-4, 4):
            px(s, cx + x, cy - 4, (255, 255, 255))


def get_item_icon(item_id, *args, size=48, **kwargs):
    """Icono pixelart del item, cacheado (16px -> size con NEAREST).

    Conecta con: ui.py (inventario, hotbar, crafteo) y game.py (drops).
    Los bloques reutilizan su textura de mundo en miniatura.
    """
    from blocks import ITEM_TO_BLOCK  # import local para evitar ciclos
    key = (item_id, size)
    if key in _cache_icons:
        return _cache_icons[key]
    if size >= 20:
        small = _small(16, 16)
        cx = cy = 8
        from items import ITEMS
        tipo = ITEMS.get(item_id, {}).get("tipo", "material")
        if tipo == "bloque" and item_id in ITEM_TO_BLOCK:
            tex = get_tile_texture(ITEM_TO_BLOCK[item_id], size=16)
            small.blit(tex, (0, 0))
        elif tipo == "pico":
            _icon_herramienta(small, item_id, cx, cy)
        elif tipo == "hacha":
            _icon_herramienta(small, item_id, cx, cy, es_hacha=True)
        elif tipo == "martillo":
            _icon_herramienta(small, item_id, cx, cy, es_martillo=True)
        elif tipo == "espada":
            _icon_espada(small, item_id, cx, cy)
        elif tipo in ("casco", "peto", "botas"):
            _icon_armadura(small, item_id, cx, cy)
        elif tipo == "pocion":
            _icon_pocion(small, item_id, cx, cy)
        else:
            _icon_material(small, item_id, cx, cy)
        s = _up(small, size)
    else:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        from items import ITEMS
        from blocks import ITEM_TO_BLOCK as _ITB
        tipo = ITEMS.get(item_id, {}).get("tipo", "material")
        if tipo == "bloque" and item_id in _ITB:
            tex = get_tile_texture(_ITB[item_id], size=size)
            s.blit(tex, (0, 0))
        else:
            s.fill((200, 200, 200, 255), (size // 4, size // 4, size // 2, size // 2))
    _cache_icons[key] = s
    return s


# ============================================================ SPRITES player
# Kael: lienzo 12x24 (pixel gordo x2 -> 24x48). Paleta fija estilo
# Terraria (vaqueros azules + botas marrones de explorador).
_SKIN = (235, 190, 150)
_SKIN_D = (200, 155, 115)
_HAIR = (120, 70, 30)
_HAIR_D = (90, 52, 22)
_TUNIC = (70, 130, 70)
_TUNIC_L = (95, 170, 95)
_TUNIC_D = (50, 95, 50)
_PANTS = (62, 82, 148)
_BOOTS = (112, 76, 42)
_BELT = (120, 85, 50)
_GOLD = (255, 215, 60)
_OUT = (25, 25, 35)  # contorno pixelart


def _spr_player_base(s, facing=1, blink=False):
    """Torso + cabeza HQ: contorno completo, pelo con mechas, cara con
    sombra, tunica con pliegues y cinturon con hebilla."""
    # --- cabeza 6x6 (y 2..7): piel + pelo con brillo ---
    rect_px(s, 3, 2, 6, 6, _SKIN)
    for x in range(3, 9):
        px(s, x, 2, _HAIR)
        px(s, x, 3, _HAIR)
    # mechas de pelo (brillo 1px)
    px(s, 4, 2, (150, 95, 45))
    px(s, 6, 2, (150, 95, 45))
    for y in range(2, 8):  # contorno cabeza
        px(s, 2, y, _OUT)
        px(s, 9, y, _OUT)
    for x in range(2, 10):
        px(s, x, 1, _OUT)
        px(s, x, 8, _OUT)
    px(s, 3, 4, _HAIR)  # patilla
    px(s, 8, 4, _HAIR)
    for x in range(3, 9):  # sombra inferior cara + mejilla
        px(s, x, 7, _SKIN_D)
    px(s, 3, 6, (225, 160, 130))  # rubor 1px
    px(s, 8, 6, (225, 160, 130))
    # ojos 1x2 con blanco (miran al facing) + ceja (parpadeo = linea)
    ex = 6 if facing > 0 else 4
    px(s, ex - 1, 4, _HAIR_D)
    px(s, ex + 2, 4, _HAIR_D)
    if blink:
        px(s, ex, 5, _HAIR_D)
        px(s, ex + 2, 5, _HAIR_D)
    else:
        px(s, ex, 5, (255, 255, 255))
        px(s, ex + 2, 5, (255, 255, 255))
        px(s, ex, 6, (20, 20, 25))
        px(s, ex + 2, 6, (20, 20, 25))
        px(s, ex, 5, (20, 20, 20)) if facing < 0 else px(s, ex + 2, 5, (20, 20, 20))
    # --- torso tunica (y 9..16) con pliegues, luz y sombra ---
    rect_px(s, 2, 9, 8, 7, _TUNIC)
    for y in range(9, 16):
        px(s, 2, y, _TUNIC_L)
        px(s, 3, y, _TUNIC_L)
        px(s, 9, y, _TUNIC_D)
        px(s, 8, y, _TUNIC_D)
    # pliegues verticales 1px
    for y in range(10, 14):
        px(s, 5, y, _TUNIC_D)
        px(s, 7, y, _TUNIC_L)
    # cuello + hombreras
    px(s, 5, 9, _SKIN)
    px(s, 6, 9, _SKIN)
    px(s, 2, 9, _GOLD)
    px(s, 9, 9, _GOLD)
    for y in range(9, 16):  # contorno torso
        px(s, 1, y, _OUT)
        px(s, 10, y, _OUT)
    # cinturon + hebilla con brillo
    for x in range(2, 10):
        px(s, x, 14, _BELT)
        px(s, x, 15, (95, 65, 38))
    rect_px(s, 5, 14, 2, 1, _GOLD)
    px(s, 5, 14, (255, 240, 170))


def _spr_player_legs(s, frame="idle", air=0):
    """Piernas 2px de ancho. frames: idle/idle1/run0..run5/jump/fall/slide."""
    y0 = 16 - air
    if frame in ("idle", "idle1"):
        # respiracion: idle1 1px mas alto + pies juntos/separados
        dy = 0 if frame == "idle" else -1
        rect_px(s, 3, y0 + dy, 2, 5, _PANTS)
        rect_px(s, 7, y0 + dy, 2, 5, _PANTS)
        px(s, 3, y0 + dy, shade(_PANTS, 25))
        px(s, 7, y0 + dy, shade(_PANTS, 25))
        rect_px(s, 3, y0 + 5 + dy, 2, 2, _BOOTS)
        rect_px(s, 7, y0 + 5 + dy, 2, 2, _BOOTS)
        px(s, 3, y0 + 5 + dy, (90, 80, 120))
    elif frame == "jump":  # piernas recogidas, una mas alta
        rect_px(s, 3, y0, 2, 3, _PANTS)
        rect_px(s, 7, y0 - 1, 2, 3, _PANTS)
        rect_px(s, 3, y0 + 3, 2, 2, _BOOTS)
        rect_px(s, 7, y0 + 2, 2, 2, _BOOTS)
        px(s, 7, y0 - 1, shade(_PANTS, 25))
    elif frame == "fall":  # piernas abiertas en tijera
        rect_px(s, 2, y0, 2, 4, _PANTS)
        rect_px(s, 8, y0 + 1, 2, 4, _PANTS)
        rect_px(s, 2, y0 + 4, 2, 2, _BOOTS)
        rect_px(s, 8, y0 + 5, 2, 2, _BOOTS)
    elif frame == "slide":  # wall-slide: rodillas dobladas contra la pared
        rect_px(s, 3, y0 + 1, 2, 4, _PANTS)
        rect_px(s, 7, y0 + 2, 2, 3, _PANTS)
        rect_px(s, 2, y0 + 5, 3, 2, _BOOTS)
        rect_px(s, 7, y0 + 5, 2, 2, _BOOTS)
    else:  # run0..run5: ciclo de 6 (contacto/paso/vuelo por pierna)
        try:
            n = int(frame.replace("run", "")) % 6
        except Exception:
            n = 0
        # offsets verticales opuestos por pierna (tijera real de 6 frames)
        off_a = (0, 1, 2, 1, 0, -1)[n]
        off_b = (1, 0, -1, 0, 1, 2)[n]
        rect_px(s, 3, y0 + max(0, off_a), 2, 5 - abs(off_a), _PANTS)
        rect_px(s, 7, y0 + max(0, off_b), 2, 5 - abs(off_b), _PANTS)
        px(s, 3, y0 + max(0, off_a), shade(_PANTS, 25))  # luz muslo
        # botas: la de atras se levanta (punta) en frames de vuelo
        lift_a = 0 if n in (0, 1, 4) else 1
        lift_b = 0 if n in (1, 4, 5) else 1
        rect_px(s, 3, y0 + 5 - lift_a, 2, 2, _BOOTS)
        rect_px(s, 7, y0 + 5 - abs(off_b) - lift_b + (1 if off_b > 0 else 0), 2, 2, _BOOTS)


def _spr_player_scarf(s, facing=1, frame="idle", sprint=False):
    """Bufanda roja al cuello que ondea (da vida al correr/saltar)."""
    bx = 3 if facing > 0 else 8  # sale por detras del cuello
    wave = 0
    if frame.startswith("run"):
        try:
            n = int(frame.replace("run", "")) % 6
        except Exception:
            n = 0
        wave = (0, 1, 0, -1, 0, 1)[n]
    elif frame in ("jump", "fall", "slide"):
        wave = -1
    length = 4 if sprint else 3
    for i in range(length):
        px(s, bx - facing * i if facing > 0 else bx - facing * i, 10 + wave * (i // 2) + (i == length - 1 and wave), (200, 50, 50))
    px(s, bx, 10, (230, 80, 80))


def _spr_player_tool(s, facing=1, frame="idle", held_id=None):
    """Herramienta en la mano delantera (pico/hacha/martillo/espada mini).
    held_id: id de items.py o None (manos vacias = puno)."""
    if not held_id:
        return
    x = 10 if facing > 0 else 1
    y0 = 10
    swing = 0
    if frame.startswith("run"):
        try:
            n = int(frame.replace("run", "")) % 6
        except Exception:
            n = 0
        swing = (0, 1, 0, -1, 0, 1)[n]
    elif frame == "jump":
        y0 -= 3
    # color por tier + forma por tipo
    tier_col = _tier_of(held_id)
    hx, hy = (x + 1 if facing > 0 else x - 3), y0 + 1 + swing
    # mango diagonal 3px
    for i in range(3):
        px(s, hx + (i if facing > 0 else -i), hy - i, (139, 90, 43))
    if "espada" in held_id:
        for i in range(4):
            px(s, hx + (1 + i if facing > 0 else -1 - i), hy - 2 - i, tier_col)
        px(s, hx + (2 if facing > 0 else -2), hy - 3, (255, 255, 255))
    elif "hacha" in held_id:
        px(s, hx + (2 if facing > 0 else -2), hy - 3, tier_col)
        px(s, hx + (3 if facing > 0 else -3), hy - 3, tier_col)
        px(s, hx + (2 if facing > 0 else -2), hy - 2, shade(tier_col, -30))
    elif "martillo" in held_id:
        rect_px(s, hx + (1 if facing > 0 else -4), hy - 4, 3, 2, tier_col)
        px(s, hx + (1 if facing > 0 else -4), hy - 4, (255, 255, 255))
    else:  # pico y resto: cabeza creciente mini estilo Terraria
        for i in range(-2, 3):
            px(s, hx + i, hy - 3 + abs(i) // 2, tier_col)
        px(s, hx - 2, hy - 2, shade(tier_col, -30))
        px(s, hx + 2, hy - 2, shade(tier_col, -30))
        px(s, hx, hy - 4, (255, 255, 255))


def _spr_player_arm(s, facing=1, frame="idle", air=0, held_id=None):
    """Brazo delantero + herramienta. En salto va arriba, en slide contra la pared."""
    x = 10 if facing > 0 else 1  # sobre el contorno del torso
    y0 = 10 - air
    if frame == "jump":
        rect_px(s, x, y0 - 2, 1, 4, _TUNIC_D)
        px(s, x, y0 - 3, _SKIN)  # puno arriba
    elif frame == "fall":
        rect_px(s, x, y0 - 1, 1, 4, _TUNIC_D)
        px(s, x, y0 + 3, _SKIN)
    elif frame == "slide":
        rect_px(s, x, y0, 1, 3, _TUNIC_D)  # mano apoyada en la pared
        px(s, x, y0 + 3, _SKIN)
        return  # sin herramienta visible al deslizar (mano ocupada)
    else:
        if frame.startswith("run"):
            try:
                n = int(frame.replace("run", "")) % 6
            except Exception:
                n = 0
            swing = (0, 1, 1, 0, -1, -1)[n]
        else:
            swing = 0
        rect_px(s, x, y0 + swing, 1, 4, _TUNIC_D)
        px(s, x, y0 + 4 + swing, _SKIN)
    _spr_player_tool(s, facing=facing, frame=frame, held_id=held_id)


def _spr_player_armor(s, armor, facing=1, air=0):
    if armor and armor[0]:  # casco: bloque 8x2 + brillo
        for x in range(3, 9):
            px(s, x, 1 - 0, (185, 190, 205))
        for x in range(3, 9):
            px(s, x, 1, (235, 240, 250))
    if armor and len(armor) > 1 and armor[1]:  # peto
        for x in range(2, 10):
            px(s, x, 9 - 0, (200, 205, 220))
            px(s, x, 10 - 0, (150, 155, 175))


def get_player_sprite(state="idle", frame_i=0, facing=1, armor=(None, None, None),
                      land_t=0.0, *args, **kwargs):
    """Frame pixelart de Kael 12x24 (sin escalar). Cacheado.

    state: idle | run | jump | fall | slide. run usa 6 frames, idle 2
    (respiracion). held_id (kwarg): herramienta en mano. sprint (kwarg):
    bufanda mas larga. land_t>0: squash de aterrizaje.
    Acepta extras (walk_phase, vy...) para no romper llamadas.
    appearance (kwarg): dict con skin_idx, hair_idx, eye_idx para colores custom.
    """
    global _SKIN, _SKIN_D, _HAIR, _HAIR_D
    held_id = kwargs.get("held_id")
    sprint = bool(kwargs.get("sprint", kwargs.get("sprinting", False)))
    appearance = kwargs.get("appearance")
    if "walk_phase" in kwargs and state == "run":
        frame_i = int(kwargs["walk_phase"]) % 6
    # categoria de herramienta para no explotar la cache (tipo+tier)
    if held_id:
        htipo = "espada" if "espada" in held_id else ("hacha" if "hacha" in held_id
                 else ("martillo" if "martillo" in held_id else ("pico" if "pico" in held_id else "otra")))
        htier = next((t for t in ("madera", "piedra", "hierro", "oro", "diamante") if t in held_id), "")
        held_cat = (htipo, htier)
    else:
        held_cat = (None, "")
    # Appearance indices for cache key
    app_key = (0, 0, 0)
    if appearance:
        app_key = (appearance.get("skin", 0), appearance.get("hair", 0), appearance.get("eye", 0))
    nframes = 6 if state == "run" else (2 if state == "idle" else 1)
    key = (state, frame_i % max(1, nframes), 1 if facing > 0 else -1,
           bool(armor[0]) if armor else False,
           bool(armor[1]) if len(armor) > 1 and armor else False,
           round(land_t, 2), held_cat, sprint, app_key)
    if key in _cache_sprites:
        return _cache_sprites[key]
    # override con PNG real si el usuario dibuja sus sprites
    png = load_sprite_file("mobs", "player", f"{state}_{frame_i % max(1, nframes)}.png")
    if png is not None:
        _cache_sprites[key] = png
        return png
    s = _small(12, 24)
    air = 0
    if state == "run":
        frames = f"run{frame_i % 6}"
    elif state == "idle":
        # idle0 = reposo, idle1 = respiracion+parpadeo (los ojos se cierran)
        frames = "idle1" if frame_i % 2 == 1 else "idle"
    elif state == "slide":
        frames = "slide"
    else:
        frames = {"jump": "jump", "fall": "fall"}.get(state, "idle")
    # Aplicar colores de appearance si se proporcionan
    old_skin, old_skin_d = _SKIN, _SKIN_D
    old_hair, old_hair_d = _HAIR, _HAIR_D
    if appearance:
        from config import SKIN_COLORS, HAIR_COLORS, EYE_COLORS
        si = appearance.get("skin", 0)
        hi = appearance.get("hair", 0)
        if 0 <= si < len(SKIN_COLORS):
            _SKIN = SKIN_COLORS[si]
            _SKIN_D = shade(_SKIN, -35)
        if 0 <= hi < len(HAIR_COLORS):
            _HAIR = HAIR_COLORS[hi]
            _HAIR_D = shade(_HAIR, -30)
    try:
        # parpadeo en idle: frame 1 con ojos cerrados
        _spr_player_base(s, facing=facing, blink=(frames == "idle1"))
        _spr_player_legs(s, frame=frames, air=air)
        _spr_player_scarf(s, facing=facing, frame=frames if frames.startswith("run") else state, sprint=sprint)
        _spr_player_arm(s, facing=facing, frame=frames, air=air, held_id=held_id)
        _spr_player_armor(s, armor, facing=facing)
        # Aplicar color de ojos si se proporciona
        if appearance:
            ei = appearance.get("eye", 0)
            if 0 <= ei < len(EYE_COLORS):
                ex = 6 if facing > 0 else 4
                if frames != "idle1":  # no parpadeando
                    px(s, ex, 6, EYE_COLORS[ei])
                    px(s, ex + 2, 6, EYE_COLORS[ei])
        if land_t > 0:  # squash: aplastar 1px abajo (mas fuerte si land_t alto)
            sq = _small(12, 24)
            sq.blit(s, (0, 1))
            for x in range(12):
                px(sq, x, 23, _OUT)
            s = sq
    finally:
        _SKIN = old_skin
        _SKIN_D = old_skin_d
        _HAIR = old_hair
        _HAIR_D = old_hair_d
    _cache_sprites[key] = s
    return s


def get_player_preview(skin_color, hair_color, eye_color):
    """Miniatura de preview para el creador de personaje. Sprite 12x24 con colores custom."""
    import hashlib
    key = ("preview", tuple(skin_color), tuple(hair_color), tuple(eye_color))
    if key in _cache_sprites:
        return _cache_sprites[key]
    s = _small(12, 24)
    # Guardar colores originales
    old_skin, old_hair = _SKIN, _HAIR
    old_skin_d, old_hair_d = _SKIN_D, _HAIR_D
    # Aplicar colores del jugador
    skin_d = shade(skin_color, -35)
    hair_d = shade(hair_color, -30)
    # Reemplazar temporalmente
    import textures as _self
    _self._SKIN = skin_color
    _self._SKIN_D = skin_d
    _self._HAIR = hair_color
    _self._HAIR_D = hair_d
    try:
        _spr_player_base(s, facing=1, blink=False)
        _spr_player_legs(s, frame="idle", air=0)
        _spr_player_scarf(s, facing=1, frame="idle", sprint=False)
        _spr_player_arm(s, facing=1, frame="idle", air=0, held_id=None)
    finally:
        _self._SKIN = old_skin
        _self._SKIN_D = old_skin_d
        _self._HAIR = old_hair
        _self._HAIR_D = old_hair_d
    # Reemplazar color de ojos
    ex = 6  # facing right
    if eye_color:
        px(s, ex, 5, (255, 255, 255))  # blanco
        px(s, ex + 2, 5, (255, 255, 255))
        px(s, ex, 6, eye_color)  # iris
        px(s, ex + 2, 6, eye_color)
        px(s, ex, 5, (20, 20, 20)) if 1 < 0 else px(s, ex + 2, 5, (20, 20, 20))  # pupila
    _cache_sprites[key] = s
    return s


# ============================================================ SPRITES mobs
def _slime_sprite(c, w_px, h_px, anim=0.0, facing=1, crown=None):
    """Slime HQ: cupula por filas + contorno oscuro, brillo 2px,
    ojos con blanco y boca. Squash de salto."""
    s = _small(w_px, h_px)
    light = tuple(min(255, v + 45) for v in c)
    dark = tuple(max(0, v - 50) for v in c)
    darker = tuple(max(0, v - 80) for v in c)
    squash = int(math.sin(anim) * 1)
    rows = max(3, h_px - 3 + squash)
    for i in range(rows):
        t = i / max(1, rows - 1)
        hw = int((w_px // 2 - 1) * math.sin(math.acos(1 - t * 1.6)) if t < 0.9 else w_px // 2 - 1)
        hw = max(2, hw)
        y = 2 + i - (1 if squash < 0 else 0)
        for x in range(w_px // 2 - hw, w_px // 2 + hw):
            # degradado vertical: arriba claro, abajo base
            px(s, x, y, light if i < 2 else c)
        px(s, w_px // 2 - hw, y, dark)  # contorno
        px(s, w_px // 2 + hw - 1, y, dark)
    for y in range(h_px - 2, h_px):  # base plana con contorno
        for x in range(1, w_px - 1):
            px(s, x, y, dark)
    for x in range(1, w_px - 1):
        px(s, x, h_px - 1, darker)
    # brillo cuadrado 2x2 + punto blanco
    rect_px(s, 3, 4, 2, 1, light)
    px(s, 3, 4, (255, 255, 255))
    px(s, 4, 5, shade(c, 30))
    # ojos 2x3 con blanco + pupila + boca
    ey = h_px // 2 + 1
    for ex in (w_px // 2 - 4, w_px // 2 + 1):
        rect_px(s, ex - 1, ey - 1, 4, 4, darker)  # contorno ojo
        rect_px(s, ex, ey, 2, 2, (255, 255, 255))
        px(s, ex + (1 if facing > 0 else 0), ey + 1, (20, 20, 25))
        px(s, ex + (1 if facing > 0 else 0), ey, (60, 60, 80))
    # boca 2px
    px(s, w_px // 2 - 1, ey + 3, darker)
    px(s, w_px // 2, ey + 3, darker)
    if crown:  # corona encajada sobre la cupula (sin flotar)
        for x in range(2, w_px - 2):
            px(s, x, 1, crown)
            px(s, x, 2, shade(crown, -40))
        for i in range(3):
            x = 3 + i * ((w_px - 6) // 2)
            px(s, x, 0, crown)
            px(s, x, 1, (255, 255, 255))
    return s


def _walker_sprite(c, anim=0.0, facing=1):
    # Putrek estilo Terraria: zombi con los BRAZOS EXTENDIDOS AL FRENTE,
    # ojos rojos, boca con dientes y marcha alterna.
    s = _small(12, 14)
    dark = tuple(max(0, v - 45) for v in c)
    light = tuple(min(255, v + 30) for v in c)
    step = int(anim) % 2
    rect_px(s, 3, 5 + step // 2, 6, 6 - step // 2, c)  # cuerpo
    for y in range(5, 11):
        px(s, 3, y, light)  # columna de luz
        px(s, 8, y, dark)   # sombra
    for x in range(3, 9):  # contorno cuerpo
        px(s, x, 5, _OUT)
    rect_px(s, 2, 1, 8, 5, (205, 185, 145))  # cara
    for y in range(1, 6):
        px(s, 2, y, _OUT)
        px(s, 9, y, _OUT)
    rect_px(s, 2, 5, 8, 1, (150, 60, 60))    # boca
    px(s, 4, 5, (255, 255, 255))  # dientes
    px(s, 7, 5, (255, 255, 255))
    px(s, 3, 3, (255, 60, 60))  # ojos 1px + brillo
    px(s, 8, 3, (255, 60, 60))
    px(s, 3, 2, (255, 200, 200))
    px(s, 8, 2, (255, 200, 200))
    # brazos EXTENDIDOS al frente (derecha; se espeja si facing < 0)
    ay = 7 + step  # leve balanceo al andar
    rect_px(s, 8, ay, 4, 2, c)
    px(s, 8, ay, light)
    px(s, 11, ay, dark)
    px(s, 11, ay + 1, dark)
    rect_px(s, 10, ay - 1 + step, 2, 1, dark)  # mano arriba/abajo
    rect_px(s, 3, 11, 2, 3, dark)  # piernas alternas
    rect_px(s, 7, 11 + step, 2, 3 - step, dark)
    px(s, 3, 13, _OUT)
    px(s, 7, 13, _OUT)
    if facing < 0:
        s = pygame.transform.flip(s, True, False)
    return s


def _skeleton_sprite(c, anim=0.0, facing=1):
    # Karkas HQ: costillas sombreadas, calavera con contorno y grieta.
    s = _small(12, 14)
    step = int(anim) % 2
    rect_px(s, 4, 9 + step, 1, 4 - step, c)  # piernas
    rect_px(s, 7, 9 + (1 - step), 1, 3 + step, c)
    px(s, 4, 12, _OUT)
    px(s, 7, 12, _OUT)
    rect_px(s, 3, 5, 6, 5, c)  # torso
    for y in range(5, 10):
        px(s, 3, y, _OUT)
        px(s, 8, y, _OUT)
    for y in range(6, 9):  # costillas 1px con luz
        px(s, 3, y, shade(c, -40))
        px(s, 8, y, shade(c, -40))
        px(s, 4, y, shade(c, 30))
    rect_px(s, 2, 0, 8, 5, (245, 245, 250))  # calavera con contorno
    for x in range(2, 10):
        px(s, x, 0, _OUT)
    for y in range(0, 5):
        px(s, 2, y, _OUT)
        px(s, 9, y, _OUT)
    rect_px(s, 4, 2, 1, 2, (10, 10, 15))  # ojos
    rect_px(s, 7, 2, 1, 2, (10, 10, 15))
    px(s, 4, 2, (180, 60, 60) if facing else (10, 10, 15))
    px(s, 5 + (1 if facing > 0 else 0), 4, (0, 0, 0))  # nariz
    px(s, 6, 1, shade(c, -30))  # grieta calavera
    return s


def _bat_sprite(c, anim=0.0, facing=1):
    # Vesper HQ: alas con membrana y "dedos", cuerpo con pelaje, colmillos.
    s = _small(16, 10)
    dark = tuple(max(0, v - 45) for v in c)
    flap = 0 if int(anim * 2) % 2 == 0 else 2  # 2 frames de aleteo
    # alas escalonadas con borde oscuro y membrana clara
    for i in range(5):
        for y in range(max(0, 2 + flap - i // 2), 6):
            px(s, 1 + i, y, (70, 45, 110))
            px(s, 14 - i, y, (70, 45, 110))
    for i in range(3):
        px(s, 2 + i, 3 + flap // 2, (135, 100, 175))
        px(s, 13 - i, 3 + flap // 2, (135, 100, 175))
    px(s, 1, 5, _OUT)
    px(s, 14, 5, _OUT)
    rect_px(s, 6, 4, 4, 5, c)  # cuerpo con pelaje
    rect_px(s, 6, 4, 1, 5, dark)
    px(s, 9, 4, shade(c, 40))
    px(s, 7, 5, (255, 255, 255))  # ojos con contorno
    px(s, 8, 5, (255, 255, 255))
    px(s, 7, 6, (255, 40, 40))  # ojos
    px(s, 8, 6, (255, 40, 40))
    px(s, 7, 7, (255, 255, 255))  # colmillos
    px(s, 8, 7, (255, 255, 255))
    px(s, 6, 3, c)  # orejas 1px con punta
    px(s, 9, 3, c)
    px(s, 6, 2, (255, 200, 220))
    px(s, 9, 2, (255, 200, 220))
    return s


def _golem_sprite(c, anim=0.0, facing=1):
    # Golem HQ: placas con remaches, visor con brillo, núcleo y musgo.
    s = _small(14, 14)
    dark = tuple(max(0, v - 45) for v in c)
    step = int(anim) % 2
    rect_px(s, 1, 4, 12, 9, _OUT)  # contorno cuerpo
    rect_px(s, 2, 5, 10, 7, dark)
    rect_px(s, 2, 5, 10, 6, c)
    dither_px(s, random.Random(5), 6, dark, area=(2, 5, 10, 6))
    px(s, 3, 6, (90, 160, 80))  # musgo
    px(s, 10, 6, (90, 160, 80))
    for x in (2, 6, 10):  # remaches
        px(s, x, 5, (220, 220, 230))
    rect_px(s, 3, 6, 8, 3, _OUT)  # visor con contorno
    rect_px(s, 3, 6, 8, 3, (90, 90, 105))
    rect_px(s, 4, 7, 2, 1, (255, 150, 0))  # ojos cuadrados
    rect_px(s, 8, 7, 2, 1, (255, 150, 0))
    px(s, 4, 7, (255, 230, 150))
    px(s, 8, 7, (255, 230, 150))
    rect_px(s, 6, 10, 2, 2, (255, 150, 0))  # nucleo pecho
    px(s, 6, 10, (255, 230, 150))
    rect_px(s, 3, 0, 8, 4, _OUT)  # casco con contorno
    rect_px(s, 3, 1, 8, 3, (70, 70, 80))
    for x in range(3, 11):
        px(s, x, 1, (110, 110, 125))
    px(s, 6, 2, (150, 150, 170))
    rect_px(s, 1, 12 + step, 3, 2 - step, dark)  # pies
    rect_px(s, 10, 12 + (1 - step), 3, 1 + step, dark)
    return s


def get_enemy_sprite(kind, anim=0.0, facing=1, *args, **kwargs):
    """Sprite pixelart del mob (lienzo pequeno, sin escalar). Cacheado por
    (kind, frame de anim). Acepta extras (hp, w...) sin romper llamadas."""
    from entities.mobs.enemies import COLORS
    frame = int(anim * 2) % 4
    key = ("enemy", kind, frame, 1 if facing > 0 else -1)
    if key in _cache_sprites:
        return _cache_sprites[key]
    png = load_sprite_file("mobs", kind, f"{frame}.png")
    if png is not None:
        _cache_sprites[key] = png
        return png
    c = COLORS.get(kind, (200, 60, 60))
    a = frame * 1.5
    if kind in ("rey_mokulon", "heraldo_abismo"):
        crown = (255, 215, 60) if kind == "rey_mokulon" else (220, 40, 90)
        s = _slime_sprite(c, 16, 14, anim=a, facing=facing, crown=crown)
    elif kind in ("moki_verde", "moki_azul", "moki_rojo", "mini_moki",
                  "orbe_rastrero"):
        s = _slime_sprite(c, 14, 10, anim=a, facing=facing)
    elif kind in ("putrek",):
        s = _walker_sprite(c, anim=a, facing=facing)
    elif kind in ("karkas", "eco_profundo"):
        s = _skeleton_sprite(c, anim=a, facing=facing)
    elif kind in ("vesper", "sedaluz"):
        s = _bat_sprite(c, anim=a, facing=facing)
    else:
        s = _golem_sprite(c, anim=a, facing=facing)
    _cache_sprites[key] = s
    return s


def _npc_sprite(tunic, cap, facing=1, frame=0, name="aldeano"):
    # NPC estilo Terraria: contorno oscuro completo, cabeza grande (1/3),
    # ojos de 2px con blanco, ropa con luz/sombra y pies que alternan.
    # Liora = guia aldeana (coleta + tunica), Bruno = vigia (barba + farol).
    s = _small(12, 24)
    cap_l = tuple(min(255, v + 35) for v in cap)
    tun_l = tuple(min(255, v + 35) for v in tunic)
    tun_d = tuple(max(0, v - 35) for v in tunic)
    skin_d = tuple(max(0, v - 30) for v in _SKIN)
    lift = frame % 2  # bob de 1px al andar
    # --- cabeza ---
    rect_px(s, 3, 2, 6, 6, _SKIN)
    for x in range(3, 9):
        px(s, x, 8 - lift, skin_d)  # sombra mandibula
    for y in range(2, 8):
        px(s, 2, y, _OUT)
        px(s, 9, y, _OUT)
    for x in range(2, 10):
        px(s, x, 1, _OUT)
    if name == "Bruno":
        # capucha de vigia + barba gris espesa
        for x in range(2, 10):
            px(s, x, 1, cap)
            px(s, x, 2, cap)
        px(s, 3, 1, cap_l)
        rect_px(s, 3, 6, 6, 4, (160, 160, 170))  # barba
        px(s, 4, 6, (200, 200, 210))
        px(s, 5, 9, (140, 140, 150))
        px(s, 4, 4, (255, 255, 255))  # ojos entre capucha y barba
        px(s, 7, 4, (255, 255, 255))
        px(s, 4, 4, (30, 30, 60))
        px(s, 7, 4, (30, 30, 60))
    else:
        # pelo de guia con coleta al lado
        for x in range(3, 9):
            px(s, x, 2, cap)
        px(s, 3, 2, cap_l)
        px(s, 5, 2, cap_l)
        rect_px(s, 9, 3, 2, 5, cap)  # coleta
        px(s, 9, 3, cap_l)
        px(s, 9, 7, tuple(max(0, v - 30) for v in cap))
        px(s, 4, 5, (255, 255, 255))  # ojos grandes estilo Terraria
        px(s, 7, 5, (255, 255, 255))
        px(s, 4, 6, (30, 30, 60))
        px(s, 7, 6, (30, 30, 60))
        px(s, 5, 7, (160, 100, 90))  # boca
        px(s, 6, 7, (160, 100, 90))
    # --- torso ---
    rect_px(s, 2, 9, 8, 8 - lift, tunic)
    for y in range(9, 17 - lift):
        px(s, 2, y, tun_l)
        px(s, 9, y, tun_d)
    for y in range(9, 17 - lift):
        px(s, 1, y, _OUT)
        px(s, 10, y, _OUT)
    for x in range(2, 10):  # cinto con hebilla
        px(s, x, 13, (90, 65, 40))
    px(s, 5, 13, (255, 215, 90))
    px(s, 6, 13, (255, 215, 90))
    if name == "Bruno":
        # farolillo del vigia en la mano
        rect_px(s, 10, 11, 2, 3, (60, 60, 72))
        rect_px(s, 10, 12, 2, 1, (255, 200, 100))
        px(s, 10, 12, (255, 255, 220))
    else:
        px(s, 1, 11, _SKIN)  # mano
        px(s, 10, 11, _SKIN)
    # --- piernas y pies (marcha) ---
    rect_px(s, 3, 17 - lift, 2, 4, (90, 70, 55))
    rect_px(s, 7, 17 - lift, 2, 4, (80, 62, 48))
    rect_px(s, 3, 21, 2, 2, _BOOTS)
    rect_px(s, 7, 21, 2, 2, _BOOTS)
    if frame % 2:
        px(s, 3, 21, (90, 80, 120))
    else:
        px(s, 7, 21, (90, 80, 120))
    return s


def get_npc_sprite(name="Liora", tunic=(130, 80, 180), cap=(90, 50, 120),
                   frame=0, *args, **kwargs):
    key = ("npc", name, frame % 2)
    if key in _cache_sprites:
        return _cache_sprites[key]
    png = load_sprite_file("mobs", "npc", f"{name}_{frame % 2}.png")
    if png is not None:
        _cache_sprites[key] = png
        return png
    s = _npc_sprite(tunic, cap, frame=frame, name=name)
    _cache_sprites[key] = s
    return s


# ------------------------------------------------------------- personajes
def draw_sword_swing(surf, x, y, facing, progress, kind="espada", item_id=None):
    """Tajo visible estilo Terraria: la espada BARRE en 3 poses pixeladas
    (arriba -> medio -> abajo) con estela blanca. Sin rotacion suave:
    todo en pixeles gordos para no romper el estilo.

    x,y: esquina del jugador en pantalla. facing: 1/-1. progress: 0..1
    del tajo. kind: 'espada' (grande) | 'herramienta' (corto) | 'puno'.
    """
    if kind == "puno":
        hx = x + (6 if facing > 0 else -1)
        hy = y + 6
        n = int(progress * 3)
        for i in range(2 + n):
            surf.fill((255, 255, 255), (hx + facing * i, hy, 1, 1))
        return
    col = _tier_of(item_id) if item_id else (200, 200, 200)
    dark = shade(col, -55)
    light = shade(col, 55)
    hand_x = x + (5 if facing > 0 else 1)
    hand_y = y + 6
    reach = 8 if kind == "espada" else 6
    if progress < 0.33:
        tip_x = hand_x + facing * 2
        tip_y = hand_y - 6
        mid_x = hand_x + facing * 3
        mid_y = hand_y - 3
    elif progress < 0.66:
        tip_x = hand_x + facing * reach
        tip_y = hand_y - 1
        mid_x = hand_x + facing * (reach - 3)
        mid_y = hand_y - 3
    else:
        tip_x = hand_x + facing * (reach - 2)
        tip_y = hand_y + 4
        mid_x = hand_x + facing * (reach - 3)
        mid_y = hand_y + 2
    trail = [(hand_x + facing * 3, hand_y - 5),
             (hand_x + facing * 5, hand_y - 3),
             (hand_x + facing * 6, hand_y - 1),
             (hand_x + facing * 5, hand_y + 3)]
    shown = int(progress * 4) + 1
    for i, (tx, ty) in enumerate(trail[:shown]):
        a = 220 - i * 45 - int(progress * 80)
        if a > 40:
            s = pygame.Surface((2, 2), pygame.SRCALPHA)
            s.fill((255, 255, 255))
            s.set_alpha(max(40, min(255, a)))
            surf.blit(s, (tx, ty))
    for t in (0.0, 0.5, 1.0):
        bx = int(hand_x + (mid_x - hand_x) * t)
        by = int(hand_y + (mid_y - hand_y) * t)
        surf.fill(dark, (bx, by, 2, 2))
        surf.fill(col, (bx, by - 1, 2, 2))
    for t in (0.0, 0.5, 1.0):
        bx = int(mid_x + (tip_x - mid_x) * t)
        by = int(mid_y + (tip_y - mid_y) * t)
        surf.fill(col, (bx, by, 2, 2))
        surf.fill(light, (bx, by - 1, 2, 1))
    surf.fill((255, 255, 255), (tip_x, tip_y, 2, 2))
    surf.fill((255, 215, 60), (hand_x - 1, hand_y - 1, 3, 2))
    surf.fill((140, 100, 30), (hand_x - 1, hand_y + 1, 3, 1))


def draw_player(surf, x, y, *args, facing=1, walk_phase=0.0, on_ground=True,
                moving=False, armor=(None, None, None), invulnerable=False,
                state=None, vy=0.0, land_t=0.0, fall_time=0.0, **kwargs):
    """Kael con sprites pixelart animados (idle 2f / run 6f / jump / fall /
    slide + squash + bufanda + herramienta en mano + tajo de espada).

    Conecta con: entities/player.py (facing, walk_phase, armor, state, vy,
    land_t, sprinting, skidding, sliding, held_id, attack_*). state manda;
    si es None se deduce de on_ground/vy. **kwargs ignora extras.
    Tamano final 14x30 (sprite 12x24 NEAREST, TILE=16).
    """
    if invulnerable and int(invulnerable * 12) % 2 == 0:
        return
    sprinting = bool(kwargs.get("sprinting", kwargs.get("sprint", False)))
    skidding = bool(kwargs.get("skidding", False))
    sliding = bool(kwargs.get("sliding", state == "slide"))
    held_id = kwargs.get("held_id")
    if state is None:
        if sliding:
            state = "slide"
        elif not on_ground:
            state = "jump" if vy < 60 else "fall"
        else:
            state = "run" if moving else "idle"
    if state == "run":
        frame_i = int(walk_phase) % 6
    elif state == "idle":
        import time
        frame_i = int(time.time() * 1.6) % 4  # 0,1,2,3 (3 = parpadeo)
        frame_i = 1 if frame_i == 3 else 0
    else:
        frame_i = 0
    small = get_player_sprite(state, frame_i, facing, armor, land_t,
                              held_id=held_id, sprint=sprinting,
                              appearance=kwargs.get("appearance"))
    # Sprite 12x24 -> tamano de juego: escala con TILE (6x12 con TILE=6).
    if small.get_width() == 12:
        big = pygame.transform.scale(small, (TILE, TILE * 2))
    else:
        big = small
    pw, ph = TILE, TILE * 2
    # sombra cuadrada (mas pequena al saltar)
    sh_w = pw if on_ground else max(2, pw - 2)
    sh_x = x + (pw - sh_w) // 2
    lift = min(4, max(0, int(-vy // 30))) if not on_ground else 0
    pygame.draw.ellipse(surf, (0, 0, 0, 90), (sh_x, y + ph - 2, sh_w, 2))
    # derrape: pequena inclinacion (1px) hacia el movimiento
    if skidding and on_ground:
        x += facing
    surf.blit(big, (x, y - (lift // 4)))
    # tajo de ataque: espada/herramienta girando delante del jugador
    atk = float(kwargs.get("attack_anim", 0.0))
    dur = float(kwargs.get("attack_dur", 0.25) or 0.25)
    if atk > 0 and dur > 0:
        prog = max(0.0, min(1.0, 1.0 - atk / dur))
        draw_sword_swing(surf, x, y - (lift // 4), facing, prog,
                         kind=kwargs.get("attack_kind") or "puno",
                         item_id=kwargs.get("attack_id"))


def draw_npc(surf, x, y, name="Liora", tunic=(130, 80, 180),
             cap=(90, 50, 120), quest_mark=False, tick=0, *args, **kwargs):
    """NPC 12x24 -> 6x12 (NEAREST, escala con TILE) con nombre pixel y
    '!' con contorno. Fuentes y nombre prerenderizados (no cada frame)."""
    import math
    frame = (tick // 500) % 2
    small = get_npc_sprite(name, tunic, cap, frame)
    big = pygame.transform.scale(small, (TILE, TILE * 2))
    pygame.draw.ellipse(surf, (0, 0, 0, 80), (x, y + TILE * 2 - 1, TILE, 2))
    surf.blit(big, (x, y))
    t, sh = _npc_name_surf(name)
    surf.blit(sh, (x + 3 - t.get_width() // 2 + 1, y - 11))
    surf.blit(t, (x + 3 - t.get_width() // 2, y - 12))
    if quest_mark:
        bob = int(math.sin(pygame.time.get_ticks() * 0.006) * 2)
        q, qsh = _npc_mark_surf()
        surf.blit(qsh, (x + 4, y - 22 + bob))
        surf.blit(q, (x + 3, y - 23 + bob))


_npc_name_cache = {}
_npc_mark_cache = None


def _npc_name_surf(name):
    """(texto, sombra) del nombre cacheados: el nombre no cambia."""
    hit = _npc_name_cache.get(name)
    if hit is not None:
        return hit
    f = pygame.font.SysFont("consolas,couriernew,monospace", 10, bold=True)
    t = f.render(name, False, (255, 255, 255))
    sh = f.render(name, False, (10, 10, 20))
    _npc_name_cache[name] = (t, sh)
    return t, sh


def _npc_mark_surf():
    """'!' del quest cacheado."""
    global _npc_mark_cache
    if _npc_mark_cache is not None:
        return _npc_mark_cache
    q = pygame.font.SysFont("consolas,couriernew,monospace", 14, bold=True)
    _npc_mark_cache = (q.render("!", False, (255, 215, 60)),
                       q.render("!", False, (60, 30, 0)))
    return _npc_mark_cache


def draw_enemy(surf, kind, x, y, w, h, *args, anim=0.0, facing=1, **kwargs):
    """Dibuja cualquier mob con su sprite pixelart (frame por anim),
    conservando la proporcion original (antes se estiraba a cuadrado).

    Conecta con: Enemy.draw(). Args extras via kwargs (hp, name...) se
    ignoran aqui; la barra de vida la pinta enemies.py encima.
    """
    small = get_enemy_sprite(kind, anim=anim, facing=facing)
    sw, sh = small.get_size()
    if sw > 0 and sh > 0:
        # encajar sin deformar, centrado abajo (los slimes son anchos y bajos)
        scale = min(w / sw, h / sh)
        bw, bh = max(1, int(sw * scale)), max(1, int(sh * scale))
        big = pygame.transform.scale(small, (bw, bh))
        ox = x + (w - bw) // 2
        oy = y + (h - bh)
    else:
        big, ox, oy = small, x, y
    pygame.draw.ellipse(surf, (0, 0, 0, 80), (x + 1, y + h - 1, max(1, w - 2), 3))
    surf.blit(big, (ox, oy))
    if kwargs.get("flash"):
        # hit-flash: silueta blanca del sprite (mascara, 1 frame)
        try:
            m = pygame.mask.from_surface(big)
            ws = m.to_surface(setcolor=(255, 255, 255, 255),
                              unsetcolor=(0, 0, 0, 0))
            surf.blit(ws, (ox, oy))
        except Exception:
            pass
