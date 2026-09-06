# -*- coding: utf-8 -*-
"""
profiles.py - Toutes les macros du macropad. C'est LE fichier à modifier.

=====================================================================
COMMENT EST ECRITE UNE MACRO
=====================================================================
Chaque touche est une paire :   (libellé affiché, liste d'actions)

Le libellé s'affiche sur l'écran OLED (14 caractères maximum).
La liste d'actions contient une ou plusieurs actions exécutées à la suite.

Les quatre types d'action disponibles :

  ("key", "TAB")                  une touche seule
  ("combo", ("CTRL", "Z"))        plusieurs touches ensemble
  ("text", "_HATCH")              écrire une chaîne, caractère par caractère
  ("text_enter", "_HATCH")        écrire une chaîne puis appuyer sur Entrée

Comme c'est une LISTE, tu peux déjà enchaîner plusieurs actions :

  ("ZOOM", [("text_enter", "_ZOOM"), ("text_enter", "E")])

=====================================================================
NOMS DE TOUCHES UTILISABLES
=====================================================================
Modificateurs : CTRL, SHIFT, ALT, WIN, ALTGR
Touches nommées : ENTER, ESC, TAB, SPACE, BACKSPACE, DELETE, INSERT,
                  HOME, END, PAGEUP, PAGEDOWN, UP, DOWN, LEFT, RIGHT,
                  F1 à F12, MENU, CAPSLOCK, PRINTSCREEN
Un seul caractère ("G", "z", "1") : désigne la TOUCHE PHYSIQUE qui écrit
ce caractère avec la disposition réglée dans config.py.

C'est ce dernier point qui fait que Ctrl+Z envoie bien "Annuler" sur un
Windows français, et non Ctrl+W qui fermerait le document.

=====================================================================
POUR AJOUTER UN PROFIL (QGIS, AutoTURN, Road Survey...)
=====================================================================
1. Ajoute une entrée dans PROFILES ci-dessous, avec exactement 4 touches.
2. Ajoute son nom dans PROFILES_ORDER, dans config.py.
Rien d'autre : la rotation circulaire s'adapte automatiquement.
"""

PROFILES = {

    # -----------------------------------------------------------------
    "BLENDER": [
        ("MOVE",  [("key", "G")]),      # G = Grab, déplacer
        ("ROT",   [("key", "R")]),      # R = Rotate
        ("SCALE", [("key", "S")]),      # S = Scale
        ("TAB",   [("key", "TAB")]),    # bascule mode Objet / mode Édition
    ],

    # -----------------------------------------------------------------
    # Le "_" devant les commandes AutoCAD force la commande INTERNATIONALE :
    # _MATCHPROP fonctionne même sur un Civil 3D installé en français.
    # C'est pour cela qu'on tient tant à écrire correctement ce caractère.
    "CIVIL3D": [
        ("MATCH", [("text_enter", "_MATCHPROP")]),        # copier les propriétés
        ("HATCH", [("text_enter", "_HATCH")]),            # hachures
        ("UNDO",  [("combo", ("CTRL", "Z"))]),            # annuler
        ("ISOLE", [("text_enter", "_ISOLATEOBJECTS")]),   # isoler les objets
    ],

    # -----------------------------------------------------------------
    # RESERVE IMPORTANTE, VALIDEE AVEC TOI :
    # ces raccourcis sont ceux de Word en ANGLAIS.
    # Sur un Word en FRANCAIS, Gras se fait avec Ctrl+G (et non Ctrl+B),
    # Italique avec Ctrl+I, Souligné avec Ctrl+U.
    # Si ton Word est français, commente les quatre lignes actives et
    # décommente le bloc "Word français" juste en dessous.
    "WORD": [
        ("BOLD",   [("combo", ("CTRL", "B"))]),
        ("ITALIC", [("combo", ("CTRL", "I"))]),
        ("SAVE",   [("combo", ("CTRL", "S"))]),
        ("UNDO",   [("combo", ("CTRL", "Z"))]),
        # --- Word français : à décommenter et remplacer les 4 lignes ci-dessus
        # ("GRAS",  [("combo", ("CTRL", "G"))]),
        # ("ITAL",  [("combo", ("CTRL", "I"))]),
        # ("ENREG", [("combo", ("CTRL", "S"))]),
        # ("ANNUL", [("combo", ("CTRL", "Z"))]),
    ],

    # -----------------------------------------------------------------
    "WINDOWS": [
        ("EXPLORER", [("combo", ("WIN", "E"))]),            # Explorateur de fichiers
        ("ALT-TAB",  [("combo", ("ALT", "TAB"))]),          # changer de fenêtre
        ("DESKTOP",  [("combo", ("WIN", "D"))]),            # afficher le bureau
        ("TASKMGR",  [("combo", ("CTRL", "SHIFT", "ESC"))]),  # gestionnaire des tâches
    ],
}

# Nom affiché à l'écran quand il diffère de la clé interne.
TITLES = {"CIVIL3D": "CIVIL 3D"}

# =====================================================================
# MACROS DE TEST (utilisées seulement si HID_TEST est réglé dans config.py)
# =====================================================================
# Elles servent à valider le clavier une brique à la fois, dans le
# Bloc-notes, sans risquer de lancer une commande dans Civil 3D.
# Les deux modes texte n'ajoutent volontairement PAS de touche Entrée :
# tu peux ainsi relire l'orthographe avant de valider quoi que ce soit.
TESTS = {
    "LETTER":   [("text", "a")],
    "ESC":      [("key", "ESC")],
    "UNDO":     [("combo", ("CTRL", "Z"))],
    "AZERTY":   [("text", "_ABCDEFGHIJKLMNOPQRSTUVWXYZ")],
    "COMMANDS": [("text", "_MATCHPROP _HATCH _ISOLATEOBJECTS")],
}


class ProfileManager:
    """Se souvient du profil courant et gère la rotation circulaire.

    "Circulaire" veut dire qu'après le dernier profil on revient au
    premier, dans les deux sens. C'est l'opérateur % (reste de la
    division) qui fait ce travail, sans aucun test if.
    """

    def __init__(self, order, default):
        # On refuse de démarrer avec une configuration incohérente :
        # mieux vaut une erreur claire tout de suite qu'un comportement
        # bizarre une fois le macropad branché.
        if not order or len(set(order)) != len(order):
            raise ValueError("Ordre des profils vide ou doublons")
        for name in order:
            if name not in PROFILES or len(PROFILES[name]) != 4:
                raise ValueError("Profil invalide : " + name)
        self.order = order
        self.index = order.index(default)

    @property
    def name(self):
        return self.order[self.index]

    def move(self, direction):
        """direction vaut +1 (profil suivant) ou -1 (profil précédent)."""
        self.index = (self.index + direction) % len(self.order)
        return self.name
