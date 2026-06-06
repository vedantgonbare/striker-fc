# ⚽ STRIKER FC — FIFA-Style Football Game

A FIFA-inspired 2D football game built with Python + Pygame.

## Project Structure

```
fifa_game/
├── main.py                  # Entry point
├── requirements.txt
├── assets/
│   ├── fonts/               # Custom TTF fonts
│   ├── images/
│   │   ├── ui/              # Menu backgrounds, icons
│   │   ├── players/         # Sprite sheets
│   │   ├── teams/           # Kit/badge images
│   │   └── pitch/           # Pitch textures
│   └── sounds/
│       ├── music/           # Background music
│       └── sfx/             # Sound effects
├── data/
│   ├── teams/               # Team JSON definitions
│   └── players/             # Player stat JSON files
├── saves/                   # Save game files
└── src/
    ├── core/
    │   ├── settings.py      # All constants & config
    │   ├── game.py          # Main loop + state machine
    │   └── base_screen.py   # Abstract screen base class
    ├── screens/
    │   ├── main_menu.py     # ✅ Animated main menu
    │   ├── team_select.py   # 🔧 Stub — coming next
    │   ├── match.py         # 🔧 Stub — coming next
    │   └── settings.py      # 🔧 Stub — coming next
    ├── entities/
    │   ├── player.py        # Player sprite + stats
    │   ├── ball.py          # Ball physics
    │   └── team.py          # Team data model
    ├── ui/
    │   └── hud.py           # In-match scoreboard/clock
    └── utils/
        └── helpers.py       # Shared utility functions
```

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Roadmap

- [x] Project structure
- [x] Animated main menu
- [ ] Team selection screen
- [ ] Pitch renderer
- [ ] Player movement & controls
- [ ] Ball physics & kicking
- [ ] Basic AI opponents
- [ ] Match HUD & clock
- [ ] Goal detection & scoring
- [ ] Tournament mode
- [ ] Career mode