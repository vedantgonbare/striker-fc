"""
game.py — Central Game class + state machine.
Now passes selected team data from TeamSelectScreen → MatchScreen.
"""

import pygame
from src.core.settings import (
    FPS, STATE_MAIN_MENU, STATE_TEAM_SELECT,
    STATE_MATCH, STATE_SETTINGS, STATE_QUIT,
)
from src.screens.main_menu   import MainMenuScreen
from src.screens.team_select import TeamSelectScreen, TEAMS
from src.screens.match       import MatchScreen
from src.screens.settings    import SettingsScreen


class Game:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen       = screen
        self.clock        = clock
        self.running      = True
        self._state       = STATE_MAIN_MENU
        self._screens     = {}

        # Stores the two teams chosen in TeamSelectScreen
        # Each entry = full TEAMS tuple: (name, short, primary, secondary, ovr, ...)
        self.selected_home = TEAMS[0]
        self.selected_away = TEAMS[3]

        self._load_screen(STATE_MAIN_MENU)

    # ── Screen factory ────────────────────────────────────────────────────
    def _load_screen(self, state: str):
        if state in self._screens:
            return
        if state == STATE_MAIN_MENU:
            self._screens[state] = MainMenuScreen(self.screen, self._change_state)
        elif state == STATE_TEAM_SELECT:
            self._screens[state] = TeamSelectScreen(
                self.screen, self._change_state,
                on_confirm=self._on_teams_confirmed,
            )
        elif state == STATE_MATCH:
            self._screens[state] = MatchScreen(
                self.screen, self._change_state,
                home_team=self.selected_home,
                away_team=self.selected_away,
            )
        elif state == STATE_SETTINGS:
            self._screens[state] = SettingsScreen(self.screen, self._change_state)

    def _on_teams_confirmed(self, home, away):
        """Callback fired by TeamSelectScreen when both teams are locked."""
        self.selected_home = home
        self.selected_away = away

    def _change_state(self, new_state: str):
        if new_state == STATE_QUIT:
            self.running = False
            return
        # Always rebuild match + team-select screens (fresh state each time)
        for s in (STATE_MATCH, STATE_TEAM_SELECT):
            if new_state == s and s in self._screens:
                del self._screens[s]
        self._state = new_state
        self._load_screen(new_state)

    # ── Main loop ─────────────────────────────────────────────────────────
    def run(self):
        while self.running:
            dt     = self.clock.tick(FPS) / 1000.0
            screen = self._screens.get(self._state)
            if screen is None:
                break
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    self.running = False
            screen.handle_events(events)
            screen.update(dt)
            screen.draw()
            pygame.display.flip()