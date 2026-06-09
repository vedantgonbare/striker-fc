"""
game.py — Central Game class + state machine.
Passes team data and match stats between screens.
"""

import pygame
from src.core.settings import (
    FPS,
    STATE_MAIN_MENU, STATE_TEAM_SELECT,
    STATE_MATCH, STATE_HALF_TIME, STATE_FULL_TIME,
    STATE_SETTINGS, STATE_QUIT,
)
from src.screens.main_menu   import MainMenuScreen
from src.screens.team_select import TeamSelectScreen, TEAMS
from src.screens.match       import MatchScreen
from src.screens.half_time   import HalfTimeScreen
from src.screens.full_time   import FullTimeScreen
from src.screens.settings    import SettingsScreen


class Game:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen       = screen
        self.clock        = clock
        self.running      = True
        self._state       = STATE_MAIN_MENU
        self._screens     = {}

        # Shared state between screens
        self.selected_home  = TEAMS[0]
        self.selected_away  = TEAMS[3]
        self._match_data    = {}      # populated after each half
        self._second_half   = False   # flag so MatchScreen knows which half

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
            ms = MatchScreen(
                self.screen, self._change_state,
                home_team=self.selected_home,
                away_team=self.selected_away,
            )
            # Restore second-half state if coming from half time
            if self._second_half and self._match_data:
                ms.home_goals  = self._match_data.get("home_goals", 0)
                ms.away_goals  = self._match_data.get("away_goals", 0)
                ms.home_shots  = self._match_data.get("home_shots", 0)
                ms.away_shots  = self._match_data.get("away_shots", 0)
                ms.all_scorers = list(self._match_data.get("all_scorers", []))
                ms.home_poss   = self._match_data.get("home_poss", 50.0)
                ms.current_half = 2
                ms.elapsed      = self._match_data.get("elapsed", 45.0)
            self._screens[state] = ms

        elif state == STATE_HALF_TIME:
            self._screens[state] = HalfTimeScreen(
                self.screen, self._change_state,
                match_data=self._match_data,
            )
        elif state == STATE_FULL_TIME:
            self._screens[state] = FullTimeScreen(
                self.screen, self._change_state,
                match_data=self._match_data,
            )
        elif state == STATE_SETTINGS:
            self._screens[state] = SettingsScreen(self.screen, self._change_state)

    def _on_teams_confirmed(self, home, away):
        self.selected_home = home
        self.selected_away = away
        self._second_half  = False
        self._match_data   = {}

    def _change_state(self, new_state: str):
        if new_state == STATE_QUIT:
            self.running = False
            return

        # Grab match snapshot before leaving match screen
        if self._state == STATE_MATCH:
            ms = self._screens.get(STATE_MATCH)
            if ms and hasattr(ms, "_match_data_snapshot"):
                self._match_data = ms._match_data_snapshot
                self._match_data["elapsed"] = ms.elapsed

        # Coming from half time → second half
        if new_state == STATE_MATCH and self._state == STATE_HALF_TIME:
            self._second_half = True

        # Coming from full time → reset everything for rematch
        if new_state == STATE_MATCH and self._state == STATE_FULL_TIME:
            self._second_half = False
            self._match_data  = {}

        # Always rebuild transient screens
        for s in (STATE_MATCH, STATE_TEAM_SELECT, STATE_HALF_TIME, STATE_FULL_TIME):
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