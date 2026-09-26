# Items: herramientas, armas, armaduras, pociones, materiales, comida, bloques.
# tipo: bloque | pico | hacha | espada | casco | peto | botas | pocion |
#       material | invocador | comida | estacion

ITEMS = {
    # ---- bloques (colocables) ----
    "tierra":        dict(name="Tierra", tipo="bloque", max_stack=999, desc="Bloque basico."),
    "piedra":        dict(name="Piedra", tipo="bloque", max_stack=999, desc="Dura y gris."),
    "madera":        dict(name="Tronco", tipo="bloque", max_stack=999, desc="Del arbol."),
    "hoja":         dict(name="Hoja", tipo="bloque", max_stack=999, desc="Hojas del arbol."),
    "arena":         dict(name="Arena", tipo="bloque", max_stack=999, desc="Fina arena."),
    "tablones":      dict(name="Tablones", tipo="bloque", max_stack=999, desc="Madera procesada."),
    "mesa_trabajo":  dict(name="Mesa de trabajo", tipo="bloque", estacion="workbench", max_stack=99, desc="Permite crafteos avanzados."),
    "horno":         dict(name="Horno", tipo="bloque", estacion="furnace", max_stack=99, desc="Funde minerales."),
    "antorcha":      dict(name="Antorcha", tipo="bloque", max_stack=999, desc="Ilumina cuevas. Click derecho."),
    "ladrillo":      dict(name="Ladrillo", tipo="bloque", max_stack=999, desc="De las ruinas."),
    "hierba":        dict(name="Bloque de hierba", tipo="bloque", max_stack=999, desc="Con cesped."),
    "flor_abisal":   dict(name="Flor abisal", tipo="bloque", max_stack=99, desc="Brilla en la oscuridad."),
    "roca_abisal":   dict(name="Roca abisal", tipo="bloque", max_stack=999, desc="Piedra del fondo."),
    # ---- biomas profundos (hongos brillantes) ----
    "micelio":       dict(name="Micelio brillante", tipo="bloque", max_stack=999, desc="Suelo fungico que brilla."),
    "tallo_fungico": dict(name="Tallo fungico", tipo="bloque", max_stack=999, desc="Tronco de seta gigante."),
    "seta_brillante":dict(name="Seta brillante", tipo="comida", hunger=18, heal=6, max_stack=30, desc="Brilla y alimenta. Click derecho."),
    # ---- bloques traseros / raseros (se pican con martillo) ----
    "pared_rustica": dict(name="Pared rustica", tipo="bloque", max_stack=999, desc="Pared de fondo. Se pica con martillo. No bloquea."),
    "pared_abisal":  dict(name="Pared abisal", tipo="bloque", max_stack=999, desc="Pared del Abismo. Solo martillo."),
    "losa_musgosa":  dict(name="Losa musgosa", tipo="bloque", max_stack=999, desc="Losa baja. Ideal con martillo."),
    # ---- temas del Abismo + muebles ----
    "pizarra":       dict(name="Pizarra abisal", tipo="bloque", max_stack=999, desc="Roca de La Gran Falla."),
    "hueso":         dict(name="Hueso antiguo", tipo="bloque", max_stack=999, desc="Del Mar de Cadaveres."),
    "farol":         dict(name="Farol", tipo="bloque", max_stack=99, desc="Luz calida. Click derecho."),
    "cama":          dict(name="Cama", tipo="bloque", max_stack=99, desc="Para descansar en tus casas."),
    "silla":         dict(name="Silla", tipo="bloque", max_stack=99, desc="Junto a la mesa."),
    "puerta":        dict(name="Puerta", tipo="bloque", max_stack=99, desc="Click derecho: abrir/cerrar."),
    "ventana":       dict(name="Ventana", tipo="bloque", max_stack=99, desc="Cristal: bloquea pero deja pasar la luz."),

    # ---- materiales ----
    "palo":          dict(name="Palo", tipo="material", max_stack=999, desc="Basico para herramientas."),
    "gel":           dict(name="Gel de slime", tipo="material", max_stack=999, desc="Baboso. Lo sueltan los Slimes."),
    "carbon":        dict(name="Carbon", tipo="material", max_stack=999, desc="Combustible y antorchas."),
    "hierro_crudo":  dict(name="Hierro crudo", tipo="material", max_stack=999, desc="Fundelo en horno."),
    "lingote_hierro":dict(name="Lingote de hierro", tipo="material", max_stack=999, desc="Metal fundido."),
    "oro_crudo":     dict(name="Oro crudo", tipo="material", max_stack=999, desc="Brillante."),
    "lingote_oro":   dict(name="Lingote de oro", tipo="material", max_stack=999, desc="Muy valioso."),
    "diamante":      dict(name="Diamante Underdown", tipo="material", max_stack=999, desc="El mineral mas duro."),
    "moneda_cobre":  dict(name="Moneda de cobre", tipo="material", max_stack=9999, desc="Dinero."),
    "moneda_plata":  dict(name="Moneda de plata", tipo="material", max_stack=9999, desc="100 cobres."),
    "moneda_oro":    dict(name="Moneda de oro", tipo="material", max_stack=9999, desc="100 platas."),
    "corazon":       dict(name="Corazon", tipo="material", max_stack=99, desc="Cura 20 al recoger.", heal=20),
    "estrella":      dict(name="Estrella", tipo="material", max_stack=99, desc="Recarga mana."),
    "reliquia_orbe": dict(name="Orbe del Abismo", tipo="material", max_stack=10, desc="Reliquia de grado 2. Bruno la busca."),

    # ---- comida (tipo="comida": hunger = saciedad, heal = vida) ----
    "manzana":       dict(name="Manzana del arbol", tipo="comida", hunger=15, heal=5, max_stack=30, desc="Cae de las hojas. Click derecho."),
    "baya_luminosa": dict(name="Baya luminosa", tipo="comida", hunger=12, heal=4, max_stack=30, desc="Brilla. Crece en flores abisales."),
    "carne_cruda":   dict(name="Carne cruda", tipo="comida", hunger=8, heal=0, max_stack=30, desc="Riesgo de indigestion. Mejor cocinala."),
    "carne_cocida":  dict(name="Carne cocida", tipo="comida", hunger=35, heal=15, max_stack=30, desc="Al horno con carbon."),
    "pan_hongo":     dict(name="Pan de hongo", tipo="comida", hunger=25, heal=8, max_stack=30, desc="Hojas + gel al horno. No preguntes."),
    "brocheta":      dict(name="Brocheta mixta", tipo="comida", hunger=45, heal=20, max_stack=20, desc="Carne y bayas."),
    "estofado_abismo":dict(name="Estofado del Abismo", tipo="comida", hunger=60, heal=40, cure=["maldicion", "espora"], max_stack=10, desc="Cura la Maldicion. Manjar de Vigia."),

    # ---- picos (power = multiplicador de minado, min_tier para ores) ----
    "pico_madera":   dict(name="Pico de madera", tipo="pico", power=1.0, damage=3, max_stack=1, desc="Para piedra y carbon."),
    "pico_piedra":   dict(name="Pico de piedra", tipo="pico", power=1.8, damage=4, max_stack=1, desc="Para hierro."),
    "pico_hierro":   dict(name="Pico de hierro", tipo="pico", power=2.8, damage=5, max_stack=1, desc="Para oro."),
    "pico_oro":      dict(name="Pico de oro", tipo="pico", power=3.6, damage=6, max_stack=1, desc="Rapido y dorado."),
    "pico_diamante": dict(name="Pico de diamante", tipo="pico", power=5.0, damage=8, max_stack=1, desc="El mejor pico."),

    # ---- hachas ----
    "hacha_madera":  dict(name="Hacha de madera", tipo="hacha", power=1.0, damage=3, max_stack=1, desc="Tala arboles."),
    "hacha_hierro":  dict(name="Hacha de hierro", tipo="hacha", power=2.5, damage=6, max_stack=1, desc="Tala veloz."),
    "hacha_diamante":dict(name="Hacha de diamante", tipo="hacha", power=4.5, damage=9, max_stack=1, desc="Corta todo."),

    # ---- martillos (para bloques traseros / raseros y losas) ----
    "martillo_madera":  dict(name="Martillo de madera", tipo="martillo", power=1.0, damage=4, max_stack=1, desc="Rompe paredes y losas."),
    "martillo_piedra":  dict(name="Martillo de piedra", tipo="martillo", power=1.8, damage=5, max_stack=1, desc="Mejor contra muros."),
    "martillo_hierro":  dict(name="Martillo de hierro", tipo="martillo", power=2.8, damage=7, max_stack=1, desc="Martillo soldado."),
    "martillo_diamante":dict(name="Martillo diamante Underdown", tipo="martillo", power=4.5, damage=10, max_stack=1, desc="Pulveriza paredes."),

    # ---- espadas (damage, knockback) ----
    "espada_madera": dict(name="Espada de madera", tipo="espada", damage=8, knock=4, cooldown=0.35, max_stack=1, desc="Arma inicial de Kael."),
    "espada_piedra": dict(name="Espada de piedra", tipo="espada", damage=12, knock=5, cooldown=0.32, max_stack=1, desc="Solida."),
    "espada_hierro": dict(name="Espada de hierro", tipo="espada", damage=18, knock=6, cooldown=0.30, max_stack=1, desc="De soldado."),
    "espada_oro":    dict(name="Espada de oro", tipo="espada", damage=24, knock=6, cooldown=0.28, max_stack=1, desc="Hoja dorada."),
    "espada_diamante":dict(name="Espada diamante Underdown", tipo="espada", damage=34, knock=8, cooldown=0.24, max_stack=1, desc="Forjada con diamantes."),

    # ---- armaduras (defensa) ----
    "casco_cuero":   dict(name="Capucha de cuero", tipo="casco", defensa=1, max_stack=1, desc="+1 defensa."),
    "peto_cuero":    dict(name="Peto de cuero", tipo="peto", defensa=2, max_stack=1, desc="+2 defensa."),
    "botas_cuero":   dict(name="Botas de cuero", tipo="botas", defensa=1, max_stack=1, desc="+1 defensa."),
    "casco_hierro":  dict(name="Casco de hierro", tipo="casco", defensa=3, max_stack=1, desc="+3 defensa."),
    "peto_hierro":   dict(name="Peto de hierro", tipo="peto", defensa=5, max_stack=1, desc="+5 defensa."),
    "botas_hierro":  dict(name="Botas de hierro", tipo="botas", defensa=3, max_stack=1, desc="+3 defensa."),
    "casco_oro":     dict(name="Casco de oro", tipo="casco", defensa=4, max_stack=1, desc="+4 defensa."),
    "peto_oro":      dict(name="Peto de oro", tipo="peto", defensa=6, max_stack=1, desc="+6 defensa."),
    "botas_oro":     dict(name="Botas de oro", tipo="botas", defensa=4, max_stack=1, desc="+4 defensa."),
    "casco_diamante":dict(name="Yelmo Underdown", tipo="casco", defensa=6, max_stack=1, desc="+6 defensa."),
    "peto_diamante": dict(name="Peto Underdown", tipo="peto", defensa=10, max_stack=1, desc="+10 defensa."),
    "botas_diamante":dict(name="Botas Underdown", tipo="botas", defensa=6, max_stack=1, desc="+6 defensa."),

    # ---- pociones / consumibles ----
    "pocion_vida_menor": dict(name="Pocion de vida menor", tipo="pocion", heal=50, cooldown=1.0, max_stack=30, desc="Cura 50 HP. Click derecho."),
    "pocion_vida_mayor": dict(name="Pocion de vida mayor", tipo="pocion", heal=120, cooldown=1.0, max_stack=30, desc="Cura 120 HP."),
    "pocion_piel_hierro":dict(name="Pocion piel de hierro", tipo="pocion", buff="iron_skin", dur=60, max_stack=20, desc="+8 defensa 60s."),
    "pocion_regen":  dict(name="Pocion de regeneracion", tipo="pocion", buff="regen", dur=30, max_stack=20, desc="Regenera vida 30s."),
    "pocion_velocidad":dict(name="Pocion de velocidad", tipo="pocion", buff="speed", dur=45, max_stack=20, desc="+40% velocidad 45s."),
    "pocion_antimaldicion":dict(name="Pocion antimaldicion", tipo="pocion", cure=["maldicion", "espora"], cooldown=1.0, max_stack=20, desc="Limpia maldicion y esporas."),
    "corona_viscosa":dict(name="Corona viscosa", tipo="invocador", max_stack=5, desc="Usala en el Altar de Underdown para invocar al Rey Underdown."),
}

# Que tier de pico exige cada mineral (power minima)
ORE_REQUIRE = {
    6: 1.0,   # carbon: madera vale
    7: 1.8,   # hierro: piedra+
    8: 2.8,   # oro: hierro+
    9: 3.6,   # diamante: oro+
    20: 1.8,  # roca abisal: piedra+
    23: 1.0,  # losa musgosa: martillo madera vale
    27: 2.8,  # pizarra abisal: hierro+
    28: 1.8,  # hueso antiguo: piedra+
}

def get_item(item_id):
    return ITEMS.get(item_id)
