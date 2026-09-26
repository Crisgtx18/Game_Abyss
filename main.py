#!/usr/bin/env python3
# UnderDown - juego estilo Terraria 2D
# Ejecutar: python3 main.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import Game

if __name__ == "__main__":
    Game().run()