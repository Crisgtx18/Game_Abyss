# Mobs inventados de UnderDown + bichos del Abismo (estilo Made in Abyss):
#  Moki verde/azul/rojo (slimes), Putrek (zombie), Karkas (esqueleto),
#  Vesper (murcielago), Rokthar (golem), Rey Mokulon (boss final),
#  Orbe rastrero, Sedaluz, Dientepiedra, Eco profundo, Heraldo (abismo).
# style: rama de dibujo en textures/draw (slime|walker|skeleton|bat|golem|king)
import random
import pygame
import physics
from config import TILE, GRAVITY, GRAVITY_FALL, MAX_FALL


# stats: hp, damage, speed, jump, coins, drops
MOB_STATS = {
    "moki_verde":  dict(name="Moki verde",  hp=30,  dmg=8,  speed=2.0, knock=4, coins=(1, 4),   drops=[("gel", 1, 3)], style="slime"),
    "moki_azul":   dict(name="Moki azul",   hp=55,  dmg=12, speed=2.2, knock=4, coins=(2, 6),   drops=[("gel", 2, 4)], style="slime"),
    "moki_rojo":   dict(name="Moki rojo",   hp=80,  dmg=16, speed=2.6, knock=5, coins=(3, 8),   drops=[("gel", 3, 5)], style="slime"),
    "putrek":      dict(name="Putrek",      hp=70,  dmg=15, speed=2.4, knock=5, coins=(3, 9),   drops=[("gel", 1, 2), ("palo", 1, 2), ("carne_cruda", 1, 2)], style="walker"),
    "karkas":      dict(name="Karkas",      hp=90,  dmg=18, speed=2.8, knock=5, coins=(4, 10),  drops=[("hueso", 0, 0), ("antorcha", 1, 3)], style="skeleton"),
    "vesper":      dict(name="Vesper",      hp=50,  dmg=14, speed=3.2, knock=3, coins=(3, 8),   drops=[("gel", 1, 2), ("carne_cruda", 1, 1)], style="bat"),
    "rokthar":     dict(name="Rokthar",     hp=220, dmg=28, speed=1.6, knock=8, coins=(10, 25), drops=[("piedra", 5, 12), ("hierro_crudo", 1, 4)], style="golem"),
    "rey_mokulon": dict(name="REY MOKULON", hp=900, dmg=35, speed=3.0, knock=10, coins=(100, 200), drops=[("diamante", 5, 10), ("moneda_oro", 5, 10), ("pocion_vida_mayor", 2, 4)], style="king"),
    "mini_moki":   dict(name="Mini Moki",   hp=20,  dmg=8,  speed=3.0, knock=3, coins=(0, 2),   drops=[("gel", 1, 2)], style="slime"),
    # ---- Abismo (capas 1-7, ver abyss.py) ----
    "orbe_rastrero": dict(name="Orbe rastrero", hp=60, dmg=14, speed=2.4, knock=4, coins=(2, 6), drops=[("gel", 2, 4), ("carne_cruda", 1, 2)], style="slime"),
    "sedaluz":     dict(name="Sedaluz",     hp=70,  dmg=16, speed=3.4, knock=3, coins=(3, 8),   drops=[("gel", 1, 3), ("baya_luminosa", 1, 3)], style="bat"),
    "dientepiedra":dict(name="Dientepiedra", hp=160, dmg=24, speed=2.0, knock=7, coins=(6, 14), drops=[("carne_cruda", 2, 4), ("piedra", 3, 8), ("hierro_crudo", 1, 3)], style="golem"),
    "eco_profundo":dict(name="Eco profundo", hp=200, dmg=30, speed=3.0, knock=6, coins=(8, 18), drops=[("carne_cruda", 2, 3), ("oro_crudo", 1, 2), ("baya_luminosa", 1, 2)], style="skeleton"),
    "heraldo_abismo":dict(name="HERALDO DEL ABISMO", hp=650, dmg=40, speed=3.2, knock=10, coins=(60, 120), drops=[("reliquia_orbe", 1, 1), ("diamante", 2, 5), ("pocion_vida_mayor", 1, 2)], style="king"),
}

COLORS = {
    "moki_verde": (60, 200, 80), "moki_azul": (70, 140, 255),
    "moki_rojo": (230, 70, 70), "putrek": (90, 140, 70),
    "karkas": (210, 210, 210), "vesper": (120, 80, 160),
    "rokthar": (130, 130, 145), "rey_mokulon": (150, 60, 220),
    "mini_moki": (100, 220, 120),
    "orbe_rastrero": (40, 90, 70), "sedaluz": (120, 220, 255),
    "dientepiedra": (110, 95, 80), "eco_profundo": (70, 60, 120),
    "heraldo_abismo": (180, 30, 90),
}


class Enemy:
    _id = 0

    def __init__(self, kind, x, y):
        s = MOB_STATS[kind]
        Enemy._id += 1
        self.id = Enemy._id
        self.kind = kind
        self.name = s["name"]
        self.max_hp = s["hp"]
        self.hp = s["hp"]
        self.dmg = s["dmg"]
        self.speed = s["speed"]
        self.knock = s["knock"]
        self.style = s.get("style", "slime")  # rama de dibujo e IA (ver abyss)
        size = 12 if kind == "rey_mokulon" else (10 if kind == "heraldo_abismo"
                else (9 if kind in ("rokthar", "dientepiedra") else 7))
        self.w = self.h = size
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.kvx = 0.0  # knockback horizontal aparte (no lo pisa la IA)
        self.on_ground = False
        self.dir = random.choice([-1, 1])
        self.hop_cd = random.uniform(0.3, 1.2)
        self.iframes = 0.0
        self.hit_t = 0.0  # flash blanco al recibir dano (ver draw)
        self.anim = random.random() * 10
        self.fly = kind == "vesper"
        self.summon_cd = 4.0
        self.dead = False
        self.fell_out = False  # cayo fuera del mundo: muere sin loot
        self.hit_wall = False  # toco pared este frame (para rebotar)
        self.wander_t = random.uniform(1.0, 3.0)  # deambular fuera de aggro
        self.dive_cd = 0.0  # murcielagos: picado tras pasar de largo

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def take_damage(self, amount, knock_x=0):
        if self.iframes > 0:
            return False
        self.hp -= int(amount)
        self.kvx += knock_x
        self.iframes = 0.15
        self.hit_t = 0.18  # parpadeo blanco de impacto
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
        return True

    # --- colisiones (motor compartido, dt-correcto, sin tuneles) ---
    def _move_collide(self, world, dt=1.0 / 60.0):
        # El knockback se suma solo durante el movimiento (la IA no lo pisa).
        self.vx += self.kvx
        res = physics.move_and_collide(self, world, dt=dt)
        self.vx -= self.kvx
        if res["hit_x"]:
            self.kvx = 0.0  # choco contra un muro: pierde el empujon
            self.hit_wall = True
        else:
            self.hit_wall = False

    def update(self, world, player, dt, spawned_minis=None):
        """IA por estilos con aggro por distancia:
        - slime: salta hacia ti en rango; fuera, saltitos errantes.
        - walker/golem/skeleton: patrulla fuera de rango, persigue dentro
          (carga de cerca) y salta muros.
        - bat: orbita y hace picados (swoop) al acercarse.
        - jefes: enfurecen bajo el 30% (mas rapidos, saltos mas altos).
        """
        import math
        dt = min(max(dt, 0.0), 0.05)
        self.anim += dt * 6
        self.iframes = max(0, self.iframes - dt)
        self.hit_t = max(0, self.hit_t - dt)
        self.kvx = physics.approach(self.kvx, 0.0, 750 * dt)
        self.dive_cd = max(0.0, self.dive_cd - dt)
        px, py = player.center()
        cx, cy = self.center()
        dx = px - cx
        dy = py - cy
        dist = math.hypot(dx, dy)
        boss = self.kind in ("rey_mokulon", "heraldo_abismo")
        enraged = boss and self.hp < self.max_hp * 0.3
        rage = 1.35 if enraged else 1.0
        # --- IA por tipo ---
        if self.kind in ("moki_verde", "moki_azul", "moki_rojo", "mini_moki", "rey_mokulon",
                         "orbe_rastrero", "heraldo_abismo"):
            # slimes y bichos rastreros: saltan hacia el jugador en rango
            aggro = 400 if boss else 150
            self.hop_cd -= dt
            if self.on_ground:
                # en suelo frena; en el aire conserva el impulso del salto
                self.vx = physics.approach(self.vx, 0.0, 450 * dt)
            if self.on_ground and self.hop_cd <= 0:
                if dist < aggro and not player.dead:
                    self.dir = 1 if dx > 0 else -1
                    close = 1.3 if dist < 70 else 1.0  # mordisco de cerca
                    spd = self.speed * (1.6 if boss else 1.0) * close * rage
                    # speed era px/frame clasico -> px/s constante
                    self.vx = self.dir * spd * 30.0
                    self.vy = physics.jump_velocity(mult=(1.25 if boss else 1.0) * rage)
                    if not boss:
                        self.vy = max(self.vy, -280.0)
                else:
                    # deambular: saltito errante sin gastar persecucion
                    self.wander_t -= dt
                    if self.wander_t <= 0:
                        self.wander_t = random.uniform(1.5, 3.5)
                        self.dir = random.choice([-1, 1])
                    self.vx = self.dir * self.speed * 12.0
                    self.vy = physics.jump_velocity(mult=0.7)
                self.hop_cd = random.uniform(0.5, 1.4) / rage
            if not self.fly:
                self.vy = physics.apply_gravity(self.vy, dt)
            self._move_collide(world, dt)
            if getattr(self, "hit_wall", False):
                self.dir *= -1  # rebota y prueba por el otro lado
            # jefes invocan crias
            if boss and spawned_minis is not None:
                self.summon_cd -= dt
                if self.summon_cd <= 0:
                    self.summon_cd = 6.0 / rage
                    cria = "mini_moki" if self.kind == "rey_mokulon" else "orbe_rastrero"
                    for _ in range(2):
                        spawned_minis.append(Enemy(cria, self.x + random.randint(-20, 20), self.y - 10))
        elif self.kind in ("vesper", "sedaluz"):
            # murcielago: orbita al jugador y pica (swoop) al estar encima
            aggro = 250
            if dist < aggro and not player.dead:
                if dist < 70 and self.dive_cd <= 0:
                    # picado: se lanza sobre ti y luego remonta
                    self.vx = (dx / max(1, dist)) * self.speed * 55.0
                    self.vy = (dy / max(1, dist)) * self.speed * 55.0
                    self.dive_cd = 1.2
                else:
                    # orbita con ondas
                    self.vx += ((1 if dx > 0 else -1) * self.speed * 27.5 - self.vx) * min(1, dt * 3)
                    target_vy = -20.0 + math.sin(self.anim * 0.8) * 45.0
                    target_vy += 15.0 if py > cy else -15.0
                    self.vy += (target_vy - self.vy) * min(1, dt * 3)
            else:
                # fuera de rango: patrulla en ondas suaves
                self.dir = 1 if self.anim % 8 < 4 else -1
                cruise = self.speed * 14.0
                self.vx += (self.dir * cruise - self.vx) * min(1, dt * 2)
                self.vy += ((-20.0 + math.sin(self.anim * 0.8) * 45.0) - self.vy) * min(1, dt * 2)
            self.x += (self.vx + self.kvx) * dt
            self.y += self.vy * dt
        else:
            # zombies / esqueletos / golem: patrullan, persiguen y cargan
            aggro = 200 if self.kind in ("rokthar", "dientepiedra") else 170
            charging = dist < 60 and not player.dead
            if dist < aggro and not player.dead:
                self.dir = 1 if dx > 0 else -1
                # speed era px/frame clasico -> px/s constante
                self.vx = self.dir * self.speed * (42.0 if charging else 30.0)
            else:
                self.wander_t -= dt
                if self.wander_t <= 0:
                    self.wander_t = random.uniform(2.0, 4.0)
                    self.dir = random.choice([-1, 1])
                self.vx = self.dir * self.speed * 12.0
            self.vy = physics.apply_gravity(self.vy, dt)
            # saltar si hay pared
            ahead_x = int((self.x + (self.w if self.dir > 0 else -2)) // TILE)
            ahead_y = int((self.y + self.h - 3) // TILE)
            if world.solid(ahead_x, ahead_y) and self.on_ground:
                self.vy = physics.jump_velocity(mult=1.1)
            self._move_collide(world, dt)
        # caido fuera del mundo: muere sin loot (no se acumula en el vacio)
        if self.y > world.h * TILE + 40:
            self.dead = True
            self.fell_out = True

    def roll_drops(self):
        rng = random.Random()
        s = MOB_STATS[self.kind]
        out = []
        for item, a, b in s["drops"]:
            if b <= 0:
                continue
            n = rng.randint(a, b)
            if n > 0:
                out.append((item, n))
        c = rng.randint(*s["coins"])
        if c > 0:
            out.append(("moneda_cobre", c))
        # corazones ocasionales
        if rng.random() < 0.25:
            out.append(("corazon", 1))
        return out

    def draw(self, surf, cam_x, cam_y):
        import textures
        x, y = int(self.x - cam_x), int(self.y - cam_y)
        if x < -40 or y < -40 or x > surf.get_width() + 40 or y > surf.get_height() + 40:
            return
        if self.iframes > 0 and int(self.anim * 8) % 2 == 0:
            pass  # sigue dibujando pero podria parpadear
        w, h = self.w, self.h
        textures.draw_enemy(surf, self.kind, x, y, w, h,
                            anim=self.anim, facing=self.dir,
                            flash=self.hit_t > 0)
        # barra de vida
        if self.hp < self.max_hp:
            pct = self.hp / self.max_hp
            pygame.draw.rect(surf, (60, 0, 0), (x, y - 4, w, 3))
            pygame.draw.rect(surf, (220, 40, 40), (x, y - 4, w * pct, 3))
