"""
match.py — Live match screen (stub).
"""

import pygame
from src.core.base_screen import BaseScreen
from src.core.settings import PITCH_GREEN, WHITE, GOLD, STATE_MAIN_MENU


class MatchScreen(BaseScreen):
    def __init__(self, screen, change_state, home_team=None, away_team=None):
        super().__init__(screen, change_state)
        self.home_team = home_team
        self.away_team = away_team
        self.font = pygame.font.Font(None, 48)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.change_state(STATE_MAIN_MENU)

    def update(self, dt):
        pass

    def draw(self):
        self.screen.fill(PITCH_GREEN)
        label = self.font.render("MATCH  —  Coming Soon", True, WHITE)
        self.screen.blit(label, label.get_rect(center=(self.width // 2, self.height // 2)))
        hint = pygame.font.Font(None, 28).render("Press ESC to go back", True, (200,255,200))
        self.screen.blit(hint, hint.get_rect(center=(self.width // 2, self.height // 2 + 55)))