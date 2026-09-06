# -*- coding: utf-8 -*-
"""
inputs.py - Lecture des boutons, du bouton ESC et des touches capacitives.

=====================================================================
LE PROBLEME DU REBOND, EXPLIQUE SIMPLEMENT
=====================================================================

Quand tu appuies sur un interrupteur mécanique, les deux lamelles de métal
ne se touchent pas franchement du premier coup : elles se cognent et
rebondissent pendant 1 à 10 millisecondes. Électriquement, l'ESP32 voit :

    appuyé - relâché - appuyé - relâché - appuyé ... puis stable

L'ESP32 lit l'état des milliers de fois par seconde : sans précaution, un
seul appui de ton doigt déclencherait la macro cinq fois. C'est ce qu'on
appelle le rebond, et le filtrer s'appelle l'anti-rebond (debounce).

Ce fichier propose DEUX filtres, au choix selon la touche :

1. MODE PATIENT (par défaut, pour B1 à B4 et les TTP223)
   On attend que l'état reste identique pendant DEBOUNCE_MS avant de le
   croire. Très robuste. Inconvénient : la macro part avec 25 ms de retard,
   ce qui est imperceptible pour une macro.

2. MODE RAPIDE (pour le bouton ESC)
   On croit le tout premier changement, on agit immédiatement, PUIS on
   ferme les yeux pendant DEBOUNCE_MS pour ignorer les rebonds. Le retard
   tombe à zéro. C'est la méthode des vrais claviers, et c'est ce qu'on
   veut pour une touche d'annulation.

Dans les deux cas, un nouvel appui n'est accepté qu'APRES un relâchement :
garder le doigt appuyé ne répète jamais l'action.

=====================================================================
POURQUOI IL N'Y A AUCUN FIL DE PLUS SUR LES BOUTONS
=====================================================================

Un interrupteur relie simplement le GPIO à la masse (GND). Au repos, le
GPIO ne serait relié à rien : on dit qu'il "flotte", et il lirait n'importe
quoi. On active donc la résistance de tirage interne de l'ESP32 (PULL_UP) :
elle maintient doucement le GPIO à 3,3 V au repos. Appuyer met le GPIO à
0 V. Le bouton est donc "actif à l'état bas" (active LOW).

Pour les TTP223, c'est l'inverse : le module pilote lui-même sa sortie et
la met à 3,3 V au toucher. On active alors un tirage vers le bas
(PULL_DOWN) pour que l'entrée lise 0 si le module est débranché.
"""

from machine import Pin
from time import ticks_ms, ticks_diff, ticks_add
import config as C


class Debouncer:
    """Filtre anti-rebond. Renvoie 1 (appui), -1 (relâchement) ou 0 (rien)."""

    def __init__(self, initial, delay_ms, now, fast=False):
        self.raw = self.stable = bool(initial)
        self.changed_at = now
        self.delay_ms = delay_ms
        self.fast = fast
        self.locked_until = now
        # Si la touche est déjà enfoncée au démarrage (cas du SAFE MODE où
        # tu maintiens B1), on refuse d'en faire un appui : il faudra la
        # relâcher d'abord. Sinon une macro partirait toute seule au boot.
        self.armed = not self.stable

    def update(self, active, now):
        active = bool(active)

        if self.fast:
            # --- Mode rapide : on croit le premier front, puis on ignore
            # tout pendant delay_ms le temps que les rebonds se calment.
            if ticks_diff(now, self.locked_until) < 0:
                return 0
            if active == self.stable:
                return 0
            self.stable = self.raw = active
            self.locked_until = ticks_add(now, self.delay_ms)
            if not active:
                self.armed = True
                return -1
            if self.armed:
                self.armed = False
                return 1
            return 0

        # --- Mode patient : on exige delay_ms de stabilité.
        if active != self.raw:
            self.raw = active
            self.changed_at = now
        if self.stable != self.raw and ticks_diff(now, self.changed_at) >= self.delay_ms:
            self.stable = self.raw
            if not self.stable:
                self.armed = True
                return -1
            if self.armed:
                self.armed = False
                return 1
        return 0


class Input:
    """Une entrée physique : une broche + son filtre."""

    def __init__(self, number, active_high, delay, fast=False):
        # PULL_DOWN pour une sortie active haute (TTP223),
        # PULL_UP pour un contact vers la masse (boutons, ESC).
        pull = Pin.PULL_DOWN if active_high else Pin.PULL_UP
        self.pin = Pin(number, Pin.IN, pull)
        self.active_high = active_high
        self.filter = Debouncer(self.active(), delay, ticks_ms(), fast)

    def active(self):
        """True si la touche est actionnée, quelle que soit sa polarité."""
        return bool(self.pin.value()) == self.active_high

    def poll(self, now):
        return self.filter.update(self.active(), now)


class Inputs:
    """Toutes les entrées du macropad, lues dans un ordre garanti."""

    def __init__(self):
        # ATTENTION : on garde une LISTE, pas seulement un dictionnaire.
        # En MicroPython, l'ordre de parcours d'un dictionnaire n'est pas
        # garanti (contrairement à Python sur PC). Une liste assure que ESC
        # est toujours lu en premier, et que les logs sortent toujours dans
        # le même ordre.
        self.sequence = [
            ("ESC", Input(C.ESC_PIN, False, C.ESC_DEBOUNCE_MS,
                          fast=getattr(C, "ESC_FAST_EDGE", True))),
        ]
        for index, pin in enumerate(C.BUTTON_PINS):
            self.sequence.append(
                ("B" + str(index + 1), Input(pin, False, C.DEBOUNCE_MS)))
        self.sequence.append(
            ("PREVIOUS", Input(C.TTP_PREVIOUS_PIN, C.TTP_ACTIVE_HIGH,
                               C.TTP_DEBOUNCE_MS)))
        self.sequence.append(
            ("NEXT", Input(C.TTP_NEXT_PIN, C.TTP_ACTIVE_HIGH,
                           C.TTP_DEBOUNCE_MS)))
        # Dictionnaire de confort pour retrouver une entrée par son nom.
        self.items = dict(self.sequence)

    def poll(self, now):
        """Renvoie la liste des changements détectés à cet instant."""
        result = []
        for name, item in self.sequence:
            edge = item.poll(now)
            if edge:
                result.append((name, edge))
        return result

    def disarm_held(self):
        """Ignore ce qui est maintenu à cet instant.

        Utilisé après la garde de démarrage et après une reconnexion USB :
        si tu tenais encore une touche, elle ne déclenchera rien tant que tu
        ne l'auras pas relâchée.
        """
        for _, item in self.sequence:
            if item.active():
                item.filter.armed = False
