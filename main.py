# -*- coding: utf-8 -*-
"""
main.py - Orchestration du macropad ESP32-S3.

Lance automatiquement au demarrage de la carte.

DEROULEMENT
-----------
1. Lecture du bouton B1 : maintenu = SAFE MODE (aucun HID ne sera envoye).
2. Initialisation de l'ecran (facultatif), de la LED (facultatif) et des
   entrees (indispensable).
3. Temporisation de securite, puis activation du clavier USB HID.
4. Boucle principale non bloquante :
       ESC  ->  boutons  ->  TTP223  ->  HID  ->  LED  ->  ecran
   L'ordre n'est pas anodin : ESC est traite en premier pour garantir sa
   reactivite quoi qu'il arrive.

Aucune touche n'est envoyee pendant le demarrage.
Pour reprendre la main : brancher le second port USB-C (USB-UART) et ouvrir
le REPL dans Thonny, ou redemarrer en maintenant B1 (SAFE MODE).
"""

import sys
import time

import config as cfg
import profiles
from display import Display
from hid_keyboard import Keyboard
from inputs import InputSet, read_safe_mode_request, EVENT_PRESS
from led import EscLed


class Macropad:

    def __init__(self):
        print()
        print("=" * 46)
        print(" MACROPAD ESP32-S3  -  Civil 3D / Blender / Word")
        print("=" * 46)

        # --- SAFE MODE : teste avant toute autre chose -----------------
        self.safe_mode = read_safe_mode_request(cfg)
        if self.safe_mode:
            print("[MAIN] SAFE MODE ACTIF : le clavier HID est desactive.")
            print("[MAIN] les entrees restent lisibles, aucune touche n'est envoyee.")

        # --- Peripheriques facultatifs --------------------------------
        self.display = Display(cfg)
        self.led = EscLed(cfg, safe_mode=self.safe_mode)

        # --- Entrees (indispensables) ---------------------------------
        self.inputs = InputSet(cfg)

        # --- Clavier USB HID ------------------------------------------
        self.keyboard = Keyboard(
            layout_name=cfg.KEYBOARD_LAYOUT,
            enabled=not self.safe_mode,
            report_interval_ms=cfg.HID_REPORT_INTERVAL_MS,
            queue_max=cfg.HID_QUEUE_MAX,
            stall_timeout_ms=cfg.HID_STALL_TIMEOUT_MS,
            manufacturer=cfg.USB_MANUFACTURER,
            product=cfg.USB_PRODUCT,
            verbose=cfg.VERBOSE,
        )

        self.profile_name = cfg.DEFAULT_PROFILE
        self.profile = profiles.get_profile(self.profile_name)
        self._status = None
        self._status_check_ms = 0

    # ------------------------------------------------------------------
    # Demarrage
    # ------------------------------------------------------------------
    def _startup_delay(self):
        """Temporisation de securite, pendant laquelle la LED respire deja.

        Elle laisse le temps de debrancher la carte si le firmware devait
        partir en boucle apres une modification malheureuse.
        """
        deadline = time.ticks_add(time.ticks_ms(), cfg.HID_START_DELAY_MS)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            now = time.ticks_ms()
            self.led.service(now)
            self.display.service(now)
            time.sleep_ms(cfg.LOOP_PERIOD_MS)

    def start(self):
        if self.safe_mode:
            self.display.message([
                "SAFE MODE",
                "HID DISABLED",
                "",
                "B1 relache =",
                "reboot normal",
            ])
            self._startup_delay()
            return

        self.display.message(["MACROPAD", "", "demarrage...", ""])
        self._startup_delay()
        self.keyboard.start()
        self._apply_profile(splash=True)

    # ------------------------------------------------------------------
    # Profils
    # ------------------------------------------------------------------
    def _apply_profile(self, splash=True):
        self.profile = profiles.get_profile(self.profile_name)
        labels = [key.get("label", "") for key in self.profile["keys"]]
        self.display.show_profile(self.profile.get("title", self.profile_name),
                                  labels, splash=splash)
        print("[MAIN] profil : %s" % self.profile_name)

    def change_profile(self, forward):
        if forward:
            self.profile_name = profiles.next_profile(self.profile_name)
        else:
            self.profile_name = profiles.previous_profile(self.profile_name)
        self._apply_profile(splash=True)

    # ------------------------------------------------------------------
    # Macros
    # ------------------------------------------------------------------
    def run_macro(self, index):
        """Execute la macro du bouton index (0..3) pour le profil courant."""
        try:
            key = self.profile["keys"][index]
        except (IndexError, KeyError):
            print("[MAIN] aucune macro definie pour B%d" % (index + 1))
            return

        if self.safe_mode:
            # SAFE MODE : on signale l'appui pour le diagnostic, mais la
            # macro n'est jamais executee.
            print("[SAFE] B%d (%s) ignore : HID desactive"
                  % (index + 1, key.get("label", "?")))
            self.display.highlight_macro(index)
            return

        if cfg.VERBOSE:
            print("[MAIN] B%d -> %s (%s)"
                  % (index + 1, key.get("label", "?"), key.get("type", "?")))
        self.display.highlight_macro(index)
        try:
            self._dispatch(key)
        except Exception as exc:
            # Une macro mal ecrite ne doit ni planter le firmware ni laisser
            # un modificateur enfonce.
            print("[MAIN] macro B%d invalide : %s" % (index + 1, exc))
            self.keyboard.clear()

    def _dispatch(self, key, depth=0):
        kind = key.get("type", "none")
        value = key.get("value")

        if kind == "key":
            self.keyboard.tap(value)
        elif kind == "combo":
            self.keyboard.combo(*value)
        elif kind == "text":
            self.keyboard.type_text(value)
        elif kind == "text_enter":
            self.keyboard.type_text(value, enter=True)
        elif kind == "sequence":
            if depth > 2:
                raise ValueError("sequence trop imbriquee")
            for step in value:
                self._dispatch(step, depth + 1)
        elif kind == "none":
            pass
        else:
            raise ValueError("type de macro inconnu : %r" % (kind,))

    # ------------------------------------------------------------------
    # Etat affiche en haut a droite
    # ------------------------------------------------------------------
    def _refresh_status(self, now):
        if time.ticks_diff(now, self._status_check_ms) < 250:
            return
        self._status_check_ms = now
        if self.safe_mode:
            status = "SAFE"
        elif self.keyboard.is_ready():
            status = "HID"
        else:
            status = "..."
        if status != self._status:
            self._status = status
            self.display.set_status(status)

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------
    def loop(self):
        inputs = self.inputs
        keyboard = self.keyboard
        led = self.led
        display = self.display

        while True:
            now = time.ticks_ms()

            # 1. ESC en priorite absolue.
            if inputs.esc.update(now) == EVENT_PRESS:
                if cfg.VERBOSE:
                    print("[MAIN] ESC")
                keyboard.press_escape()
                led.flash(now)

            # 2. Les quatre touches mecaniques.
            for index, button in enumerate(inputs.buttons):
                if button.update(now) == EVENT_PRESS:
                    self.run_macro(index)

            # 3. Changement de profil au toucher capacitif.
            if inputs.ttp_next.update(now) == EVENT_PRESS:
                self.change_profile(True)
            if inputs.ttp_prev.update(now) == EVENT_PRESS:
                self.change_profile(False)

            # 4. Taches de fond, toutes non bloquantes.
            keyboard.service(now)
            led.service(now)
            display.service(now)
            self._refresh_status(now)

            time.sleep_ms(cfg.LOOP_PERIOD_MS)

    def shutdown(self):
        """Arret propre : plus aucune touche enfoncee, LED eteinte."""
        try:
            self.keyboard.clear()
            self.keyboard.release_all_now()
        finally:
            self.led.off()


def run():
    pad = Macropad()
    try:
        pad.start()
        pad.loop()
    except KeyboardInterrupt:
        print("\n[MAIN] arret demande depuis le REPL.")
    except Exception as exc:
        print("[MAIN] ERREUR FATALE dans la boucle principale :", exc)
        if hasattr(sys, "print_exception"):
            sys.print_exception(exc)
        raise
    finally:
        pad.shutdown()
        print("[MAIN] toutes les touches ont ete relachees.")


if __name__ == "__main__":
    run()
