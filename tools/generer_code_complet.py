# -*- coding: utf-8 -*-
"""
generer_code_complet.py - Reconstruit CODE_COMPLET.md a partir de device/.

CODE_COMPLET.md est une copie lisible de tout le firmware, pratique pour
relire le projet sans ouvrir douze fichiers. Comme c'est une copie, elle
se perime des qu'on modifie le code : ce script la regenere.

Utilisation, depuis la racine du projet :

    python3 tools/generer_code_complet.py

Ce script ne tourne que sur le PC ; ne le copie pas sur la carte.
"""

import hashlib
import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVICE = os.path.join(RACINE, "device")

# Ordre de lecture pense pour un debutant : du plus general au plus technique.
ORDRE = [
    "config.py",
    "profiles.py",
    "boot.py",
    "main.py",
    "runtime.py",
    "inputs.py",
    "layouts.py",
    "hid_keyboard.py",
    "display.py",
    "led.py",
    "diag.py",
    "sh1106.py",
    "lib/usb/device/__init__.py",
    "lib/usb/device/core.py",
    "lib/usb/device/hid.py",
    "lib/usb/device/keyboard.py",
]

TIERS = {
    "sh1106.py": "Fichier TIERS repris sans modification (robert-hh/SH1106, MIT).",
    "lib/usb/device/__init__.py": "Fichier TIERS repris sans modification (micropython-lib, MIT).",
    "lib/usb/device/core.py": "Fichier TIERS repris sans modification (micropython-lib, MIT).",
    "lib/usb/device/hid.py": "Fichier TIERS repris sans modification (micropython-lib, MIT).",
    "lib/usb/device/keyboard.py": "Fichier TIERS repris sans modification (micropython-lib, MIT).",
}


def main():
    morceaux = [
        "# Code complet du firmware\n",
        "",
        "Copie lisible de tous les fichiers de `device/`.",
        "**Ce document est genere automatiquement** par",
        "`tools/generer_code_complet.py` : ne le modifie pas a la main,",
        "modifie les fichiers `.py` puis relance le script.",
        "",
        "Pour transferer le firmware sur la carte, utilise les fichiers `.py`",
        "de `device/`, pas ce document.",
        "",
        "## Sommaire",
        "",
    ]
    for nom in ORDRE:
        ancre = nom.replace("/", "").replace(".", "").replace("_", "")
        morceaux.append("- [`device/%s`](#device%s)" % (nom, ancre))
    morceaux.append("")

    for nom in ORDRE:
        chemin = os.path.join(DEVICE, nom)
        with open(chemin, "rb") as fichier:
            brut = fichier.read()
        empreinte = hashlib.sha256(brut).hexdigest()
        texte = brut.decode("utf-8")
        lignes = texte.count("\n")

        morceaux.append("")
        morceaux.append("---")
        morceaux.append("")
        morceaux.append("## device/%s" % nom)
        morceaux.append("")
        if nom in TIERS:
            morceaux.append("> %s" % TIERS[nom])
            morceaux.append("")
        morceaux.append("`%d lignes - sha256 %s`" % (lignes, empreinte[:16]))
        morceaux.append("")
        morceaux.append("```python")
        morceaux.append(texte.rstrip("\n"))
        morceaux.append("```")

    morceaux.append("")
    sortie = "\n".join(morceaux) + "\n"
    with open(os.path.join(RACINE, "CODE_COMPLET.md"), "w") as fichier:
        fichier.write(sortie)
    print("CODE_COMPLET.md regenere : %d fichiers, %d octets"
          % (len(ORDRE), len(sortie)))


if __name__ == "__main__":
    main()
