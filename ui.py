# UI: menus, HUD, inventario, crafteo, ayuda, pausa, muerte, misiones.
import pygame
from config import (SCREEN_W, SCREEN_H, UI_BG, UI_PANEL, UI_ACCENT,
                    RESOLUTIONS, SKIN_COLORS, HAIR_COLORS, EYE_COLORS)
from items import ITEMS
from blocks import BLOCKS


def _font(size):
    # Estilo pixel: monoespaciada, negrita en titulares y SIN antialias
    # al renderizar (los render usan False -> pixel nitido, no difuminado).
    # Se prueba en orden: consolas > couriernew > monospace > default.
    # Cacheada: SysFont cada frame costaba ~12ms (ver profile).
    return _font_cached(size)


import functools


@functools.lru_cache(maxsize=24)
def _font_cached(size):
    for name in ("consolas", "couriernew", "monospace", "dejavusansmono"):
        try:
            f = pygame.font.SysFont(name, size, bold=(size >= 20))
            if f:
                return f
        except Exception:
            continue
    return pygame.font.SysFont("monospace", size, bold=(size >= 20))


def _px(surf, font, text, color, pos, shadow=(10, 10, 20)):
    """Texto pixel con sombra dura 1px (legible sobre el mundo)."""
    sh = font.render(text, False, shadow)
    surf.blit(sh, (pos[0] + 1, pos[1] + 1))
    t = font.render(text, False, color)
    surf.blit(t, pos)
    return t


def _dim(surf, rgb=(0, 0, 0), alpha=150):
    """Oscurece toda la pantalla de forma translucida.

    pygame.draw con color alfa sobre la pantalla (sin alfa) pintaria
    OPACO; por eso se usa una capa intermedia con SRCALPHA + blit.
    """
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    layer.fill((*rgb, alpha))
    surf.blit(layer, (0, 0))


def draw_item_icon(surf, item_id, rect):
    """Icono del item. Delega en textures.py (iconos bonitos cacheados).

    Conecta con: hotbar, inventario, crafteo y drops (via game.py).
    Misma firma de siempre para no romper llamadas."""
    import textures
    x, y, w, h = rect
    size = min(w, h)
    icon = textures.get_item_icon(item_id, size=size)
    surf.blit(icon, (x + (w - size) // 2, y + (h - size) // 2))


def draw_text_center(surf, text, size, color, y):
    f = _font(size)
    t = f.render(text, False, color)
    surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, y))


def draw_menu(surf, title_sel=0, has_save=False):
    surf.fill((10, 12, 30))
    # estrellas animadas
    import random
    rng = random.Random(7)
    for _ in range(150):
        x, y = rng.randint(0, SCREEN_W), rng.randint(0, SCREEN_H)
        brillo = rng.randint(150, 235)
        sz = rng.choice((1, 1, 2, 2, 3))
        surf.fill((brillo, brillo, min(255, brillo + 20)), (x, y, sz, sz))
    # titulo con sombra
    draw_text_center(surf, "UNDERDOWN", 72, (255, 200, 80), 100)
    draw_text_center(surf, "Una aventura estilo Terraria - Kael vs el Rey Mokulon", 20, (180, 190, 220), 190)
    # menu con opciones separadas
    if has_save:
        opts = ["NUEVA PARTIDA", "CONTINUAR", "COMO JUGAR", "SALIR"]
    else:
        opts = ["NUEVA PARTIDA", "COMO JUGAR", "SALIR"]
    for i, o in enumerate(opts):
        col = (255, 255, 255) if i == title_sel else (140, 150, 180)
        bg = UI_PANEL if i == title_sel else None
        f = _font(28)
        t = f.render(("> " if i == title_sel else "  ") + o, False, col, bg)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 280 + i * 60))
    draw_text_center(surf, "W/S o flechas + ENTER  |  v2.0 UnderDown", 18, (120, 130, 160), SCREEN_H - 60)


def draw_help(surf):
    surf.fill(UI_BG)
    draw_text_center(surf, "COMO JUGAR", 48, UI_ACCENT, 30)
    lines = [
        "A/D o flechas: moverse   |   ESPACIO: saltar   |   SHIFT: sprint",
        "Salto en pared: pegate, desliza y pulsa ESPACIO (wall-jump)",
        "Click IZQUIERDO: picar bloque / atacar con espada",
        "Click DERECHO: colocar / comer / pocion / hablar con NPC",
        "1-0 o RUEDA del mouse: hotbar   |   E: inventario / puerta / cofre   |   C: crafteo   |   J: misiones",
        "- / = : alejar / acercar vista",
        "Q: tirar item   |   F: antorcha rapida   |   T: comprar a Liora   |   ESC: pausa",
        "--- 3 CAPAS DE BLOQUES ---",
        "CAPA 1 (frente): bloques solidos con colision (tierra, piedra, etc.)",
        "CAPA 2 (objetos): camas, mesas, antorchas, arboles - ATRAVESABLES",
        "CAPA 3 (fondo): paredes traseras - ATRAVESABLES, solo con MARTILLO",
        "--- BIOMAS SUBTERRANEOS ---",
        "Hongos brillantes, bosques subterraneos, civilizaciones antiguas",
        "El ABISMO: crater gigante de 7 capas. SUBIR = Maldicion.",
        "Habla con Liora y Bruno (!): misiones con recompensa. J para verlas",
        "ENTER o ESC para volver",
    ]
    f = _font(17)
    for i, l in enumerate(lines):
        t = f.render(l, False, (220, 225, 240))
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 100 + i * 34))


def draw_hud(surf, player, world, msg, boss=None, layer_idx=0):
    # barra vida / mana / hambre
    pygame.draw.rect(surf, (0, 0, 0), (12, 12, 244, 22))
    pygame.draw.rect(surf, (180, 30, 30), (14, 14, 240 * (player.hp / player.max_hp), 18))
    f = _font(16)
    surf.blit(f.render(f"{int(player.hp)}/{player.max_hp}", False, (255, 255, 255)), (16, 13))
    pygame.draw.rect(surf, (0, 0, 0), (12, 38, 204, 14))
    pygame.draw.rect(surf, (50, 100, 230), (14, 40, 200 * (player.mana / player.max_mana), 10))
    hunger = getattr(player, "hunger", 100)
    max_h = getattr(player, "max_hunger", 100)
    pygame.draw.rect(surf, (0, 0, 0), (12, 54, 204, 12))
    hcol = (230, 150, 40) if hunger > 25 else (220, 50, 50)
    pygame.draw.rect(surf, hcol, (14, 56, 200 * (hunger / max_h), 8))
    surf.blit(f.render("HAMBRE" if hunger <= 25 else "", False, (255, 120, 120)), (220, 53))
    # defensa + hora + capa del Abismo
    import abyss
    t = "DIA" if not world.is_night() else "NOCHE"
    lname = abyss.get_layer(layer_idx)["name"] if layer_idx else t
    surf.blit(f.render(f"DEF {player.defense}  |  {lname}  |  {' '.join(k for k in player.buffs)}", False, (255, 255, 255)), (12, 70))
    if boss:
        pygame.draw.rect(surf, (0, 0, 0), (SCREEN_W // 2 - 250, 12, 500, 20))
        pygame.draw.rect(surf, (160, 40, 200), (SCREEN_W // 2 - 248, 14, 496 * max(0, boss.hp / boss.max_hp), 16))
        surf.blit(f.render("REY MOKULON", False, (255, 255, 255)), (SCREEN_W // 2 - 60, 14))
    # hotbar
    inv = player.inventory
    for i in range(10):
        x = SCREEN_W // 2 - 10 * 26 + i * 52
        y = SCREEN_H - 60
        col = (255, 220, 120) if i == inv.selected else (60, 64, 90)
        pygame.draw.rect(surf, (20, 22, 36), (x, y, 48, 48))
        pygame.draw.rect(surf, col, (x, y, 48, 48), 2 if i == inv.selected else 1)
        s = inv.slots[i]
        if s:
            draw_item_icon(surf, s["id"], (x, y, 48, 48))
            n = _font(14).render(str(s["count"]), False, (255, 255, 255))
            surf.blit(n, (x + 30, y + 30))
        num = _font(12).render(str((i + 1) % 10), False, (150, 150, 170))
        surf.blit(num, (x + 3, y + 2))
    if msg:
        m = _font(18).render(msg, False, (255, 240, 180))
        surf.blit(m, (SCREEN_W // 2 - m.get_width() // 2, SCREEN_H - 110))


def draw_inventory(surf, player, held, mx, my):
    inv = player.inventory
    W, H = 560, 420
    x0, y0 = SCREEN_W // 2 - W // 2, SCREEN_H // 2 - H // 2
    _dim(surf)
    pygame.draw.rect(surf, UI_PANEL, (x0, y0, W, H))
    pygame.draw.rect(surf, UI_ACCENT, (x0, y0, W, H), 2)
    f = _font(20)
    surf.blit(f.render("INVENTARIO  (E cerrar | click: agarrar/soltar | click der. en armadura: equipar)", False, (255, 255, 255)), (x0 + 12, y0 + 8))
    # armadura
    labels = ["Casco", "Peto", "Botas"]
    armor_rects = []
    for i in range(3):
        ax = x0 + 20 + i * 64
        ay = y0 + 40
        pygame.draw.rect(surf, (15, 18, 32), (ax, ay, 56, 56))
        pygame.draw.rect(surf, (150, 150, 220), (ax, ay, 56, 56), 1)
        surf.blit(_font(12).render(labels[i], False, (170, 170, 200)), (ax + 4, ay - 16))
        a = inv.armor[i]
        if a:
            draw_item_icon(surf, a["id"], (ax, ay, 56, 56))
        armor_rects.append(pygame.Rect(ax, ay, 56, 56))
    # slots
    slot_rects = []
    for i in range(inv.SIZE):
        r = i % 10
        rr = i // 10
        sx = x0 + 20 + r * 52
        sy = y0 + 120 + rr * 56
        if i < 10:
            pygame.draw.rect(surf, (50, 45, 20), (sx - 2, sy - 2, 52, 52))
        pygame.draw.rect(surf, (15, 18, 32), (sx, sy, 48, 48))
        pygame.draw.rect(surf, (90, 95, 130), (sx, sy, 48, 48), 1)
        s = inv.slots[i]
        if s:
            draw_item_icon(surf, s["id"], (sx, sy, 48, 48))
            info = ITEMS.get(s["id"], {})
            n = _font(14).render(str(s["count"]), False, (255, 255, 255))
            surf.blit(n, (sx + 30, sy + 30))
        slot_rects.append(pygame.Rect(sx, sy, 48, 48))
    # tooltip del seleccionado / held
    if held and held.get("id"):
        draw_item_icon(surf, held["id"], (mx - 20, my - 20, 40, 40))
        info = ITEMS.get(held["id"], {})
        tip = f'{info.get("name", held["id"])}: {info.get("desc", "")}'
        t = _font(16).render(tip, False, (255, 240, 180))
        surf.blit(t, (mx + 16, my))
    return slot_rects, armor_rects


def draw_crafting(surf, player, recipes_state, scroll, mx, my):
    W, H = 620, 440
    x0, y0 = SCREEN_W // 2 - W // 2, SCREEN_H // 2 - H // 2
    _dim(surf)
    pygame.draw.rect(surf, UI_PANEL, (x0, y0, W, H))
    pygame.draw.rect(surf, UI_ACCENT, (x0, y0, W, H), 2)
    surf.blit(_font(22).render("CRAFTEO  (C cerrar | click en VERDE para crear | rueda para bajar)", False, (255, 255, 255)), (x0 + 12, y0 + 8))
    row_rects = []
    f = _font(16)
    sf = _font(13)
    y = y0 + 44 - scroll
    for r, ok in recipes_state:
        if y < y0 + 30 or y > y0 + H - 30:
            y += 46
            continue
        col = (40, 90, 50) if ok else (60, 60, 75)
        pygame.draw.rect(surf, col, (x0 + 12, y, W - 24, 40))
        draw_item_icon(surf, r["result"], (x0 + 16, y, 40, 40))
        info = ITEMS.get(r["result"], {})
        mats = ", ".join(f"{k}x{v}" for k, v in r["materials"].items())
        st = r.get("station")
        stag = "" if not st else (" [MESA]" if st == "workbench" else " [HORNO]")
        t = f.render(f'{info.get("name", r["result"])} x{r["count"]}{stag}', False, (255, 255, 255))
        surf.blit(t, (x0 + 62, y + 2))
        surf.blit(sf.render(mats, False, (230, 230, 200)), (x0 + 62, y + 22))
        row_rects.append((pygame.Rect(x0 + 12, y, W - 24, 40), r, ok))
        y += 46
    return row_rects


def draw_pause(surf, sel=0):
    _dim(surf)
    draw_text_center(surf, "PAUSA", 56, UI_ACCENT, 200)
    opts = ["SEGUIR", "GUARDAR MUNDO", "AJUSTES", "SALIR AL MENU"]
    for i, o in enumerate(opts):
        f = _font(28)
        col = (255, 255, 255) if i == sel else (140, 150, 180)
        t = f.render(("> " if i == sel else "  ") + o, False, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 300 + i * 55))


def draw_settings(surf, sel=0, res_idx=0, fullscreen=False):
    _dim(surf)
    draw_text_center(surf, "AJUSTES", 56, UI_ACCENT, 80)
    # Resolucion
    draw_text_center(surf, f"RESOLUCION: {RESOLUTIONS[res_idx][0]}x{RESOLUTIONS[res_idx][1]}  (< >)", 24,
                     (255, 255, 255) if sel == 0 else (140, 150, 180), 200)
    # Pantalla completa
    fs_txt = "SI" if fullscreen else "NO"
    draw_text_center(surf, f"PANTALLA COMPLETA: {fs_txt}  (ENTER)", 24,
                     (255, 255, 255) if sel == 1 else (140, 150, 180), 260)
    # Volver
    draw_text_center(surf, "VOLVER  (ESC)", 24,
                     (255, 255, 255) if sel == 2 else (140, 150, 180), 340)
    draw_text_center(surf, "ESC: volver al juego  |  los cambios se aplican al momento", 16, (120, 130, 160), SCREEN_H - 50)


def draw_confirm(surf, text, sel=0):
    _dim(surf, (60, 20, 20), 180)
    draw_text_center(surf, text, 28, (255, 200, 120), SCREEN_H // 2 - 60)
    for i, o in enumerate(["SI", "NO"]):
        f = _font(26)
        col = (255, 255, 255) if i == sel else (140, 150, 180)
        t = f.render(("> " if i == sel else "  ") + o, False, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2 + 20 + i * 50))


def draw_char_create(surf, sel=0, skin_idx=0, hair_idx=0, eye_idx=0, name="Kael", editing=False):
    import time
    surf.fill((10, 12, 30))
    draw_text_center(surf, "CREAR PERSONAJE", 52, UI_ACCENT, 30)
    f24 = _font(24)
    f20 = _font(20)
    cx = SCREEN_W // 2
    # Nombres legibles para cada color
    SKIN_NAMES = ["Claro", "Medio", "Moreno", "Oscuro"]
    HAIR_NAMES = ["Castano", "Negro", "Rubio", "Rojo", "Gris"]
    EYE_NAMES = ["Negro", "Azul", "Verde", "Marron"]
    skin_name = SKIN_NAMES[skin_idx] if 0 <= skin_idx < len(SKIN_NAMES) else f"{skin_idx + 1}"
    hair_name = HAIR_NAMES[hair_idx] if 0 <= hair_idx < len(HAIR_NAMES) else f"{hair_idx + 1}"
    eye_name = EYE_NAMES[eye_idx] if 0 <= eye_idx < len(EYE_NAMES) else f"{eye_idx + 1}"

    # Cursor parpadeante para el nombre
    name_shown = name
    if sel == 0 and editing and int(time.time() * 2) % 2 == 0:
        name_shown = name + "|"
    elif sel == 0:
        name_shown = name + "_"

    y_name, y_skin, y_hair, y_eye, y_start = 110, 165, 275, 385, 495
    rows = [
        (0, y_name, f"NOMBRE: {name_shown}"),
        (1, y_skin, f"PIEL: < {skin_name} >"),
        (2, y_hair, f"CABELLO: < {hair_name} >"),
        (3, y_eye, f"OJOS: < {eye_name} >"),
        (4, y_start, "EMPEZAR AVENTURA"),
    ]
    for i, y, o in rows:
        col = (255, 255, 255) if i == sel else (140, 150, 180)
        t = f24.render(("> " if i == sel else "  ") + o, False, col)
        surf.blit(t, (cx - t.get_width() // 2, y))
        if i == 0 and editing:
            h = f20.render("escribe + ENTER para confirmar", False, (255, 220, 130))
            surf.blit(h, (cx - h.get_width() // 2, y + 32))

    # Muestras de colores (sin solaparse con el texto: debajo de cada etiqueta)
    def _swatches(colors, idx, y):
        n = len(colors)
        bw, gap = 40, 10
        total = n * bw + (n - 1) * gap
        x0 = cx - total // 2
        rects = []
        for j, c in enumerate(colors):
            bx = x0 + j * (bw + gap)
            pygame.draw.rect(surf, c, (bx, y, bw, 28))
            if j == idx:
                pygame.draw.rect(surf, (255, 255, 100), (bx - 2, y - 2, bw + 4, 32), 3)
            else:
                pygame.draw.rect(surf, (60, 64, 90), (bx - 2, y - 2, bw + 4, 32), 1)
            rects.append(pygame.Rect(bx - 2, y - 2, bw + 4, 32))
        return rects

    skin_rects = _swatches(SKIN_COLORS, skin_idx, y_skin + 34)
    hair_rects = _swatches(HAIR_COLORS, hair_idx, y_hair + 34)
    eye_rects = _swatches(EYE_COLORS, eye_idx, y_eye + 34)

    # Preview del personaje (miniatura)
    try:
        import textures
        skin_c = SKIN_COLORS[skin_idx]
        hair_c = HAIR_COLORS[hair_idx]
        eye_c = EYE_COLORS[eye_idx]
        preview = textures.get_player_preview(skin_c, hair_c, eye_c)
        if preview:
            big = pygame.transform.scale(preview, (60, 120))
            surf.blit(big, (cx + 260, 200))
            lab = _font(16).render(name or "Kael", False, (255, 220, 130))
            surf.blit(lab, (cx + 260 + 30 - lab.get_width() // 2, 325))
    except Exception:
        pass

    draw_text_center(surf, "W/S: elegir  A/D o click: cambiar color  ENTER: editar/confirmar  ESC: volver", 16, (120, 130, 160), SCREEN_H - 40)
    return {"skin": skin_rects, "hair": hair_rects, "eye": eye_rects,
            "start": pygame.Rect(cx - 160, y_start - 6, 320, 40)}


def draw_loading(surf, frac, label="Generando mundo...", tip=""):
    """Pantalla de carga con barra de progreso (nueva partida / cargar).

    frac 0..1, label = fase actual, tip = consejo rotativo."""
    surf.fill((10, 12, 30))
    import random
    rng = random.Random(7)
    for _ in range(120):
        x, y = rng.randint(0, SCREEN_W), rng.randint(0, SCREEN_H)
        brillo = rng.randint(150, 235)
        sz = rng.choice((1, 1, 2, 2, 3))
        surf.fill((brillo, brillo, min(255, brillo + 20)), (x, y, sz, sz))
    draw_text_center(surf, "UNDERDOWN", 64, (255, 200, 80), 120)
    draw_text_center(surf, label, 24, (255, 255, 255), 260)
    # barra
    bw, bh = min(560, SCREEN_W - 200), 30
    bx, by = SCREEN_W // 2 - bw // 2, 320
    pygame.draw.rect(surf, (20, 22, 36), (bx - 4, by - 4, bw + 8, bh + 8))
    pygame.draw.rect(surf, (90, 95, 130), (bx - 4, by - 4, bw + 8, bh + 8), 2)
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, (60, 60, 75), (bx, by, bw, bh))
    if frac > 0:
        pygame.draw.rect(surf, (255, 200, 80), (bx, by, int(bw * frac), bh))
        pygame.draw.rect(surf, (255, 240, 180), (bx, by, int(bw * frac), 6))
    pct = _font(20).render(f"{int(frac * 100)}%", False, (255, 240, 180))
    surf.blit(pct, (SCREEN_W // 2 - pct.get_width() // 2, by + bh + 12))
    if tip:
        draw_text_center(surf, tip, 16, (140, 150, 180), SCREEN_H - 80)
    draw_text_center(surf, "Generar el mundo puede tardar unos segundos...", 16, (120, 130, 160), SCREEN_H - 50)


def draw_dead(surf, t_left):
    _dim(surf, (80, 0, 0), 160)
    draw_text_center(surf, "HAS MUERTO", 64, (255, 80, 80), 220)
    draw_text_center(surf, f"Kael renace en {t_left:.1f}s... (pierdes la mitad de tus monedas)", 22, (255, 220, 220), 320)


def draw_quests(surf, quests):
    """Panel de misiones (J). quests = QuestState de quests.py."""
    from quests import QUESTS
    W, H = 640, 460
    x0, y0 = SCREEN_W // 2 - W // 2, SCREEN_H // 2 - H // 2
    _dim(surf)
    pygame.draw.rect(surf, UI_PANEL, (x0, y0, W, H))
    pygame.draw.rect(surf, UI_ACCENT, (x0, y0, W, H), 2)
    surf.blit(_font(24).render("MISIONES  (J cerrar | habla con quien tenga ! )", False, (255, 255, 255)), (x0 + 12, y0 + 8))
    y = y0 + 48
    for qid, estado, prog in quests.status_list():
        q = QUESTS[qid]
        if estado == "done":
            col, mark = (40, 90, 50), "[OK]"
        elif estado == "active":
            col, mark = (90, 70, 20), "[**]"
        elif estado == "new":
            col, mark = (50, 60, 110), "[!]"
        else:
            col, mark = (45, 45, 60), "[..]"
        pygame.draw.rect(surf, col, (x0 + 12, y, W - 24, 62))
        giver = "Liora" if q["giver"] == "liora" else "Bruno"
        surf.blit(_font(17).render(f"{mark} {q['name']}  ({giver})  {prog}", False, (255, 255, 255)), (x0 + 20, y + 4))
        surf.blit(_font(14).render(q["desc"][:78], False, (220, 220, 200)), (x0 + 20, y + 26))
        rw = ", ".join(f"{ITEMS.get(i, {}).get('name', i)}x{c}" for i, c in q["reward"])
        surf.blit(_font(13).render("Recompensa: " + rw, False, (255, 220, 150)), (x0 + 20, y + 44))
        y += 68


def draw_layer_banner(surf, layer_idx, alpha=255):
    """Nombre grande de la capa al entrar (estilo Made in Abyss)."""
    import abyss
    L = abyss.get_layer(layer_idx)
    if layer_idx <= 0:
        return
    a = max(0, min(255, alpha))
    f1, f2 = _font(54), _font(22)
    t1 = f1.render(L["name"], False, (240, 230, 255))
    t1.set_alpha(a)
    t2 = f2.render(L["sub"], False, (200, 190, 220))
    t2.set_alpha(a)
    surf.blit(t1, (SCREEN_W // 2 - t1.get_width() // 2, 140))
    surf.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, 210))
