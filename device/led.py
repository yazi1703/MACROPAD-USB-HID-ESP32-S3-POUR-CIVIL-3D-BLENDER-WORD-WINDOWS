# -*- coding: utf-8 -*-
"""
led.py - La LED du gros bouton ESC : respiration douce et flash à l'appui.

=====================================================================
CE QU'EST LE PWM, EN DEUX PHRASES
=====================================================================
Un GPIO ne sait faire que deux choses : 0 V ou 3,3 V. Pour obtenir une
demi-luminosité, on allume et on éteint très vite : 2000 fois par seconde
ici. Si on est allumé 25 % du temps, l'oeil voit une LED à 25 % de
luminosité. Ce pourcentage s'appelle le rapport cyclique.

2000 Hz est choisi assez haut pour qu'aucun scintillement ne soit visible,
même du coin de l'oeil ou devant une caméra.

=====================================================================
RAPPEL DE SECURITE ELECTRIQUE
=====================================================================
Ce GPIO ne pilote PAS la LED. Il pilote la base d'un transistor BC547 à
travers une résistance de 2,2 kilo-ohms, et c'est le transistor qui laisse
passer le courant de la LED. Le GPIO ne fournit qu'environ 1,2 mA.

Brancher une LED 1 W directement sur un GPIO détruirait la broche : un
GPIO d'ESP32-S3 ne supporte qu'environ 40 mA, et une LED sans résistance
en tirerait beaucoup plus. Voir docs/05-electronique.md.

=====================================================================
POURQUOI UN COSINUS ET PAS UNE SIMPLE MONTEE
=====================================================================
Une rampe qui monte puis redescend en ligne droite donne un effet
"clignotant triangulaire" assez désagréable : les changements de sens sont
brutaux. Le cosinus, lui, arrive en douceur aux extrémités, exactement
comme une respiration.

L'exposant 1,6 accentue encore l'effet : la LED s'attarde dans les valeurs
basses et ne fait que passer par le maximum. C'est ce qui rend l'animation
naturelle plutôt que mécanique.

Aucune méthode de ce fichier n'attend : tick() calcule la valeur qui
correspond à l'instant présent et rend la main aussitôt. La respiration ne
ralentit donc jamais les touches.
"""

from machine import Pin, PWM
from time import ticks_ms, ticks_diff
from math import cos, pi
import config as C


def breath(phase_ms):
    """Luminosité voulue (de 0.0 à 1.0) à un instant donné du cycle.

    phase_ms va de 0 à LED_PERIOD_MS. La fonction est "pure" : elle ne
    dépend que de son argument, ce qui permet de la tester sur PC sans
    aucun matériel.
    """
    # (1 - cos(x)) / 2 dessine une courbe qui part de 0, monte doucement
    # jusqu'à 1 au milieu du cycle, puis redescend en douceur jusqu'à 0.
    wave = (1 - cos(2 * pi * phase_ms / C.LED_PERIOD_MS)) / 2
    return C.LED_MIN + (C.LED_MAX - C.LED_MIN) * wave ** 1.6


class Led:

    def __init__(self):
        self.pwm = PWM(Pin(C.LED_PIN), freq=C.PWM_FREQ, duty_u16=0)
        self.last = ticks_ms()
        self.phase = 0            # où on en est dans le cycle de respiration
        self.flashed_at = None    # instant du dernier appui sur ESC

    def flash(self, now):
        """Éclat lumineux immédiat, déclenché par le bouton ESC.

        On monte à 100 % tout de suite, sans attendre le prochain tick :
        l'éclat doit être perçu comme simultané à l'appui.
        Aucun risque de surchauffe : le courant reste limité à quelques
        milliampères par la résistance de 330 ohms.
        """
        self.flashed_at = now
        self.set_level(1.0)

    def set_level(self, value):
        """Applique une luminosité de 0.0 à 1.0 au PWM."""
        # duty_u16 attend un nombre de 0 à 65535. Le min/max est une
        # ceinture de sécurité contre une valeur de calcul aberrante.
        self.pwm.duty_u16(int(max(0, min(1, value)) * 65535))

    def tick(self, now):
        """Appelé à chaque tour de la boucle principale."""
        # On avance la phase du temps réellement écoulé. ticks_diff gère
        # correctement le "retour à zéro" du compteur de millisecondes de
        # MicroPython, qui repart de 0 au bout d'environ 12 jours.
        self.phase = (self.phase + max(0, ticks_diff(now, self.last))) % C.LED_PERIOD_MS
        self.last = now
        level = breath(self.phase)

        if self.flashed_at is not None:
            age = ticks_diff(now, self.flashed_at)
            if age < C.LED_FLASH_MS:
                level = 1.0                      # plein éclat
            elif age < C.LED_FLASH_MS + C.LED_RETURN_MS:
                # Retour progressif vers la respiration. La formule
                # x*x*(3-2x) est un lissage classique : elle démarre et
                # finit tout en douceur au lieu de "casser".
                x = (age - C.LED_FLASH_MS) / C.LED_RETURN_MS
                smooth = x * x * (3 - 2 * x)
                level = 1.0 + (level - 1.0) * smooth
            else:
                self.flashed_at = None           # flash terminé

        self.set_level(level)

    def close(self):
        """Extinction propre quand le programme s'arrête."""
        self.set_level(0)
        self.pwm.deinit()
        # deinit() relâche la broche ; on la repasse en sortie à 0 pour
        # être certain que le transistor reste bloqué et la LED éteinte.
        Pin(C.LED_PIN, Pin.OUT, value=0)
