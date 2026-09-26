# Bloques del mundo. id -> propiedades
# tool: None = mano, "pico" = necesita pico, "hacha" = hacha talando mas rapido

BLOCKS = {
    0:  dict(name="Aire",          solid=False, hardness=0,   tool=None,  drop=None,           colors=[(0, 0, 0)]),
    1:  dict(name="Tierra",        solid=True,  hardness=0.7, tool=None,  drop="tierra",       colors=[(139, 90, 43), (125, 80, 38)]),
    2:  dict(name="Piedra",        solid=True,  hardness=1.6, tool="pico", drop="piedra",       colors=[(128, 128, 135), (110, 110, 118)]),
    # Arboles: NO solidos -> el jugador pasa a traves, pero se pican con hacha.
    # background=True marca que son "de fondo" (no colisionan).
    3:  dict(name="Tronco",        solid=False, hardness=1.0, tool="hacha", drop="madera",      colors=[(101, 67, 33), (88, 58, 28)], background=True),
    4:  dict(name="Hojas",         solid=False, hardness=0.4, tool=None,  drop="hoja",         colors=[(34, 139, 34), (45, 160, 45)], background=True),
    5:  dict(name="Arena",         solid=True,  hardness=0.6, tool=None,  drop="arena",        colors=[(233, 214, 150), (220, 200, 135)]),
    6:  dict(name="Carbon",        solid=True,  hardness=2.0, tool="pico", drop="carbon",       colors=[(100, 100, 110)], ore=(20, 20, 20)),
    7:  dict(name="Hierro",        solid=True,  hardness=2.6, tool="pico", drop="hierro_crudo", colors=[(150, 130, 120)], ore=(210, 150, 120)),
    8:  dict(name="Oro",           solid=True,  hardness=3.0, tool="pico", drop="oro_crudo",    colors=[(150, 130, 120)], ore=(255, 215, 60)),
    9:  dict(name="Diamante",      solid=True,  hardness=3.8, tool="pico", drop="diamante",     colors=[(120, 130, 150)], ore=(120, 230, 255)),
    10: dict(name="Bedrock",       solid=True,  hardness=999, tool=None,  drop=None,           colors=[(40, 40, 48), (30, 30, 38)]),
    11: dict(name="Tablones",      solid=True,  hardness=1.0, tool="hacha", drop="tablones",    colors=[(160, 115, 60), (145, 100, 50)]),
    12: dict(name="Mesa trabajo",  solid=False, hardness=1.0, tool="hacha", drop="mesa_trabajo",colors=[(170, 125, 70)], station="workbench"),
    13: dict(name="Horno",         solid=True,  hardness=2.0, tool="pico", drop="horno",        colors=[(90, 90, 100)], station="furnace"),
    14: dict(name="Antorcha",      solid=False, hardness=0.2, tool=None,  drop="antorcha",     colors=[(60, 50, 30)], light=True),
    15: dict(name="Ladrillo",      solid=True,  hardness=2.2, tool="pico", drop="ladrillo",     colors=[(150, 70, 60), (135, 60, 52)]),
    16: dict(name="Cofre antiguo", solid=False, hardness=1.2, tool="hacha", drop="moneda_oro",  colors=[(140, 100, 40)], chest=True),
    17: dict(name="Altar de Underdown",   solid=True,  hardness=5.0, tool="pico", drop=None,           colors=[(70, 60, 120), (90, 80, 150)], station="altar"),
    18: dict(name="Hierba",        solid=True,  hardness=0.7, tool=None,  drop="tierra",       colors=[(110, 75, 35)], grass=True),
    19: dict(name="Flor abisal",   solid=False, hardness=0.3, tool=None,  drop="baya_luminosa",colors=[(30, 40, 60)], light=True),
    20: dict(name="Roca abisal",   solid=True,  hardness=2.8, tool="pico", drop="roca_abisal",  colors=[(45, 40, 70), (55, 48, 85)]),
    # ---- Bloques traseros / raseros: solo con MARTILLO, no bloquean ----
    # Son "paredes de fondo": decoran y se pican rapidisimo con martillo,
    # con otra herramienta van lentisimo. Ideales para el Abismo y casas.
    21: dict(name="Pared rustica", solid=False, hardness=0.9, tool="martillo", drop="pared_rustica", colors=[(120, 95, 65), (100, 78, 52)], background=True),
    22: dict(name="Pared abisal",  solid=False, hardness=1.2, tool="martillo", drop="pared_abisal",  colors=[(55, 45, 90), (45, 36, 75)], background=True),
    23: dict(name="Losa musgosa",  solid=True,  hardness=1.4, tool="martillo", drop="losa_musgosa",  colors=[(90, 110, 70), (75, 92, 58)]),
    # ---- Biomas profundos: hongos brillantes y bosques subterraneos ----
    24: dict(name="Micelio brillante", solid=True, hardness=0.8, tool=None, drop="micelio", colors=[(70, 60, 130), (60, 50, 115)]),
    25: dict(name="Seta luminosa", solid=False, hardness=0.3, tool=None, drop="seta_brillante", colors=[(120, 255, 190)], light=True),
    26: dict(name="Tallo fungico", solid=True, hardness=0.9, tool="hacha", drop="tallo_fungico", colors=[(200, 190, 200), (180, 170, 190)]),
    # ---- Temas del Abismo (una roca distinta por capa, ver world.py) ----
    27: dict(name="Pizarra abisal", solid=True, hardness=2.4, tool="pico", drop="pizarra", colors=[(70, 80, 110), (58, 66, 94)]),
    28: dict(name="Hueso antiguo", solid=True, hardness=1.8, tool="pico", drop="hueso", colors=[(215, 205, 180), (190, 178, 150)]),
    # ---- Muebles (edificaciones con camas, sillas y luces) ----
    29: dict(name="Farol", solid=False, hardness=0.2, tool=None, drop="farol", colors=[(60, 50, 30)], light=True),
    30: dict(name="Cama", solid=True, hardness=1.0, tool="hacha", drop="cama", colors=[(150, 60, 60)]),
    31: dict(name="Silla", solid=False, hardness=0.8, tool="hacha", drop="silla", colors=[(160, 115, 60)]),
    # ---- Puertas y ventanas ----
    # La puerta cerrada (32) bloquea y tapa el sol; ABIERTA (33) se
    # atraviesa y deja pasar la luz (click derecho para abrir/cerrar).
    32: dict(name="Puerta", solid=True, hardness=1.0, tool="hacha", drop="puerta", colors=[(140, 100, 55)]),
    33: dict(name="Puerta abierta", solid=False, hardness=1.0, tool="hacha", drop="puerta", colors=[(140, 100, 55)]),
    # La ventana (34) bloquea el paso pero NO la luz (cristal).
    34: dict(name="Ventana", solid=True, hardness=0.8, tool="hacha", drop="ventana", colors=[(170, 210, 230)], glass=True),
}

NAME_TO_ID = {v["name"]: k for k, v in BLOCKS.items()}
# item bloque -> id de bloque al colocar
ITEM_TO_BLOCK = {
    "tierra": 1, "piedra": 2, "madera": 3, "hoja": 4, "arena": 5,
    "tablones": 11, "mesa_trabajo": 12, "horno": 13, "antorcha": 14,
    "ladrillo": 15, "hierba": 18, "flor_abisal": 19, "roca_abisal": 20,
    "pared_rustica": 21, "pared_abisal": 22, "losa_musgosa": 23,
    "micelio": 24, "tallo_fungico": 26, "pizarra": 27, "hueso": 28,
    "farol": 29, "cama": 30, "silla": 31, "puerta": 32, "ventana": 34,
}
