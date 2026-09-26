# Motor principal del juego Mokulandia (Terraria-like 2D)
import json
import math
import os
import random
from collections import OrderedDict
import pygame

from config import (SCREEN_W, SCREEN_H, FPS, TILE, WORLD_W, WORLD_H,
                    DAY_LENGTH, RESPAWN_TIME, REACH_DIST, PLAYER_SPAWN_ITEMS,
                    SKY_DAY, SKY_NIGHT, HUNGER_TIME,
                    RESOLUTIONS, SKIN_COLORS, HAIR_COLORS, EYE_COLORS)
from blocks import BLOCKS, ITEM_TO_BLOCK
from items import ITEMS, ORE_REQUIRE
from inventory import Inventory
from world import World
from entities.player import Player
from entities.mobs.enemies import Enemy
from entities.npc import NPC
import ui
import crafting
import abyss
import textures as _tx
from quests import QuestState, QUESTS
from audio import Audio

SAVE_DIR = "saves"
WORLD_SAVE = os.path.join(SAVE_DIR, "mundo.json")
PLAYER_SAVE = os.path.join(SAVE_DIR, "jugador.json")

# Sets precalculados para el render en un pase (evitan dict.get por tile).
_SOLID_IDS = frozenset(b for b, v in BLOCKS.items() if v.get("solid"))
_BG_IDS = frozenset(b for b, v in BLOCKS.items() if v.get("background"))
_GLOW_IDS = frozenset((14, 19, 25, 29))  # antorcha, flor, seta, farol


class GroundItem:
    def __init__(self, item_id, count, x, y):
        self.id = item_id
        self.count = count
        self.x, self.y = float(x), float(y)
        self.vx = random.uniform(-60, 60)
        self.vy = random.uniform(-190, -70)
        self.t = 0.0


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        # Cargar ajustes guardados
        self.settings = self._load_settings()
        self.res_idx = self.settings["res_idx"]
        self.fullscreen = self.settings["fullscreen"]
        self._apply_settings()
        pygame.display.set_caption("Mokulandia - Terraria 2D")
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.state = "menu"   # menu | help | play | settings | char_create | confirm
        self.menu_sel = 0
        self.pause_sel = 0
        self.paused = False
        self.inv_open = False
        self.craft_open = False
        self.craft_scroll = 0
        self.held = None      # item en el cursor (drag inventario)
        self.msg = ""
        self.msg_t = 0.0
        self.tile_cache = {}
        self.particles = []
        self.world = None
        self.player = None
        self.enemies = []
        self.drops = []
        self.npc = None
        self.boss = None
        self.spawn_cd = 2.0
        self.dead_t = 0.0
        self.cam_x = self.cam_y = 0.0
        # Abismo + misiones + hambre/HUD
        self.quests = QuestState()
        self.quest_open = False
        self.cur_layer = 0
        self.layer_banner_t = 0.0
        self.npc2 = None      # Bruno el Vigia (borde del Abismo)
        self.npcs = []        # [Liora, Bruno]
        # Fondo por bioma con transicion suave (ver draw_background)
        self.bg_cur = "pradera"   # bioma mostrado (mezclado)
        self.bg_from = None       # bioma origen de la transicion
        self.bg_to = None         # bioma destino
        self.bg_t = 1.0           # 0..1 (1 = sin transicion)
        self.bg_mix = None        # colores mezclados actuales (cache)
        self._auto_cache = {}     # (tx,ty) -> (bid, exp, seam) autotile
        # Zoom de vista con - / = (1.0 = normal). Se aplica reescalando la
        # escena con NEAREST (pixel intacto) y mapeando el raton al mundo.
        self.zoom = 0.75  # zoom inicial mas alejado para ver mas mundo
        self.ZOOM_MIN = 0.35
        self.ZOOM_MAX = 2.5
        # Ajustes
        self.settings_sel = 0
        self.settings_return = "menu"  # a donde vuelve ESC/VOLVER: menu | play
        self.res_idx = self.settings["res_idx"]
        self.fullscreen = self.settings["fullscreen"]
        # Creacion de personaje
        self.char_sel = 0
        self.char_name = "Kael"
        self.char_skin = self.settings.get("skin_idx", 0)
        self.char_hair = self.settings.get("hair_idx", 0)
        self.char_eye = self.settings.get("eye_idx", 0)
        self.char_name_editing = False
        self.char_name_cursor = len("Kael")
        self.char_rects = {}
        # Pantalla de carga (nueva partida)
        self._loading_frac = 0.0
        self._loading_label = ""
        # Cache LRU de chunks horneados (ver _get_chunk)
        self._chunks = OrderedDict()
        # Confirmacion
        self.confirm_sel = 0
        self.confirm_text = ""
        self.confirm_yes = None  # callback si SE
        self.confirm_no = None   # callback si NO
        # Menu: 4 opciones si hay save, 3 si no
        self._menu_opts = 4 if self.has_save() else 3

    # ============ helpers ============
    def say(self, text, t=3.0):
        self.msg = text
        self.msg_t = t

    def new_world(self, progress=None):
        self.world = World(WORLD_W, WORLD_H)
        self.world.generate(progress=progress)
        sx, sy = self.world.spawn
        self.player = Player(sx * TILE, sy * TILE)
        self.player.inventory = Inventory()
        for iid, c in PLAYER_SPAWN_ITEMS:
            self.player.inventory.add(iid, c)
        self.after_world_load()

    def after_world_load(self):
        # Liora junto al spawn + Bruno al borde del Abismo
        sx, sy = self.world.spawn
        gy = self.world.find_ground(sx, sy)
        self.npc = NPC(sx * TILE, (gy + 1) * TILE - 13)
        ax = getattr(self.world, "abyss_x", sx + 80)
        atop = getattr(self.world, "abyss_top", gy)
        bx = max(3, min(self.world.w - 4, ax + 40))
        gy2 = self.world.find_ground(bx, max(2, atop - 4))
        self.npc2 = NPC(bx * TILE, (gy2 + 1) * TILE - 13, name="Bruno",
                        giver="bruno", tunic=(70, 110, 70), cap=(160, 40, 40))
        self.npcs = [self.npc, self.npc2]
        self.enemies = []
        self.drops = []
        self.boss = None
        self.particles = []
        self.cur_layer = 0
        self.bg_cur = "pradera"
        self.bg_from = None
        self.bg_to = None
        self.bg_t = 1.0
        self._auto_cache = {}
        self.tile_cache = {}
        self._wall_cache = {}
        self._depth_cache = {}
        self._chunks = OrderedDict()

    def save_game(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        self.world.save(WORLD_SAVE)
        pdata = {
            "x": self.player.x, "y": self.player.y,
            "hp": self.player.hp, "max_hp": self.player.max_hp,
            "mana": self.player.mana,
            "hunger": getattr(self.player, "hunger", 100),
            "meals": getattr(self.player, "meals_eaten", 0),
            "inv": self.player.inventory.to_dict(),
            "quests": self.quests.to_dict(),
            "layer": self.cur_layer,
            "name": getattr(self.player, "name", "Kael"),
            "appearance": getattr(self.player, "appearance", {"skin": 0, "hair": 0, "eye": 0}),
        }
        with open(PLAYER_SAVE, "w") as f:
            json.dump(pdata, f)
        self.say("Mundo guardado.")

    def load_game(self):
        if not (os.path.exists(WORLD_SAVE) and os.path.exists(PLAYER_SAVE)):
            return False
        try:
            ui.draw_loading(self.screen, 0.5, "Encendiendo antorchas...", "")
            pygame.display.flip()
            self.world = World.load(WORLD_SAVE, WORLD_W, WORLD_H)
            with open(PLAYER_SAVE) as f:
                pdata = json.load(f)
            self.player = Player(pdata["x"], pdata["y"])
            # Migracion de saves viejos (TILE=12 -> TILE=6): si la posicion
            # guardada queda fuera del mundo reescalado, renacer en el spawn.
            if not (0 <= self.player.x < self.world.w * TILE
                    and 0 <= self.player.y < self.world.h * TILE):
                sx, sy = self.world.spawn
                self.player.x, self.player.y = sx * TILE, sy * TILE
                self.say("Partida antigua migrada: renaces en el spawn.")
            self.player.inventory = Inventory()
            self.player.inventory.from_dict(pdata["inv"])
            self.player.hp = pdata.get("hp", 100)
            self.player.max_hp = pdata.get("max_hp", 100)
            self.player.mana = pdata.get("mana", 50)
            self.player.hunger = pdata.get("hunger", 100)
            self.player.meals_eaten = pdata.get("meals", 0)
            self.player.name = pdata.get("name", "Kael")
            self.player.appearance = pdata.get("appearance", {"skin": 0, "hair": 0, "eye": 0})
            self.quests.from_dict(pdata.get("quests", {}))
            self.cur_layer = pdata.get("layer", 0)
            self.after_world_load_keep_pos()
            # Hornear chunks del jugador (continuar fluido desde el frame 1).
            ptx = int((self.player.x + self.player.w / 2) // TILE)
            pty = int((self.player.y + self.player.h / 2) // TILE)
            self._warm_chunks_around(ptx, pty, radius=2)
            return True
        except Exception as e:
            print("Error cargando:", e)
            return False

    def after_world_load_keep_pos(self):
        sx, sy = self.world.spawn
        self.npc = NPC(sx * TILE, (self.world.find_ground(sx, sy) + 1) * TILE - 13)
        ax = getattr(self.world, "abyss_x", sx + 80)
        atop = getattr(self.world, "abyss_top", sy)
        bx = max(3, min(self.world.w - 4, ax + 40))
        gy2 = self.world.find_ground(bx, max(2, atop - 4))
        self.npc2 = NPC(bx * TILE, (gy2 + 1) * TILE - 13, name="Bruno",
                        giver="bruno", tunic=(70, 110, 70), cap=(160, 40, 40))
        self.npcs = [self.npc, self.npc2]
        self.enemies = []
        self.drops = []
        self.boss = None
        self.particles = []
        self.cur_layer = 0
        self._auto_cache = {}
        self.tile_cache = {}
        self._wall_cache = {}
        self._depth_cache = {}
        self._chunks = OrderedDict()

    def has_save(self):
        return os.path.exists(WORLD_SAVE) and os.path.exists(PLAYER_SAVE)

    def _settings_path(self):
        return os.path.join(SAVE_DIR, "settings.json")

    def _load_settings(self):
        defaults = {"res_idx": 0, "fullscreen": False, "skin_idx": 0, "hair_idx": 0, "eye_idx": 0}
        try:
            with open(self._settings_path()) as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
        # Bounds check
        defaults["res_idx"] = max(0, min(len(RESOLUTIONS) - 1, defaults["res_idx"]))
        defaults["skin_idx"] = max(0, min(len(SKIN_COLORS) - 1, defaults["skin_idx"]))
        defaults["hair_idx"] = max(0, min(len(HAIR_COLORS) - 1, defaults["hair_idx"]))
        defaults["eye_idx"] = max(0, min(len(EYE_COLORS) - 1, defaults["eye_idx"]))
        return defaults

    def _save_settings(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        self.settings["res_idx"] = self.res_idx
        self.settings["fullscreen"] = self.fullscreen
        self.settings["skin_idx"] = self.char_skin
        self.settings["hair_idx"] = self.char_hair
        self.settings["eye_idx"] = self.char_eye
        with open(self._settings_path(), "w") as f:
            json.dump(self.settings, f)

    def _apply_settings(self):
        global SCREEN_W, SCREEN_H
        import config
        import ui as _ui
        res = RESOLUTIONS[self.res_idx]
        SCREEN_W, SCREEN_H = res
        config.SCREEN_W, config.SCREEN_H = res
        _ui.SCREEN_W, _ui.SCREEN_H = res
        if self.fullscreen:
            self.screen = pygame.display.set_mode(res, pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(res)

    def show_confirm(self, text, on_yes, on_no=None):
        self.state = "confirm"
        self.confirm_text = text
        self.confirm_sel = 0
        self.confirm_yes = on_yes
        self.confirm_no = on_no

    LOADING_TIPS = [
        "El Abismo tiene 7 capas. Bajar es facil. Subir... no.",
        "Habla con Liora y Bruno (!): misiones con recompensa.",
        "La corona viscosa + el altar invocan al Rey Mokulon.",
        "El martillo rompe paredes de fondo. El pico, minerales.",
        "Come bayas y manzanas: el hambre tambien mata.",
    ]

    def start_new_game(self):
        """Nueva partida con pantalla de carga y barra de progreso.

        La generacion es pesada (mundo gigante); el callback de
        progreso repinta la barra y bombea eventos para que la
        ventana no se congele ni el SO la mate por 'no responde'."""
        import random
        self.state = "loading"
        self._loading_frac = 0.0
        self._loading_label = "Preparando..."
        tip = random.choice(self.LOADING_TIPS)
        ui.draw_loading(self.screen, 0.0, "Preparando...", tip)
        pygame.display.flip()

        def _progress(frac, label):
            self._loading_frac = frac
            self._loading_label = label
            ui.draw_loading(self.screen, frac, label, tip)
            pygame.display.flip()
            # bombear eventos para no congelar la ventana
            for ev in pygame.event.get(pygame.QUIT):
                pygame.event.post(ev)
            pygame.event.pump()

        self.new_world(progress=_progress)
        _progress(0.98, "Despertando a Kael...")
        self.player.name = self.char_name
        self.player.appearance = {
            "skin": self.char_skin,
            "hair": self.char_hair,
            "eye": self.char_eye,
        }
        self._save_settings()
        # Hornear los chunks del spawn (el primer frame ya va fluido).
        sx, sy = self.world.spawn
        self._warm_chunks_around(
            sx, sy, radius=2,
            progress=lambda f: _progress(0.98 + f * 0.02, "Iluminando Mokulandia..."))
        _progress(1.0, "Listo!")
        self.state = "play"
        self.paused = False
        self.say(f"{self.char_name} despierta en Mokulandia. Habla con Liora (!).", 6.0)

    def _start_char_create(self):
        self.state = "char_create"
        self.char_sel = 0
        self.char_name = "Kael"
        self.char_name_editing = False
        # Cargar apariencia de settings si existe
        self.char_skin = self.settings.get("skin_idx", 0)
        self.char_hair = self.settings.get("hair_idx", 0)
        self.char_eye = self.settings.get("eye_idx", 0)

    # ============ tiles dibujo ============
    def zoom_pivot(self):
        """Posicion del jugador en pantalla (layout zoom 1): punto fijo del zoom."""
        pcx, pcy = self.player.center()
        return (pcx - self.cam_x, pcy - self.cam_y)

    def zoom_offset(self):
        """Desplazamiento del blit reescalado para que el jugador quede fijo."""
        z = self.zoom
        if z == 1.0:
            return (0.0, 0.0)
        px, py = self.zoom_pivot()
        return (px * (1.0 - z), py * (1.0 - z))

    def screen_to_world(self, mx, my):
        """Raton (pantalla) -> mundo (tiles/fisicas), compensando el zoom."""
        z = self.zoom
        ox, oy = self.zoom_offset()
        return ((mx - ox) / z + self.cam_x, (my - oy) / z + self.cam_y)

    def apply_zoom(self):
        """Reescala la escena ya dibujada con NEAREST (pixel intacto).

        Se llama tras la escena y antes del HUD: el HUD/menus quedan
        nitidos y el raton se mapea con screen_to_world().
        """
        if self.zoom == 1.0:
            return
        z = self.zoom
        snap = self.screen.copy()
        self.screen.fill(self.sky_color())
        scaled = pygame.transform.scale(snap, (max(1, int(SCREEN_W * z)),
                                               max(1, int(SCREEN_H * z))))
        ox, oy = self.zoom_offset()
        self.screen.blit(scaled, (int(ox), int(oy)))

    def tile_surface(self, bid, exp=0, seam=0, variant=0):
        # Texturas pixelart con AUTOTILE (textures.py): los bloques del mismo
        # grupo conectan sin borde; el borde solo sale al aire y la costura
        # suave entre grupos distintos (tierra/piedra...) hace la transicion.
        # variant 0..3 = dibujo aleatorio por posicion (nada mecanico).
        key = (bid, exp, seam, variant)
        if key in self.tile_cache:
            return self.tile_cache[key]
        if exp == 0 and seam == 0 and variant == 0:
            s = _tx.get_tile_texture(bid)
        else:
            s = _tx.get_tile_texture_auto(bid, exp, seam, variant=variant)
        self.tile_cache[key] = s
        return s

    def autotile_at(self, tx, ty, bid):
        """Mascara autotile + variante aleatoria por posicion, cacheadas.
        La variante (0..3, hash de tx,ty) hace que cada bloque tenga un
        dibujo distinto -> nada mecanico. Se invalida al picar/colocar."""
        key = (tx, ty)
        hit = self._auto_cache.get(key)
        if hit is not None and hit[0] == bid:
            return hit[1], hit[2], hit[3]
        exp, seam = _tx.autotile_masks(self.world, tx, ty)
        if bid in _BG_IDS:
            exp, seam = 0, 0
        variant = ((tx * 73856093) ^ (ty * 19349663)) % 4
        # OPT: acotar la cache (antes crecia sin limite -> OOM al explorar).
        # 60k cubre la vista TILE=6 (~27k) sin limpiar cada N frames.
        if len(self._auto_cache) > 60000:
            self._auto_cache.clear()
        self._auto_cache[key] = (bid, exp, seam, variant)
        return exp, seam, variant

    def dirty_autotile(self, tx, ty):
        """Invalidar autotile en 3x3 tras picar/colocar un bloque."""
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                self._auto_cache.pop((tx + dx, ty + dy), None)
                self._chunk_dirty(tx + dx, ty + dy)

    # ---------- chunks de render (OPT: el mundo estatico se prerenderiza)
    # Un chunk = 32x32 tiles horneados (muros, solidos, deco, AO, depth).
    # Por frame solo se blitean ~35 chunks visibles en vez de 27k tiles
    # uno a uno. LRU de 96 (~14MB). Se invalidan al picar/colocar.
    CHUNK = 32

    def _chunk_dirty(self, tx, ty):
        """Tira de la cache los chunks que solapan el tile (al editar)."""
        chunks = getattr(self, "_chunks", None)
        if chunks is not None:
            chunks.pop((tx // self.CHUNK, ty // self.CHUNK), None)

    def recalc_light(self, tx, ty):
        """Tras picar/colocar: rehace sol/antorchas en la caja y tira los
        chunks afectados (ver world.recalc_light_box)."""
        if self.world is None:
            return
        R = 28
        self.world.recalc_light_box(tx, ty, R=R)
        chunks = getattr(self, "_chunks", None)
        if chunks is not None:
            for ccy in range((ty - R) // self.CHUNK, (ty + R) // self.CHUNK + 1):
                for ccx in range((tx - R) // self.CHUNK, (tx + R) // self.CHUNK + 1):
                    chunks.pop((ccx, ccy), None)

    def _get_chunk(self, ccx, ccy):
        """Chunk cacheado (lo construye si falta). Devuelve
        (albedo, torch): albedo con el sol horneado y torch =
        superficie de luz de antorchas (o None) para BLEND_ADD."""
        chunks = self._chunks
        key = (ccx, ccy)
        hit = chunks.get(key)
        if hit is not None:
            chunks.move_to_end(key)
            return hit
        CS = self.CHUNK * TILE
        surf = pygame.Surface((CS, CS), pygame.SRCALPHA)
        x1 = min(ccx * self.CHUNK + self.CHUNK - 1, self.world.w - 1)
        y1 = min(ccy * self.CHUNK + self.CHUNK - 1, self.world.h - 1)
        torch = self._draw_tiles(surf, ccx * CS, ccy * CS,
                                 ccx * self.CHUNK, ccy * self.CHUNK, x1, y1)
        item = (surf, torch)
        chunks[key] = item
        if len(chunks) > 96:
            chunks.popitem(last=False)
        return item

    def _warm_chunks_around(self, tile_x, tile_y, radius=2, progress=None):
        """Prerenderiza los chunks alrededor de un tile (pantalla de carga:
        el primer frame ya va fluido y calienta las caches de texturas)."""
        ccx, ccy = tile_x // self.CHUNK, tile_y // self.CHUNK
        total = (radius * 2 + 1) ** 2
        n = 0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                kx, ky = ccx + dx, ccy + dy
                if 0 <= kx * self.CHUNK < self.world.w and 0 <= ky * self.CHUNK < self.world.h:
                    self._get_chunk(kx, ky)
                n += 1
                if progress:
                    progress(n / total)

    def _overlay(self, color3, alpha):
        """Overlay fullscreen cacheado: solo se reconstruye si cambia el
        alfa (cuantizado a pasos de 4). Antes se creaba + rellenaba una
        Surface 1280x720 varias veces POR FRAME."""
        if alpha <= 0:
            return None
        aq = (alpha // 4) * 4
        key = (color3, aq)
        hit = self._overlay_cache.get(key) if hasattr(self, "_overlay_cache") else None
        if hit is not None and hit.get_size() == (SCREEN_W, SCREEN_H):
            return hit
        if not hasattr(self, "_overlay_cache"):
            self._overlay_cache = {}
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((*color3, aq))
        if len(self._overlay_cache) > 24:
            self._overlay_cache.clear()
        self._overlay_cache[key] = s
        return s

    def sky_color(self):
        d = self.world.daylight()
        if d >= 1:
            return SKY_DAY
        if d <= 0:
            return SKY_NIGHT
        return tuple(int(SKY_NIGHT[i] + (SKY_DAY[i] - SKY_NIGHT[i]) * d) for i in range(3))

    # ---------- fondos por bioma (parallax + transicion suave) ----------
    # Cada bioma: cielo arriba/abajo de dia y de noche, montanas, colinas.
    BIOME_BG = {
        "pradera":  dict(top_d=(92, 168, 252), bot_d=(188, 228, 252),
                         top_n=(8, 10, 38), bot_n=(26, 32, 76),
                         far=(118, 152, 192), near=(88, 168, 112)),
        "bosque":   dict(top_d=(88, 162, 238), bot_d=(168, 218, 198),
                         top_n=(6, 12, 32), bot_n=(20, 38, 58),
                         far=(66, 112, 132), near=(42, 116, 72)),
        "desierto": dict(top_d=(110, 182, 255), bot_d=(255, 222, 165),
                         top_n=(10, 12, 42), bot_n=(48, 36, 74),
                         far=(192, 158, 128), near=(224, 186, 128)),
        "cielo":    dict(top_d=(72, 148, 248), bot_d=(168, 212, 252),
                         top_n=(5, 8, 30), bot_n=(20, 26, 64),
                         far=(108, 142, 188), near=(140, 172, 212)),
        "cuevas":   dict(top_d=(28, 24, 40), bot_d=(44, 36, 60),
                         top_n=(12, 10, 22), bot_n=(22, 18, 38),
                         far=(38, 32, 60), near=(54, 46, 76)),
        "abismo":   dict(top_d=(32, 26, 66), bot_d=(64, 38, 96),
                         top_n=(12, 8, 28), bot_n=(36, 20, 58),
                         far=(48, 32, 86), near=(74, 44, 116)),
    }

    @staticmethod
    def _lerp_col(a, b, t):
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def _biome_colors(self, biome, daylight):
        """Colores del bioma mezclando dia/noche (sin transicion entre biomas)."""
        B = self.BIOME_BG.get(biome, self.BIOME_BG["pradera"])
        top = self._lerp_col(B["top_n"], B["top_d"], daylight)
        bot = self._lerp_col(B["bot_n"], B["bot_d"], daylight)
        far = self._lerp_col(tuple(max(0, c - 40) for c in B["far"]), B["far"], daylight)
        near = self._lerp_col(tuple(max(0, c - 40) for c in B["near"]), B["near"], daylight)
        return top, bot, far, near

    def _update_bg_transition(self, dt):
        """Avanza la mezcla entre biomas (1.2s). Devuelve colores mezclados."""
        if self.world is None or self.player is None:
            return
        ptx = int((self.player.x + self.player.w / 2) // TILE)
        pty = int((self.player.y + self.player.h / 2) // TILE)
        try:
            wanted = self.world.biome_at(ptx, pty)
        except Exception:
            wanted = "pradera"
        if wanted != self.bg_cur and wanted != self.bg_to:
            self.bg_from = self.bg_cur
            self.bg_to = wanted
            self.bg_t = 0.0
        if self.bg_to is not None:
            self.bg_t = min(1.0, self.bg_t + dt / 2.2)
            if self.bg_t >= 1.0:
                self.bg_cur = self.bg_to
                self.bg_from = None
                self.bg_to = None

    def _mixed_bg_colors(self, daylight):
        """Colores actuales mezclando bg_from->bg_to segun bg_t (transicion)."""
        if self.bg_to is None or self.bg_from is None:
            return self._biome_colors(self.bg_cur, daylight)
        t = self.bg_t * self.bg_t * (3 - 2 * self.bg_t)  # smoothstep
        c1 = self._biome_colors(self.bg_from, daylight)
        c2 = self._biome_colors(self.bg_to, daylight)
        return tuple(self._lerp_col(c1[i], c2[i], t) for i in range(4))

    def draw_background(self):
        """Cielo por bioma: gradiente + sol/luna + montanas/colinas parallax
        + siluetas del bioma (arboles/cactus) + nubes. En cuevas/abismo:
        roca de fondo con motas y brillos. La transicion entre biomas es
        una mezcla de 1.2s (sin cortes)."""
        import math
        daylight = self.world.daylight()
        top, bot, far_c, near_c = self._mixed_bg_colors(daylight)
        W, H = SCREEN_W, SCREEN_H
        # gradiente vertical por franjas finas (8px: transicion suave)
        for i in range(0, H, 8):
            t = i / max(1, H - 1)
            c = self._lerp_col(top, bot, t)
            self.screen.fill(c, (0, i, W, 8))
        cx, cy = self.cam_x, self.cam_y
        biome = self.bg_to if self.bg_to else self.bg_cur
        if biome in ("cuevas", "abismo"):
            # fondo rocoso: motas parallax + brillos abisales
            import random
            rng = random.Random(99)
            for _ in range(70):
                bx = (rng.randint(0, W * 2) - cx * 0.3) % (W + 40) - 20
                by = (rng.randint(0, H * 2) - cy * 0.3) % (H + 40) - 20
                sz = rng.choice((2, 2, 3))
                col = (far_c[0] // 2, far_c[1] // 2, far_c[2] // 2)
                self.screen.fill(col, (bx, by, sz, sz))
            if biome == "abismo":
                for _ in range(12):
                    gx = (rng.randint(0, W) - cx * 0.5) % W
                    gy = (rng.randint(0, H) - cy * 0.5) % H
                    pygame.draw.circle(self.screen, (150, 100, 220), (int(gx), int(gy)), 2)
            return
        # sol/luna con halo (ojo: screen sin alfa -> halo con color solido claro)
        t = self.world.time % 1.0
        sun_x = int(W * t)
        sun_y = int(H * 0.25 - abs(t - 0.5) * 200)
        night = self.world.is_night()
        sc = (220, 220, 240) if night else (255, 235, 150)
        halo = self._lerp_col(sc, bot, 0.45)
        pygame.draw.circle(self.screen, halo, (sun_x % W, max(20, sun_y)), 34)
        pygame.draw.circle(self.screen, sc, (sun_x % W, max(20, sun_y)), 24)
        # estrellas titilantes de noche (parallax fijo al cielo)
        if daylight < 0.35:
            import time as _time
            tw = int(_time.time() * 2)
            for i in range(70):
                ex = (i * 173 + 41) % W
                ey = (i * 97 + 13) % int(H * 0.55)
                if (i * 7 + tw) % 5 == 0:
                    continue  # titileo: algunas se apagan por turno
                br = 150 + (i * 37 + tw * 11) % 90
                self.screen.fill((br, br, min(255, br + 20)), (ex, ey, 2, 2))
        else:
            # pajaros de dia: 3 siluetas en V con aleteo
            import time as _time
            tt = _time.time()
            for i in range(3):
                bx = (i * 431 + tt * 28 - cx * 0.12) % (W + 60) - 30
                by = int(H * 0.18 + i * 26 + math.sin(tt * 2 + i * 2) * 8 - cy * 0.03)
                flap = 3 if int(tt * 6 + i) % 2 == 0 else 1
                bcol = self._lerp_col((40, 40, 60), top, 0.25)
                self.screen.fill(bcol, (int(bx) - 4, by, 4, 1))
                self.screen.fill(bcol, (int(bx), by - flap, 1, flap + 1))
                self.screen.fill(bcol, (int(bx) + 1, by, 4, 1))
        # montanas lejanas (parallax 0.15) + cercanas (0.3): dientes de sierra
        for par, col, base, amp in ((0.15, far_c, 0.62, 90), (0.3, near_c, 0.74, 70)):
            pts = []
            step = 32
            off = -cx * par
            for sx in range(-step, W + step * 2, step):
                wx = sx - off
                h1 = math.sin(wx * 0.008 + par * 10) * amp + math.sin(wx * 0.021) * amp * 0.35
                pts.append((sx, base * H - h1 - cy * par * 0.15))
            pts += [(W + step, H), (-step, H)]
            pygame.draw.polygon(self.screen, col, [(int(x), int(y)) for x, y in pts])
        # siluetas del bioma (parallax 0.5): arboles o cactus
        if biome == "bosque":
            for i in range(14):
                sx = (i * 173 - cx * 0.5) % (W + 80) - 40
                th = 40 + (i * 37 % 30)
                by = int(0.82 * H - cy * 0.08)
                pygame.draw.rect(self.screen, (35, 80, 55), (sx, by - th, 8, th))
                pygame.draw.rect(self.screen, (30, 95, 60), (sx - 12, by - th - 18, 32, 22))
        elif biome == "desierto":
            for i in range(8):
                sx = (i * 251 - cx * 0.5) % (W + 80) - 40
                by = int(0.84 * H - cy * 0.08)
                dh = 26 + (i * 53 % 22)
                pygame.draw.rect(self.screen, (60, 140, 70), (sx, by - dh, 8, dh))
                pygame.draw.rect(self.screen, (60, 140, 70), (sx - 8, by - dh + 8, 8, 10))
            # dunas
            for i in range(5):
                sx = (i * 311 - cx * 0.4) % (W + 200) - 100
                pygame.draw.ellipse(self.screen, (235, 205, 150), (sx, int(0.86 * H), 220, 40))
        else:
            # pradera/cielo: colinas suaves + arbustos + flores punteadas
            for i in range(6):
                sx = (i * 283 - cx * 0.45) % (W + 200) - 100
                pygame.draw.ellipse(self.screen, near_c, (sx, int(0.85 * H - cy * 0.05), 260, 60))
            for i in range(16):  # arbustos
                bx = (i * 197 - cx * 0.5) % (W + 40) - 20
                by = int(0.86 * H - cy * 0.05) + (i * 29 % 14)
                self.screen.fill(self._lerp_col((35, 95, 55), near_c, 0.3), (bx, by, 10, 6))
                self.screen.fill(self._lerp_col((50, 130, 70), near_c, 0.3), (bx + 2, by - 2, 6, 3))
            for i in range(12):  # florecillas
                fx = (i * 331 - cx * 0.55) % (W + 40) - 20
                fy = int(0.88 * H - cy * 0.05) + (i * 41 % 10)
                fcol = (255, 235, 150) if i % 3 == 0 else ((235, 150, 200) if i % 3 == 1 else (255, 255, 255))
                self.screen.fill(fcol, (fx, fy, 2, 2))
        # nubes (siempre de dia, tenue de noche)
        na = 200 if daylight > 0.5 else 90
        for i in range(6):
            nx = (i * 397 + self.world.time * 800 - cx * 0.1) % (W + 200) - 100
            ny = 40 + (i * 67 % 120) - cy * 0.05
            cl = (255, 255, 255) if daylight > 0.3 else (120, 130, 170)
            pygame.draw.rect(self.screen, cl, (nx, ny, 70, 14))
            pygame.draw.rect(self.screen, cl, (nx + 14, ny - 8, 42, 12))

    def stations_near(self):
        """Detecta mesa/horno/altar cerca del jugador."""
        px = int((self.player.x + self.player.w / 2) // TILE)
        py = int((self.player.y + self.player.h / 2) // TILE)
        found = set()
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                b = self.world.get(px + dx, py + dy)
                st = BLOCKS.get(b, {}).get("station")
                if st:
                    found.add(st)
        return found

    # ============ spawn enemigos ============
    def try_spawn(self, dt):
        self.spawn_cd -= dt
        if self.spawn_cd > 0 or len(self.enemies) > 14:
            return
        self.spawn_cd = random.uniform(2.5, 6.0)
        if self.boss and not self.boss.dead:
            self.spawn_cd = 5.0
        px = int((self.player.x + self.player.w / 2) // TILE)
        py = int((self.player.y + self.player.h / 2) // TILE)
        night = self.world.is_night()
        depth = py / self.world.h
        player_layer = self.world.layer_at(px, py)
        if player_layer >= 1 and abyss.near_abyss(self.world, px):
            # en la fosa: el Abismo te encuentra (spawn cerca, de su capa)
            side = random.choice([-1, 1])
            sx = max(2, min(self.world.w - 3, self.world.abyss_x + side * random.randint(6, 18)))
            sy = max(2, min(self.world.h - 3, py + random.randint(-16, 12)))
        else:
            side = random.choice([-1, 1])
            sx = max(2, min(self.world.w - 3, px + side * random.randint(36, 60)))
            sy = py
        # buscar suelo
        for _ in range(40):
            if self.world.solid(sx, sy + 1) and not self.world.solid(sx, sy):
                break
            sy += 1 if random.random() < 0.6 else -1
            sy = max(2, min(self.world.h - 3, sy))
        if self.world.solid(sx, sy):
            return
        x, y = sx * TILE, sy * TILE
        layer_here = self.world.layer_at(sx, sy)
        in_abyss = layer_here >= 1 and abyss.near_abyss(self.world, sx)
        if in_abyss:
            # Abismo: pool de la capa + escalado (mas duros abajo)
            kind = abyss.pick_enemy(layer_here)
            if kind == "heraldo_abismo" and any(e.kind == "heraldo_abismo" and not e.dead for e in self.enemies):
                kind = "eco_profundo"  # un Heraldo cada vez
        elif depth > 0.65 and random.random() < 0.25:
            kind = "rokthar"
        elif depth > 0.35:
            kind = random.choice(["karkas", "karkas", "vesper", "moki_azul"])
        else:
            kind = random.choice(["putrek", "moki_rojo"]) if night else random.choice(["moki_verde", "moki_verde", "putrek"] if night else ["moki_verde"])
            if not night and random.random() < 0.7:
                kind = "moki_verde"
        # de dia no spawnear bajo tierra enemigos de superficie y viceversa: simple filtro
        e = Enemy(kind, x, y - 10)
        if in_abyss and kind != "rey_mokulon":
            sc = abyss.scale_for(layer_here)
            e.max_hp = e.hp = int(e.hp * sc)
            e.dmg = int(e.dmg * sc)
        self.enemies.append(e)

    # ============ combate / minado ============
    def tool_power(self, block_id):
        """Devuelve (power, puede_picar, mensaje)."""
        info = BLOCKS[block_id]
        sel = self.player.inventory.selected_item()
        tipo = ITEMS.get(sel["id"], {}).get("tipo") if sel else None
        power = ITEMS.get(sel["id"], {}).get("power", 0) if sel else 0
        need_tool = info.get("tool")
        if block_id == 10:
            return 0, False, "Bedrock irrompible"
        if need_tool is None:
            # mano vale, herramientas dan bonus
            return max(1.0, power if power else 1.0), True, ""
        if need_tool == "pico" and tipo == "pico":
            req = ORE_REQUIRE.get(block_id, 0)
            if power < req:
                return power, True, "Necesitas un pico mejor"
            return power, True, ""
        if need_tool == "hacha" and tipo == "hacha":
            return power, True, ""
        if need_tool == "martillo" and tipo == "martillo":
            req = ORE_REQUIRE.get(block_id, 0)
            if power < req:
                return power, True, "Necesitas un martillo mejor"
            return power * 1.2, True, ""
        # Arboles con la mano se pueden picar (lento) para no bloquear inicio
        if block_id in (3, 4):
            if tipo == "hacha":
                return power, True, ""
            return 0.6, True, "Usa el hacha para talar mas rapido"
        # herramienta equivocada: lento
        if need_tool == "martillo":
            return 0.25, True, "Usa un martillo!"
        return 0.35, True, ""

    def break_tile(self, tx, ty):
        bid = self.world.get(tx, ty)
        if bid == 0 or bid == 10:
            return
        info = BLOCKS[bid]
        h = TILE // 2
        # Cama de 2 tiles: al romper una mitad cae la otra sin duplicar loot.
        if bid == 30:
            for dx in (-1, 1):
                if self.world.get(tx + dx, ty) == 30:
                    self.world.set(tx + dx, ty, 0)
                    self.dirty_autotile(tx + dx, ty)
        # Puerta de 2 tiles: cae la otra mitad sin duplicar.
        if bid in (32, 33):
            for dy in (-1, 1):
                if self.world.get(tx, ty + dy) == bid:
                    self.world.set(tx, ty + dy, 0)
                    self.dirty_autotile(tx, ty + dy)
        # loot cofre
        if (tx, ty) in self.world.chest_loot:
            for iid, c in self.world.chest_loot.pop((tx, ty)):
                self.spawn_drop(iid, c, tx * TILE + h, ty * TILE)
            self.say("Cofre antiguo abierto!")
        drop = info.get("drop")
        if drop:
            # ores dan extra aleatorio
            n = 1
            if bid in (6, 7, 8):
                n = random.randint(1, 2)
            self.spawn_drop(drop, n, tx * TILE + h, ty * TILE)
        if bid == 4 and random.random() < 0.08:
            self.spawn_drop("manzana", 1, tx * TILE + h, ty * TILE)  # fruta
        self.world.set(tx, ty, 0)
        self.dirty_autotile(tx, ty)
        self.recalc_light(tx, ty)
        self.audio.break_block()
        for _ in range(8):
            self.particles.append([tx * TILE + h, ty * TILE + h,
                                   random.uniform(-3, 3), random.uniform(-5, -1),
                                   0.5, info["colors"][0]])
        # TALA: si rompes un tronco, cae el arbol entero hacia arriba
        # (estilo Terraria) y las hojas cercanas sueltan madera/hojas.
        if bid == 3:
            self._fell_tree(tx, ty)

    def _fell_tree(self, tx, ty):
        """Rompe troncos conectados hacia arriba + hojas vecinas.
        El jugador atraviesa el arbol, asi que talar desde abajo lo tumba."""
        h = TILE // 2
        # subir por el tronco
        for dy in range(1, 12):
            b = self.world.get(tx, ty - dy)
            if b == 3:
                self.world.set(tx, ty - dy, 0)
                self.spawn_drop("madera", 1, tx * TILE + h, (ty - dy) * TILE)
                for _ in range(4):
                    self.particles.append([tx * TILE + h, (ty - dy) * TILE + h,
                                           random.uniform(-2, 2), random.uniform(-4, -1),
                                           0.4, (101, 67, 33)])
            else:
                # copa: romper hojas en radio 2 (dan hoja + a veces manzana)
                if b == 4 or self.world.get(tx, ty - dy) == 0:
                    pass
                break
        top = ty
        while self.world.get(tx, top - 1) == 3 and top - 1 > ty - 12:
            top -= 1
        # hojas alrededor de la copa
        for dy in range(-3, 2):
            for dx in range(-2, 3):
                if self.world.get(tx + dx, top + dy) == 4 and random.random() < 0.7:
                    self.world.set(tx + dx, top + dy, 0)
                    self.spawn_drop("hoja", 1, (tx + dx) * TILE + h, (top + dy) * TILE)
                    if random.random() < 0.06:
                        self.spawn_drop("manzana", 1, (tx + dx) * TILE + h, (top + dy) * TILE)
        self.dirty_autotile(tx, ty)
        self.dirty_autotile(tx, top)
        self.recalc_light(tx, (ty + top) // 2)

    def spawn_drop(self, item_id, count, x, y):
        if item_id not in ITEMS:
            return
        # monedas de cobre pequenas se acumulan: buscar drop cercano igual
        self.drops.append(GroundItem(item_id, count, x, y))

    def melee_attack(self):
        p = self.player
        if p.attack_cd > 0:
            return
        sel = p.inventory.selected_item()
        if sel and ITEMS.get(sel["id"], {}).get("tipo") == "espada":
            dmg = ITEMS[sel["id"]]["damage"]
            cd = ITEMS[sel["id"]].get("cooldown", 0.3)
            knock = ITEMS[sel["id"]].get("knock", 5)
            kind, aid = "espada", sel["id"]
        elif sel and ITEMS.get(sel["id"], {}).get("tipo") in ("pico", "hacha", "martillo"):
            dmg = ITEMS[sel["id"]].get("damage", 3)
            cd, knock = 0.35, 4 if ITEMS[sel["id"]].get("tipo") == "martillo" else 3
            kind, aid = "herramienta", sel["id"]
        else:
            dmg, cd, knock = 2, 0.3, 2  # punos
            kind, aid = "puno", None
        p.attack_cd = cd
        # tajo visible: la espada gira en 3 frames (ver draw_player)
        p.attack_anim = p.attack_dur = 0.28 if kind == "espada" else 0.22
        p.attack_kind = kind
        p.attack_id = aid
        mx, _ = pygame.mouse.get_pos()
        direction = 1 if mx >= SCREEN_W // 2 else -1
        p.facing = direction
        pcx, pcy = p.center()
        hit_any = False
        for e in self.enemies:
            if e.dead:
                continue
            ecx, ecy = e.center()
            if abs(ecx - pcx) < 50 and abs(ecy - pcy) < 40 and ((ecx - pcx) * direction > -5):
                e.take_damage(dmg, knock_x=direction * knock * 15)
                hit_any = True
                for _ in range(5):
                    self.particles.append([ecx, ecy, random.uniform(-3, 3), random.uniform(-4, 0), 0.4, (255, 220, 120)])
        if hit_any:
            self.audio.hit()
            # pequeno arco visual
            self.particles.append([pcx + direction * 20, pcy, direction * 2, 0, 0.15, (255, 255, 255)])

    def use_selected_right(self):
        """Click derecho: puerta / hablar / altar / comer / pocion / bloque."""
        p = self.player
        mx, my = pygame.mouse.get_pos()
        wmx, wmy = self.screen_to_world(mx, my)
        # 0) puerta: abrir/cerrar (ocupa 2 de alto, cambia las 2 mitades)
        dtx, dty = int(wmx // TILE), int(wmy // TILE)
        if self.world.in_bounds(dtx, dty) and self.world.get(dtx, dty) in (32, 33):
            self.toggle_door(dtx, dty)
            return
        # 0b) cofre: coger el loot sin picarlo
        if self.world.in_bounds(dtx, dty) and self.world.get(dtx, dty) == 16:
            self.open_chest(dtx, dty)
            return
        # 1) hablar con Liora o Bruno (misiones primero, consejos despues)
        for npc in getattr(self, "npcs", [self.npc]):
            if npc and npc.rect().collidepoint(wmx, wmy):
                res = self.quests.turn_in(npc.giver, p.inventory)
                if res:
                    self.say(f"{npc.name}: {res[1]}", 6.0)
                    self.audio.craft()
                else:
                    self.say(f"{npc.name}: {npc.talk()}", 5.0)
                return
        # 2) altar + corona?
        sel = p.inventory.selected_item()
        if sel and sel["id"] == "corona_viscosa":
            px = int((p.x + p.w / 2) // TILE)
            py = int((p.y + p.h / 2) // TILE)
            near_altar = any(self.world.get(px + dx, py + dy) == 17
                             for dy in range(-5, 6) for dx in range(-5, 6))
            if near_altar:
                if self.boss and not self.boss.dead:
                    self.say("El Rey Mokulon ya esta aqui!")
                    return
                p.inventory.remove("corona_viscosa", 1)
                bx, by = p.x, p.y - 60
                self.boss = Enemy("rey_mokulon", bx, by)
                self.enemies.append(self.boss)
                self.audio.boss()
                self.say("Has invocado al REY MOKULON!", 5.0)
                return
            else:
                self.say("Usa la corona junto al Altar Mokul (plataforma de ladrillo).")
                return
        # 3) comida? (click derecho con comida en mano)
        if sel and ITEMS.get(sel["id"], {}).get("tipo") == "comida":
            ok, msg = p.eat(sel["id"])
            self.say(msg, 2.5 if ok else 1.5)
            if ok:
                self.audio.potion()
                self.quests.progress_event("eat", sel["id"])
                for _ in range(8):
                    self.particles.append([p.x + 12, p.y + 10, random.uniform(-2, 2), random.uniform(-3, -1), 0.5, (230, 180, 80)])
            return
        # 4) pocion? (heal, buff o cure de maldicion/esporas)
        if sel and ITEMS.get(sel["id"], {}).get("tipo") == "pocion":
            if p.potion_cd > 0:
                return
            info = ITEMS[sel["id"]]
            cures = [b for b in info.get("cure", []) if b in p.buffs]
            if info.get("heal"):
                if p.hp >= p.max_hp and not info.get("buff") and not cures:
                    self.say("Vida llena.")
                    return
                p.heal(info["heal"])
            if info.get("buff"):
                p.buffs[info["buff"]] = info.get("dur", 30)
            for b in info.get("cure", []):
                p.buffs.pop(b, None)
            if not info.get("heal") and not info.get("buff") and not cures:
                self.say("No tienes nada que curar.")
                return
            p.inventory.remove(sel["id"], 1)
            p.potion_cd = info.get("cooldown", 1.0)
            self.audio.potion()
            self.say(f'Usaste {info["name"]}.')
            for _ in range(10):
                self.particles.append([p.x + 12, p.y + 10, random.uniform(-2, 2), random.uniform(-3, -1), 0.6, (120, 255, 150)])
            return
        # 5) colocar bloque
        if sel and ITEMS.get(sel["id"], {}).get("tipo") == "bloque":
            bid = ITEM_TO_BLOCK.get(sel["id"])
            if bid is None:
                return
            tx = int(wmx // TILE)
            ty = int(wmy // TILE)
            pcx, pcy = p.center()
            if math.hypot(tx * TILE - pcx, ty * TILE - pcy) > REACH_DIST * TILE:
                return
            if not self.world.in_bounds(tx, ty) or self.world.get(tx, ty) != 0:
                return
            # no colocar dentro del jugador/enemigos (salvo paredes de fondo)
            is_bg = BLOCKS.get(bid, {}).get("background", False)
            r = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
            if not is_bg:
                if r.colliderect(p.rect()):
                    return
                if any(r.colliderect(e.rect()) for e in self.enemies if not e.dead):
                    return
            # antorchas y bloques normales: antorcha no necesita soporte estricto
            if bid == 32:
                # Puerta: ocupa 2 de alto (arriba debe estar libre)
                if not self.world.in_bounds(tx, ty - 1) or self.world.get(tx, ty - 1) != 0:
                    self.say("La puerta necesita 2 de alto libres.")
                    return
                r2 = pygame.Rect(tx * TILE, (ty - 1) * TILE, TILE, TILE)
                if r2.colliderect(p.rect()):
                    return
                self.world.set(tx, ty - 1, 32)
                self.dirty_autotile(tx, ty - 1)
            self.world.set(tx, ty, bid)
            self.dirty_autotile(tx, ty)
            self.recalc_light(tx, ty)
            p.inventory.remove(sel["id"], 1)
            if not p.inventory.selected_item():
                pass

    def nearby_door(self):
        """Puerta (32/33) pegada al jugador o justo delante (para la E).
        Devuelve (tx, ty) o None."""
        p = self.player
        # 1) solapando al jugador (dentro del marco abierto)
        x0 = int(p.x // TILE)
        x1 = int((p.x + p.w) // TILE)
        y0 = int(p.y // TILE)
        y1 = int((p.y + p.h) // TILE)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.world.in_bounds(tx, ty) and self.world.get(tx, ty) in (32, 33):
                    return (tx, ty)
        # 2) delante (2 tiles) a varias alturas, en la direccion del jugador
        cxp = p.x + p.w / 2
        for d in (1, 2):
            for dy in (p.h / 2, 2, p.h - 1):
                tx = int((cxp + p.facing * TILE * d) // TILE)
                ty = int((p.y + dy) // TILE)
                if self.world.in_bounds(tx, ty) and self.world.get(tx, ty) in (32, 33):
                    return (tx, ty)
        return None

    def nearby_chest(self):
        """Cofre (16) pegado al jugador o justo delante (para la E).
        Devuelve (tx, ty) o None."""
        p = self.player
        x0 = int(p.x // TILE)
        x1 = int((p.x + p.w) // TILE)
        y0 = int(p.y // TILE)
        y1 = int((p.y + p.h) // TILE)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.world.in_bounds(tx, ty) and self.world.get(tx, ty) == 16:
                    return (tx, ty)
        cxp = p.x + p.w / 2
        for d in (1, 2):
            for dy in (p.h / 2, 2, p.h - 1):
                tx = int((cxp + p.facing * TILE * d) // TILE)
                ty = int((p.y + dy) // TILE)
                if self.world.in_bounds(tx, ty) and self.world.get(tx, ty) == 16:
                    return (tx, ty)
        return None

    def open_chest(self, tx, ty):
        """Coge el loot del cofre sin picarlo (E o click derecho). Si el
        inventario se llena, el resto cae al suelo. Sin duplicar: el loot
        se saca de chest_loot (picarlo despues ya no lo da)."""
        loot = self.world.chest_loot.pop((tx, ty), None)
        if not loot:
            self.say("Cofre vacio.")
            return
        got = []
        for iid, c in loot:
            left = self.player.inventory.add(iid, c)
            got.append(f'{ITEMS.get(iid, {}).get("name", iid)}x{c - left}')
            if left:
                self.spawn_drop(iid, left, tx * TILE + TILE / 2, ty * TILE)
        self.audio.pickup()
        self.say("Cofre: +" + ", ".join(got) + ".", 4.0)

    def toggle_door(self, tx, ty):
        """Abre/cierra la puerta (las 2 mitades a la vez) y rehace la luz
        (cerrada tapa el sol, abierta lo deja pasar)."""
        cur = self.world.get(tx, ty)
        if cur not in (32, 33):
            return
        nuevo = 33 if cur == 32 else 32
        self.world.set(tx, ty, nuevo)
        self.dirty_autotile(tx, ty)
        for dy in (-1, 1):
            if self.world.get(tx, ty + dy) == cur:
                self.world.set(tx, ty + dy, nuevo)
                self.dirty_autotile(tx, ty + dy)
        self.recalc_light(tx, ty)
        self.audio.pickup()

    # ============ update ============
    def update(self, dt):
        if self.state != "play" or self.paused or self.world is None:
            return
        keys = pygame.key.get_pressed()
        # tiempo dia/noche + transicion de fondo por bioma
        self.world.time = (self.world.time + dt / DAY_LENGTH) % 1.0
        self._update_bg_transition(dt)
        # capa del Abismo (hambre xN + banner + maldicion al subir)
        ptx0 = int((self.player.x + self.player.w / 2) // TILE)
        pty0 = int((self.player.y + self.player.h / 2) // TILE)
        layer = self.world.layer_at(ptx0, pty0)
        L = abyss.get_layer(layer)
        self._check_layer(layer)
        if not (self.inv_open or self.craft_open):
            self.player.update(keys, self.world, dt, hunger_mult=L["hunger_mult"])
            # polvo de pasos / derrape / wall-slide (sin polvo de aterrizaje)
            p = self.player
            if getattr(p, "want_step_dust", False):
                p.want_step_dust = False
                for _ in range(2 if not p.skidding else 4):
                    self.particles.append([p.x + p.w / 2 + random.uniform(-6, 6), p.y + p.h - 2,
                                           random.uniform(-30, 30), random.uniform(-60, -10),
                                           0.4, (200, 190, 170)])
            p.want_land_dust = 0.0  # desactivado: sin nube al caer
            if getattr(p, "sliding", False) and random.random() < 0.35:
                self.particles.append([p.x + (0 if p.slide_dir > 0 else p.w), p.y + random.uniform(4, p.h - 4),
                                       random.uniform(-20, 20), random.uniform(20, 60),
                                       0.35, (220, 220, 230)])
        else:
            # con menus abiertos: fisica minima + sin slide/sprint (evita pose pegada)
            self.player.sliding = False
            self.player.sprinting = False
            self.player.skidding = False
            self.player.vx *= 0.8
            import physics
            self.player.vy = physics.apply_gravity(self.player.vy, dt)
            self.player._collide(self.world, dt)
            self.player.hunger = max(0, self.player.hunger - 100.0 / HUNGER_TIME * L["hunger_mult"] * dt)
        for npc in getattr(self, "npcs", [self.npc]):
            if npc:
                npc.update(dt)
        # minado continuo con click izquierdo
        mouse = pygame.mouse.get_pressed()
        if mouse[0] and not (self.inv_open or self.craft_open or self.quest_open) and not self.player.dead:
            mx, my = pygame.mouse.get_pos()
            wmx, wmy = self.screen_to_world(mx, my)
            tx = int(wmx // TILE)
            ty = int(wmy // TILE)
            pcx, pcy = self.player.center()
            h = TILE // 2
            if math.hypot(tx * TILE + h - pcx, ty * TILE + h - pcy) <= REACH_DIST * TILE:
                bid = self.world.get(tx, ty)
                if bid != 0 and BLOCKS[bid]["hardness"] < 900:
                    # si hay enemigo cerca del cursor -> atacar en vez de picar
                    target_enemy = None
                    for e in self.enemies:
                        if not e.dead and e.rect().collidepoint(wmx, wmy):
                            target_enemy = e
                            break
                    if target_enemy:
                        self.melee_attack()
                        self.player.mine_target = None
                    else:
                        power, ok, warn = self.tool_power(bid)
                        if warn and (self.player.mine_target != (tx, ty)):
                            self.say(warn, 1.2)
                        hard = BLOCKS[bid]["hardness"]
                        mult = power if "mejor" not in warn else power * 0.15
                        if (self.player.mine_target != (tx, ty)):
                            self.player.mine_target = (tx, ty)
                            self.player.mine_progress = 0.0
                        self.player.mine_progress += dt * max(0.05, mult) / max(0.2, hard)
                        if self.player.mine_progress >= 1.0:
                            self.break_tile(tx, ty)
                            self.player.mine_target = None
                            self.player.mine_progress = 0.0
                else:
                    # click al aire con espada = atacar
                    if self.world.get(tx, ty) == 0:
                        self.melee_attack()
                        self.player.mine_target = None
            else:
                self.player.mine_target = None
        else:
            if not (mouse[0]):
                self.player.mine_target = None
                self.player.mine_progress = 0.0
        # RMB (place) se maneja por eventos para no repetir
        # enemigos
        minis = []
        for e in self.enemies:
            if not e.dead:
                e.update(self.world, self.player, dt, spawned_minis=minis)
        self.enemies.extend(minis)
        # separacion: los bichos no se apilan (empuje barato O(n^2), n<=14)
        _es = self.enemies
        for i in range(len(_es)):
            a = _es[i]
            if a.dead:
                continue
            for j in range(i + 1, len(_es)):
                b = _es[j]
                if b.dead:
                    continue
                ox = (a.x + a.w / 2) - (b.x + b.w / 2)
                oy = (a.y + a.h / 2) - (b.y + b.h / 2)
                rr = (a.w + b.w) / 2
                if abs(ox) < rr and abs(oy) < rr:
                    push = 30.0 if ox >= 0 else -30.0
                    a.vx += push
                    b.vx -= push
        # contacto dano
        for e in self.enemies:
            if e.dead:
                continue
            if e.rect().colliderect(self.player.rect()):
                if self.player.take_damage(e.dmg):
                    self.audio.hurt()
                    # knockback al jugador (px/s)
                    self.player.vx = (1 if self.player.x < e.x else -1) * -120
                    self.player.vy = -160
                    if self.player.dead:
                        self.on_death()
        # limpiar muertos -> drops + misiones (los caidos al vacio no dan nada)
        for e in [e for e in self.enemies if e.dead]:
            if getattr(e, "fell_out", False):
                continue
            for iid, c in e.roll_drops():
                self.spawn_drop(iid, c, e.x + e.w / 2, e.y)
            fresh = self.quests.progress_event("kill", e.kind)
            if fresh:
                self.say("Mision lista para entregar (busca el !).", 4.0)
            if e.kind == "heraldo_abismo":
                self.say("HERALDO CAIDO! El Abismo guarda silencio... por ahora.", 8.0)
            if e.kind == "rey_mokulon":
                self.say("REY MOKULON DERROTADO! Mokulandia es libre... por ahora.", 8.0)
                self.boss = None
            if e is self.boss:
                self.boss = None
        self.enemies = [e for e in self.enemies if not e.dead]
        if self.boss and self.boss.dead:
            self.boss = None
        # drops fisica + pickup
        for d in self.drops:
            d.t += dt
            d.vy = min(275, d.vy + 750 * dt)
            d.x += d.vx * dt
            d.y += d.vy * dt
            tx, ty = int(d.x // TILE), int(d.y // TILE)
            if self.world.solid(tx, ty + 1) and d.y > (ty + 1) * TILE - 8:
                d.y = (ty + 1) * TILE - 8
                d.vy = 0
                d.vx *= 0.9
            # magnet + pickup
            pcx, pcy = self.player.center()
            dist = math.hypot(d.x - pcx, d.y - pcy)
            if dist < 55:
                d.x += (pcx - d.x) * dt * 5
                d.y += (pcy - d.y) * dt * 5
            if dist < 13 and d.t > 0.4:
                if d.id == "corazon":
                    if self.player.hp < self.player.max_hp:
                        self.player.heal(20)
                        d.count = 0
                        self.audio.pickup()
                elif d.id == "estrella":
                    self.player.mana = min(self.player.max_mana, self.player.mana + 15)
                    d.count = 0
                    self.audio.pickup()
                else:
                    left = self.player.inventory.add(d.id, d.count)
                    if left == 0:
                        d.count = 0
                        self.audio.pickup()
                    else:
                        d.count = left
        self.drops = [d for d in self.drops if d.count > 0]
        # respawn tras muerte
        if self.player.dead:
            self.dead_t -= dt
            if self.dead_t <= 0:
                self.player.respawn(self.world)
                self.say("Kael ha renacido en el spawn.")
        # spawns
        if not self.player.dead:
            self.try_spawn(dt)
        # ambiente del Abismo: esporas/polvo flotando segun capa
        if self.cur_layer > 0 and random.random() < 0.12 + self.cur_layer * 0.03:
            pcx0, pcy0 = self.player.center()
            L0 = abyss.get_layer(self.cur_layer)
            scol = L0.get("spore", (180, 150, 255))
            self.particles.append([pcx0 + random.uniform(-300, 300),
                                   pcy0 + random.uniform(-200, 200),
                                   random.uniform(-12, 12), random.uniform(-18, -4),
                                   random.uniform(1.2, 2.5), scol])
        # ambiente fungico: esporas cian cerca de micelio/setas
        if random.random() < 0.25:
            stx = ptx0 + random.randint(-8, 8)
            sty = pty0 + random.randint(-6, 6)
            if self.world.in_bounds(stx, sty) and self.world.get(stx, sty) in (24, 25):
                self.particles.append([stx * TILE + random.uniform(0, TILE),
                                       sty * TILE + random.uniform(0, TILE),
                                       random.uniform(-8, 8), random.uniform(-25, -8),
                                       random.uniform(1.5, 3.0), (140, 255, 200)])
        # particulas (limitar cantidad para rendimiento)
        np = []
        for x, y, vx, vy, life, col in self.particles:
            life -= dt
            if life > 0:
                np.append([x + vx, y + vy + 60 * dt, vx, vy + 3 * dt, life, col])
        self.particles = np[:150]  # max 150 particulas
        # camara
        pcx, pcy = self.player.center()
        self.cam_x += ((pcx - SCREEN_W / 2) - self.cam_x) * min(1, dt * 6)
        self.cam_y += ((pcy - SCREEN_H / 2) - self.cam_y) * min(1, dt * 6)
        self.cam_x = max(0, min(self.world.w * TILE - SCREEN_W, self.cam_x))
        self.cam_y = max(0, min(self.world.h * TILE - SCREEN_H, self.cam_y))
        # mensajes + banner de capa
        self.msg_t = max(0, self.msg_t - dt)
        self.layer_banner_t = max(0, self.layer_banner_t - dt)

    def _check_layer(self, layer):
        """Banner al bajar de capa, evento 'reach' de misiones, esporas de la
        capa 2 y MALDICION al ascender dentro de la fosa (Made in Abyss).

        Conecta: abyss.py (datos), quests.py (reach), player.buffs.
        """
        if layer != self.cur_layer:
            if layer > self.cur_layer and layer > 0:
                self.layer_banner_t = 3.5
                fresh = self.quests.progress_event("reach", layer)
                if fresh:
                    self.say("Mision lista para entregar (busca el !).", 4.0)
                if layer >= 6:
                    self.say("PUNTO DE NO RETORNO: la Maldicion te matara al subir.", 6.0)
                    self.audio.boss()
            if layer < self.cur_layer and self.cur_layer >= 2:
                ptx = int((self.player.x + self.player.w / 2) // TILE)
                if abyss.near_abyss(self.world, ptx):
                    dmg, dur = abyss.curse_for(self.cur_layer)
                    self.player.buffs["maldicion"] = dur
                    self.player.take_damage(dmg, ignore_iframes=True)
                    self.audio.hurt()
                    self.say(f"MALDICION DEL ABISMO al ascender: -{dmg} HP y pesadez {int(dur)}s.", 4.5)
                    for _ in range(12):
                        self.particles.append([self.player.x + 12, self.player.y + 10,
                                               random.uniform(-3, 3), random.uniform(-4, 0),
                                               0.8, (150, 60, 220)])
                    if self.player.dead:
                        self.on_death()
            self.cur_layer = layer
        if layer == 2 and not self.player.dead:
            self.player.buffs["espora"] = max(self.player.buffs.get("espora", 0), 3.0)

    def _npc_mark(self, npc):
        """'!' si el NPC tiene mision entregable o disponible (quests.py)."""
        if not npc:
            return False
        if self.quests.available_for(npc.giver):
            return True
        return any(self.quests.is_complete(q, self.player.inventory)
                   for q in self.quests.started
                   if QUESTS[q]["giver"] == npc.giver and q not in self.quests.done)

    def on_death(self):
        # perder mitad de monedas
        inv = self.player.inventory
        for coin in ("moneda_cobre", "moneda_plata", "moneda_oro"):
            n = inv.count_of(coin)
            if n > 0:
                drop_n = n // 2
                inv.remove(coin, drop_n)
                if drop_n:
                    self.spawn_drop(coin, drop_n, self.player.x, self.player.y - 10)
        self.dead_t = RESPAWN_TIME
        self.say("Has muerto...", 4.0)

    # ============ render ============
    def _ensure_tile_overlays(self):
        """Superficies reutilizadas del pase de tiles (idempotente: el
        prebuild de chunks en carga corre antes del primer render)."""
        if not hasattr(self, "_bg_dim") or self._bg_dim.get_size() != (TILE, TILE):
            self._bg_dim = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            self._bg_dim.fill((0, 0, 0, 70))
            self._wall_dim = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            self._wall_dim.fill((0, 0, 0, 115))
            self._depth_cache = {}
        if not hasattr(self, "_depth_cache"):
            self._depth_cache = {}
        if not hasattr(self, "_wall_cache"):
            self._wall_cache = {}
        if len(self._wall_cache) > 4096:
            self._wall_cache.clear()

    def _draw_tiles(self, dest, cam_x, cam_y, x0, y0, x1, y1):
        """Pase unico de tiles sobre `dest` (pantalla o chunk): muros de
        fondo + solidos + deco + objetos, con AO horneado, depth y el
        SOL horneado por tile (albedo x sol: en cueva queda oscuro).

        cam_x/cam_y: origen en px. x0..y1 recortados al mundo.
        Devuelve la superficie de luz de antorchas (para BLEND_ADD) o None.
        """
        self._ensure_tile_overlays()
        _tiles = self.world.tiles
        _wh = self.world.h
        _blit = dest.blit
        heights = self.world.heights
        wall_cache = self._wall_cache
        _ao = (35, 35, 35, 0)
        _MULT = pygame.BLEND_RGBA_MULT
        _sun = self.world.sun
        for ty in range(y0, y1 + 1):
            depth_alpha = int((ty / _wh - 0.4) * 220) if ty / _wh > 0.4 else 0
            depth_surf = None
            if depth_alpha > 0:
                depth_surf = self._depth_cache.get(depth_alpha)
                if depth_surf is None:
                    depth_surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                    depth_surf.fill((0, 0, 30, depth_alpha))
                    self._depth_cache[depth_alpha] = depth_surf
            row = _tiles[ty]
            sunrow = _sun[ty]
            base_y = ty * TILE - cam_y
            for tx in range(x0, x1 + 1):
                bid = row[tx]
                px_ = tx * TILE - cam_x
                if bid == 0:
                    if ty >= heights[tx]:
                        wall_bid = 2 if ty / _wh > 0.45 else 1
                        variant = ((tx * 73856093) ^ (ty * 19349663)) % 4
                        wkey = (wall_bid, variant, depth_alpha)
                        ws = wall_cache.get(wkey)
                        if ws is None:
                            ws = self.tile_surface(wall_bid, 0, 0, variant).copy()
                            ws.blit(self._wall_dim, (0, 0))
                            if depth_surf is not None:
                                ws.blit(depth_surf, (0, 0))
                            wall_cache[wkey] = ws
                        _blit(ws, (px_, base_y))
                        v = sunrow[tx]
                        if v < 255:
                            dest.fill((v, v, v, 255), (px_, base_y, TILE, TILE), _MULT)
                    continue
                if bid in _BG_IDS:
                    exp, seam, variant = self.autotile_at(tx, ty, bid)
                    _blit(self.tile_surface(bid, exp, seam, variant), (px_, base_y))
                    _blit(self._bg_dim, (px_, base_y))
                    if depth_surf is not None:
                        _blit(depth_surf, (px_, base_y))
                    v = sunrow[tx]
                    if v < 255:
                        dest.fill((v, v, v, 255), (px_, base_y, TILE, TILE), _MULT)
                elif bid in _SOLID_IDS:
                    exp, seam, variant = self.autotile_at(tx, ty, bid)
                    _blit(self.tile_surface(bid, exp, seam, variant), (px_, base_y))
                    if depth_surf is not None:
                        _blit(depth_surf, (px_, base_y))
                    v = sunrow[tx]
                    if v < 255:
                        dest.fill((v, v, v, 255), (px_, base_y, TILE, TILE), _MULT)
                    if exp & 2:  # AO horneado: sombra bajo el borde expuesto
                        dest.fill(_ao, (px_, base_y + TILE - 2, TILE, 2),
                                  pygame.BLEND_RGBA_SUB)
                else:
                    _blit(self.tile_surface(bid, 0, 0, 0), (px_, base_y))
                    # Las luces brillan en la oscuridad; los muebles no.
                    if bid not in _GLOW_IDS:
                        v = sunrow[tx]
                        if v < 255:
                            dest.fill((v, v, v, 255), (px_, base_y, TILE, TILE), _MULT)
        # Luz de antorchas: 1px por tile desde los arrays RGB, suavizada
        # al tamano del chunk (pozos blandos). Negra = sin luz: se blitea
        # con BLEND_ADD por encima de todo (incluso de noche).
        CS = self.CHUNK * TILE
        px32 = pygame.Surface((self.CHUNK, self.CHUNK))
        px32.fill((0, 0, 0))
        any_light = False
        _lr, _lg, _lb = self.world.lr, self.world.lg, self.world.lb
        for _y in range(y0, y1 + 1):
            _r, _g, _b = _lr[_y], _lg[_y], _lb[_y]
            for _x in range(x0, x1 + 1):
                _rv, _gv, _bv = _r[_x], _g[_x], _b[_x]
                if _rv or _gv or _bv:
                    px32.set_at((_x - x0, _y - y0), ((_rv * 4) // 5, (_gv * 4) // 5, (_bv * 4) // 5))
                    any_light = True
        if not any_light:
            return None
        return pygame.transform.smoothscale(px32, (CS, CS))

    def render(self):
        if self.state == "menu":
            ui.draw_menu(self.screen, self.menu_sel, has_save=self.has_save())
        elif self.state == "help":
            ui.draw_help(self.screen)
        elif self.state == "settings":
            ui.draw_settings(self.screen, self.settings_sel, self.res_idx, self.fullscreen)
        elif self.state == "char_create":
            self.char_rects = ui.draw_char_create(self.screen, self.char_sel, self.char_skin,
                                self.char_hair, self.char_eye, self.char_name,
                                editing=self.char_name_editing)
        elif self.state == "confirm":
            ui.draw_confirm(self.screen, self.confirm_text, self.confirm_sel)
        elif self.state == "loading":
            ui.draw_loading(self.screen, getattr(self, "_loading_frac", 0.0),
                            getattr(self, "_loading_label", "Generando mundo..."), "")
        elif self.state == "play" and self.world:
            # Fondo vivo por bioma (cielo/atardecer/noche + parallax).
            self.draw_background()
            cx, cy = int(self.cam_x), int(self.cam_y)
            x0 = max(0, cx // TILE - 1)
            x1 = min(self.world.w - 1, (cx + SCREEN_W) // TILE + 2)
            y0 = max(0, cy // TILE - 1)
            y1 = min(self.world.h - 1, (cy + SCREEN_H) // TILE + 2)
            # Overlays reutilizados (ver _ensure_tile_overlays; el prebuild
            # ya los dejo listos).
            self._ensure_tile_overlays()

            day = self.world.daylight()
            # Tiles por chunks: solo se blitean ~35 surfaces horneadas.
            # La luz fisica (sol horneado + ADD de antorchas) basta: sin halos.
            CS = self.CHUNK * TILE
            ccx0 = max(0, x0 // self.CHUNK)
            ccx1 = min((self.world.w - 1) // self.CHUNK, x1 // self.CHUNK)
            ccy0 = max(0, y0 // self.CHUNK)
            ccy1 = min((self.world.h - 1) // self.CHUNK, y1 // self.CHUNK)
            torch_surfs = []
            for ccy in range(ccy0, ccy1 + 1):
                for ccx in range(ccx0, ccx1 + 1):
                    surf, torch = self._get_chunk(ccx, ccy)
                    self.screen.blit(surf, (ccx * CS - cx, ccy * CS - cy))
                    if torch is not None:
                        torch_surfs.append((torch, ccx * CS - cx, ccy * CS - cy))

            # progreso de minado
            if self.player.mine_target:
                tx, ty = self.player.mine_target
                pr = self.player.mine_progress
                pygame.draw.rect(self.screen, (0, 0, 0), (tx * TILE - cx, ty * TILE - cy - 6, TILE, 5))
                pygame.draw.rect(self.screen, (255, 200, 60), (tx * TILE - cx, ty * TILE - cy - 6, TILE * min(1, pr), 5))
            # drops
            for d in self.drops:
                dx, dy = int(d.x - cx), int(d.y - cy)
                if -30 < dx < SCREEN_W + 30 and -30 < dy < SCREEN_H + 30:
                    bob = int(math.sin(d.t * 5) * 2)
                    if d.id == "corazon":
                        pygame.draw.circle(self.screen, (230, 40, 60), (dx, dy + bob), 6)
                        pygame.draw.circle(self.screen, (255, 150, 150), (dx - 2, dy - 2 + bob), 2)
                    else:
                        ui.draw_item_icon(self.screen, d.id, (dx - 5, dy - 5 + bob, 10, 10))
            # npc + enemigos + jugador
            for npc in getattr(self, "npcs", [self.npc]):
                if npc:
                    npc.draw(self.screen, cx, cy, quest_mark=self._npc_mark(npc))
            for e in self.enemies:
                e.draw(self.screen, cx, cy)
            if not self.player.dead:
                self.player.draw(self.screen, cx, cy)
            # particulas
            for x, y, vx, vy, life, col in self.particles:
                pygame.draw.rect(self.screen, col, (x - cx, y - cy, 3, 3))
            # Noche + profundidad: overlays globales (la luz por tile ya
            # va horneada en los chunks; las antorchas se suman despues).
            ptdx = int((self.player.x + self.player.w / 2) // TILE)
            ptdy = int((self.player.y + self.player.h / 2) // TILE)
            depth01 = max(0.0, min(1.0, ptdy / max(1, self.world.h)))
            if day < 1:
                ov = self._overlay((4, 4, 26), int((1 - day) * 175))
                if ov is not None:
                    self.screen.blit(ov, (0, 0))
            deep_a = int(max(0.0, min(1.0, (depth01 - 0.28) / 0.72)) * 210)
            if deep_a > 0:
                ov = self._overlay((2, 2, 12), deep_a)
                if ov is not None:
                    self.screen.blit(ov, (0, 0))
            # Tinte y niebla de la capa (mezcla progresiva).
            _tint, _fog, _dark = abyss.blend_at(depth01)
            if _tint[3] > 0:
                ov = self._overlay(_tint[:3], _tint[3])
                if ov is not None:
                    self.screen.blit(ov, (0, 0))
            if _fog[3] > 0:
                ov = self._overlay(_fog[:3], _fog[3])
                if ov is not None:
                    self.screen.blit(ov, (0, 0))
            if _dark > 0.03:
                ov = self._overlay((0, 0, 10), int(_dark * 150))
                if ov is not None:
                    self.screen.blit(ov, (0, 0))
            # Luz de antorchas horneada (BLEND_ADD): brilla de dia, de
            # noche y en cuevas, incluso sobre los overlays. Es la unica
            # luz dinamica: sin halos ni circulos (fisica Terraria).
            for tsurf, tox, toy in torch_surfs:
                self.screen.blit(tsurf, (tox, toy), special_flags=pygame.BLEND_ADD)
            # profundidad en tiles
            # profundidad en tiles
            try:
                import ui as _ui
                ptx_ = int((self.player.x + self.player.w / 2) // TILE)
                sy_ = self.world.heights[ptx_] if 0 <= ptx_ < self.world.w else 0
                pty_ = int((self.player.y + self.player.h / 2) // TILE)
                depth_m = max(0, (pty_ - sy_) * 2)
                L = abyss.get_layer(self.cur_layer)
                df = _ui._font(14)
                dt_txt = df.render(f"ABISMO {depth_m}m - {L['name']}", False, (220, 200, 255))
                self.screen.blit(dt_txt, (SCREEN_W - dt_txt.get_width() - 14, 12))
            except Exception:
                pass
            # Zoom de vista
            self.apply_zoom()
            # HUD + banner + paneles
            ui.draw_hud(self.screen, self.player, self.world,
                        self.msg if self.msg_t > 0 else "", self.boss if self.boss and not self.boss.dead else None,
                        layer_idx=self.cur_layer)
            if self.zoom != 1.0:
                zf = ui._font(12)
                zt = zf.render(f"ZOOM {int(self.zoom * 100)}%  (-/=)", False, (255, 255, 255))
                self.screen.blit(zt, (SCREEN_W - zt.get_width() - 12, SCREEN_H - 26))
            if self.layer_banner_t > 0:
                ui.draw_layer_banner(self.screen, self.cur_layer,
                                     alpha=int(255 * min(1, self.layer_banner_t)))
            if self.inv_open:
                mx, my = pygame.mouse.get_pos()
                self.inv_rects, self.armor_rects = ui.draw_inventory(self.screen, self.player, self.held, mx, my)
            if self.craft_open:
                recs = crafting.available_recipes(self.player.inventory, self.stations_near())
                mx, my = pygame.mouse.get_pos()
                self.craft_rows = ui.draw_crafting(self.screen, self.player, recs, self.craft_scroll, mx, my)
            if self.quest_open:
                ui.draw_quests(self.screen, self.quests)
            if self.paused:
                ui.draw_pause(self.screen, self.pause_sel)
            if self.player.dead:
                ui.draw_dead(self.screen, self.dead_t)
        pygame.display.flip()

    # ============ eventos ============
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if self.state == "loading":
                # durante la carga se ignora todo (la barra bombea QUIT aparte)
                continue
            if self.state == "menu":
                if ev.type == pygame.KEYDOWN:
                    n_opts = 4 if self.has_save() else 3
                    if ev.key in (pygame.K_w, pygame.K_UP):
                        self.menu_sel = (self.menu_sel - 1) % n_opts
                    elif ev.key in (pygame.K_s, pygame.K_DOWN):
                        self.menu_sel = (self.menu_sel + 1) % n_opts
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        has = self.has_save()
                        if has:
                            # 4 opciones: NUEVA PARTIDA, CONTINUAR, COMO JUGAR, SALIR
                            if self.menu_sel == 0:
                                if self.has_save():
                                    self.show_confirm("Borrar partida actual y empezar nueva?",
                                                      lambda: self._start_char_create())
                                else:
                                    self._start_char_create()
                            elif self.menu_sel == 1:
                                if self.load_game():
                                    self.state = "play"
                                else:
                                    self.say("No hay guardado valido.")
                            elif self.menu_sel == 2:
                                self.state = "help"
                            else:
                                return False
                        else:
                            # 3 opciones: NUEVA PARTIDA, COMO JUGAR, SALIR
                            if self.menu_sel == 0:
                                self._start_char_create()
                            elif self.menu_sel == 1:
                                self.state = "help"
                            else:
                                return False
                continue
            if self.state == "help":
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.state = "menu"
                continue
            if self.state == "settings":
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_w, pygame.K_UP):
                        self.settings_sel = (self.settings_sel - 1) % 3
                    elif ev.key in (pygame.K_s, pygame.K_DOWN):
                        self.settings_sel = (self.settings_sel + 1) % 3
                    elif ev.key in (pygame.K_a, pygame.K_LEFT):
                        if self.settings_sel == 0:
                            self.res_idx = (self.res_idx - 1) % len(RESOLUTIONS)
                    elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                        if self.settings_sel == 0:
                            self.res_idx = (self.res_idx + 1) % len(RESOLUTIONS)
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.settings_sel == 1:
                            self.fullscreen = not self.fullscreen
                        elif self.settings_sel == 2:
                            self._save_settings()
                            self._apply_settings()
                            if getattr(self, "settings_return", "menu") == "play":
                                self.state = "play"
                                self.paused = True
                                self.pause_sel = 0
                            else:
                                self.state = "menu"
                    elif ev.key == pygame.K_ESCAPE:
                        self._save_settings()
                        self._apply_settings()
                        # ESC en ajustes vuelve al juego (pausa), no al menu principal
                        if getattr(self, "settings_return", "menu") == "play":
                            self.state = "play"
                            self.paused = True
                            self.pause_sel = 0
                        else:
                            self.state = "menu"
                continue
            if self.state == "char_create":
                if self.char_name_editing:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                            self.char_name_editing = False
                        elif ev.key == pygame.K_BACKSPACE:
                            self.char_name = self.char_name[:-1] if self.char_name else ""
                        else:
                            ch = ev.unicode or ""
                            if (ch.isalnum() or ch in " _-") and len(self.char_name) < 12:
                                self.char_name += ch
                    continue
                else:
                    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        rects = getattr(self, "char_rects", None)
                        if rects:
                            mx, my = ev.pos
                            for j, r in enumerate(rects.get("skin", [])):
                                if r.collidepoint(mx, my):
                                    self.char_skin = j
                                    self.char_sel = 1
                                    break
                            for j, r in enumerate(rects.get("hair", [])):
                                if r.collidepoint(mx, my):
                                    self.char_hair = j
                                    self.char_sel = 2
                                    break
                            for j, r in enumerate(rects.get("eye", [])):
                                if r.collidepoint(mx, my):
                                    self.char_eye = j
                                    self.char_sel = 3
                                    break
                            if rects.get("start") and rects["start"].collidepoint(mx, my):
                                if not self.char_name.strip():
                                    self.char_name = "Kael"
                                self._save_settings()
                                self.start_new_game()
                                continue
                    if ev.type == pygame.KEYDOWN:
                        if ev.key in (pygame.K_w, pygame.K_UP):
                            self.char_sel = (self.char_sel - 1) % 5
                        elif ev.key in (pygame.K_s, pygame.K_DOWN):
                            self.char_sel = (self.char_sel + 1) % 5
                        elif ev.key in (pygame.K_a, pygame.K_LEFT):
                            if self.char_sel == 1:
                                self.char_skin = (self.char_skin - 1) % len(SKIN_COLORS)
                            elif self.char_sel == 2:
                                self.char_hair = (self.char_hair - 1) % len(HAIR_COLORS)
                            elif self.char_sel == 3:
                                self.char_eye = (self.char_eye - 1) % len(EYE_COLORS)
                            elif self.char_sel == 0 and self.char_name:
                                self.char_name = self.char_name[:-1]
                        elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                            if self.char_sel == 1:
                                self.char_skin = (self.char_skin + 1) % len(SKIN_COLORS)
                            elif self.char_sel == 2:
                                self.char_hair = (self.char_hair + 1) % len(HAIR_COLORS)
                            elif self.char_sel == 3:
                                self.char_eye = (self.char_eye + 1) % len(EYE_COLORS)
                        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                            if self.char_sel == 0:
                                self.char_name_editing = True
                            elif self.char_sel == 1:
                                self.char_skin = (self.char_skin + 1) % len(SKIN_COLORS)
                            elif self.char_sel == 2:
                                self.char_hair = (self.char_hair + 1) % len(HAIR_COLORS)
                            elif self.char_sel == 3:
                                self.char_eye = (self.char_eye + 1) % len(EYE_COLORS)
                            elif self.char_sel == 4:
                                if not self.char_name.strip():
                                    self.char_name = "Kael"
                                self._save_settings()
                                self.start_new_game()
                        elif ev.key == pygame.K_ESCAPE:
                            self.state = "menu"
                continue
            if self.state == "confirm":
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_w, pygame.K_UP, pygame.K_a, pygame.K_LEFT):
                        self.confirm_sel = (self.confirm_sel - 1) % 2
                    elif ev.key in (pygame.K_s, pygame.K_DOWN, pygame.K_d, pygame.K_RIGHT):
                        self.confirm_sel = (self.confirm_sel + 1) % 2
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.confirm_sel == 0 and self.confirm_yes:
                            self.confirm_yes()
                        else:
                            self.state = "menu"
                    elif ev.key == pygame.K_ESCAPE:
                        self.state = "menu"
                continue
            # ---- estado play ----
            if ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_ESCAPE:
                    if self.quest_open:
                        self.quest_open = False
                    elif self.inv_open:
                        self.inv_open = False
                        self.held = None
                    elif self.craft_open:
                        self.craft_open = False
                    elif self.paused:
                        self.paused = False
                    else:
                        self.paused = True
                        self.pause_sel = 0
                elif self.paused:
                    if k in (pygame.K_w, pygame.K_UP):
                        self.pause_sel = (self.pause_sel - 1) % 4
                    elif k in (pygame.K_s, pygame.K_DOWN):
                        self.pause_sel = (self.pause_sel + 1) % 4
                    elif k in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.pause_sel == 0:
                            self.paused = False
                        elif self.pause_sel == 1:
                            self.save_game()
                            self.paused = False
                        elif self.pause_sel == 2:
                            self.paused = False
                            self.state = "settings"
                            self.settings_sel = 0
                            self.settings_return = "play"
                        else:
                            self.state = "menu"
                            self.paused = False
                elif k == pygame.K_e:
                    # E junto a puerta/cofre los usa (estilo Terraria);
                    # si no, abre/cierra el inventario.
                    target = None
                    action = None
                    if not (self.inv_open or self.craft_open or self.quest_open):
                        door = self.nearby_door()
                        if door is not None:
                            target, action = door, "door"
                        else:
                            chest = self.nearby_chest()
                            if chest is not None:
                                target, action = chest, "chest"
                    if action == "door":
                        self.toggle_door(*target)
                    elif action == "chest":
                        self.open_chest(*target)
                    else:
                        self.inv_open = not self.inv_open
                    self.craft_open = False
                    self.quest_open = False
                    if not self.inv_open:
                        # devolver held al inventario
                        if self.held:
                            left = self.player.inventory.add(self.held["id"], self.held["count"])
                            if left:
                                self.spawn_drop(self.held["id"], left, self.player.x, self.player.y)
                            self.held = None
                elif k == pygame.K_c:
                    self.craft_open = not self.craft_open
                    self.inv_open = False
                    self.quest_open = False
                elif k == pygame.K_j:
                    self.quest_open = not self.quest_open
                    self.inv_open = False
                    self.craft_open = False
                elif k == pygame.K_q and not (self.inv_open or self.craft_open):
                    sel = self.player.inventory.selected_item()
                    if sel:
                        self.spawn_drop(sel["id"], 1, self.player.x, self.player.y - 5)
                        self.player.inventory.remove(sel["id"], 1)
                elif k == pygame.K_f and not (self.inv_open or self.craft_open):
                    # antorcha rapida bajo el jugador
                    if self.player.inventory.has("antorcha"):
                        px = int((self.player.x + self.player.w / 2) // TILE)
                        py = int((self.player.y + self.player.h / 2) // TILE)
                        if self.world.get(px, py) == 0:
                            self.world.set(px, py, 14)
                            self.dirty_autotile(px, py)
                            self.recalc_light(px, py)
                            self.player.inventory.remove("antorcha", 1)
                elif k == pygame.K_t and not (self.inv_open or self.craft_open):
                    # comercio con Liora cerca: 10 cobres -> 1 pocion menor
                    if self.npc and math.hypot(self.player.x - self.npc.x, self.player.y - self.npc.y) < 60:
                        if self.player.inventory.has("moneda_cobre", 10):
                            self.player.inventory.remove("moneda_cobre", 10)
                            self.player.inventory.add("pocion_vida_menor", 1)
                            self.say("Liora te vende 1 pocion (10 cobres).")
                            self.audio.pickup()
                        else:
                            self.say("Liora: necesitas 10 cobres (pulsa T cerca de mi).")
                elif pygame.K_1 <= k <= pygame.K_9 and not (self.inv_open or self.craft_open):
                    self.player.inventory.selected = k - pygame.K_1
                elif k == pygame.K_0 and not (self.inv_open or self.craft_open):
                    self.player.inventory.selected = 9
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    # alejar vista
                    self.zoom = max(self.ZOOM_MIN, self.zoom / 1.15)
                elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    # acercar vista (Shift+= da PLUS en algunos layouts)
                    self.zoom = min(self.ZOOM_MAX, self.zoom * 1.15)
            elif ev.type == pygame.MOUSEWHEEL:
                # Rueda: crafteo = scroll lista | inventario = cambia hotbar
                # | juego = cambia hotbar 1-0 (cicla 0..9).
                if self.craft_open:
                    self.craft_scroll = max(0, self.craft_scroll + ev.y * -30)
                elif self.player is not None and self.state == "play" and not self.paused:
                    step = -1 if ev.y > 0 else 1  # arriba = anterior, abajo = siguiente
                    inv = self.player.inventory
                    inv.selected = (inv.selected + step) % 10
                    self.audio.pickup()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if self.paused or self.player is None:
                    continue
                if self.inv_open:
                    self.click_inventory(mx, my, ev.button)
                elif self.craft_open:
                    if ev.button == 1:
                        for rect, r, ok in getattr(self, "craft_rows", []):
                            if rect.collidepoint(mx, my) and ok:
                                good, m = crafting.craft(self.player.inventory, r)
                                self.say(m)
                                if good:
                                    self.audio.craft()
                                break
                else:
                    if ev.button == 1:
                        # ataque inmediato si no hay bloque solido (el minado continuo sigue en update)
                        pass
                    elif ev.button == 3:
                        self.use_selected_right()
            elif ev.type == pygame.MOUSEBUTTONUP:
                pass
        # hotbar con rueda cuando no hay menus
        return True

    def click_inventory(self, mx, my, button):
        inv = self.player.inventory
        # slots
        for i, rect in enumerate(self.inv_rects):
            if rect.collidepoint(mx, my):
                slot = inv.slots[i]
                if button == 1:  # agarrar / soltar / intercambiar
                    if self.held is None and slot:
                        self.held = slot
                        inv.slots[i] = None
                    elif self.held is not None and slot is None:
                        inv.slots[i] = self.held
                        self.held = None
                    elif self.held and slot:
                        if slot["id"] == self.held["id"]:
                            mxc = ITEMS[slot["id"]].get("max_stack", 99)
                            room = mxc - slot["count"]
                            take = min(room, self.held["count"])
                            slot["count"] += take
                            self.held["count"] -= take
                            if self.held["count"] <= 0:
                                self.held = None
                        else:
                            inv.slots[i], self.held = self.held, slot
                    self.audio.pickup()
                elif button == 3:  # equipar armadura o mitad
                    if slot and ITEMS.get(slot["id"], {}).get("tipo") in ("casco", "peto", "botas"):
                        tipo = ITEMS[slot["id"]]["tipo"]
                        idx = {"casco": 0, "peto": 1, "botas": 2}[tipo]
                        old = inv.armor[idx]
                        inv.armor[idx] = {"id": slot["id"], "count": 1}
                        if slot["count"] > 1:
                            slot["count"] -= 1
                        else:
                            inv.slots[i] = None
                        if old:
                            inv.add(old["id"], 1)
                        self.audio.craft()
                        self.say(f'Equipado: {ITEMS[slot["id"]]["name"]}')
                return
        # armadura: click para desequipar
        for i, rect in enumerate(self.armor_rects):
            if rect.collidepoint(mx, my) and inv.armor[i]:
                if self.held is None:
                    self.held = inv.armor[i]
                    inv.armor[i] = None
                return

    # ============ loop ============
    def run(self):
        running = True
        while running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            running = self.handle_events()
            self.update(dt)
            self.render()
        # autoguardar al salir si hay partida
        if self.world and self.player and self.state == "play":
            try:
                self.save_game()
            except Exception:
                pass
        pygame.quit()
