# -*- coding: utf-8 -*-
"""
inputs.py - Lecture anti-rebond des entrees (switches, ESC, TTP223).

PRINCIPE
--------
Anti-rebond "front + verrouillage" :
  1. Des que l'entree change d'etat, l'evenement est emis IMMEDIATEMENT
     (latence ~0 ms, indispensable pour un clavier).
  2. L'entree est ensuite ignoree pendant debounce_ms : les rebonds
     mecaniques du contact ne produisent donc aucun evenement parasite.
  3. Un nouvel appui n'est accepte qu'apres un relachement detecte, car
     l'evenement est un CHANGEMENT d'etat, pas un niveau.

Aucune boucle bloquante : update() lit l'entree, met a jour l'etat et rend
la main immediatement. C'est la boucle principale qui rythme le tout.
"""

import time
from machine import Pin

# Evenements retournes par update()
EVENT_NONE = 0
EVENT_PRESS = 1
EVENT_RELEASE = 2


class DigitalInput:
    """Une entree tout-ou-rien anti-rebondie.

    active_low = True  : contact vers la masse + pull-up interne (switches, ESC)
    active_low = False : sortie active a l'etat haut (modules TTP223)
    """

    def __init__(self, pin_number, active_low=True, debounce_ms=25, name=""):
        self.pin_number = pin_number
        self.active_low = active_low
        self.debounce_ms = debounce_ms
        self.name = name or ("GPIO%d" % pin_number)

        if active_low:
            # Pull-up interne : le contact n'a besoin que d'un fil vers GND.
            self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        else:
            # Le TTP223 pilote sa sortie dans les deux sens, mais un pull-down
            # interne evite un etat flottant si le module est absent ou
            # debranche : au repos l'entree lit alors 0 = non actif.
            self.pin = Pin(pin_number, Pin.IN, Pin.PULL_DOWN)

        self.pressed = self._read_raw()
        self._locked_until = 0
        self._locked = False

    def _read_raw(self):
        """Lecture brute traduite en booleen 'actif'."""
        level = self.pin.value()
        return (level == 0) if self.active_low else (level == 1)

    def update(self, now):
        """A appeler a chaque tour de boucle. Retourne EVENT_*."""
        if self._locked:
            if time.ticks_diff(now, self._locked_until) < 0:
                return EVENT_NONE
            self._locked = False

        raw = self._read_raw()
        if raw == self.pressed:
            return EVENT_NONE

        self.pressed = raw
        self._locked = True
        self._locked_until = time.ticks_add(now, self.debounce_ms)
        return EVENT_PRESS if raw else EVENT_RELEASE

    def read_now(self):
        """Etat instantane, sans anti-rebond (diagnostic uniquement)."""
        return self._read_raw()


class InputSet:
    """Regroupe toutes les entrees du macropad."""

    def __init__(self, cfg):
        # Les 4 touches mecaniques principales.
        self.buttons = [
            DigitalInput(pin, active_low=True, debounce_ms=cfg.DEBOUNCE_MS,
                         name="B%d" % (index + 1))
            for index, pin in enumerate(cfg.PIN_BUTTONS)
        ]

        # Le gros bouton ESC deporte : anti-rebond plus court = plus reactif.
        self.esc = DigitalInput(cfg.PIN_ESC, active_low=True,
                                debounce_ms=cfg.DEBOUNCE_ESC_MS, name="ESC")

        # Les deux modules capacitifs.
        self.ttp_prev = DigitalInput(cfg.PIN_TTP_PREV,
                                     active_low=not cfg.TTP_ACTIVE_HIGH,
                                     debounce_ms=cfg.DEBOUNCE_TTP_MS,
                                     name="TTP-PREV")
        self.ttp_next = DigitalInput(cfg.PIN_TTP_NEXT,
                                     active_low=not cfg.TTP_ACTIVE_HIGH,
                                     debounce_ms=cfg.DEBOUNCE_TTP_MS,
                                     name="TTP-NEXT")

    def all_inputs(self):
        """Toutes les entrees, pour le diagnostic."""
        return list(self.buttons) + [self.esc, self.ttp_prev, self.ttp_next]


def read_safe_mode_request(cfg):
    """True si le bouton de SAFE MODE est maintenu au demarrage.

    Lecture directe, avant toute autre initialisation, avec une petite
    temporisation pour laisser le pull-up interne stabiliser la ligne.
    """
    pin_number = cfg.PIN_BUTTONS[cfg.SAFE_MODE_BUTTON_INDEX]
    pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
    time.sleep_ms(5)
    # Trois lectures concordantes pour ne pas declencher sur une perturbation.
    for _ in range(3):
        if pin.value() != 0:
            return False
        time.sleep_ms(3)
    return True
