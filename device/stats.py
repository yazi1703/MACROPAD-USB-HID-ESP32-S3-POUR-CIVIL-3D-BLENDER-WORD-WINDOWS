# -*- coding: utf-8 -*-
"""
stats.py - Compteur d'usage des macros.

=====================================================================
A QUOI CA SERT
=====================================================================
Le macropad compte combien de fois chaque macro est declenchee. Au bout
de deux semaines, la page de configuration te les classe et tu sais
OBJECTIVEMENT :

  * quelles macros meritent la premiere rangee de ton boitier ;
  * lesquelles ne servent jamais et peuvent laisser leur place ;
  * quels profils tu utilises vraiment.

C'est de la donnee pour concevoir, pas de la decoration. Particulierement
utile AVANT de figer la disposition d'un boitier imprime.

=====================================================================
POURQUOI ON N'ECRIT PAS A CHAQUE APPUI
=====================================================================
La memoire flash d'un microcontroleur supporte un nombre limite de cycles
d'ecriture (de l'ordre de 100 000 par secteur). Ecrire a chaque appui
userait la flash pour rien.

Les compteurs vivent donc en memoire vive, et ne sont ecrits sur la flash
que toutes les STATS_SAVE_EVERY frappes (25 par defaut), plus une fois a
l'arret propre du programme. Au pire tu perds les vingt-quatre derniers
appuis si tu debranches brutalement : sans importance pour une statistique.

Le fichier stats.json n'est jamais indispensable : s'il manque ou s'il est
illisible, on repart de zero sans rien signaler de dramatique.
"""

import json

import config as C


class Stats:
    """Compteurs par profil et par touche."""

    def __init__(self, nb_touches, actif=True):
        self.nb_touches = nb_touches
        self.actif = actif and getattr(C, "STATS_ENABLED", True)
        self.compteurs = {}          # {"CIVIL3D": [12, 3, 40, 0, 1, 5], ...}
        self._depuis_ecriture = 0
        if self.actif:
            self.charger()

    # ------------------------------------------------------------------
    def charger(self):
        try:
            with open(C.STATS_FILE) as fichier:
                data = json.load(fichier)
        except OSError:
            return                    # pas encore de statistiques : normal
        except Exception as exc:
            print("[stats] fichier illisible (%s), on repart de zero" % exc)
            return
        if not isinstance(data, dict):
            return
        for nom, valeurs in data.items():
            try:
                liste = [int(v) for v in valeurs][:self.nb_touches]
            except Exception:
                continue
            while len(liste) < self.nb_touches:
                liste.append(0)
            self.compteurs[str(nom)] = liste

    def enregistrer(self):
        """Ecrit les compteurs. Retourne True si l'ecriture a eu lieu."""
        if not self.actif or not self.compteurs:
            return False
        try:
            temporaire = C.STATS_FILE + ".tmp"
            with open(temporaire, "w") as fichier:
                json.dump(self.compteurs, fichier)
            import os
            try:
                os.remove(C.STATS_FILE)
            except OSError:
                pass
            os.rename(temporaire, C.STATS_FILE)
        except Exception as exc:
            print("[stats] ecriture impossible :", exc)
            return False
        self._depuis_ecriture = 0
        return True

    # ------------------------------------------------------------------
    def compter(self, profil, index):
        """Enregistre un appui. Ecrit sur la flash de temps en temps."""
        if not self.actif or not (0 <= index < self.nb_touches):
            return
        liste = self.compteurs.get(profil)
        if liste is None:
            liste = [0] * self.nb_touches
            self.compteurs[profil] = liste
        liste[index] += 1
        self._depuis_ecriture += 1
        if self._depuis_ecriture >= getattr(C, "STATS_SAVE_EVERY", 25):
            self.enregistrer()

    def pour(self, profil):
        """Compteurs d'un profil, toujours de la bonne longueur."""
        return self.compteurs.get(profil, [0] * self.nb_touches)

    def total(self):
        return sum(sum(v) for v in self.compteurs.values())

    def remettre_a_zero(self):
        self.compteurs = {}
        try:
            import os
            os.remove(C.STATS_FILE)
        except OSError:
            pass
        self._depuis_ecriture = 0
