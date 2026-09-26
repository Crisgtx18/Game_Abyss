# ============================================================
#  UNDERDOWN (estilo Terraria 2D) - Configuracion global
#  Lore inventado:
#   Mundo: UnderDown, continente flotante tras la caida del Rey Mokulon.
#   Heroe: Kael el Explorador (el jugador).
#   Mobs: Mokis (slimes), Putrek (zombie), Karkas (esqueleto),
#         Vesper (murcielago), Rokthar (golem), Rey Mokulon (boss).
#   NPC: Maestra Liora (aldeana que da consejos y vende pociones).
# ============================================================

SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
# Bloques mini: 6px -> el doble de granularidad que antes (estilo Terraria:
# el jugador mide ~1 x 2 tiles). La fisica esta en px/s pero ajustada para
# que la sensacion en TILES sea la misma que con TILE=12 (todo x0.5).
TILE = 6

# Resoluciones disponibles
RESOLUTIONS = [
    (1280, 720),
    (1920, 1080),
    (1600, 900),
    (1024, 576),
    (800, 450),
]

# Estilos de personaje
SKIN_COLORS = [
    (235, 190, 150),  # Claro
    (200, 155, 115),  # Medio
    (160, 110, 70),   # Moreno
    (120, 80, 50),    # Oscuro
]
HAIR_COLORS = [
    (120, 70, 30),    # Castano
    (40, 30, 20),     # Negro
    (200, 160, 80),   # Rubio
    (180, 50, 40),    # Rojo
    (100, 100, 110),  # Gris
]
EYE_COLORS = [
    (20, 20, 25),     # Negro
    (50, 100, 180),   # Azul
    (50, 140, 50),    # Verde
    (160, 100, 40),   # Marron
]

# Mundo 3x mas grande: 960x1620 (antes 320x540).
WORLD_W = 960
WORLD_H = 1620

GRAVITY = 750.0       # subida (px/s^2) - ajustado para TILE=6 (mitad que 12)
GRAVITY_FALL = 1100.0 # bajada: caer mas rapido que subir = salto con peso
MAX_FALL = 260.0      # velocidad maxima de caida (px/s)
MOVE_SPEED = 90.0     # velocidad horizontal maxima (px/s)
SPRINT_MULT = 1.45    # Shift = sprint (ver player.py)
JUMP_VEL = -230.0     # impulso inicial de salto (px/s) ~5 tiles con TILE=6
# Aceleracion / friccion (px/s^2)
GROUND_ACCEL = 1100.0
AIR_ACCEL = 800.0
GROUND_FRICTION = 1100.0
AIR_FRICTION = 200.0
WALL_SLIDE_SPEED = 50.0   # caida maxima pegado a la pared
WALL_JUMP_X = 115.0       # impulso horizontal del wall-jump
WALL_JUMP_Y = -215.0      # impulso vertical del wall-jump

# Salto "con perdon" (usa physics.py: coyote time + buffer + salto variable)
COYOTE_TIME = 0.10   # seg. de gracia para saltar tras salir de un borde
JUMP_BUFFER = 0.12   # seg. que se guarda un salto pulsado antes de caer
JUMP_CUT = 0.55      # tope de subida al soltar pronto (salto corto ~1 tile)

# Generacion procedural (usa noise.py + world.py). Tocables sin miedo:
WG_HILLS_AMP = 4.0    # detalle de colinas (relieve grande = fbm continente)
WG_CAVE_SIZE = 0.06   # umbral de tuneles: mas alto = mas cuevas (0.03-0.10)
WG_ORE_RICHNESS = 1.0 # >1 mas minerales, <1 mundo pobre
WG_TREE_DENSITY = 0.12  # prob. base de arbol por columna de bosque

# Hambre y Abismo (usa player.py hunger + abyss.py)
HUNGER_TIME = 480.0   # segundos en vaciar el hambre (x mult de capa)
STARVE_DPS = 2.0      # dano por segundo con hambre a 0
ABYSS_MARGIN = 45     # ancho extra de la fosa para efectos/spawns (pozo ancho)

DAY_LENGTH = 480.0          # segundos de un dia completo (dia+noche)
RESPAWN_TIME = 5.0

REACH_DIST = 5.5            # alcance para picar/poner (en tiles)

# Colores
SKY_DAY = (88, 165, 252)
SKY_NIGHT = (10, 12, 46)
SKY_SUNSET = (255, 140, 80)
UI_BG = (18, 20, 32)
UI_PANEL = (30, 34, 52)
UI_ACCENT = (255, 200, 80)

PLAYER_SPAWN_ITEMS = [
    ("pico_madera", 1),
    ("espada_madera", 1),
    ("hacha_madera", 1),
    ("martillo_madera", 1),
    ("antorcha", 20),
    ("pocion_vida_menor", 3),
    ("tierra", 30),
    ("madera", 20),
    ("pared_rustica", 20),
]
