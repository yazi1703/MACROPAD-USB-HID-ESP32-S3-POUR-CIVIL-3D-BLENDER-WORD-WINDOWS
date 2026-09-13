#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apercu_agenda.py - Dessine la vue AGENDA dans le terminal.

=====================================================================
A QUOI CA SERT
=====================================================================
Verifier la mise en page SANS carte et SANS ecran. Ce n'est pas une
maquette dessinee a la main : c'est le VRAI code de device/display.py
qui tourne, avec un faux ecran qui note chaque trait et chaque texte,
puis les redessine ici.

Un bloc mal place, un intitule qui deborde sur son voisin, la ligne
"maintenant" a la mauvaise hauteur : ca se voit ici, en une seconde, au
lieu de se decouvrir apres avoir tout soude.

    python3 tools/apercu_agenda.py                  # a l'heure qu'il est
    python3 tools/apercu_agenda.py 19:47            # a une heure choisie
    python3 tools/apercu_agenda.py 19:47 mon.json   # avec ton agenda

Les traits sont dessines au pixel pres. Les textes, eux, sont poses a
leur position en caracteres : la police 8x8 de MicroPython n'existe pas
sur un PC, et la dessiner ici n'apprendrait rien de plus.
"""

import datetime
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "device"))
sys.path.insert(0, os.path.join(RACINE, "pc"))

# --- MicroPython n'existe pas ici : on bouche ce que display.py importe ---
import time as _time
import types

_time.ticks_ms = getattr(_time, "ticks_ms", lambda: 0)
_time.ticks_add = getattr(_time, "ticks_add", lambda a, b: a + b)
_time.ticks_diff = getattr(_time, "ticks_diff", lambda a, b: a - b)
sys.modules.setdefault("utime", _time)
_fb = types.ModuleType("framebuf")
_fb.FrameBuffer = type("FrameBuffer", (), {})
_fb.MONO_HLSB, _fb.MONO_VLSB = 3, 0
sys.modules.setdefault("framebuf", _fb)
_machine = types.ModuleType("machine")
sys.modules.setdefault("machine", _machine)

LARGEUR, HAUTEUR = 128, 64


class EcranPapier:
    """Un faux ecran qui garde tout ce qu'on lui dessine."""

    def __init__(self):
        self.pixels = [[0] * LARGEUR for _ in range(HAUTEUR)]
        self.textes = []                 # (x, y, texte)
        self.displaybuf = bytearray(1024)
        self.hors = 0

    def _point(self, x, y):
        if 0 <= x < LARGEUR and 0 <= y < HAUTEUR:
            self.pixels[y][x] = 1
        else:
            self.hors += 1

    def fill(self, couleur):
        for ligne in self.pixels:
            for x in range(LARGEUR):
                ligne[x] = couleur

    def fill_rect(self, x, y, w, h, couleur):
        for dy in range(h):
            for dx in range(w):
                if couleur:
                    self._point(x + dx, y + dy)
                elif 0 <= x + dx < LARGEUR and 0 <= y + dy < HAUTEUR:
                    self.pixels[y + dy][x + dx] = 0

    def rect(self, x, y, w, h, couleur):
        for dx in range(w):
            self._point(x + dx, y)
            self._point(x + dx, y + h - 1)
        for dy in range(h):
            self._point(x, y + dy)
            self._point(x + w - 1, y + dy)

    def hline(self, x, y, w, couleur):
        self.fill_rect(x, y, w, 1, couleur)

    def vline(self, x, y, h, couleur):
        self.fill_rect(x, y, 1, h, couleur)

    def pixel(self, x, y, couleur=1):
        self._point(x, y)

    def text(self, texte, x, y, couleur=1):
        self.textes.append((x, y, texte))

    def contrast(self, valeur):
        pass

    def sleep(self, valeur):
        pass

    def write_cmd(self, commande):
        pass

    def write_data(self, donnees):
        pass


def rendre(ecran):
    """L'image, en grille de caracteres.

    Une colonne de sortie = une CASE de 8 pixels, c'est-a-dire la largeur
    d'un caractere de la police : l'ecran fait donc 16 colonnes de large,
    exactement comme la vraie dalle. Une ligne de sortie = une rangee de
    pixels, pour voir au pixel pres ou tombent les traits et la ligne
    "maintenant".

    ATTENTION AU PIEGE QUI M'A EU : une premiere version n'affichait
    qu'une colonne de pixels sur deux. Tous les textes poses a une
    abscisse impaire disparaissaient, et on croyait a un defaut du
    firmware alors que le dessin etait juste. Un apercu doit etre fidele,
    ou ne pas etre.
    """
    cases = LARGEUR // 8
    grille = [[" "] * cases for _ in range(HAUTEUR)]

    # 1. les traits : une case s'allume selon le nombre de pixels allumes.
    for y in range(HAUTEUR):
        for case in range(cases):
            allumes = sum(ecran.pixels[y][case * 8:case * 8 + 8])
            if allumes >= 6:
                grille[y][case] = "#"
            elif allumes:
                grille[y][case] = "."

    # 2. les textes par-dessus, a leur case. Un caractere occupe huit
    #    rangees de pixels ; on l'ecrit sur la premiere, et on libere les
    #    suivantes pour ne pas confondre son corps avec un trait.
    for x, y, texte in ecran.textes:
        for index, caractere in enumerate(texte):
            case = x // 8 + index
            if 0 <= case < cases and 0 <= y < HAUTEUR:
                grille[y][case] = caractere

    bord = "    +" + "-" * cases + "+"
    lignes = [bord]
    for y, ligne in enumerate(grille):
        # Le numero de rangee tous les huit pixels : c'est la grille des
        # caracteres, et c'est ce qui permet de verifier une hauteur.
        repere = "%3d " % y if y % 8 == 0 else "    "
        lignes.append(repere + "|" + "".join(ligne) + "|")
    lignes.append(bord)
    return "\n".join(lignes)


def main():
    heure = sys.argv[1] if len(sys.argv) > 1 else None
    fichier = (sys.argv[2] if len(sys.argv) > 2
               else os.path.join(RACINE, "pc", "agenda-exemple.json"))

    import macropad_auto as MA
    from agenda import Agenda
    from display import Display

    aujourdhui = datetime.date.today()
    with open(fichier, encoding="utf-8") as source:
        evenements = MA.evenements_du_jour(json.load(source), aujourdhui)

    maintenant = datetime.datetime.now()
    if heure:
        heures, minutes = heure.split(":")
        maintenant = maintenant.replace(hour=int(heures), minute=int(minutes))

    journee = Agenda()
    journee.set_heure(MA.ligne_heure(maintenant)[2:], 0)
    for ligne in MA.lignes_agenda(evenements):
        if ligne == "!AGBEGIN":
            journee.commencer()
        elif ligne == "!AGEND":
            journee.terminer()
        else:
            journee.ajouter(ligne[2:])

    ecran = Display()
    ecran.oled = EcranPapier()
    ecran.set_agenda(journee)
    ecran.rafraichir_agenda(0)

    print()
    print(rendre(ecran.oled))
    prefixe, titre = journee.resume(journee.minute(0))
    print("\n  ligne du bas : %r + %r" % (prefixe, titre))
    print("  evenements   : %d aujourd'hui, %d dans la fenetre"
          % (len(journee.evenements), len(journee.fenetre(journee.minute(0))[1])))
    if ecran.oled.hors:
        print("  ATTENTION    : %d pixels dessines hors de l'ecran"
              % ecran.oled.hors)
    return 0


if __name__ == "__main__":
    sys.exit(main())
