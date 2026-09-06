# -*- coding: utf-8 -*-
"""
boot.py - Premier fichier exécuté par MicroPython au démarrage.

=====================================================================
POURQUOI CE FICHIER EST AUSSI COURT
=====================================================================
boot.py s'exécute AVANT tout le reste et avant que le REPL ne soit
disponible. S'il plante ou s'il part en boucle, la carte devient pénible
à récupérer. On y met donc le strict minimum.

=====================================================================
LES TROIS MODES DE DÉMARRAGE
=====================================================================
Ce que tu maintiens pendant le RESET décide de tout :

  rien           -> MACROPAD : clavier USB actif, usage normal
  B1 maintenu    -> SAFE MODE : le clavier n'est même pas créé.
                    Impossible de taper quoi que ce soit, même avec une
                    macro mal écrite. C'est ton filet de secours.
  B2 maintenu    -> MODE CONFIG : pas de clavier non plus, mais le WiFi
                    s'allume et une page web permet de modifier tes
                    macros depuis un navigateur.

Dans les deux modes spéciaux, `create_interface()` n'est jamais appelé :
le macropad est PHYSIQUEMENT incapable d'envoyer une touche.

AUCUNE TOUCHE N'EST ENVOYÉE ICI, dans aucun des trois cas. boot.py se
contente d'exister en tant que clavier ; c'est main.py qui décide quoi
envoyer, et seulement sur un appui de ta part.
"""

from machine import Pin
from time import sleep_ms
import config as C
import runtime


def _maintenu(index):
    """True si la touche d'index donné est maintenue enfoncée.

    La résistance de tirage interne met la broche à 3,3 V (valeur 1) ;
    appuyer la relie à la masse (valeur 0). On laisse 5 ms à la broche
    pour se stabiliser, puis on lit trois fois : un seul parasite ne doit
    pas nous faire croire à un appui.
    """
    broche = Pin(C.BUTTON_PINS[index], Pin.IN, Pin.PULL_UP)
    sleep_ms(5)
    for _ in range(3):
        if broche.value() != 0:
            return False
        sleep_ms(3)
    return True


# --- 1. LED éteinte, quoi qu'il arrive -------------------------------
# Au démarrage un GPIO est dans un état indéfini ; on force un 0 franc
# pour que la LED ne s'allume pas bêtement pendant l'initialisation.
Pin(C.LED_PIN, Pin.OUT, value=0)

# --- 2. Quel mode de démarrage ? -------------------------------------
runtime.safe_mode = _maintenu(C.SAFE_MODE_BUTTON_INDEX)
if not runtime.safe_mode:
    runtime.config_mode = _maintenu(C.CONFIG_MODE_BUTTON_INDEX)

# --- 3. Création du clavier USB, ou pas ------------------------------
if runtime.safe_mode:
    print("SAFE MODE - HID DISABLED")
elif runtime.config_mode:
    print("MODE CONFIG - WiFi actif, HID desactive")
elif C.HID_ENABLED:
    try:
        from hid_keyboard import create_interface
        runtime.interface = create_interface()
    except Exception as exc:
        # On n'avale jamais silencieusement une erreur de clavier :
        # elle est affichée et mémorisée pour que main.py la signale.
        runtime.hid_error = str(exc)
        print("ERREUR CRITIQUE INITIALISATION HID :", exc)
else:
    print("HID_ENABLED = False : le macropad ne tapera aucune touche.")
