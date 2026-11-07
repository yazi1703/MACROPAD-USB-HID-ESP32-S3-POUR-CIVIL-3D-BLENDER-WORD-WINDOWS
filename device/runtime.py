# -*- coding: utf-8 -*-
"""
runtime.py - Petite mémoire partagée entre boot.py et main.py.

MicroPython exécute d'abord boot.py, puis main.py. Ce sont deux fichiers
séparés qui ne peuvent pas se passer de variables directement. On utilise
donc ce module comme une boîte aux lettres : boot.py y dépose ce qu'il a
constaté, main.py vient le lire.

Rien n'est écrit dans la mémoire flash : tout est perdu au RESET, ce qui
est voulu (aucune usure de la flash, aucun état bizarre qui survivrait).
"""

safe_mode = False    # True si la touche de mode sans échec était maintenue
config_mode = False  # True si B2 était maintenu au démarrage (WiFi + page web)
interface = None     # l'objet clavier USB, ou None si HID désactivé
souris = None        # l'objet souris USB, ou None si pas de joystick
hid_error = None     # message d'erreur si la création du clavier a échoué
souris_error = None  # message d'erreur si la souris n'a pas pu être créée
