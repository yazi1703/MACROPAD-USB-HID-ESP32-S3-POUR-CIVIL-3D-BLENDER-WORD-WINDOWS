# -*- coding: utf-8 -*-
"""
profiles.py - Les profils et macros D'USINE du macropad.

=====================================================================
DEUX FAÇONS DE MODIFIER TES MACROS
=====================================================================
1. **La page web** (recommandé) : maintiens B2 pendant le RESET, connecte-toi
   au WiFi du macropad, ouvre http://192.168.4.1 et modifie tout à la
   souris. Tes réglages sont enregistrés dans `profils.json` sur la carte.

2. **Ce fichier** : ce sont les valeurs d'usine. Elles servent tant que
   `profils.json` n'existe pas, et de filet de secours si ce fichier est
   corrompu. Supprimer `profils.json` revient donc aux valeurs ci-dessous.

=====================================================================
COMMENT EST ÉCRITE UNE MACRO
=====================================================================
Chaque touche est une paire :   (libellé affiché, liste d'actions)

Le libellé s'affiche sur l'écran OLED : **6 caractères maximum**, parce que
l'écran affiche maintenant six touches sur trois lignes.

Les types d'action :

  ("key", "TAB")                  une touche seule
  ("combo", ("CTRL", "Z"))        plusieurs touches ensemble
  ("text", "_HATCH")              écrire une chaîne
  ("text_enter", "_HATCH")        écrire une chaîne puis Entrée

La liste permet d'enchaîner plusieurs actions :

  ("ZOOM-E", [("text_enter", "_ZOOM"), ("text_enter", "E")])

Attention : les séquences à plusieurs actions ne sont pas éditables depuis
la page web (elle ne gère qu'une action par touche). Si tu en écris une ici
et que tu enregistres ensuite depuis la page web, elle sera remplacée.

=====================================================================
NOMS DE TOUCHES UTILISABLES
=====================================================================
Modificateurs : CTRL, SHIFT, ALT, WIN, ALTGR
Touches nommées : ENTER, ESC, TAB, SPACE, BACKSPACE, DELETE, INSERT,
                  HOME, END, PAGEUP, PAGEDOWN, UP, DOWN, LEFT, RIGHT,
                  F1 à F12, MENU, CAPSLOCK, PRINTSCREEN
Un seul caractère ("G", "z", "1") : la TOUCHE PHYSIQUE qui écrit ce
caractère avec la disposition réglée dans config.py.
"""

PROFILES = {

    # -----------------------------------------------------------------
    "BLENDER": [
        ("MOVE",   [("key", "G")]),                  # Grab, déplacer
        ("ROT",    [("key", "R")]),                  # Rotate
        ("SCALE",  [("key", "S")]),                  # Scale
        ("TAB",    [("key", "TAB")]),                # Objet / Édition
        ("EXTRUD", [("key", "E")]),                  # Extrude
        ("ANNUL",  [("combo", ("CTRL", "Z"))]),      # Annuler
    ],

    # -----------------------------------------------------------------
    # Le "_" devant les commandes AutoCAD force la commande INTERNATIONALE :
    # _MATCHPROP fonctionne même sur un Civil 3D installé en français.
    "CIVIL3D": [
        ("MATCH", [("text_enter", "_MATCHPROP")]),      # copier les propriétés
        ("HATCH", [("text_enter", "_HATCH")]),          # hachures
        ("ANNUL", [("combo", ("CTRL", "Z"))]),          # annuler
        ("ISOLE", [("text_enter", "_ISOLATEOBJECTS")]),  # isoler
        ("ZOOM",  [("text_enter", "_ZOOM")]),           # zoom
        ("ENREG", [("combo", ("CTRL", "S"))]),          # enregistrer
    ],

    # -----------------------------------------------------------------
    # RÉSERVE VALIDÉE AVEC TOI : ces raccourcis sont ceux de Word en
    # ANGLAIS. Sur un Word FRANÇAIS, Gras se fait avec Ctrl+G et non
    # Ctrl+B. Tu peux corriger cela en trente secondes depuis la page web.
    "WORD": [
        ("GRAS",   [("combo", ("CTRL", "B"))]),
        ("ITAL",   [("combo", ("CTRL", "I"))]),
        ("ENREG",  [("combo", ("CTRL", "S"))]),
        ("ANNUL",  [("combo", ("CTRL", "Z"))]),
        ("SOULIG", [("combo", ("CTRL", "U"))]),
        ("REFAIR", [("combo", ("CTRL", "Y"))]),
    ],

    # -----------------------------------------------------------------
    "WINDOWS": [
        ("EXPLOR", [("combo", ("WIN", "E"))]),               # Explorateur
        ("ALTTAB", [("combo", ("ALT", "TAB"))]),             # changer de fenêtre
        ("BUREAU", [("combo", ("WIN", "D"))]),               # afficher le bureau
        ("TACHES", [("combo", ("CTRL", "SHIFT", "ESC"))]),   # gestionnaire
        ("PRESSE", [("combo", ("WIN", "V"))]),               # presse-papiers
        ("CAPTUR", [("combo", ("WIN", "SHIFT", "S"))]),      # capture d'écran
    ],
}

# Nom affiché à l'écran quand il diffère de la clé interne.
TITLES = {"CIVIL3D": "CIVIL 3D"}

# =====================================================================
# MACROS DE TEST (utilisées seulement si HID_TEST est réglé dans config.py)
# =====================================================================
TESTS = {
    "LETTER":   [("text", "a")],
    "ESC":      [("key", "ESC")],
    "UNDO":     [("combo", ("CTRL", "Z"))],
    "AZERTY":   [("text", "_ABCDEFGHIJKLMNOPQRSTUVWXYZ")],
    "COMMANDS": [("text", "_MATCHPROP _HATCH _ISOLATEOBJECTS")],
}

LABEL_MAX = 6          # largeur d'un libellé sur l'écran OLED


class ProfileManager:
    """Se souvient du profil courant et gère la rotation circulaire.

    "Circulaire" veut dire qu'après le dernier profil on revient au
    premier, dans les deux sens. C'est l'opérateur % (reste de la
    division) qui fait ce travail, sans aucun test if.
    """

    def __init__(self, order, default, profiles=None, keys_expected=None):
        # profiles=None : on utilise les profils d'usine ci-dessus.
        # Sinon on utilise ceux fournis (venant de profils.json).
        self.profiles = PROFILES if profiles is None else profiles

        if not order or len(set(order)) != len(order):
            raise ValueError("Ordre des profils vide ou doublons")
        for name in order:
            if name not in self.profiles:
                raise ValueError("Profil invalide : " + name)
            if keys_expected is not None and len(self.profiles[name]) != keys_expected:
                raise ValueError("Profil %s : %d touches au lieu de %d"
                                 % (name, len(self.profiles[name]), keys_expected))
        self.order = order
        self.index = order.index(default) if default in order else 0

    @property
    def name(self):
        return self.order[self.index]

    @property
    def macros(self):
        """Les macros du profil courant."""
        return self.profiles[self.name]

    def move(self, direction):
        """direction vaut +1 (profil suivant) ou -1 (profil précédent)."""
        self.index = (self.index + direction) % len(self.order)
        return self.name
