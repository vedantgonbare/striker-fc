"""
game.py — Central Game class.
Owns the main loop, state machine, and screen transitions.
"""

import pygame
from src.core.settings import FPS, STATE_MAIN_MENU, STATE_QUIT
from src.screens.main_menu import MainMenuScreen


class Game:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock  = clock
        self.running = True

        # State machine
        self._state   = STATE_MAIN_MENU
        self._screens = {}          # lazy-loaded screen objects
        self._load_screen(STATE_MAIN_MENU)

    # ── Screen management ────────────────────────────────────────────────────
    def _load_screen(self, state: str):
        """Instantiate a screen object if not already loaded."""
        if state == STATE_MAIN_MENU and state not in self._screens:
            self._screens[state] = MainMenuScreen(self.screen, self._change_state)

    def _change_state(self, new_state: str):
        """Called by screens to request a transition."""
        if new_state == STATE_QUIT:
            self.running = False
            return
        self._state = new_state
        self._load_screen(new_state)

    # ── Main loop ────────────────────────────────────────────────────────────
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0     # delta-time in seconds

            current_screen = self._screens.get(self._state)
            if current_screen is None:
                break

            # Gather events once, pass to active screen
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            if current_screen:
                current_screen.handle_events(events)
                current_screen.update(dt)
                current_screen.draw()

            pygame.display.flip()