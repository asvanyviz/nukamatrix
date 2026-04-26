# Settings Menu — Blueprint

## Overview
Runtime settings overlay accessible during PyMatrix execution via `p` key. The matrix pauses in the background while the settings panel is active.

## Architecture

### New Module: `nukamatrix/settings.py`
- `SettingsMenu` class
- Renders overlay panel with bordered box, centered on screen
- Handles keyboard navigation
- Applies changes to `Config` in real-time

### Engine Integration (`nukamatrix/core/engine.py`)
- `_check_input()` catches `p` key → enters settings mode
- `_run_settings_menu()` sub-loop:
  - Renders settings overlay every frame
  - Captures keyboard input for menu navigation
  - Applies mutable config fields immediately
  - Exits on `q` (save + resume) or `Esc` (discard + resume)

## Config Field Mapping

| Setting | Config Field | Type | Range/Values | Immediate? |
|---------|-------------|------|-------------|-----------|
| Color | config.color | str | 7 colors | ✅ next frame |
| Rainbow | config.rainbow | bool | ON/OFF | ✅ next frame |
| Speed | config.speed | int | 0-10 | ✅ recalculates interval |
| FPS | config.fps | int | 15-60 | ✅ changes sleep |
| Charset | config.charset | str | ascii/kana/mixed | ⚠️ reinit columns |
| Bold | config.bold | bool | ON/OFF | ✅ next frame |
| Lambda mode | config.lambda_mode | bool | ON/OFF | ⚠️ reinit columns |

## UI Design

```
┌──────────────────────────────┐
│       Settings [p]           │
├──────────────────────────────┤
│ > Color        [ green ]     │
│   Rainbow      [  OFF  ]     │
│   Speed        [   2   ]     │
│   FPS          [  30   ]     │
│   Charset      [ mixed ]     │
│   Bold         [  ON   ]     │
│   Lambda mode  [  OFF  ]     │
├──────────────────────────────┤
│ ↑↓ navigate  ←→ adjust       │
│ Enter toggle  Save/Resume     │
│ Esc discard                   │
└──────────────────────────────┘
```

## Checklist

- [ ] Create `nukamatrix/settings.py` with SettingsMenu class
- [ ] Add `_current_setting`, `_settings_dirty` to engine state
- [ ] Modify `_check_input()` to enter settings on `p`
- [ ] Add `_run_settings_menu()` sub-loop
- [ ] Implement `_render_settings_overlay()` with bordered panel
- [ ] Handle immediate fields (color, rainbow, speed, fps, bold)
- [ ] Handle reinit fields (charset, lambda) with column recreation
- [ ] Save config on exit (`q`) — write to `~/.pymatrix.conf`
- [ ] Keyboard navigation: ↑↓←→, Enter, q, Esc
- [ ] Test all modes work with settings menu
- [ ] Commit + push
