"""El Abismo estilo Made in Abyss: fosa enorme con 7 capas, cada una con su
nombre, color, bichos, efectos ambientales y su Maldicion al ascender.

Que hace:
    - Define las LAYERS (nombre, rango de profundidad, tint, oscuridad,
      hambre xN, maldicion al subir, pool de enemigos, escalado).
    - layer_at(ty, world_h, surface_y): dice en que capa esta un tile.
    - near_abyss(world, tx): True si estas dentro/hasta el borde de la fosa.
    - pick_enemy(layer, rng): bicho aleatorio de la capa (para game.py).
    - curse_for(layer): dano y debuff al SUBIR desde esa capa (la Maldicion).

Con que conecta:
    - world.py  -> _fase_abismo() abre la fosa y guarda abyss_x/abyss_top;
      usa LAYER_BOUNDS para decorar por capa (flores, roca abisal).
    - game.py   -> banner al entrar en capa, efectos (esporas, hambre x2,
      oscuridad), maldicion al ascender, spawns del pool de la capa.
    - entities/mobs/enemies.py -> MOB_STATS de los bichos del pool.
    - ui.py     -> banner con el nombre y color de la capa.

Como tocarlo luego:
    Cambia nombres, umbrales (LAYER_BOUNDS) o pools sin tocar game.py.
    Sube curse_dmg para un abismo mas cruel, o baja dark para ver mejor.

Uso *args/**kwargs:
    Las funciones aceptan *args/**kwargs para banderas futuras
    (ej. layer_at(..., strict=True)) sin romper llamadas viejas.
"""
import random

# Fracciones de profundidad (ty / H) donde empieza cada capa 1..7.
# El pozo es enorme y recto: las capas hondas ocupan mas tramo.
LAYER_BOUNDS = [0.24, 0.36, 0.48, 0.60, 0.72, 0.84]

LAYERS = [
    dict(idx=0, name="Superficie", sub="Mokulandia respira aqui",
         tint=(0, 0, 0, 0), dark=0.0, hunger_mult=1.0, curse_dmg=0,
         slow=1.0, pool=["moki_verde"], desc="Sin efectos.",
         fog=(0, 0, 0, 0), spore=(0, 0, 0), glow=90),
    dict(idx=1, name="Borde del Abismo", sub="Capa 1: el viento huele a flor",
         tint=(40, 110, 70, 28), dark=0.05, hunger_mult=1.0, curse_dmg=0,
         slow=1.0, pool=["moki_verde", "moki_azul", "orbe_rastrero"],
         desc="Bichos un poco mas duros (+10%).",
         fog=(60, 140, 90, 18), spore=(140, 255, 170), glow=85),
    dict(idx=2, name="Bosque de Tentaculos", sub="Capa 2: esporas en el aire",
         tint=(70, 45, 130, 48), dark=0.14, hunger_mult=1.2, curse_dmg=6,
         slow=0.9, pool=["orbe_rastrero", "sedaluz", "moki_azul"],
         desc="Esporas: -10% velocidad. Subir mareado hace dano.",
         fog=(110, 70, 200, 30), spore=(190, 150, 255), glow=75),
    dict(idx=3, name="La Gran Falla", sub="Capa 3: el pozo vertical",
         tint=(30, 40, 110, 65), dark=0.24, hunger_mult=1.4, curse_dmg=12,
         slow=0.9, pool=["sedaluz", "dientepiedra", "karkas"],
         desc="Caidas largas. La maldicion ya muerde al ascender.",
         fog=(60, 80, 220, 35), spore=(140, 180, 255), glow=65),
    dict(idx=4, name="Copas de los Gigantes", sub="Capa 4: calor humedo",
         tint=(110, 60, 35, 65), dark=0.32, hunger_mult=2.0, curse_dmg=20,
         slow=0.85, pool=["dientepiedra", "eco_profundo", "vesper"],
         desc="El hambre aprieta x2. Sangrado leve al subir.",
         fog=(220, 130, 60, 30), spore=(255, 190, 120), glow=55),
    dict(idx=5, name="Mar de Cadaveres", sub="Capa 5: punto de no retorno",
         tint=(10, 10, 30, 95), dark=0.45, hunger_mult=2.5, curse_dmg=38,
         slow=0.8, pool=["eco_profundo", "heraldo_abismo", "rokthar"],
         desc="Casi ciego sin antorchas. Subir puede matarte.",
         fog=(20, 20, 50, 50), spore=(150, 60, 220), glow=45),
    dict(idx=6, name="Capital del Retorno", sub="Capa 6: casi el fondo",
         tint=(130, 30, 100, 95), dark=0.50, hunger_mult=3.0, curse_dmg=55,
         slow=0.8, pool=["heraldo_abismo", "eco_profundo"],
         desc="Reliquias y muerte. La maldicion es maxima.",
         fog=(200, 50, 150, 40), spore=(255, 120, 220), glow=40),
    dict(idx=7, name="Torbellino Final", sub="Capa 7: el fondo del mundo",
         tint=(20, 5, 45, 110), dark=0.58, hunger_mult=3.5, curse_dmg=70,
         slow=0.75, pool=["heraldo_abismo", "eco_profundo", "dientepiedra"],
         desc="Remolino de reliquias. Subir es casi imposible.",
         fog=(90, 20, 160, 55), spore=(200, 80, 255), glow=35),
]

# Escalado de bichos por capa (hp y dano x esto, salvo jefes del pool)
LAYER_SCALE = [1.0, 1.1, 1.25, 1.45, 1.7, 2.0, 2.4, 2.9]


def layer_at(ty, world_h, surface_y=0, *args, **kwargs):
    """Indice de capa 0..7 para el tile (tx no importa, solo profundidad).

    surface_y: superficie de esa columna; por encima = capa 0.
    Conecta con: game.py (banner/efectos) y world.py (decorar fosa).
    """
    if ty < surface_y + 2:
        return 0
    d = ty / max(1, world_h)
    for i, bound in enumerate(LAYER_BOUNDS):
        if d < bound:
            return i + 1 if d >= 0.18 else 0
    return 7


def get_layer(idx, *args, **kwargs):
    """Ficha de la capa idx. Acepta extras para no romper llamadas."""
    return LAYERS[max(0, min(7, idx))]


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def blend_at(depth01, *args, **kwargs):
    """(tint, fog, dark) mezclados SUAVE entre capas vecinas.

    depth01 = ty/H del jugador. En una banda de +-0.035 alrededor de
    cada bound se interpola (smoothstep) entre la capa anterior y la
    siguiente: la transicion ya no es un corte seco de color.
    Solo visual: el gameplay (hambre, maldicion) sigue usando la capa
    discreta de layer_at().
    """
    d = max(0.0, min(1.0, depth01))
    lower, upper = 0, 0
    f = 0.0
    for i, bound in enumerate(LAYER_BOUNDS):
        if d < bound:
            lower, upper = i, i + 1
            f = _smooth((d - (bound - 0.035)) / 0.07)
            break
    else:
        lower, upper, f = 7, 7, 0.0
    if d < 0.18:
        return (0, 0, 0, 0), (0, 0, 0, 0), 0.0
    A, B = get_layer(lower), get_layer(upper)

    def _mix4(a, b):
        return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(4))

    dark = A["dark"] + (B["dark"] - A["dark"]) * f
    return _mix4(A["tint"], B["tint"]), _mix4(A["fog"], B["fog"]), dark


def near_abyss(world, tx, *args, margen=45, **kwargs):
    """True si el tile tx esta dentro del crater (+margen a cada lado).

    world necesita .abyss_x (los saves viejos no lo tienen: usa getattr).
    La boca es muy ancha (~76), asi que el margen cubre murallas y borde.
    """
    ax = getattr(world, "abyss_x", None)
    if ax is None:
        return False
    return abs(tx - ax) <= margen


def pick_enemy(layer_idx, rng=None, *args, **kwargs):
    """Bicho aleatorio del pool de la capa. Pesa el primero como comun."""
    rng = rng or random
    pool = get_layer(layer_idx)["pool"]
    return rng.choice(pool[0:1] * 2 + pool[1:])


def scale_for(layer_idx, *args, **kwargs):
    """Multiplicador hp/dano de la capa."""
    return LAYER_SCALE[max(0, min(7, layer_idx))]


def curse_for(layer_idx, *args, **kwargs):
    """(dano, segundos_debuff) de la Maldicion al ASCENDER desde esa capa."""
    L = get_layer(layer_idx)
    return L["curse_dmg"], 6 + layer_idx * 2
