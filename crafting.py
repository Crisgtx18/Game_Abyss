# Recetas de crafteo
# station: None (mano) | "workbench" (mesa) | "furnace" (horno)

RECIPES = [
    # estaciones
    dict(result="mesa_trabajo", count=1, materials={"madera": 10}, station=None, desc="Mesa de trabajo"),
    dict(result="horno", count=1, materials={"piedra": 20, "madera": 5, "antorcha": 2}, station="workbench", desc="Horno fundidor"),
    dict(result="antorcha", count=5, materials={"madera": 1, "carbon": 1}, station=None, desc="5 antorchas"),
    dict(result="tablones", count=4, materials={"madera": 1}, station=None, desc="4 tablones"),

    # palos y base
    dict(result="palo", count=4, materials={"madera": 1}, station=None, desc="Palos"),

    # picos
    dict(result="pico_madera", count=1, materials={"madera": 8, "palo": 4}, station=None, desc="Pico inicial"),
    dict(result="pico_piedra", count=1, materials={"piedra": 12, "palo": 4}, station="workbench", desc="Pica hierro"),
    dict(result="pico_hierro", count=1, materials={"lingote_hierro": 10, "palo": 4}, station="workbench", desc="Pica oro"),
    dict(result="pico_oro", count=1, materials={"lingote_oro": 10, "palo": 4}, station="workbench", desc="Pica diamante"),
    dict(result="pico_diamante", count=1, materials={"diamante": 10, "palo": 4}, station="workbench", desc="El mejor"),

    # hachas
    dict(result="hacha_madera", count=1, materials={"madera": 6, "palo": 3}, station=None, desc="Hacha basica"),
    dict(result="hacha_hierro", count=1, materials={"lingote_hierro": 8, "palo": 3}, station="workbench", desc="Hacha veloz"),
    dict(result="hacha_diamante", count=1, materials={"diamante": 8, "palo": 3}, station="workbench", desc="Hacha final"),

    # martillos (rompen bloques traseros / raseros)
    dict(result="martillo_madera", count=1, materials={"madera": 8, "palo": 3}, station=None, desc="Rompe paredes"),
    dict(result="martillo_piedra", count=1, materials={"piedra": 10, "palo": 3}, station="workbench", desc="Martillo solido"),
    dict(result="martillo_hierro", count=1, materials={"lingote_hierro": 8, "palo": 3}, station="workbench", desc="Martillo soldado"),
    dict(result="martillo_diamante", count=1, materials={"diamante": 8, "palo": 3}, station="workbench", desc="Martillo final"),

    # paredes / losas (construccion de fondo)
    dict(result="pared_rustica", count=8, materials={"madera": 2}, station=None, desc="8 paredes de fondo"),
    dict(result="pared_abisal", count=8, materials={"roca_abisal": 2}, station="workbench", desc="8 paredes abisales"),
    dict(result="losa_musgosa", count=4, materials={"piedra": 3, "hoja": 2}, station="workbench", desc="4 losas bajas"),

    # muebles (para casas y cabañas)
    dict(result="cama", count=1, materials={"madera": 12, "hoja": 6}, station="workbench", desc="Cama rustica"),
    dict(result="silla", count=1, materials={"madera": 6}, station="workbench", desc="Silla de madera"),
    dict(result="farol", count=2, materials={"madera": 2, "baya_luminosa": 2}, station="workbench", desc="2 faroles"),
    dict(result="puerta", count=1, materials={"madera": 6}, station="workbench", desc="Puerta (ocupa 2 de alto)"),
    dict(result="ventana", count=2, materials={"arena": 6}, station="furnace", desc="2 ventanas de cristal"),

    # espadas
    dict(result="espada_madera", count=1, materials={"madera": 8}, station=None, desc="Espada de Kael"),
    dict(result="espada_piedra", count=1, materials={"piedra": 12}, station="workbench", desc="+dano"),
    dict(result="espada_hierro", count=1, materials={"lingote_hierro": 12}, station="workbench", desc="Hoja soldado"),
    dict(result="espada_oro", count=1, materials={"lingote_oro": 12}, station="workbench", desc="Hoja dorada"),
    dict(result="espada_diamante", count=1, materials={"diamante": 14}, station="workbench", desc="Arma legendaria"),

    # fundicion
    dict(result="lingote_hierro", count=1, materials={"hierro_crudo": 3, "carbon": 1}, station="furnace", desc="Fundir hierro"),
    dict(result="lingote_oro", count=1, materials={"oro_crudo": 3, "carbon": 1}, station="furnace", desc="Fundir oro"),
    dict(result="ladrillo", count=4, materials={"piedra": 4}, station="furnace", desc="Ladrillos"),

    # armaduras cuero (gel de Mokis = cuero)
    dict(result="casco_cuero", count=1, materials={"gel": 8}, station="workbench", desc="Capucha"),
    dict(result="peto_cuero", count=1, materials={"gel": 14}, station="workbench", desc="Peto cuero"),
    dict(result="botas_cuero", count=1, materials={"gel": 8}, station="workbench", desc="Botas cuero"),
    # hierro
    dict(result="casco_hierro", count=1, materials={"lingote_hierro": 8}, station="workbench", desc="+3 def"),
    dict(result="peto_hierro", count=1, materials={"lingote_hierro": 14}, station="workbench", desc="+5 def"),
    dict(result="botas_hierro", count=1, materials={"lingote_hierro": 8}, station="workbench", desc="+3 def"),
    # oro
    dict(result="casco_oro", count=1, materials={"lingote_oro": 8}, station="workbench", desc="+4 def"),
    dict(result="peto_oro", count=1, materials={"lingote_oro": 14}, station="workbench", desc="+6 def"),
    dict(result="botas_oro", count=1, materials={"lingote_oro": 8}, station="workbench", desc="+4 def"),
    # diamante
    dict(result="casco_diamante", count=1, materials={"diamante": 10}, station="workbench", desc="+6 def"),
    dict(result="peto_diamante", count=1, materials={"diamante": 18}, station="workbench", desc="+10 def"),
    dict(result="botas_diamante", count=1, materials={"diamante": 10}, station="workbench", desc="+6 def"),

    # pociones
    dict(result="pocion_vida_menor", count=1, materials={"gel": 4, "hoja": 3}, station=None, desc="Cura 50"),
    dict(result="pocion_vida_mayor", count=1, materials={"pocion_vida_menor": 1, "oro_crudo": 2, "gel": 4}, station="workbench", desc="Cura 120"),
    dict(result="pocion_piel_hierro", count=1, materials={"gel": 5, "hierro_crudo": 2}, station="workbench", desc="+8 def 60s"),
    dict(result="pocion_regen", count=1, materials={"gel": 5, "hoja": 6}, station="workbench", desc="Regen 30s"),
    dict(result="pocion_velocidad", count=1, materials={"gel": 3, "arena": 5}, station="workbench", desc="Velocidad 45s"),
    dict(result="corona_viscosa", count=1, materials={"gel": 25, "oro_crudo": 5}, station="workbench", desc="Invoca al Rey Mokulon"),

    # cocina (estilo Starbound: lo crudo rinde poco, lo cocinado mucho)
    dict(result="carne_cocida", count=1, materials={"carne_cruda": 2, "carbon": 1}, station="furnace", desc="+35 saciedad, +15 vida"),
    dict(result="pan_hongo", count=2, materials={"hoja": 6, "gel": 3}, station="furnace", desc="+25 saciedad c/u"),
    dict(result="brocheta", count=1, materials={"carne_cocida": 1, "baya_luminosa": 2}, station=None, desc="+45 saciedad, +20 vida"),
    dict(result="estofado_abismo", count=1, materials={"carne_cocida": 1, "baya_luminosa": 3, "hoja": 4}, station="workbench", desc="Cura la Maldicion"),
    dict(result="pocion_antimaldicion", count=1, materials={"gel": 4, "baya_luminosa": 3}, station="workbench", desc="Limpia maldicion y esporas"),
]


def available_recipes(inventory, stations):
    """Devuelve lista de (receta, crafteable_bool)."""
    out = []
    for r in RECIPES:
        st = r.get("station")
        if st and st not in stations:
            out.append((r, False))
            continue
        ok = all(inventory.count_of(k) >= v for k, v in r["materials"].items())
        out.append((r, ok))
    return out


def craft(inventory, recipe):
    for k, v in recipe["materials"].items():
        if inventory.count_of(k) < v:
            return False, "Faltan materiales"
    for k, v in recipe["materials"].items():
        inventory.remove(k, v)
    leftover = inventory.add(recipe["result"], recipe["count"])
    if leftover > 0:
        # devolver materiales si no cabe (simple)
        for k, v in recipe["materials"].items():
            inventory.add(k, v)
        return False, "Inventario lleno"
    return True, "Creado: " + recipe["result"]
