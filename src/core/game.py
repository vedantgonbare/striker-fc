"""
game.py — Central Game class.
Owns the main loop, state machine, and screen transitions.
"""

import pygame
from src.core.settings import FPS, STATE_MAIN_MENU, STATE_TEAM_SELECT, STATE_MATCH, STATE_SETTINGS, STATE_QUIT
from src.screens.main_menu   import MainMenuScreen
from src.screens.team_select import TeamSelectScreen
from src.screens.match       import MatchScreen
from src.screens.settings    import SettingsScreen


class Game:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen  = screen
        self.clock   = clock
        self.running = True

        self._state   = STATE_MAIN_MENU
        self._screens = {}
        self._load_screen(STATE_MAIN_MENU)

    def _load_screen(self, state: str):
        if state in self._screens:
            return
        if state == STATE_MAIN_MENU:
            self._screens[state] = MainMenuScreen(self.screen, self._change_state)
        elif state == STATE_TEAM_SELECT:
            self._screens[state] = TeamSelectScreen(self.screen, self._change_state)
        elif state == STATE_MATCH:
            self._screens[state] = MatchScreen(self.screen, self._change_state)
        elif state == STATE_SETTINGS:
            self._screens[state] = SettingsScreen(self.screen, self._change_state)

    def _change_state(self, new_state: str):
        if new_state == STATE_QUIT:
            self.running = False
            return
        # Force fresh match screen each time
        if new_state == STATE_MATCH and new_state in self._screens:
            del self._screens[new_state]
        # Force fresh team select each time
        if new_state == STATE_TEAM_SELECT and new_state in self._screens:
            del self._screens[new_state]
        self._state = new_state
        self._load_screen(new_state)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            current_screen = self._screens.get(self._state)
            if current_screen is None:
                break

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            current_screen.handle_events(events)
            current_screen.update(dt)
            current_screen.draw()
            pygame.display.flip()