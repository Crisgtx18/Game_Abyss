# Sistema de inventario: hotbar (0-9) + mochila (10-39) + armadura (3)
from items import ITEMS


class Inventory:
    SIZE = 40
    HOTBAR = 10

    def __init__(self):
        self.slots = [None] * self.SIZE  # cada slot: {"id": str, "count": int}
        self.armor = [None, None, None]  # casco, peto, botas
        self.selected = 0

    # ---------- basico ----------
    def add(self, item_id, count=1):
        if item_id not in ITEMS:
            return count
        max_stack = ITEMS[item_id].get("max_stack", 99)
        # apilar primero
        for i in range(self.SIZE):
            s = self.slots[i]
            if s and s["id"] == item_id and s["count"] < max_stack:
                room = max_stack - s["count"]
                take = min(room, count)
                s["count"] += take
                count -= take
                if count <= 0:
                    return 0
        # slots vacios
        for i in range(self.SIZE):
            if self.slots[i] is None:
                take = min(max_stack, count)
                self.slots[i] = {"id": item_id, "count": take}
                count -= take
                if count <= 0:
                    return 0
        return count  # sobrante (inventario lleno)

    def remove(self, item_id, count=1):
        for i in range(self.SIZE):
            s = self.slots[i]
            if s and s["id"] == item_id:
                take = min(s["count"], count)
                s["count"] -= take
                count -= take
                if s["count"] <= 0:
                    self.slots[i] = None
                if count <= 0:
                    return True
        return count <= 0

    def count_of(self, item_id):
        return sum(s["count"] for s in self.slots if s and s["id"] == item_id)

    def has(self, item_id, count=1):
        return self.count_of(item_id) >= count

    def selected_item(self):
        return self.slots[self.selected]

    def total_defense(self):
        from items import ITEMS as _I
        d = 0
        for a in self.armor:
            if a:
                d += _I.get(a["id"], {}).get("defensa", 0)
        return d

    # ---------- guardado ----------
    def to_dict(self):
        return {"slots": self.slots, "armor": self.armor, "selected": self.selected}

    def from_dict(self, d):
        self.slots = d.get("slots", [None] * self.SIZE)
        while len(self.slots) < self.SIZE:
            self.slots.append(None)
        self.slots = self.slots[: self.SIZE]
        self.armor = d.get("armor", [None, None, None])
        self.selected = d.get("selected", 0)
