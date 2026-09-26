# Kael el Explorador - jugador estilo Terraria
# Hambre/estilo Starbound: el hambre baja con el tiempo (x2 en el Abismo),
# a 0 hace dano; lleno (>80) regenera. La comida se usa con click derecho.
import pygame
from config import (TILE, MOVE_SPEED, SPRINT_MULT, GROUND_ACCEL, AIR_ACCEL,
                    GROUND_FRICTION, AIR_FRICTION, MAX_FALL,
                    WALL_SLIDE_SPEED, WALL_JUMP_X, WALL_JUMP_Y,
                    HUNGER_TIME, STARVE_DPS)
from blocks import BLOCKS
from items import ITEMS
import physics
from physics import JumpState


class Player:
    def __init__(self, x, y):
        # Tamano ajustado a TILE=6: ~1.0 x 2.0 tiles (como Terraria).
        self.w, self.h = 6, 12
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.max_hp = 100
        self.hp = 100
        self.max_mana = 50
        self.mana = 50
        self.max_hunger = 100
        self.hunger = 100       # 0 = famelico (dano), >80 = saciado (regen)
        self.meals_eaten = 0    # cuenta para la mision q_dieta (quests.py)
        self.iframes = 0.0
        self.attack_cd = 0.0
        self.potion_cd = 0.0
        self.dead = False
        self.buffs = {}  # nombre -> tiempo restante
        self.mine_target = None
        self.mine_progress = 0.0
        self.walk_anim = 0.0
        self.inventory = None  # se asigna desde game.py
        # --- animacion de ataque (espada girando, ver melee_attack) ---
        self.attack_anim = 0.0   # tiempo restante del tajo visible
        self.attack_dur = 0.25   # duracion total del tajo
        self.attack_kind = None  # 'espada' | 'herramienta' | 'puno'
        self.attack_id = None    # id del item blandido (color por tier)
        # --- salto con perdon (coyote + buffer + altura variable) ---
        self.jump = JumpState()
        self._prev_jump_down = False  # para detectar el flanco de salto
        self.jump_held = False
        self.was_ground = True
        self.fall_time = 0.0     # tiempo cayendo (para animar la caida)
        self.land_t = 0.0        # squash al aterrizar
        self.jump_t = 0.0        # tiempo desde que despego (anim salto)
        self.state = "idle"      # idle | run | jump | fall | slide (para sprites)
        # --- movimiento avanzado (game.py los lee para particulas) ---
        self.sprinting = False   # Shift + moverse en suelo
        self.skidding = False    # derrape al invertir direccion rapido
        self.sliding = False     # wall-slide pegado a la pared
        self.slide_dir = 0       # hacia que pared desliza (-1/1)
        self.step_t = 0.0        # temporizador de polvo al correr
        self.want_step_dust = False  # game.py lo consume y genera polvo
        self.want_land_dust = 0.0    # fuerza del aterrizaje (>0 = polvo)
        self.coyote_t = 0.0      # para inclinar el sprite al borde
        self.name = "Kael"
        self.appearance = {"skin": 0, "hair": 0, "eye": 0}

    @property
    def defense(self):
        base = self.inventory.total_defense() if self.inventory else 0
        if self.buffs.get("iron_skin", 0) > 0:
            base += 8
        if self.buffs.get("maldicion", 0) > 0:
            base -= 4  # la Maldicion debilita (Made in Abyss)
        return max(0, base)

    @property
    def speed_mult(self):
        m = 1.4 if self.buffs.get("speed", 0) > 0 else 1.0
        if self.buffs.get("espora", 0) > 0:
            m *= 0.9    # esporas capa 2
        if self.buffs.get("maldicion", 0) > 0:
            m *= 0.8    # maldicion: pesadez
        if self.buffs.get("indigestion", 0) > 0:
            m *= 0.85   # carne cruda...
        if self.hunger <= 0:
            m *= 0.85   # famelico
        return m

    def eat(self, food_id, *args, **kwargs):
        """Come comida del inventario. Devuelve (ok, mensaje).

        Conecta con: game.py (click derecho) que luego registra el evento
        'eat' en quests.py. La carne cruda puede dar indigestion.
        """
        import random
        info = ITEMS.get(food_id, {})
        if info.get("tipo") != "comida":
            return False, "No es comida."
        if self.hunger >= self.max_hunger and not info.get("heal"):
            return False, "Estas lleno."
        if not self.inventory or not self.inventory.has(food_id):
            return False, "No tienes."
        self.inventory.remove(food_id, 1)
        self.hunger = min(self.max_hunger, self.hunger + info.get("hunger", 10))
        if info.get("heal"):
            self.heal(info["heal"])
        for b in info.get("cure", []):
            self.buffs.pop(b, None)
        msg = f"Comiste {info['name']}."
        if food_id == "carne_cruda" and random.random() < 0.3:
            self.buffs["indigestion"] = 10.0
            msg += " Te cayo mal... (cocinala al horno)"
        self.meals_eaten += 1
        return True, msg

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    # ---------- colisiones ----------
    def _collide(self, world, dt):
        # Delegar en el motor compartido (sub-pasos + sonda de suelo).
        physics.move_and_collide(self, world, dt=dt)

    def queue_jump(self, *args, **kwargs):
        """Fuerza un salto en el proximo update (para eventos KEYDOWN)."""
        self.jump.buffer = self.jump.buffer_max

    def update(self, keys, world, dt, hunger_mult=1.0, *args,
               jump_pressed=None, jump_held=None, **kwargs):
        """Fisicas + hambre. hunger_mult lo da game.py segun la capa del
        Abismo (x2 en Copas...). *args/**kwargs para futuras banderas.

        Salto: coyote time + buffer + altura variable + caida con peso.
        jump_pressed (flanco) y jump_held se detectan solos desde `keys`
        si no se pasan (ESPACIO/W/UP). dt en segundos.
        """
        if self.dead:
            return
        dt = min(max(dt, 0.0), 0.05)
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        sprint_key = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if jump_held is None:
            jump_held = bool(keys[pygame.K_SPACE] or keys[pygame.K_w]
                             or keys[pygame.K_UP])
        if jump_pressed is None:
            jump_pressed = jump_held and not self._prev_jump_down
        self._prev_jump_down = bool(jump_held)
        self.jump_held = bool(jump_held)
        self.want_step_dust = False

        # --- sprint: Shift + direccion en suelo (polvo extra, anim mas rapida) ---
        moving = bool(left) != bool(right)
        self.sprinting = bool(sprint_key and moving and self.on_ground
                              and self.hunger > 0)
        # --- horizontal: aceleracion distinta en suelo/aire + friccion ---
        # en el apice del salto hay mas control (estrial) para no flotar.
        speed = MOVE_SPEED * self.speed_mult * (SPRINT_MULT if self.sprinting else 1.0)
        if left and not right:
            self.facing = -1
            # derrape: iba rapido a la derecha y gira de golpe
            self.skidding = bool(self.on_ground and self.vx > 70)
            if abs(self.vy) < 60 and not self.on_ground:
                accel = GROUND_ACCEL  # control extra en el apice
            else:
                accel = GROUND_ACCEL if self.on_ground else AIR_ACCEL
            self.vx = physics.approach(self.vx, -speed, accel * dt)
        elif right and not left:
            self.facing = 1
            self.skidding = bool(self.on_ground and self.vx < -70)
            if abs(self.vy) < 60 and not self.on_ground:
                accel = GROUND_ACCEL
            else:
                accel = GROUND_ACCEL if self.on_ground else AIR_ACCEL
            self.vx = physics.approach(self.vx, speed, accel * dt)
        else:
            self.skidding = False
            fric = GROUND_FRICTION if self.on_ground else AIR_FRICTION
            self.vx = physics.approach(self.vx, 0.0, fric * dt)
            if abs(self.vx) < 2:
                self.vx = 0.0

        # anim de carrera: mas rapida en sprint (12 vs 10)
        if abs(self.vx) > 10 and self.on_ground:
            self.walk_anim += dt * (13 if self.sprinting else 10)
            # polvo de pasos a ritmo constante
            self.step_t += dt * abs(self.vx) / 100.0
            if self.step_t > 0.22:
                self.step_t = 0.0
                self.want_step_dust = True
        else:
            self.step_t = 0.0
        if self.skidding and abs(self.vx) > 30:
            self.want_step_dust = True

        # --- salto con perdon ---
        self.jump.update(dt, self.on_ground, jump_pressed)
        # wall-slide: en el aire, cayendo, empujando hacia la pared
        self.sliding = False
        self.slide_dir = 0
        if not self.on_ground and self.vy > 0:
            push = (-1 if left else (1 if right else 0))
            if push != 0 and physics.wall_ahead(self, world, push):
                self.sliding = True
                self.slide_dir = push
                self.facing = -push  # mira hacia fuera de la pared
                if self.vy > WALL_SLIDE_SPEED:
                    self.vy = WALL_SLIDE_SPEED
                self.fall_time = 0.0  # no parece caida libre
        if self.jump.consume_jump():
            self.vy = physics.jump_velocity()
            self.on_ground = False
            self.sliding = False
            self.jump_t = 0.0
            self.fall_time = 0.0
        elif jump_pressed and self.sliding:
            # wall-jump: impulso hacia fuera + arriba
            self.vx = -self.slide_dir * WALL_JUMP_X
            self.vy = WALL_JUMP_Y
            self.facing = -self.slide_dir
            self.on_ground = False
            self.sliding = False
            self.jump_t = 0.0
            self.fall_time = 0.0
            self.jump.buffer = 0.0

        # --- gravedad: sube suave, cae con peso; abajo = caer picado ---
        self.vy = physics.apply_gravity(self.vy, dt, fast_fall=bool(down))
        # Altura variable: soltar pronto corta el salto.
        self.vy = physics.variable_jump_cut(self.vy, self.jump_held, dt=dt)
        self.vy = min(MAX_FALL, self.vy)

        was_ground = self.on_ground
        vy_before = self.vy
        self._collide(world, dt)

        # Aterrizaje: squash + reset de tiempos + polvo segun fuerza.
        if self.on_ground and not was_ground:
            self.land_t = 0.20 if vy_before > 225 else 0.14
            self.fall_time = 0.0
            # Polvo al caer fuerte.
            self._land_strength = max(0.0, vy_before)
            if vy_before > 125:
                self.want_land_dust = min(1.0, vy_before / 340.0)
        if not self.on_ground:
            self.jump_t += dt
            if self.vy > 0 and not self.sliding:
                self.fall_time += dt
        else:
            self.fall_time = 0.0
            self.sliding = False
        self.land_t = max(0.0, self.land_t - dt)
        self.was_ground = was_ground
        self.coyote_t = self.jump.coyote

        # Estado para los sprites (idle/run/jump/fall/slide).
        if self.sliding:
            self.state = "slide"
        elif not self.on_ground:
            self.state = "jump" if self.vy < 30 else "fall"
        else:
            self.state = "run" if abs(self.vx) > 10 else "idle"

        # fuera del mundo -> dano
        if self.y > world.h * TILE:
            self.take_damage(9999)
        # timers
        self.iframes = max(0, self.iframes - dt)
        self.attack_cd = max(0, self.attack_cd - dt)
        self.attack_anim = max(0, self.attack_anim - dt)
        self.potion_cd = max(0, self.potion_cd - dt)
        for k in list(self.buffs):
            self.buffs[k] -= dt
            if self.buffs[k] <= 0:
                del self.buffs[k]
        # regen buff + lenta natural + hambre
        if self.buffs.get("regen", 0) > 0:
            self.hp = min(self.max_hp, self.hp + 4 * dt)
        if self.hunger > 80:
            self.hp = min(self.max_hp, self.hp + 1.0 * dt)  # saciado
        self.hunger = max(0, self.hunger - 100.0 / HUNGER_TIME * hunger_mult * dt)
        if self.hunger <= 0 and not self.dead:
            self.hp -= STARVE_DPS * dt  # inanicion (ignora defensa)
            if self.hp <= 0:
                self.hp = 0
                self.dead = True
        self.mana = min(self.max_mana, self.mana + 3 * dt)

    def take_damage(self, amount, *args, ignore_iframes=False, **kwargs):
        if self.dead or (self.iframes > 0 and not ignore_iframes):
            return False
        real = max(1, int(amount - self.defense * 0.7))
        self.hp -= real
        self.iframes = 0.6
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
        return True

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def respawn(self, world):
        sx, sy = world.spawn
        self.x = sx * TILE
        self.y = sy * TILE
        self.vx = self.vy = 0
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.hunger = max(self.hunger, 60)  # renaces con algo en el estomago
        self.dead = False
        self.iframes = 2.0
        self.buffs.clear()
        self.jump = JumpState()
        self._prev_jump_down = False
        self.fall_time = 0.0
        self.land_t = 0.0
        self.state = "idle"
        self.sprinting = False
        self.skidding = False
        self.sliding = False
        self.want_step_dust = False
        self.want_land_dust = 0.0
        self.attack_anim = 0.0
        self.attack_kind = None
        self.attack_id = None

    # ---------- dibujo: delega en el sistema de sprites pixelart ----------
    def draw(self, surf, cam_x, cam_y):
        import textures
        held_id = None
        try:
            sel = self.inventory.selected_item() if self.inventory else None
            if sel:
                held_id = sel.get("id")
        except Exception:
            held_id = None
        textures.draw_player(
            surf, int(self.x - cam_x), int(self.y - cam_y),
            facing=self.facing, walk_phase=self.walk_anim,
            on_ground=self.on_ground, moving=abs(self.vx) > 10,
            armor=self.inventory.armor if self.inventory else (None, None, None),
            invulnerable=self.iframes if self.iframes > 0 else False,
            state=getattr(self, "state", "idle"),
            vy=self.vy, land_t=getattr(self, "land_t", 0.0),
            fall_time=getattr(self, "fall_time", 0.0),
            sprinting=getattr(self, "sprinting", False),
            skidding=getattr(self, "skidding", False),
            sliding=getattr(self, "sliding", False),
            held_id=held_id,
            attack_anim=getattr(self, "attack_anim", 0.0),
            attack_dur=getattr(self, "attack_dur", 0.25),
            attack_kind=getattr(self, "attack_kind", None),
            attack_id=getattr(self, "attack_id", None),
            appearance=getattr(self, "appearance", None),
        )
