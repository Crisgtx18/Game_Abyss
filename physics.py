"""Fisicas compartidas: colisiones AABB por ejes, salto con coyote time,
buffer de salto y altura variable. Unidades: pixeles y segundos.

Que hace:
    - Resolver colisiones contra la rejilla de tiles solidos del mundo.
    - Gravedad con caida maxima, friccion/aceleracion horizontal.
    - Salto "con perdon": coyote time (saltar justo tras salir del borde),
      jump buffer (pulsar un poco antes de tocar suelo) y salto variable
      (soltar la tecla = salto mas corto). Gravedad extra al caer para
      que el salto tenga peso y la caida no flote.

Con que conecta:
    - entities/player.py -> Player.update() usa move_and_collide(),
      update_jump() y apply_gravity(). Ahi se tocan los numeros del salto.
    - entities/mobs/enemies.py -> Enemy usa move_and_collide() y
      jump_velocity() con dt.
    - world.py -> aporta world.solid(tx, ty) (unico requisito del mundo).
    - config.py -> GRAVITY, GRAVITY_FALL, MAX_FALL, MOVE_SPEED, JUMP_VEL y
      COYOTE_TIME, JUMP_BUFFER, JUMP_CUT como valores por defecto.

Como tocarlo luego:
    Ajusta los numeros en config.py (COYOTE_TIME, JUMP_BUFFER...). Si quieres
    otra sensacion de movimiento, cambia approach() o los multiplicadores
    ground_accel / air_control al llamar a las funciones.

Uso *args/**kwargs:
    Todas las funciones aceptan *args/**kwargs extra para poder pasar
    banderas de depuracion o multiplicadores sin romper llamadas viejas.
"""
import math

from config import (TILE, GRAVITY, GRAVITY_FALL, MAX_FALL, JUMP_VEL,
                    COYOTE_TIME, JUMP_BUFFER, JUMP_CUT)

# Maximo desplazamiento por sub-paso de colision (evita atravesar tiles
# finos al caer rapido con dt grandes).
_MAX_STEP = 8.0


# ------------------------------------------------------------- cinematica 1D
def approach(value, target, delta, *args, **kwargs):
    """Mueve value hacia target como maximo delta (friccion/aceleracion).

    Ej: approach(vx, 0, friction*dt) para frenar, o
    approach(vx, speed, accel*dt) para arrancar. *args/**kwargs se ignoran.
    """
    if value < target:
        return min(target, value + delta)
    if value > target:
        return max(target, value - delta)
    return target


def apply_gravity(vy, dt, *args, gravity=GRAVITY, fall_gravity=GRAVITY_FALL,
                  max_fall=MAX_FALL, mult=1.0, **kwargs):
    """Suma gravedad a vy con tope de caida.

    Usa gravedad suave al subir y mas fuerte al caer (salto con peso,
    la caida ya no flota). mult permite caer mas rapido (p. ej. mantener
    abajo pulsado). Soporta la firma vieja apply_gravity(vy, dt, mult=..).
    """
    g = fall_gravity if vy > 0 else gravity
    # Si se mantiene "abajo", caer aun mas rapido (caida dirigida).
    if kwargs.get("fast_fall") and vy > 0:
        mult = max(mult, 1.6)
    return min(max_fall * mult, vy + g * dt * mult)


def jump_velocity(*args, base=JUMP_VEL, mult=1.0, **kwargs):
    """Velocidad inicial de salto. mult>1 salta mas alto (slimes, botas...)."""
    return base * mult


def variable_jump_cut(vy, jump_held, *args, cut=JUMP_CUT, **kwargs):
    """Salto de altura variable: si se SUELTA pronto, el salto queda corto.

    Llamalo cada frame con jump_held=True/False. Mientras no se sujete,
    la velocidad de subida se limita a JUMP_VEL*cut (tope estable, no
    depende de los FPS): pulsacion larga = salto completo, toquecito
    = saltito de ~1 tile. cut se lee de config.JUMP_CUT (0.55).
    """
    if not jump_held and vy < 0:
        ceiling = jump_velocity() * cut  # p. ej. -720*0.55 = -396
        if vy < ceiling:
            return ceiling
    return vy


# ------------------------------------------------------- estado de salto
class JumpState:
    """Guarda coyote_time y buffer para una entidad.

    Uso tipico (ver Player.update):
        js.update(dt, on_ground, jump_pressed)
        if js.consume_jump(): vy = jump_velocity()
    """

    def __init__(self, *args, coyote=COYOTE_TIME, buffer=JUMP_BUFFER, **kwargs):
        self.coyote_max = coyote
        self.buffer_max = buffer
        self.coyote = 0.0
        self.buffer = 0.0

    def update(self, dt, on_ground, jump_pressed, *args, **kwargs):
        """Refresca temporizadores. jump_pressed = flanco (pulsado este frame)."""
        if on_ground:
            self.coyote = self.coyote_max
        else:
            self.coyote = max(0.0, self.coyote - dt)
        if jump_pressed:
            self.buffer = self.buffer_max
        else:
            self.buffer = max(0.0, self.buffer - dt)

    def consume_jump(self, *args, **kwargs):
        """True si hay salto pendiente (buffer + coyote/suelo). Lo gasta."""
        if self.buffer > 0 and self.coyote > 0:
            self.buffer = 0.0
            self.coyote = 0.0
            return True
        return False


# ------------------------------------------------------------- colisiones
def _iter_overlapping_tiles(rect):
    """Tiles (tx,ty) que solapan un pygame.Rect. Funcion interna.

    Usa un epsilon (no -1px) para no tragar el tile vecino al estar
    perfectamente alineado, pero SI detectar penetraciones sub-pixel
    (la gravedad mueve <1px/frame al estar de pie).
    """
    eps = 1e-4
    x0 = int(math.floor(rect.left / TILE))
    x1 = int(math.floor((rect.right - eps) / TILE))
    y0 = int(math.floor(rect.top / TILE))
    y1 = int(math.floor((rect.bottom - eps) / TILE))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            yield tx, ty


def move_axis_collide(entity, world, axis, *args, dt=None, **kwargs):
    """Mueve la entidad en UN eje y resuelve choques con tiles solidos.

    entity: objeto con x,y,w,h,vx,vy,on_ground (Player o Enemy).
    axis: "x" o "y". Devuelve True si choco. **kwargs: hit_* callbacks
    futuros (on_hit_wall(entity, tile)...). No rompe llamadas viejas.

    OJO: vx/vy estan en px/s y se integran con dt. Si dt es None se usa
    1/60 para llamadas viejas. El desplazamiento se trocea en pasos de
    como maximo _MAX_STEP px para no atravesar tiles al caer rapido.
    """
    import pygame
    if dt is None:
        dt = kwargs.get("dt", 1.0 / 60.0)
    dt = min(max(dt, 0.0), 0.05)
    hit = False
    if axis == "x":
        dist = entity.vx * dt
        steps = max(1, int(math.ceil(abs(dist) / _MAX_STEP)))
        for _ in range(steps):
            entity.x += dist / steps
            r = entity.rect()
            for tx, ty in _iter_overlapping_tiles(r):
                if world.solid(tx, ty):
                    t = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if dist > 0:
                            entity.x = t.left - entity.w
                        elif dist < 0:
                            entity.x = t.left + TILE
                        else:
                            continue
                        entity.vx = 0
                        hit = True
                        r = entity.rect()
                        break
            if hit:
                break
    else:
        dist = entity.vy * dt
        steps = max(1, int(math.ceil(abs(dist) / _MAX_STEP)))
        landed = False
        for _ in range(steps):
            entity.y += dist / steps
            r = entity.rect()
            for tx, ty in _iter_overlapping_tiles(r):
                if world.solid(tx, ty):
                    t = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                    if r.colliderect(t):
                        if dist > 0:
                            entity.y = t.top - entity.h
                            entity.vy = 0
                            landed = True
                        elif dist < 0:
                            entity.y = t.top + TILE
                            entity.vy = 0
                        else:
                            continue
                        hit = True
                        r = entity.rect()
                        break
            if hit and landed:
                break
        if landed:
            entity.on_ground = True
        elif dist > 0 and hit:
            entity.on_ground = True
        elif entity.vy == 0 and dist == 0:
            # Quieto: comprobar apoyo con una sonda de 1px (no perder suelo).
            entity.on_ground = standing_on(entity, world)
        else:
            entity.on_ground = False
    cb = kwargs.get("on_collide")
    if hit and callable(cb):
        cb(entity, axis)
    return hit


def move_and_collide(entity, world, *args, dt=None, order=("x", "y"), **kwargs):
    """Mueve en X y luego en Y resolviendo colisiones (estanndar plataformas).

    Devuelve dict {"hit_x": bool, "hit_y": bool, "ground": bool}.
    order permite invertir el orden en casos raros. **kwargs se reenvia a
    move_axis_collide (ej. on_collide=...).
    """
    if dt is None:
        dt = kwargs.get("dt", 1.0 / 60.0)
    hit_x = hit_y = False
    for axis in order:
        hit = move_axis_collide(entity, world, axis, *args, dt=dt, **kwargs)
        if axis == "x":
            hit_x = hit
        else:
            hit_y = hit
    return {"hit_x": hit_x, "hit_y": hit_y, "ground": entity.on_ground}


def standing_on(entity, world, *args, extra=2, **kwargs):
    """True si hay suelo solido justo debajo (para IA que decide saltar)."""
    import pygame
    r = pygame.Rect(int(entity.x), int(entity.y), entity.w, entity.h + extra)
    x0 = int(math.floor(r.left / TILE))
    x1 = int(math.floor((r.right - 1e-4) / TILE))
    ty = int(math.floor((r.bottom - 1e-4) / TILE))
    for tx in range(x0, x1 + 1):
        if world.solid(tx, ty):
            return True
    return False


def wall_ahead(entity, world, direction, *args, **kwargs):
    """True si hay pared en la direccion de marcha (para IA que salta muros)."""
    front = entity.x + (entity.w + 2 if direction > 0 else -2)
    ty = int(math.floor((entity.y + entity.h - 6) / TILE))
    tx = int(math.floor(front / TILE))
    return world.solid(tx, ty)
