# -*- coding: utf-8 -*-
"""
boot.py - Execute avant main.py au demarrage de la carte.

VOLONTAIREMENT MINIMAL.

boot.py doit rester quasiment vide : s'il plante, la carte devient
difficile a recuperer. On n'y initialise donc AUCUN peripherique, et
surtout aucun clavier USB HID.

Tout le materiel est initialise dans main.py, qui est lui protege par le
SAFE MODE (maintenir B1 pendant la mise sous tension).
"""

import gc

gc.collect()
print("[BOOT] MicroPython pret, lancement de main.py")
