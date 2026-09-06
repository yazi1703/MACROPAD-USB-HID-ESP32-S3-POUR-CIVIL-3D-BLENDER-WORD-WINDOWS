# -*- coding: utf-8 -*-
"""
test_logique.py - Verification du firmware SUR PC, sans ESP32.

Ce script installe de faux peripheriques (tools/mp_stubs.py) puis importe et
EXECUTE REELLEMENT les modules du macropad. Il verifie :

  1. la coherence des profils et la rotation circulaire
  2. la traduction AZERTY de toutes les macros
  3. les rapports USB HID reellement produits, octet par octet
  4. l'absence de modificateur reste enfonce
  5. la priorite du bouton ESC
  6. l'anti-rebond (contact qui rebondit, doigt maintenu)
  7. la courbe de respiration de la LED
  8. le rendu OLED (aucun debordement hors des 128x64 pixels)
  9. la boucle principale complete, du boot jusqu'aux frappes

Lancement :  python3 tools/test_logique.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import mp_stubs                                            # noqa: E402
from mp_stubs import CLOCK, SCRIPT, StopSimulation         # noqa: E402

mp_stubs.install()

import config as cfg                                       # noqa: E402
import keymaps                                             # noqa: E402
import profiles                                            # noqa: E402
import hid_keyboard                                        # noqa: E402
import inputs as inputs_mod                                # noqa: E402
import led as led_mod                                      # noqa: E402
import display as display_mod                              # noqa: E402

FAILURES = []
CHECKS = [0]


def check(condition, description):
    CHECKS[0] += 1
    if condition:
        print("   ok   %s" % description)
    else:
        print("   FAIL %s" % description)
        FAILURES.append(description)


def title(text):
    print()
    print("=" * 66)
    print(text)
    print("=" * 66)


def drain(keyboard, limit_ms=8000):
    """Fait tourner la file HID jusqu'a ce qu'elle soit vide."""
    elapsed = 0
    while keyboard.pending() and elapsed < limit_ms:
        keyboard.service(CLOCK.now)
        CLOCK.advance(1)
        elapsed += 1
    keyboard.service(CLOCK.now)


def new_keyboard():
    keyboard = hid_keyboard.Keyboard(layout_name=cfg.KEYBOARD_LAYOUT,
                                     report_interval_ms=cfg.HID_REPORT_INTERVAL_MS,
                                     verbose=False)
    keyboard.start()
    return keyboard


def reports_of(keyboard):
    return [report for _, report in keyboard._itf.reports]


# =====================================================================
title("1. PROFILS ET NAVIGATION CIRCULAIRE")
problems = profiles.validate()
check(not problems, "structure des profils valide (%s)"
      % ("aucun probleme" if not problems else problems))

check(profiles.next_profile("CIVIL3D") == "WORD", "CIVIL3D + NEXT = WORD")
check(profiles.next_profile("WINDOWS") == "BLENDER", "WINDOWS + NEXT = BLENDER")
check(profiles.previous_profile("BLENDER") == "WINDOWS",
      "BLENDER + PREV = WINDOWS")
check(profiles.next_profile(profiles.previous_profile("WORD")) == "WORD",
      "NEXT(PREV(x)) == x")
check(cfg.DEFAULT_PROFILE in profiles.PROFILES,
      "profil par defaut %s existe" % cfg.DEFAULT_PROFILE)

chain = ["CIVIL3D"]
for _ in range(len(profiles.PROFILES_ORDER)):
    chain.append(profiles.next_profile(chain[-1]))
check(chain[0] == chain[-1], "un tour complet revient au point de depart")
print("   rotation : %s" % " -> ".join(chain))


# =====================================================================
title("2. TRADUCTION CLAVIER (AZERTY)")
table = keymaps.get_layout("FR_AZERTY")
check(table["_"] == (keymaps.K_8, 0),
      "'_' AZERTY = touche 8 sans SHIFT (code 0x%02X)" % keymaps.K_8)
check(table["a"][0] == keymaps.K_Q, "'a' AZERTY est sur la touche Q du QWERTY")
check(table["z"][0] == keymaps.K_W, "'z' AZERTY est sur la touche W du QWERTY")
check(table["m"][0] == keymaps.K_SEMICOLON, "'m' AZERTY est a droite du L")
check(keymaps.LAYOUTS["US_QWERTY"]["_"] == (keymaps.K_MINUS, keymaps.MOD_SHIFT),
      "'_' QWERTY = SHIFT + touche tiret")

keyboard = new_keyboard()
for name in profiles.PROFILES_ORDER:
    for index, key in enumerate(profiles.PROFILES[name]["keys"]):
        kind, value = key["type"], key["value"]
        try:
            if kind == "key":
                keyboard._resolve(value)
            elif kind == "combo":
                for item in value:
                    keyboard._resolve(item)
            elif kind in ("text", "text_enter"):
                missing = [c for c in value if c not in keyboard.layout]
                assert not missing, missing
            ok, detail = True, ""
        except Exception as exc:
            ok, detail = False, str(exc)
        check(ok, "%s B%d (%s) traduisible %s" % (name, index + 1,
                                                  key["label"], detail))


# =====================================================================
title("3. RAPPORTS USB HID REELLEMENT PRODUITS")
keyboard = new_keyboard()
keyboard.combo("CTRL", "Z")
drain(keyboard)
sent = reports_of(keyboard)
expected_z = keymaps.LAYOUTS["FR_AZERTY"]["z"][0]
check(len(sent) == 2, "CTRL+Z = 2 rapports (appui + relachement)")
check(sent[0][0] == keymaps.MOD_CTRL, "CTRL+Z : octet modificateur = 0x01")
check(sent[0][2] == expected_z,
      "CTRL+Z : code 0x%02X (touche 'z' AZERTY, PAS 0x%02X du QWERTY)"
      % (expected_z, keymaps.K_Z))
check(sent[-1] == bytes(8), "CTRL+Z : dernier rapport entierement a zero")

keyboard = new_keyboard()
keyboard.combo("CTRL", "SHIFT", "ESC")
drain(keyboard)
sent = reports_of(keyboard)
check(sent[0][0] == keymaps.MOD_CTRL | keymaps.MOD_SHIFT,
      "CTRL+SHIFT+ESC : modificateurs 0x03")
check(sent[0][2] == keymaps.K_ESC, "CTRL+SHIFT+ESC : code ESC 0x29")
check(sent[-1] == bytes(8), "CTRL+SHIFT+ESC : tout relache a la fin")

keyboard = new_keyboard()
keyboard.combo("WIN", "E")
drain(keyboard)
sent = reports_of(keyboard)
check(sent[0][0] == keymaps.MOD_WIN, "WIN+E : modificateur WIN 0x08")
check(sent[0][2] == keymaps.K_E, "WIN+E : code de la touche E")
check(sent[-1] == bytes(8), "WIN+E : touche Windows bien relachee")

keyboard = new_keyboard()
keyboard.combo("ALT", "TAB")
drain(keyboard)
sent = reports_of(keyboard)
check(sent[0][0] == keymaps.MOD_ALT and sent[0][2] == keymaps.K_TAB,
      "ALT+TAB : modificateur ALT + code TAB")
check(sent[-1] == bytes(8), "ALT+TAB : ALT bien relache")

# --- commandes Civil 3D ---
for command in ("_MATCHPROP", "_HATCH", "_ISOLATEOBJECTS"):
    keyboard = new_keyboard()
    keyboard.type_text(command, enter=True)
    drain(keyboard)
    sent = reports_of(keyboard)
    check(len(sent) == 2 * (len(command) + 1),
          "%s : %d rapports (%d caracteres + ENTREE)"
          % (command, len(sent), len(command)))
    typed = []
    for index in range(0, len(sent), 2):
        report = sent[index]
        typed.append((report[2], report[0]))
    # Les commandes sont ecrites en majuscules : chaque lettre part donc avec
    # SHIFT. AutoCAD est insensible a la casse, seul le prefixe "_" compte.
    expected = [table[c] for c in command] + [(keymaps.K_ENTER, 0)]
    check(typed == expected, "%s : suite de codes HID conforme a l'AZERTY"
          % command)
    check(all(sent[i] == bytes(8) for i in range(1, len(sent), 2)),
          "%s : un relachement apres chaque caractere" % command)
    shifted = [r for r in sent[0::2] if r[0] == keymaps.MOD_SHIFT]
    check(len(shifted) == sum(1 for c in command if c.isalpha()),
          "%s : SHIFT applique aux %d lettres majuscules puis relache"
          % (command, sum(1 for c in command if c.isalpha())))
    check(sent[0][0] == 0 and sent[0][2] == keymaps.K_8,
          "%s : le prefixe '_' part sans aucun modificateur en AZERTY"
          % command)

# --- aucun modificateur ne reste enfonce, quelle que soit la macro ---
stuck = []
for name in profiles.PROFILES_ORDER:
    for index, key in enumerate(profiles.PROFILES[name]["keys"]):
        keyboard = new_keyboard()
        kind, value = key["type"], key["value"]
        if kind == "key":
            keyboard.tap(value)
        elif kind == "combo":
            keyboard.combo(*value)
        elif kind == "text":
            keyboard.type_text(value)
        elif kind == "text_enter":
            keyboard.type_text(value, enter=True)
        drain(keyboard)
        final = reports_of(keyboard)[-1]
        if final != bytes(8):
            stuck.append("%s B%d" % (name, index + 1))
check(not stuck, "les 16 macros finissent toutes touches relachees %s"
      % (stuck or ""))


# =====================================================================
title("4. PRIORITE DU BOUTON ESC")
keyboard = new_keyboard()
keyboard.type_text("_ISOLATEOBJECTS", enter=True)
before = keyboard.pending()
for _ in range(3):                       # on laisse partir quelques rapports
    keyboard.service(CLOCK.now)
    CLOCK.advance(cfg.HID_REPORT_INTERVAL_MS)
keyboard.press_escape()
check(keyboard.pending() == 2,
      "ESC vide la file en cours (%d rapports en attente avant, 2 apres)"
      % before)
drain(keyboard)
sent = reports_of(keyboard)
check(sent[-2][2] == keymaps.K_ESC, "ESC : avant-dernier rapport = code 0x29")
check(sent[-1] == bytes(8), "ESC : relachement final")


# =====================================================================
title("5. ANTI-REBOND")
mp_stubs.install()
import importlib                                            # noqa: E402
importlib.reload(inputs_mod)

SCRIPT.set_default(4, 1)
SCRIPT.press(100, 4, duration_ms=80, active_level=0, bounces=6)
button = inputs_mod.DigitalInput(4, active_low=True,
                                 debounce_ms=cfg.DEBOUNCE_MS, name="B1")
presses = releases = 0
CLOCK.now = 0
for _ in range(400):
    event = button.update(CLOCK.now)
    if event == inputs_mod.EVENT_PRESS:
        presses += 1
    elif event == inputs_mod.EVENT_RELEASE:
        releases += 1
    CLOCK.advance(1)
check(presses == 1, "contact avec 6 rebonds -> 1 seul appui (%d)" % presses)
check(releases == 1, "contact avec 6 rebonds -> 1 seul relachement (%d)"
      % releases)

# doigt maintenu longtemps sur un TTP223 : un seul evenement
mp_stubs.install()
importlib.reload(inputs_mod)
SCRIPT.set_default(11, 0)
SCRIPT.schedule(50, 11, 1)
SCRIPT.schedule(3000, 11, 0)
touch = inputs_mod.DigitalInput(11, active_low=False,
                                debounce_ms=cfg.DEBOUNCE_TTP_MS, name="TTP")
presses = 0
CLOCK.now = 0
for _ in range(4000):
    if touch.update(CLOCK.now) == inputs_mod.EVENT_PRESS:
        presses += 1
    CLOCK.advance(1)
check(presses == 1, "doigt pose 3 s sur le TTP223 -> 1 seul profil change (%d)"
      % presses)

# deux touchers separes = deux evenements
mp_stubs.install()
importlib.reload(inputs_mod)
SCRIPT.set_default(11, 0)
SCRIPT.schedule(50, 11, 1)
SCRIPT.schedule(300, 11, 0)
SCRIPT.schedule(600, 11, 1)
SCRIPT.schedule(900, 11, 0)
touch = inputs_mod.DigitalInput(11, active_low=False,
                                debounce_ms=cfg.DEBOUNCE_TTP_MS, name="TTP")
presses = 0
CLOCK.now = 0
for _ in range(1200):
    if touch.update(CLOCK.now) == inputs_mod.EVENT_PRESS:
        presses += 1
    CLOCK.advance(1)
check(presses == 2, "deux touchers distincts -> 2 evenements (%d)" % presses)


# =====================================================================
title("6. LED : COURBE DE RESPIRATION")
mp_stubs.install()
importlib.reload(led_mod)
lamp = led_mod.EscLed(cfg)
check(lamp.available, "PWM initialise sur GPIO%d" % cfg.PIN_LED)

samples = [lamp.breathing_pct(t) for t in range(0, cfg.LED_BREATH_PERIOD_MS, 10)]
low, high = min(samples), max(samples)
check(abs(low - cfg.LED_BREATH_MIN_PCT) < 0.2,
      "minimum de respiration = %.1f %% (attendu %.1f)"
      % (low, cfg.LED_BREATH_MIN_PCT))
check(abs(high - cfg.LED_BREATH_MAX_PCT) < 0.5,
      "maximum de respiration = %.1f %% (attendu %.1f)"
      % (high, cfg.LED_BREATH_MAX_PCT))
check(abs(lamp.breathing_pct(0) - lamp.breathing_pct(cfg.LED_BREATH_PERIOD_MS))
      < 0.01, "la courbe est bien periodique sur %d ms"
      % cfg.LED_BREATH_PERIOD_MS)
half = cfg.LED_BREATH_PERIOD_MS // 2
rising = [lamp.breathing_pct(t) for t in range(0, half, 25)]
check(all(rising[i] <= rising[i + 1] + 1e-9 for i in range(len(rising) - 1)),
      "montee strictement progressive (aucune cassure)")
steps = [abs(samples[i + 1] - samples[i]) for i in range(len(samples) - 1)]
check(max(steps) < 1.0,
      "variation maximale %.3f %% par 10 ms : transition tres douce"
      % max(steps))

lamp.flash(CLOCK.now)
check(abs(lamp.target_pct(CLOCK.now) - cfg.LED_FLASH_PCT) < 0.01,
      "le flash monte immediatement a %.0f %%" % cfg.LED_FLASH_PCT)
CLOCK.advance(cfg.LED_FLASH_MS - 10)
check(abs(lamp.target_pct(CLOCK.now) - cfg.LED_FLASH_PCT) < 0.01,
      "le flash dure bien %d ms" % cfg.LED_FLASH_MS)
CLOCK.advance(20)
check(lamp.target_pct(CLOCK.now) < cfg.LED_FLASH_PCT,
      "apres le flash la luminosite redescend")
CLOCK.advance(cfg.LED_RECOVER_MS + 50)
after = lamp.target_pct(CLOCK.now)
breath = lamp.breathing_pct(mp_stubs._ticks_diff(CLOCK.now, lamp._start_ms))
check(abs(after - breath) < 0.01, "retour exact a la respiration normale")

lamp_safe = led_mod.EscLed(cfg, safe_mode=True)
check(lamp_safe.max_pct == cfg.LED_SAFE_MODE_MAX_PCT,
      "SAFE MODE : respiration limitee a %.0f %%" % cfg.LED_SAFE_MODE_MAX_PCT)


# =====================================================================
title("7. RENDU OLED")
mp_stubs.install()
importlib.reload(display_mod)
screen = display_mod.Display(cfg)
check(screen.ok, "ecran detecte a l'adresse 0x%02X" % (screen.address or 0))

for name in profiles.PROFILES_ORDER:
    profile = profiles.PROFILES[name]
    labels = [key["label"] for key in profile["keys"]]
    screen.show_profile(profile["title"], labels, splash=True)
    for _ in range(cfg.SPLASH_MS + 200):
        screen.service(CLOCK.now)
        CLOCK.advance(1)
    for index in range(4):
        screen.highlight_macro(index)
        for _ in range(cfg.MACRO_HIGHLIGHT_MS + 50):
            screen.service(CLOCK.now)
            CLOCK.advance(1)
screen.message(["SAFE MODE", "HID DISABLED"])
check(screen.oled.out_of_bounds == 0,
      "aucun debordement hors des 128x64 pixels (%d)"
      % screen.oled.out_of_bounds)
check(screen.oled.i2c.data_bytes > 0, "des donnees ont bien ete envoyees a l'ecran")

pages_per_call = []
screen.oled.mark_all()
sent_before = screen.oled.i2c.data_bytes
screen.oled.flush_step(cfg.OLED_PAGES_PER_SERVICE)
delta = screen.oled.i2c.data_bytes - sent_before
check(delta == cfg.OLED_PAGES_PER_SERVICE * cfg.OLED_WIDTH,
      "un service envoie %d octets au maximum (%d) : ~%.1f ms d'I2C"
      % (cfg.OLED_PAGES_PER_SERVICE * cfg.OLED_WIDTH, delta,
         delta * 9.0 / 400.0))


# =====================================================================
title("8. BOUCLE PRINCIPALE COMPLETE (du boot aux frappes)")
mp_stubs.install()
for module in ("config", "profiles", "keymaps", "hid_keyboard", "inputs",
               "led", "display", "sh1106", "main"):
    sys.modules.pop(module, None)

SCRIPT.set_default(cfg.PIN_BUTTONS[0], 1)          # B1 relache : pas de SAFE MODE
for pin_number in cfg.PIN_BUTTONS[1:]:
    SCRIPT.set_default(pin_number, 1)
SCRIPT.set_default(cfg.PIN_ESC, 1)
SCRIPT.set_default(cfg.PIN_TTP_PREV, 0)
SCRIPT.set_default(cfg.PIN_TTP_NEXT, 0)

# Scenario : B1 en CIVIL3D, puis NEXT, puis B1 en WORD, puis ESC.
SCRIPT.press(2000, cfg.PIN_BUTTONS[0], duration_ms=60, active_level=0, bounces=4)
SCRIPT.schedule(3200, cfg.PIN_TTP_NEXT, 1)
SCRIPT.schedule(3400, cfg.PIN_TTP_NEXT, 0)
SCRIPT.press(4000, cfg.PIN_BUTTONS[0], duration_ms=60, active_level=0, bounces=2)
SCRIPT.press(4800, cfg.PIN_ESC, duration_ms=50, active_level=0, bounces=3)

import main as main_mod                                     # noqa: E402

pad = main_mod.Macropad()
check(not pad.safe_mode, "demarrage normal (B1 relache) : SAFE MODE inactif")
pad.start()
check(pad.keyboard.available, "clavier HID initialise au demarrage")
check(len(pad.keyboard._itf.reports) == 0,
      "AUCUNE touche envoyee pendant le boot (%d rapports)"
      % len(pad.keyboard._itf.reports))
check(CLOCK.now >= cfg.HID_START_DELAY_MS,
      "temporisation de securite de %d ms respectee" % cfg.HID_START_DELAY_MS)

CLOCK.max_steps = 6000
try:
    pad.loop()
except StopSimulation:
    pass
pad.shutdown()

emitted = [report for _, report in pad.keyboard._itf.reports]
codes = [report[2] for report in emitted if report[2]]
expected_civil = [table[c][0] for c in "_matchprop"] + [keymaps.K_ENTER]
check(codes[:len(expected_civil)] == expected_civil,
      "B1 en CIVIL3D a bien tape _MATCHPROP + ENTREE")
check(pad.profile_name == "WORD",
      "le toucher TTP NEXT a fait passer CIVIL3D -> %s" % pad.profile_name)
word_report = None
for report in emitted:
    if report[0] == keymaps.MOD_CTRL and report[2] == table["b"][0]:
        word_report = report
check(word_report is not None, "B1 en WORD a bien envoye CTRL+B")
check(keymaps.K_ESC in codes, "le bouton ESC a bien envoye Echap")
check(emitted[-1] == bytes(8), "arret propre : toutes les touches relachees")
check(pad.display.oled.out_of_bounds == 0, "affichage sans debordement")
flashes = [duty for _, duty in pad.led.pwm.history if duty > 60000]
check(len(flashes) > 0, "la LED a bien produit un flash sur l'appui ESC")


# =====================================================================
title("9. SAFE MODE (B1 maintenu au demarrage)")
mp_stubs.install()
for module in ("config", "profiles", "keymaps", "hid_keyboard", "inputs",
               "led", "display", "sh1106", "main"):
    sys.modules.pop(module, None)

SCRIPT.set_default(cfg.PIN_BUTTONS[0], 0)          # B1 MAINTENU = SAFE MODE
for pin_number in cfg.PIN_BUTTONS[1:]:
    SCRIPT.set_default(pin_number, 1)
SCRIPT.set_default(cfg.PIN_ESC, 1)
SCRIPT.set_default(cfg.PIN_TTP_PREV, 0)
SCRIPT.set_default(cfg.PIN_TTP_NEXT, 0)
# On relache B1 puis on appuie sur tout : rien ne doit sortir.
SCRIPT.schedule(500, cfg.PIN_BUTTONS[0], 1)
SCRIPT.press(2500, cfg.PIN_BUTTONS[1], duration_ms=60, active_level=0)
SCRIPT.press(3000, cfg.PIN_ESC, duration_ms=60, active_level=0)
SCRIPT.schedule(3500, cfg.PIN_TTP_NEXT, 1)
SCRIPT.schedule(3700, cfg.PIN_TTP_NEXT, 0)

import main as main_safe                                    # noqa: E402
importlib.reload(main_safe)

pad = main_safe.Macropad()
check(pad.safe_mode, "B1 maintenu au demarrage : SAFE MODE detecte")
pad.start()
check(pad.keyboard.enabled is False, "clavier HID desactive en SAFE MODE")
check(pad.keyboard.available is False, "aucune interface USB HID creee")
pad._refresh_status(mp_stubs._ticks_add(CLOCK.now, 1000))
check(pad.display._message_active,
      "l'ecran SAFE MODE n'est pas ecrase par la mise a jour d'etat")
CLOCK.max_steps = 5000
try:
    pad.loop()
except StopSimulation:
    pass
pad.shutdown()
check(pad.keyboard._itf is None,
      "SAFE MODE : aucun rapport HID n'a pu etre emis, meme en appuyant")
check(pad.led.max_pct == cfg.LED_SAFE_MODE_MAX_PCT,
      "SAFE MODE : la LED respire faiblement mais fonctionne")
check(pad.display.ok, "SAFE MODE : l'ecran reste utilisable")


# =====================================================================
title("10. TOLERANCE AUX PANNES")
# --- Ecran OLED absent -------------------------------------------------
mp_stubs.install()
for module in ("config", "profiles", "keymaps", "hid_keyboard", "inputs",
               "led", "display", "sh1106", "main"):
    sys.modules.pop(module, None)
original_i2c_init = mp_stubs.I2C.__init__


def _i2c_without_screen(self, bus, scl=None, sda=None, freq=100000):
    original_i2c_init(self, bus, scl=scl, sda=sda, freq=freq)
    self.devices = []                                # plus aucun peripherique


mp_stubs.I2C.__init__ = _i2c_without_screen
SCRIPT.set_default(cfg.PIN_BUTTONS[0], 1)
for pin_number in cfg.PIN_BUTTONS[1:]:
    SCRIPT.set_default(pin_number, 1)
SCRIPT.set_default(cfg.PIN_ESC, 1)
SCRIPT.set_default(cfg.PIN_TTP_PREV, 0)
SCRIPT.set_default(cfg.PIN_TTP_NEXT, 0)
SCRIPT.press(2200, cfg.PIN_BUTTONS[2], duration_ms=60, active_level=0)

import main as main_nooled                                  # noqa: E402
importlib.reload(main_nooled)
pad = main_nooled.Macropad()
pad.start()
check(pad.display.ok is False, "ecran absent correctement detecte")
CLOCK.max_steps = 4000
try:
    pad.loop()
except StopSimulation:
    pass
pad.shutdown()
emitted = [report for _, report in pad.keyboard._itf.reports]
check(any(report[0] == keymaps.MOD_CTRL for report in emitted),
      "sans ecran, le clavier continue de fonctionner (CTRL+Z envoye)")
mp_stubs.I2C.__init__ = original_i2c_init

# --- Bibliotheque USB HID absente -------------------------------------
mp_stubs.install(with_usb=False)
for module in ("config", "profiles", "keymaps", "hid_keyboard", "inputs",
               "led", "display", "sh1106", "main"):
    sys.modules.pop(module, None)
import hid_keyboard as hid_missing                          # noqa: E402
check(hid_missing.HID_LIB_AVAILABLE is False,
      "absence de usb.device.keyboard correctement detectee")
keyboard = hid_missing.Keyboard(verbose=False)
check(keyboard.start() is False, "start() renvoie False, sans planter")
check(keyboard.tap("ESC") is False, "aucune touche empilee sans bibliotheque")
keyboard.service(0)
check(True, "service() reste inoffensif sans bibliotheque HID")

mp_stubs.install()
for module in ("config", "profiles", "keymaps", "hid_keyboard", "inputs",
               "led", "display", "sh1106", "main"):
    sys.modules.pop(module, None)


# =====================================================================
title("RESULTAT")
print("%d verifications executees" % CHECKS[0])
if FAILURES:
    print("%d ECHEC(S) :" % len(FAILURES))
    for failure in FAILURES:
        print("   - %s" % failure)
    sys.exit(1)
print("TOUT EST CONFORME")
sys.exit(0)
