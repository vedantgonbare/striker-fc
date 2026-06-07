"""
settings.py (screen) — Settings screen (stub).
"""

import pygame
from src.core.base_screen import BaseScreen
from src.core.settings import DARK_BG, GOLD, STATE_MAIN_MENU


class SettingsScreen(BaseScreen):
    def __init__(self, screen, change_state):
        super().__init__(screen, change_state)
        self.font = pygame.font.Font(None, 48)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.change_state(STATE_MAIN_MENU)

    def update(self, dt):
        pass

    def draw(self):
        self.screen.fill(DARK_BG)
        label = self.font.render("SETTINGS  —  Coming Soon", True, GOLD)
        self.screen.blit(label, label.get_rect(center=(self.width // 2, self.height // 2)))
        hint = pygame.font.Font(None, 28).render("Press ESC to go back", True, (120, 130, 150))
        self.screen.blit(hint, hint.get_rect(center=(self.width // 2, self.height // 2 + 55)))