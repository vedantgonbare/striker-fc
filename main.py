"""
FIFA-Style Football Game
Entry point — initialises Pygame and boots the game engine.
"""

import pygame
import sys
from src.core.game import Game
from src.core.settings import WINDOW_WIDTH, WINDOW_HEIGHT, GAME_TITLE, FPS


def main():
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(GAME_TITLE)

    clock = pygame.time.Clock()
    game = Game(screen, clock)
    game.run()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()