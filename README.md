# UNDERDOWN - Terraria 2D en Python + Pygame

Aventura 2D estilo Terraria. Eres **Kael el Explorador** y debes sobrevivir,
minar hasta el fondo, equiparte y derrotar al **Rey Underdown**.

## Personajes inventados
- **Kael** (tu): explorador de la superficie.
- **Maestra Liora** (NPC): vende pociones (acercate y pulsa `T`, 10 cobres).
- **Slime verde / azul / rojo**: slimes saltarines (el rojo sale de noche).
- **Putrek**: zombie nocturno. **Karkas**: esqueleto de cueva.
- **Vesper**: murcielago volador. **Rokthar**: golem de las profundidades.
- **Rey Underdown** (boss): invocalo con la **Corona viscosa** en el **Altar de Underdown**.

## Controles
- `A/D` moverse, `ESPACIO` saltar
- Click izq: picar / atacar | Click der: colocar / comer / pocion / hablar
- `1-0` hotbar, `E` inventario, `C` crafteo, `J` misiones, `Q` tirar, `F` antorcha
- `T` comprar a Liora, `ESC` pausa, rueda en crafteo para scroll

## Hambre y comida (estilo Starbound)
El hambre baja sola (x3 en el fondo del Abismo); a 0 te hace dano, llena
regenera. Manzanas (hojas), bayas (flores abisales), carne cruda (bichos,
puede caer mal) y cocina al HORNO: carne cocida, pan de hongo, brochetas y
el estofado del Abismo (cura la Maldicion).

## El Abismo (estilo Made in Abyss)
Una fosa enorme cruza el mapa con 6 capas: Borde, Bosque de Tentaculos,
Gran Falla, Copas, Mar de Cadaveres y Capital del Retorno. Cada capa tiene
su color, sus bichos (Orbe rastrero, Sedaluz, Dientepiedra, Eco profundo y
el Heraldo, mini-jefe con Orbe), mas oscuridad y hambre. Y la Maldicion:
SUBIR rapido dentro de la fosa te hiere y te deja pesadez. Bruno el Vigia
vive en el borde: acepta sus misiones (!).

## Misiones (Liora y Bruno, tecla J)
Madera y Slimes con Liora; bajar a la Capa 2, comer, traer un Orbe y matar
al Heraldo con Bruno. Habla con quien tenga `!` para aceptar/entregar.

## Progresion
1. Tala arboles (madera) > mesa de trabajo > pico de piedra.
2. Baja a cuevas: carbon, hierro + horno > lingotes > armadura y espada hierro.
3. Oro > diamante (fondo del mundo, cerca del bedrock).
4. Fabrica la Corona viscosa (25 gel + 5 oro) y ve al Altar de ladrillo.

## Estructuras del mundo
Casa en ruinas (cofre + mesa), mina vertical con antorchas y cofre profundo,
Altar de Underdown, cofres de cueva, arboles, cuevas, playas de arena,
vetas de carbon/hierro/oro/diamante, bedrock al fondo.

## Carpetas (enrutamiento)
```
juego/
  main.py              <- entrada
  config.py            <- ajustes, lore, balance
  blocks.py            <- definicion de bloques/tierra/roca/minerales
  items.py             <- armas, armaduras, pociones, materiales
  crafting.py          <- recetas
  inventory.py         <- sistema de inventario + armadura
  world.py             <- generacion procedural + guardado
  game.py              <- bucle, camara, combate, dia/noche, drops
  ui.py                <- menus, HUD, inventario, crafteo
  audio.py             <- sonidos procedurales
  entities/
    player.py          <- Kael (fisicas, vida, buffs)
    npc.py             <- Liora
    mobs/
      enemies.py       <- todos los enemigos + boss
  assets/
    mobs/player/       <- sprites de Kael (procedurales, se generan)
    mobs/slime/ etc.
    tiles/ items/
  saves/               <- mundo.json + jugador.json (autoguardado)
```

Los sprites son procedurales (sin PNG externos) para que el juego funcione
directo. La carpeta `assets/mobs/...` guarda capturas y futuros sprites.

## Como ejecutar
```bash
pip install -r requirements.txt
python main.py
```
Solo requiere `pygame` (>=2.5). El juego se autoguarda al salir y desde
pausa > **GUARDAR MUNDO**. Python 3.10+ recomendado.

## Tecnologia
- **Python 3** + **Pygame** (sin motor externo: todos los sprites son
  procedurales, el juego funciona sin assets descargados)
- **Mundo generado por codigo**: ruido fractal + capas de bioma, cuevas,
  vetas de minerales y bedrock
- **Fisica propia**: gravedad, saltos, colisiones y plataformas solidas
- **Audio procedural**: sonidos sintetizados, sin archivos de audio
- **Persistencia en JSON**: `mundo.json` + `jugador.json` con autoguardado
- Sin assets externos: todo se genera al vuelo, por eso el repo pesa poco

## Licencia
Codigo de uso educativo. Si te sirve, cita el proyecto.
