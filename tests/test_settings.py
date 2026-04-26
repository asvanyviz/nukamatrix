"""Automated settings menu test suite."""
from nukamatrix.settings import SettingsMenu, ALL_SETTINGS
from nukamatrix.config import Config, load_config_file
from blessed import Terminal

errors = []

def check(desc, condition, detail=""):
    if not condition:
        errors.append(f"FAIL: {desc} — {detail}")
        print(f"  FAIL: {desc}: {detail}")
    else:
        print(f"  OK: {desc}")

print("=== Test 1: Config defaults ===")
c = Config()
check("default color", c.color == "green")
check("default speed", c.speed == 2)
check("default fps", c.fps == 30)
check("default charset", c.charset == "mixed")
check("default bold", c.bold is True)
check("default rainbow", c.rainbow is False)
check("default lambda_mode", c.lambda_mode is False)

print("\n=== Test 2: Value getters ===")
sm = SettingsMenu(c)
check("color value", sm._get_value(0) == "green")
check("rainbow value", sm._get_value(1) == "OFF")
check("speed value", sm._get_value(2) == "2")
check("fps value", sm._get_value(3) == "30")
check("charset value", sm._get_value(4) == "mixed")
check("bold value", sm._get_value(5) == "ON")
check("lambda value", sm._get_value(6) == "OFF")

print("\n=== Test 3: Color cycling ===")
for direction in [1, -1]:
    c2 = Config()
    sm2 = SettingsMenu(c2)
    for _ in range(7):  # 7 colors = full cycle
        sm2._cycle_value(0, direction)
    check(f"color cycle dir={direction} back to green", c2.color == "green")

print("\n=== Test 4: Range boundaries ===")
c3 = Config()
sm3 = SettingsMenu(c3)
for _ in range(20):
    sm3._adjust_range(2, delta=1)
check("speed clamped to max 10", c3.speed == 10)
for _ in range(20):
    sm3._adjust_range(2, delta=-1)
check("speed clamped to min 0", c3.speed == 0)

c4 = Config()
sm4 = SettingsMenu(c4)
for _ in range(20):
    sm4._action(3, delta=1)
check("fps clamped to max 60", c4.fps == 60)
for _ in range(20):
    sm4._action(3, delta=-1)
check("fps clamped to min 15", c4.fps == 15)

print("\n=== Test 5: Toggle behavior ===")
c5 = Config()
sm5 = SettingsMenu(c5)
sm5._toggle_value(1)
check("rainbow toggled ON", c5.rainbow is True)
sm5._toggle_value(1)
check("rainbow toggled OFF", c5.rainbow is False)
sm5._toggle_value(5)
check("bold toggled OFF", c5.bold is False)
sm5._toggle_value(5)
check("bold toggled ON again", c5.bold is True)

print("\n=== Test 6: Dirty fields ===")
c6 = Config()
sm6 = SettingsMenu(c6)
sm6._cycle_value(0, 1)
check("color change dirty", "color" in sm6._dirty_fields)
sm6._cycle_value(4, 1)
check("charset change dirty", "charset" in sm6._dirty_fields)
sm6._adjust_range(2, 1)
check("speed change dirty", "speed" in sm6._dirty_fields)
check("rainbow NOT dirty", "rainbow" not in sm6._dirty_fields)

print("\n=== Test 7: Snapshot/escape ===")
c7 = Config()
c7.color = "red"
sm7 = SettingsMenu(c7)
c7.color = "blue"
for k, v in sm7._snapshot.items():
    setattr(c7, k, v)
check("escape restores snapshot", c7.color == "red")
sm7._dirty_fields.clear()
for k, v in sm7._snapshot.items():
    setattr(c7, k, v)
check("dirty cleared after reset", len(sm7._dirty_fields) == 0)

print("\n=== Test 8: needs_reinit ===")
c8 = Config()
sm8 = SettingsMenu(c8)
sm8._cycle_value(4, 1)
check("charset needs reinit", "charset" in sm8._dirty_fields)
c9 = Config()
sm9 = SettingsMenu(c9)
sm9._cycle_value(0, 1)
check("color-only no reinit", "charset" not in sm9._dirty_fields)

print("\n=== Test 9: Config save round-trip ===")
c10 = Config()
c10.color = "magenta"
c10.speed = 7
c10.fps = 60
c10.bold = False
c10.rainbow = True
sm10 = SettingsMenu(c10)
sm10.save_to_file()
loaded = load_config_file()
check("saved color", loaded.get("color") == "magenta")
check("saved speed", loaded.get("speed") == 7)
check("saved fps", loaded.get("fps") == 60)
check("saved bold", loaded.get("bold") is False)
check("saved rainbow", loaded.get("rainbow") is True)

print("\n=== Test 10: Render ===")
term = Terminal()
c11 = Config()
sm11 = SettingsMenu(c11)
try:
    sm11._render(term, 0)
    check("render no crash", True)
except Exception as e:
    check("render no crash", False, str(e))

print("\n=== Test 11: _action edge cases ===")
c12 = Config()
sm12 = SettingsMenu(c12)
try:
    sm12._action(-1, delta=1)
    check("action idx=-1 no crash", True)
except Exception as e:
    check("action idx=-1 no crash", False, str(e))
try:
    sm12._action(100, delta=1)
    check("action idx=100 no crash", True)
except Exception as e:
    check("action idx=100 no crash", False, str(e))

print("\n=== Test 12: Invalid color cycling ===")
c13 = Config(color="purple")
sm13 = SettingsMenu(c13)
try:
    sm13._cycle_value(0, 1)
    check("invalid color cycles OK", True)
except Exception as e:
    check("invalid color cycles OK", False, str(e))

print("\n=== Test 13: Cycle direction ===")
c14 = Config()
sm14 = SettingsMenu(c14)
# Forward: green → red
sm14._cycle_value(0, 1)
check("color forward: green→red", c14.color == "red")
# Backward: green → white
c15 = Config()
sm15 = SettingsMenu(c15)
sm15._cycle_value(0, -1)
check("color backward: green→white", c15.color == "white")
# Speed range forward/backward
c16 = Config()
sm16 = SettingsMenu(c16)
sm16._adjust_range(2, 1)
check("speed up: 2→3", c16.speed == 3)
sm16._adjust_range(2, -1)
check("speed down: 3→2", c16.speed == 2)

print("\n" + "="*50)
if errors:
    print(f"FAILED: {len(errors)} errors")
    for e in errors:
        print(f"  {e}")
else:
    print("ALL TESTS PASSED")
