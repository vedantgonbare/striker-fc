"""
base_screen.py — Abstract base class for all game screens.
Every screen (menu, match, team select, etc.) inherits from this.
"""

import pygame
from abc import ABC, abstractmethod
from typing import Callable


class BaseScreen(ABC):
    def __init__(self, screen: pygame.Surface, change_state: Callable):
        self.screen       = screen
        self.change_state = change_state
        self.width        = screen.get_width()
        self.height       = screen.get_height()

    @abstractmethod
    def handle_events(self, events: list) -> None:
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        pass

    @abstractmethod
    def draw(self) -> None:
        pass