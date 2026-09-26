"""Misiones de Liora y Bruno el Vigia: aceptar, progresar y entregar.

Que hace:
    - QUESTS: ficha de cada mision (quien la da, tipo collect/kill/reach/eat,
      objetivo, cantidad, recompensas, mision previa requerida).
    - QuestState: progreso del jugador (empezadas, conteos, completadas).
      Persiste en saves/ via to_dict()/from_dict().

Con que conecta:
    - entities/npc.py -> cada NPC tiene .giver ('liora'/'bruno'); game.py
      pregunta available_for(giver) al hablar para ofrecerla, y
      turn_in(giver, inventory) para entregar.
    - game.py -> registra eventos: progress_event('kill', kind) al morir un
      bicho, ('eat', food_id) al comer, ('reach', layer_idx) al bajar de capa.
    - ui.py -> draw_quests() lista misiones con su progreso.
    - items.py -> los ids de recompensas y objetivos collect.

Como tocarlo luego:
    Anade una entrada a QUESTS y listo (sin tocar game.py). El target de
    'kill' acepta 'moki*' como comodin (moki_verde/azul/rojo/mini_moki).

Uso *args/**kwargs:
    progress_event() y check_* aceptan extras para futuros tipos de evento.
"""
from items import ITEMS

QUESTS = {
    "q_madera": dict(
        name="Primeros troncos", giver="liora", tipo="collect",
        target="madera", count=10, requires=None,
        desc="Trae 10 de madera (tala Mokubos con el hacha).",
        reward=[("pocion_vida_menor", 2), ("pan_hongo", 2)],
        give_msg="Liora: con madera haras tu mesa. Toma, para el camino."),
    "q_mokis": dict(
        name="Limpieza de Mokis", giver="liora", tipo="kill",
        target="moki*", count=8, requires="q_madera",
        desc="Derrota 8 Mokis (verdes, azules o rojos).",
        reward=[("moneda_plata", 15), ("carne_cocida", 2)],
        give_msg="Liora: los Mokis invaden el huerto. Acaba con 8."),
    "q_filo": dict(
        name="Al filo del Abismo", giver="bruno", tipo="reach",
        target=2, count=1, requires=None,
        desc="Desciende hasta la Capa 2 del Abismo y vuelve... si puedes.",
        reward=[("antorcha", 15), ("baya_luminosa", 4)],
        give_msg="Bruno: el Abismo llama. Baja a la Capa 2. Y no subas corriendo."),
    "q_dieta": dict(
        name="Dieta del explorador", giver="bruno", tipo="eat",
        target="any", count=3, requires=None,
        desc="Come 3 comidas (manzanas, bayas, carne cocida...).",
        reward=[("pocion_regen", 1), ("pan_hongo", 2)],
        give_msg="Bruno: un explorador con hambre es un explorador muerto."),
    "q_reliquia": dict(
        name="Reliquia perdida", giver="bruno", tipo="collect",
        target="reliquia_orbe", count=1, requires="q_filo",
        desc="El Heraldo guarda orbes en lo hondo. Traeme 1.",
        reward=[("lingote_oro", 8), ("pocion_vida_mayor", 1)],
        give_msg="Bruno: los Vigias perdimos un orbe abajo. Recuperalo."),
    "q_heraldo": dict(
        name="El Heraldo del Abismo", giver="bruno", tipo="kill",
        target="heraldo_abismo", count=1, requires="q_reliquia",
        desc="Derrota al Heraldo (mini-jefe de las capas 5-6).",
        reward=[("diamante", 5), ("pocion_vida_mayor", 2)],
        give_msg="Bruno: solo un Silbato Negro bajaria... o tu. Ve."),
    "q_torno": dict(
        name="El Torbellino Final", giver="bruno", tipo="reach",
        target=7, count=1, requires="q_heraldo",
        desc="Desciende a la Capa 7, el fondo del mundo, y vuelve para contarlo.",
        reward=[("diamante", 8), ("pocion_vida_mayor", 3), ("moneda_oro", 5)],
        give_msg="Bruno: nadie ha vuelto del Torbellino. Se tu el primero."),
}

ORDER = ["q_madera", "q_mokis", "q_filo", "q_dieta", "q_reliquia", "q_heraldo", "q_torno"]


def _kill_match(target, kind, *args, **kwargs):
    """Comodin de caza: 'moki*' vale para verde/azul/rojo/mini."""
    if target.endswith("*"):
        prefix = target[:-1]
        if prefix == "moki":
            return kind.startswith("moki") or kind == "mini_moki"
        return kind.startswith(prefix)
    return target == kind


class QuestState:
    """Progreso de misiones. Una instancia vive en game.py (game.quests)."""

    def __init__(self, *args, **kwargs):
        self.started = []      # ids aceptadas
        self.done = []         # ids entregadas
        self.progress = {}     # id -> conteo actual

    # ---------- flujo ----------
    def available_for(self, giver, *args, **kwargs):
        """Misiones que ese NPC puede ofrecer ahora (previa cumplida)."""
        out = []
        for qid in ORDER:
            q = QUESTS[qid]
            if q["giver"] != giver or qid in self.started:
                continue
            req = q.get("requires")
            if req and req not in self.done:
                continue
            out.append(qid)
        return out

    def accept(self, qid, *args, **kwargs):
        """Acepta una mision disponible. Devuelve su mensaje de encargo."""
        if qid in self.started or qid not in QUESTS:
            return None
        if qid not in self.available_for(QUESTS[qid]["giver"]):
            # la previa no esta entregada: pista util
            req = QUESTS[qid].get("requires")
            if req:
                return f"Primero completa '{QUESTS[req]['name']}'."
            return None
        self.started.append(qid)
        self.progress[qid] = 0
        return QUESTS[qid]["give_msg"]

    def progress_event(self, etype, key, n=1, *args, **kwargs):
        """Registra un evento ('kill'/'eat'/'reach'). key: kind/food/capa.

        'reach' guarda la capa MAXIMA alcanzada. 'eat' cuenta cualquier
        comida si target='any'. Devuelve lista de qids recién completables.
        """
        fresh = []
        for qid in self.started:
            if qid in self.done:
                continue
            q = QUESTS[qid]
            if q["tipo"] != etype:
                continue
            if etype == "kill" and not _kill_match(q["target"], key):
                continue
            if etype == "eat" and q["target"] not in ("any", key):
                continue
            if etype == "reach":
                self.progress[qid] = max(self.progress.get(qid, 0), int(key))
            else:
                self.progress[qid] = self.progress.get(qid, 0) + n
            if self.is_complete(qid, physics_check=False):
                fresh.append(qid)
        return fresh

    def is_complete(self, qid, inventory=None, physics_check=True, *args, **kwargs):
        """True si la mision esta lista para entregar.

        collect: mira el inventario (no gasta hasta entregar). El resto usa
        el conteo de progress_event(). **kwargs para no romper llamadas.
        """
        q = QUESTS[qid]
        if qid in self.done or qid not in self.started:
            return False
        if q["tipo"] == "collect":
            if inventory is None:
                return False
            return inventory.count_of(q["target"]) >= q["count"]
        return self.progress.get(qid, 0) >= q["count"]

    def turn_in(self, giver, inventory, *args, **kwargs):
        """Entrega la primera mision completable de ese NPC.

        Gasta los items collect y da recompensas. Devuelve (qid, msg) o None.
        Si no hay completable pero si disponible, la acepta y devuelve eso.
        """
        for qid in ORDER:
            q = QUESTS[qid]
            if q["giver"] != giver or qid not in self.started or qid in self.done:
                continue
            if self.is_complete(qid, inventory):
                if q["tipo"] == "collect":
                    inventory.remove(q["target"], q["count"])
                for iid, c in q["reward"]:
                    inventory.add(iid, c)
                self.done.append(qid)
                names = ", ".join(f"{ITEMS.get(i, {}).get('name', i)}x{c}" for i, c in q["reward"])
                return qid, f"Mision '{q['name']}' completada! Recompensa: {names}."
        avail = self.available_for(giver)
        if avail:
            msg = self.accept(avail[0])
            return avail[0], msg
        return None

    def status_list(self, *args, **kwargs):
        """[(qid, estado, texto_progreso)] para ui.draw_quests()."""
        out = []
        for qid in ORDER:
            q = QUESTS[qid]
            if qid in self.done:
                out.append((qid, "done", "Completada"))
            elif qid in self.started:
                if q["tipo"] == "collect":
                    out.append((qid, "active", f"{q['target']} (? en mochila)"))
                elif q["tipo"] == "reach":
                    out.append((qid, "active", f"capa {self.progress.get(qid,0)}/{q['count']}"))
                else:
                    out.append((qid, "active", f"{self.progress.get(qid,0)}/{q['count']}"))
            else:
                out.append((qid, "locked" if q.get("requires") not in self.done and q.get("requires") else "new", q["giver"]))
        return out

    # ---------- guardado ----------
    def to_dict(self, *args, **kwargs):
        return {"started": self.started, "done": self.done, "progress": self.progress}

    def from_dict(self, d, *args, **kwargs):
        self.started = d.get("started", [])
        self.done = d.get("done", [])
        self.progress = {k: int(v) for k, v in d.get("progress", {}).items()}
