# -*- coding: utf-8 -*-
"""
diag.py - Diagnostic materiel du macropad, SANS ENVOI DE TOUCHE.

UTILISATION DANS THONNY
-----------------------
    >>> import diag
    >>> diag.run()                 # diagnostic complet, aucun HID envoye

Ou test par test :
    >>> diag.info()                # version MicroPython, plateforme
    >>> diag.test_i2c()            # scan du bus + detection de l'OLED
    >>> diag.test_oled()           # mire de test a l'ecran
    >>> diag.test_inputs(20)       # 20 s de surveillance des entrees
    >>> diag.test_led()            # rampes PWM + respiration + flash
    >>> diag.test_keymap()         # verification AZERTY des commandes Civil 3D
    >>> diag.test_hid()            # etat du HID, toujours SANS rien envoyer
    >>> diag.test_hid(send_letter=True)   # seul appel qui envoie une touche

Le HID est desactive par defaut dans ce fichier : on peut donc tout tester
sans risque que la carte se mette a taper dans Thonny.
"""

import sys
import time

from machine import Pin, I2C, PWM

import config as cfg
import keymaps
import profiles

SEPARATOR = "-" * 46


# =====================================================================
def info():
    """Version MicroPython et plateforme."""
    print(SEPARATOR)
    print("MICROPYTHON")
    print("  version   :", sys.version)
    print("  plateforme:", sys.platform)
    try:
        import os
        uname = os.uname()
        print("  sysname   :", uname.sysname)
        print("  release   :", uname.release)
        print("  machine   :", uname.machine)
    except Exception as exc:
        print("  os.uname indisponible :", exc)
    try:
        import machine
        print("  frequence :", machine.freq(), "Hz")
    except Exception:
        pass
    try:
        import gc
        gc.collect()
        print("  RAM libre :", gc.mem_free(), "octets")
    except Exception:
        pass


# =====================================================================
def test_i2c():
    """Scan du bus I2C et recherche de l'ecran."""
    print(SEPARATOR)
    print("BUS I2C  (SDA=GPIO%d, SCL=GPIO%d, %d Hz)"
          % (cfg.PIN_I2C_SDA, cfg.PIN_I2C_SCL, cfg.I2C_FREQ))
    try:
        i2c = I2C(cfg.I2C_BUS, scl=Pin(cfg.PIN_I2C_SCL),
                  sda=Pin(cfg.PIN_I2C_SDA), freq=cfg.I2C_FREQ)
    except Exception as exc:
        print("  ECHEC : bus I2C inutilisable :", exc)
        return None

    devices = i2c.scan()
    if not devices:
        print("  aucun peripherique detecte")
        print("  -> verifier VCC (3V3), GND, SDA, SCL et les soudures")
        return None

    for address in devices:
        marker = ""
        if address in cfg.OLED_ADDRESSES:
            marker = "   <-- OLED SH1106 probable"
        print("  0x%02X (%d)%s" % (address, address, marker))

    for address in cfg.OLED_ADDRESSES:
        if address in devices:
            print("  ecran retenu : 0x%02X" % address)
            return i2c
    print("  ATTENTION : peripheriques presents mais aucun a 0x3C / 0x3D")
    return i2c


def test_oled():
    """Affiche une mire de test sur l'ecran."""
    print(SEPARATOR)
    print("ECRAN OLED")
    from display import Display
    display = Display(cfg)
    if not display.ok:
        print("  ECHEC : ecran non initialise (voir messages ci-dessus)")
        return False
    display.message([
        "DIAG OLED",
        "SH1106 128x64",
        "0x%02X" % display.address,
        "",
        "OK",
    ])
    print("  mire affichee : vous devez lire DIAG OLED / SH1106 128x64")
    return True


# =====================================================================
def test_inputs(duration_s=20):
    """Surveille toutes les entrees et affiche chaque changement.

    Aucune touche HID n'est envoyee : c'est le test a faire AVANT de
    brancher le macropad comme clavier.
    """
    print(SEPARATOR)
    print("ENTREES  (%d s ; Ctrl-C pour arreter)" % duration_s)
    print("  B1..B4 : GPIO %s (actif BAS, pull-up interne)"
          % (", ".join(str(p) for p in cfg.PIN_BUTTONS)))
    print("  TTP    : PREV=GPIO%d  NEXT=GPIO%d  (actif %s)"
          % (cfg.PIN_TTP_PREV, cfg.PIN_TTP_NEXT,
             "HAUT" if cfg.TTP_ACTIVE_HIGH else "BAS"))
    print("  ESC    : GPIO%d (actif BAS, pull-up interne)" % cfg.PIN_ESC)
    print()

    from inputs import InputSet, EVENT_PRESS, EVENT_RELEASE
    inputs = InputSet(cfg)
    entries = inputs.all_inputs()

    print("  etat initial :", "  ".join(
        "%s=%s" % (e.name, "APPUI" if e.read_now() else "repos")
        for e in entries))
    print("  actionnez les touches...")

    counters = {}
    deadline = time.ticks_add(time.ticks_ms(), duration_s * 1000)
    try:
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            now = time.ticks_ms()
            for entry in entries:
                event = entry.update(now)
                if event == EVENT_PRESS:
                    counters[entry.name] = counters.get(entry.name, 0) + 1
                    print("  %-9s APPUI    (total %d)"
                          % (entry.name, counters[entry.name]))
                elif event == EVENT_RELEASE:
                    print("  %-9s relache" % entry.name)
            time.sleep_ms(cfg.LOOP_PERIOD_MS)
    except KeyboardInterrupt:
        print("  interrompu")

    print()
    print("  bilan des appuis detectes :")
    for entry in entries:
        print("    %-9s : %d" % (entry.name, counters.get(entry.name, 0)))
    print("  un appui franc doit compter EXACTEMENT 1 : sinon augmenter")
    print("  DEBOUNCE_MS dans config.py")
    return counters


# =====================================================================
def test_led():
    """Rampe PWM, respiration puis flash. Verifiez l'absence de chauffe."""
    print(SEPARATOR)
    print("LED ESC  (GPIO%d, %d Hz)" % (cfg.PIN_LED, cfg.LED_PWM_FREQ))
    try:
        pwm = PWM(Pin(cfg.PIN_LED, Pin.OUT))
        pwm.freq(cfg.LED_PWM_FREQ)
    except Exception as exc:
        print("  ECHEC : PWM indisponible :", exc)
        return False

    try:
        for pct in (0, 5, 20, 50, 100):
            print("  rapport cyclique %3d %%  (touchez la LED : elle doit "
                  "rester froide)" % pct)
            pwm.duty_u16(int(pct * 655.35))
            time.sleep_ms(1200)
        pwm.duty_u16(0)

        print("  respiration pendant 6 s...")
        from led import EscLed
        pwm.deinit()
        led = EscLed(cfg)
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 6000:
            led.service(time.ticks_ms())
            time.sleep_ms(cfg.LOOP_PERIOD_MS)

        print("  flash x3...")
        for _ in range(3):
            led.flash()
            start = time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(), start) < 900:
                led.service(time.ticks_ms())
                time.sleep_ms(cfg.LOOP_PERIOD_MS)
        led.off()
    except KeyboardInterrupt:
        print("  interrompu")
    print("  termine")
    return True


# =====================================================================
def test_keymap(text="_MATCHPROP", layout=None):
    """Verifie hors materiel la traduction caractere -> code HID."""
    print(SEPARATOR)
    layout_name = layout or cfg.KEYBOARD_LAYOUT
    table = keymaps.get_layout(layout_name)
    print("DISPOSITION %s" % layout_name)
    print("  chaine testee : %s" % text)
    missing = []
    for char in text:
        entry = table.get(char)
        if entry is None:
            missing.append(char)
            print("    %-3r ABSENT DE LA TABLE" % char)
        else:
            print("    %-3r -> code HID 0x%02X   modificateur 0x%02X"
                  % (char, entry[0], entry[1]))
    if missing:
        print("  ATTENTION : %d caractere(s) non traduisible(s)" % len(missing))
    else:
        print("  tous les caracteres sont traduisibles")
    return not missing


def test_profiles():
    """Coherence des profils et rotation circulaire."""
    print(SEPARATOR)
    print("PROFILS")
    problems = profiles.validate()
    if problems:
        for problem in problems:
            print("  PROBLEME :", problem)
    else:
        print("  structure valide (%d profils)" % len(profiles.PROFILES_ORDER))
    current = cfg.DEFAULT_PROFILE
    chain = [current]
    for _ in range(len(profiles.PROFILES_ORDER)):
        current = profiles.next_profile(current)
        chain.append(current)
    print("  SUIVANT   :", " -> ".join(chain))
    current = cfg.DEFAULT_PROFILE
    chain = [current]
    for _ in range(len(profiles.PROFILES_ORDER)):
        current = profiles.previous_profile(current)
        chain.append(current)
    print("  PRECEDENT :", " -> ".join(chain))
    return not problems


# =====================================================================
def test_hid(send_letter=False):
    """Etat de la pile USB HID.

    Par defaut AUCUNE touche n'est envoyee. send_letter=True envoie une
    seule lettre 'a' apres un decompte, pour le TEST 7.
    """
    print(SEPARATOR)
    print("USB HID")
    import hid_keyboard

    print("  bibliotheque usb.device.keyboard :",
          "PRESENTE" if hid_keyboard.HID_LIB_AVAILABLE else "ABSENTE")
    if not hid_keyboard.HID_LIB_AVAILABLE:
        print("  detail :", hid_keyboard.HID_LIB_ERROR)
        print("  installation depuis le PC :")
        print("     mpremote connect COMx mip install usb-device-keyboard")
        return False

    try:
        import machine
        print("  machine.USBDevice :",
              "DISPONIBLE" if hasattr(machine, "USBDevice") else "ABSENTE")
    except Exception as exc:
        print("  machine indisponible :", exc)

    if not send_letter:
        print("  HID volontairement NON initialise (diagnostic sans risque).")
        print("  pour le test reel : diag.test_hid(send_letter=True)")
        return True

    print()
    print("  ATTENTION : une lettre 'a' va etre envoyee au PC.")
    print("  placez le curseur dans le Bloc-notes MAINTENANT.")
    for remaining in range(8, 0, -1):
        print("    %d..." % remaining)
        time.sleep(1)

    keyboard = hid_keyboard.Keyboard(layout_name=cfg.KEYBOARD_LAYOUT,
                                     manufacturer=cfg.USB_MANUFACTURER,
                                     product=cfg.USB_PRODUCT)
    if not keyboard.start():
        print("  ECHEC : initialisation HID impossible")
        return False

    print("  attente de la configuration par Windows...")
    deadline = time.ticks_add(time.ticks_ms(), 5000)
    while not keyboard.is_ready():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            print("  ECHEC : l'hote n'a pas ouvert l'interface clavier.")
            print("  -> etes-vous branche sur le port USB NATIF de la carte ?")
            return False
        time.sleep_ms(20)

    print("  interface ouverte, envoi de 'a'")
    keyboard.type_text("a")
    deadline = time.ticks_add(time.ticks_ms(), 2000)
    while keyboard.pending() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        keyboard.service(time.ticks_ms())
        time.sleep_ms(cfg.LOOP_PERIOD_MS)
    keyboard.release_all_now()
    print("  termine : un 'a' doit etre apparu dans le Bloc-notes.")
    return True


# =====================================================================
def run(inputs_duration_s=20):
    """Diagnostic complet, sans jamais envoyer de touche."""
    info()
    test_profiles()
    test_keymap("_MATCHPROP")
    test_keymap("_ISOLATEOBJECTS")
    test_i2c()
    test_oled()
    test_hid(send_letter=False)
    test_inputs(inputs_duration_s)
    print(SEPARATOR)
    print("DIAGNOSTIC TERMINE")
    print("test LED separement : diag.test_led()")
    print(SEPARATOR)
