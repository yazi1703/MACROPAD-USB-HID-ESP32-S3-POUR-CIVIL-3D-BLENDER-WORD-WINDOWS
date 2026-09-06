# -*- coding: utf-8 -*-
"""
boot.py - Premier fichier exécuté par MicroPython au démarrage.

=====================================================================
POURQUOI CE FICHIER EST AUSSI COURT
=====================================================================
boot.py s'exécute AVANT tout le reste et avant que le REPL ne soit
disponible. S'il plante ou s'il part en boucle, la carte devient
pénible à récupérer. On y met donc le strict minimum.

Il fait exactement trois choses :

1. Il éteint la LED du bouton ESC. Au démarrage un GPIO est dans un état
   indéfini ; on force un 0 franc pour que la LED ne s'allume pas
   bêtement pendant l'initialisation.

2. Il regarde si tu maintiens B1 : c'est le SAFE MODE.
   En SAFE MODE, le clavier USB n'est même pas créé. Il devient donc
   physiquement impossible que le macropad tape quoi que ce soit, même si
   une macro est mal écrite. C'est ton filet de secours.

3. Si tout va bien et si HID_ENABLED est True, il déclare le clavier USB
   à Windows. AUCUNE TOUCHE N'EST ENVOYEE ICI : on se contente d'exister
   en tant que clavier.

Ensuite MicroPython lance main.py.
"""

from machine import Pin
from time import sleep_ms
import config as C
import runtime

# --- 1. LED éteinte, quoi qu'il arrive -------------------------------
Pin(C.LED_PIN, Pin.OUT, value=0)

# --- 2. Détection du SAFE MODE ---------------------------------------
# La résistance de tirage interne met la broche à 3,3 V (valeur 1).
# Appuyer sur B1 la relie à la masse (valeur 0).
# On laisse 5 ms à la broche pour se stabiliser, puis on lit trois fois :
# un seul parasite ne doit pas nous faire croire à un appui.
_b1 = Pin(C.BUTTON_PINS[0], Pin.IN, Pin.PULL_UP)
sleep_ms(5)
runtime.safe_mode = True
for _ in range(3):
    if _b1.value() != 0:
        runtime.safe_mode = False
        break
    sleep_ms(3)

# --- 3. Création du clavier USB, ou pas ------------------------------
if runtime.safe_mode:
    print("SAFE MODE - HID DISABLED")
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
