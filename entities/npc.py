# NPCs: Maestra Liora (aldea, pociones y misiones iniciales) y
# Bruno el Vigia (borde del Abismo, misiones de capas y reliquias).
import random
import pygame
from config import TILE

TIPS = {
    "liora": [
        "Hola Kael. Pica arboles con el hacha.",
        "Funde hierro crudo + carbon en el horno.",
        "De noche salen Putreks... lleva espada y antorchas.",
        "El Altar de Underdown al este... usa la Corona viscosa ahi. No digas que te avise.",
        "Los cofres antiguos guardan diamantes. Busca la mina.",
        "Equipa armadura con E: casco, peto y botas te protegen.",
        "Come algo con click derecho (prueba la manzana). El hambre mata.",
        "Pulsa J para ver tus misiones. Yo te doy las primeras.",
    ],
    "bruno": [
        "Soy Bruno, Vigia del Abismo. Llevo 20 anos mirando este agujero.",
        "Cada capa tiene su Maldicion: SUBIR te hiere. Baja despacio, sube despacio.",
        "Las flores abisales dan bayas que brillan. Comelas si te pierdes.",
        "La carne cruda cae mal... cocinala en el horno, chaval.",
        "El Heraldo duerme en el fondo. Si lo despiertas, trae un orbe.",
        "El estofado del Abismo cura hasta la Maldicion. Aprende la receta.",
    ],
}

POTION_PRICE = [("pocion_vida_menor", 10), ("antorcha", 2)]  # 10 cobres / 2 cobres


class NPC:
    """Aldeano con dialogos y misiones. giver conecta con quests.py
    ('liora' o 'bruno'). *args/**kwargs para futuros oficios."""

    def __init__(self, x, y, *args, name="Liora", giver="liora",
                 tunic=(130, 80, 180), cap=(90, 50, 120), **kwargs):
        self.x, self.y = float(x), float(y)
        self.w, self.h = 8, 16  # TILE=6: ~1.3 x 2.6 tiles
        self.name = name
        self.giver = giver
        self.tunic = tunic
        self.cap = cap
        self.tip_i = 0
        self.bubble_t = 0.0
        # Deambulado estilo Terraria: pasea junto a su casa.
        self.home_x = float(x)
        self.walk_tx = float(x)
        self.walk_t = 2.0
        self.facing = 1

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def talk(self, *args, **kwargs):
        tips = TIPS.get(self.giver, TIPS["liora"])
        msg = tips[self.tip_i % len(tips)]
        self.tip_i += 1
        self.bubble_t = 5.0
        return msg

    def update(self, dt, *args, **kwargs):
        self.bubble_t = max(0, self.bubble_t - dt)
        # Paseo corto alrededor de casa (sin fisica: suelo llano).
        self.walk_t -= dt
        if self.walk_t <= 0:
            self.walk_t = random.uniform(2.0, 5.0)
            self.walk_tx = self.home_x + random.uniform(-14, 14)
        dx = self.walk_tx - self.x
        if abs(dx) > 1.0:
            self.facing = 1 if dx > 0 else -1
            self.x += max(-1, min(1, dx)) * min(abs(dx), 10 * dt)

    def draw(self, surf, cx, cy, *args, quest_mark=False, **kwargs):
        """NPC con sprite pixelart (delega en textures.draw_npc).

        quest_mark='!' si tiene mision disponible/entregable (lo decide
        game.py con quests.py y lo pasa aqui)."""
        import textures
        x, y = int(self.x - cx), int(self.y - cy)
        textures.draw_npc(surf, x, y, name=self.name, tunic=self.tunic,
                          cap=self.cap, quest_mark=quest_mark,
                          tick=pygame.time.get_ticks())
