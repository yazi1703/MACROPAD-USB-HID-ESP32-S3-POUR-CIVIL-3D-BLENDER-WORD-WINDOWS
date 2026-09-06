# -*- coding: utf-8 -*-
"""
led.py - LED du gros bouton ESC : respiration permanente + flash a l'appui.

MATERIEL
--------
La LED n'est JAMAIS branchee directement sur un GPIO : elle est pilotee par
un transistor BC547 (voir docs/02-cablage.md). Le GPIO ne fournit que le
courant de base (environ 1,2 mA a travers 2,2 kOhm).

La LED 1 W est volontairement utilisee a quelques milliamperes seulement
grace a sa resistance serie de 330 Ohm : elle ne chauffe pas et le PWM peut
donc monter a 100 % sans risque lors du flash.

ANIMATION
---------
Respiration : rapport cyclique = MIN + (MAX - MIN) * s^gamma
              avec s = (1 - cos(2*pi*phase)) / 2, une sinusoide surelevee.
Le cosinus donne des extremes doux (pas de rampe triangulaire agressive) et
l'exposant gamma > 1 fait "trainer" la LED dans les valeurs basses, ce qui
imite la respiration bien mieux qu'une sinusoide pure.

Aucune temporisation bloquante : service() calcule la valeur correspondant a
l'instant courant et rend la main immediatement.
"""

import math
import time
from machine import Pin, PWM

_TWO_PI = 6.283185307179586


class EscLed:
    """Pilotage PWM de la LED du bouton ESC."""

    def __init__(self, cfg, safe_mode=False):
        self.cfg = cfg
        self.available = False
        self.pwm = None

        self.min_pct = cfg.LED_BREATH_MIN_PCT
        self.max_pct = (cfg.LED_SAFE_MODE_MAX_PCT if safe_mode
                        else cfg.LED_BREATH_MAX_PCT)
        self.period_ms = cfg.LED_BREATH_PERIOD_MS
        self.gamma = cfg.LED_BREATH_GAMMA
        self.flash_pct = cfg.LED_FLASH_PCT
        self.flash_ms = cfg.LED_FLASH_MS
        self.recover_ms = cfg.LED_RECOVER_MS

        self._start_ms = time.ticks_ms()
        self._flash_start = 0
        self._flashing = False
        self._last_duty = -1

        try:
            self.pwm = PWM(Pin(cfg.PIN_LED, Pin.OUT))
            self.pwm.freq(cfg.LED_PWM_FREQ)
            self.pwm.duty_u16(0)
            self.available = True
        except Exception as exc:
            # La LED n'est pas vitale : on signale et on continue sans elle.
            print("[LED] PWM indisponible sur GPIO%d : %s" % (cfg.PIN_LED, exc))

    # ------------------------------------------------------------------
    def breathing_pct(self, elapsed_ms):
        """Rapport cyclique de la respiration a l'instant donne (en %).

        Fonction pure : elle est testee hors materiel par tools/test_logique.py.
        """
        phase = (elapsed_ms % self.period_ms) / self.period_ms
        smooth = (1.0 - math.cos(_TWO_PI * phase)) / 2.0     # 0.0 -> 1.0 -> 0.0
        shaped = math.pow(smooth, self.gamma)
        return self.min_pct + (self.max_pct - self.min_pct) * shaped

    def target_pct(self, now):
        """Rapport cyclique voulu, respiration et flash confondus."""
        breath = self.breathing_pct(time.ticks_diff(now, self._start_ms))
        if not self._flashing:
            return breath

        since_flash = time.ticks_diff(now, self._flash_start)
        if since_flash < self.flash_ms:
            return self.flash_pct                      # eclat plein

        fade = since_flash - self.flash_ms
        if fade < self.recover_ms:
            # Retour progressif du flash vers la respiration.
            ratio = fade / self.recover_ms
            eased = ratio * ratio * (3.0 - 2.0 * ratio)   # lissage smoothstep
            return self.flash_pct + (breath - self.flash_pct) * eased

        self._flashing = False
        return breath

    # ------------------------------------------------------------------
    def flash(self, now=None):
        """Declenche l'eclat lumineux (appel non bloquant)."""
        self._flash_start = now if now is not None else time.ticks_ms()
        self._flashing = True

    def service(self, now):
        """A appeler a chaque tour de boucle."""
        if not self.available:
            return
        pct = self.target_pct(now)
        if pct < 0.0:
            pct = 0.0
        elif pct > 100.0:
            pct = 100.0
        duty = int(pct * 655.35)
        # On n'ecrit dans le PWM que si la valeur a reellement change :
        # inutile de solliciter le peripherique 1000 fois par seconde.
        if abs(duty - self._last_duty) >= 64 or (duty == 0) != (self._last_duty == 0):
            self._last_duty = duty
            try:
                self.pwm.duty_u16(duty)
            except Exception as exc:
                print("[LED] ecriture PWM impossible :", exc)
                self.available = False

    def off(self):
        """Extinction (arret propre)."""
        if self.available:
            try:
                self.pwm.duty_u16(0)
                self._last_duty = 0
            except Exception:
                pass
