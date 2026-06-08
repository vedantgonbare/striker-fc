"""
STRIKER FC — Entry point.
Initialises Pygame + mixer, then boots the game engine.
"""

import pygame
import sys

# Pre-init mixer BEFORE pygame.init() for best audio quality
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
try:
    pygame.mixer.init(44100, -16, 2, 512)
except Exception:
    pass   # audio unavailable — game runs silently

from src.core.game     import Game
from src.core.settings import WINDOW_WIDTH, WINDOW_HEIGHT, GAME_TITLE, FPS


def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(GAME_TITLE)
    clock  = pygame.time.Clock()

    game = Game(screen, clock)
    game.run()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()