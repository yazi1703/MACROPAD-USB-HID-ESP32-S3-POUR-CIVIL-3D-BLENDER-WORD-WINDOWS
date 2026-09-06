# -*- coding: utf-8 -*-
"""
diag.py - Diagnostic du matériel. N'ENVOIE JAMAIS AUCUNE TOUCHE.

=====================================================================
A QUOI CA SERT
=====================================================================
C'est l'outil à utiliser pour les étapes 1 à 6 des tests, quand tu montes
le matériel morceau par morceau. Il n'initialise même pas le clavier USB :
il est donc impossible qu'il tape quelque chose dans Thonny pendant que tu
travailles.

=====================================================================
COMMENT L'UTILISER DANS THONNY
=====================================================================
Dans la zone du bas (le REPL, celle où il y a ">>>") :

    >>> import diag
    >>> diag.run()              # 20 secondes de surveillance des entrées
    >>> diag.run(seconds=60)    # plus long
    >>> diag.run(led_test=True) # ajoute le test de la LED

Test par test :

    >>> diag.keymap()               # vérifie l'AZERTY, sans matériel
    >>> diag.keymap("_ISOLATEOBJECTS")

Pour arrêter avant la fin : Ctrl-C, ou le bouton STOP de Thonny.
"""

import sys
from time import ticks_ms, ticks_diff, sleep_ms
import config as C


def keymap(text="_MATCHPROP"):
    """Montre comment chaque caractère sera tapé. Aucun matériel requis.

    C'est le test à faire en premier si Civil 3D reçoit des lettres
    fausses : il affiche le numéro de touche envoyé pour chaque caractère.
    """
    from layouts import character_keys, TABLES
    print("-" * 46)
    print("DISPOSITION :", C.KEYBOARD_LAYOUT,
          "(%d caracteres connus)" % len(TABLES[C.KEYBOARD_LAYOUT]))
    print("Chaine testee :", text)
    print("  Verr. Maj ETEINT :")
    for char in text:
        print("    %-4r -> %s" % (char, character_keys(char, C.KEYBOARD_LAYOUT)))
    print("  Verr. Maj ALLUME (Windows FR inverse la rangee des chiffres) :")
    for char in text[:3]:
        print("    %-4r -> %s" % (char,
                                  character_keys(char, C.KEYBOARD_LAYOUT, True)))
    print("Rappel : en AZERTY le '_' doit sortir en touche 37 sans Maj.")
    return True


def run(seconds=20, led_test=False):
    """Diagnostic complet du matériel branché."""
    import machine
    import runtime
    from inputs import Inputs
    from display import Display

    # --- 1. Informations sur le firmware ---------------------------
    print("-" * 46)
    print("MicroPython :", sys.version)
    print("Implementation :", sys.implementation)
    print("Plateforme :", sys.platform)
    # Si cette ligne affiche False, le clavier USB est impossible :
    # ce n'est pas le bon firmware.
    print("machine.USBDevice disponible :", hasattr(machine, "USBDevice"))
    print("HID initialise au boot :", runtime.interface is not None)
    print("Envois HID : DESACTIVES en diagnostic")

    # --- 2. Ecran ---------------------------------------------------
    print("I2C bus", C.I2C_ID, "SDA", C.OLED_SDA, "SCL", C.OLED_SCL)
    print("OLED : attention, un ACK I2C prouve qu'un ecran repond,")
    print("       pas que son controleur est bien un SH1106.")
    display = Display()
    display.message("DIAGNOSTIC", "HID DISABLED")
    display.flush_startup()

    # --- 3. Etat instantané des entrées ----------------------------
    controls = Inputs()
    print("Etat initial des entrees :")
    for name, item in controls.sequence:
        print("  %-9s actif = %-5s  niveau electrique = %d"
              % (name, item.active(), item.pin.value()))
    print("Au repos, tout doit afficher 'actif = False'.")
    print("Si une entree est active sans que tu y touches, verifie son cablage.")

    # --- 4. LED (facultatif) ---------------------------------------
    led = None
    if led_test:
        from led import Led
        led = Led()
        print("LED : 0-3 s a 5 %, 3-6 s a 20 %, puis respiration.")
        print("      Appuie sur ESC pour declencher le flash.")
        print("      TOUCHE la LED et la resistance : elles doivent rester froides.")

    # --- 5. Surveillance des entrées -------------------------------
    print("Actionne maintenant chaque touche, une par une (%d s) :" % seconds)
    start = ticks_ms()
    compteur = {}
    try:
        while ticks_diff(ticks_ms(), start) < int(seconds * 1000):
            now = ticks_ms()
            for name, edge in controls.poll(now):
                if edge == 1:
                    compteur[name] = compteur.get(name, 0) + 1
                    print("  %-9s APPUI/TOUCHER  (total %d)"
                          % (name, compteur[name]))
                    if led and name == "ESC":
                        led.flash(now)
                else:
                    print("  %-9s relachement" % name)
            if led:
                age = ticks_diff(now, start)
                if age < 3000:
                    led.set_level(0.05)
                elif age < 6000:
                    led.set_level(0.20)
                else:
                    led.tick(now)
            sleep_ms(5)
    except KeyboardInterrupt:
        print("  interrompu")
    finally:
        if led:
            led.close()

    # --- 6. Bilan ---------------------------------------------------
    print("Bilan des appuis detectes :")
    for name, _ in controls.sequence:
        print("  %-9s : %d" % (name, compteur.get(name, 0)))
    print("Un appui franc doit compter EXACTEMENT 1.")
    print("S'il en compte 2 ou 3 : augmente DEBOUNCE_MS dans config.py.")
    print("Diagnostic termine, retour REPL")


if __name__ == "__main__":
    run()
