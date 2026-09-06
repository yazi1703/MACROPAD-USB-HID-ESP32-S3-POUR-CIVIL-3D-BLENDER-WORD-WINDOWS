# -*- coding: utf-8 -*-
"""
profiles.py - Les profils, macros et logiciels D'USINE du macropad.

=====================================================================
DEUX FACONS DE MODIFIER TES MACROS
=====================================================================
1. **Les pages web** (recommande) :
   - par USB : lance pc/macropad_auto.py, va sur http://127.0.0.1:8765
   - par WiFi : maintiens B2 au RESET, va sur http://192.168.4.1
   Tes reglages sont enregistres dans `profils.json` sur la carte.

2. **Ce fichier** : ce sont les valeurs d'usine. Elles servent tant que
   `profils.json` n'existe pas, et de filet de secours s'il est corrompu.
   Supprimer `profils.json` revient donc aux valeurs ci-dessous.

=====================================================================
TROIS GESTES PAR TOUCHE
=====================================================================
Chaque touche peut declencher trois macros differentes :

    appui court   -> obligatoire
    appui long    -> facultatif (maintenu au-dela de GESTE_LONG_MS)
    double appui  -> facultatif (deux appuis rapproches)

Six touches donnent donc jusqu'a dix-huit actions.

Une touche qui n'a PAS de macro double part instantanement au
relachement : on ne paie le delai d'attente que la ou on s'en sert.

On ecrit une touche avec l'aide K() :

    K("ANNUL",  [("combo", ("CTRL", "Z"))],              # appui court
        long=  [("combo", ("CTRL", "Y"))],               # appui long
        double=[("text_enter", "_UNDO")])                # double appui

Le libelle s'affiche sur l'ecran : **6 caracteres maximum**.

=====================================================================
LES TYPES D'ACTION
=====================================================================
  ("key", "TAB")                  une touche seule
  ("combo", ("CTRL", "Z"))        plusieurs touches ensemble
  ("text", "_HATCH")              ecrire une chaine
  ("text_enter", "_HATCH")        ecrire une chaine puis Entree

Une liste permet d'enchainer plusieurs actions dans un meme geste :

    K("ZOOM-E", [("text_enter", "_ZOOM"), ("text_enter", "E")])

Attention : les sequences a plusieurs actions ne sont pas editables depuis
les pages web (elles gerent une action par geste). Si tu en ecris une ici
et que tu enregistres ensuite depuis une page web, elle sera remplacee.

=====================================================================
NOMS DE TOUCHES UTILISABLES
=====================================================================
Modificateurs : CTRL, SHIFT, ALT, WIN, ALTGR
Touches nommees : ENTER, ESC, TAB, SPACE, BACKSPACE, DELETE, INSERT,
                  HOME, END, PAGEUP, PAGEDOWN, UP, DOWN, LEFT, RIGHT,
                  F1 a F12, MENU, CAPSLOCK, PRINTSCREEN
Un seul caractere ("G", "z", "1") : la TOUCHE PHYSIQUE qui ecrit ce
caractere avec la disposition reglee dans config.py.
"""

COURT = "court"
LONG = "long"
DOUBLE = "double"
GESTES = (COURT, LONG, DOUBLE)

LABEL_MAX = 6          # largeur d'un libelle sur l'ecran OLED


def K(label, court, long=None, double=None):
    """Construit une touche. Seul l'appui court est obligatoire."""
    gestes = {COURT: court}
    if long:
        gestes[LONG] = long
    if double:
        gestes[DOUBLE] = double
    return (label, gestes)


PROFILES = {

    # -----------------------------------------------------------------
    "BLENDER": [
        K("MOVE",   [("key", "G")]),
        K("ROT",    [("key", "R")]),
        K("SCALE",  [("key", "S")]),
        K("TAB",    [("key", "TAB")]),
        K("EXTRUD", [("key", "E")]),
        K("ANNUL",  [("combo", ("CTRL", "Z"))],
          long=[("combo", ("CTRL", "SHIFT", "Z"))]),      # retablir
    ],

    # -----------------------------------------------------------------
    # Le "_" devant les commandes AutoCAD force la commande INTERNATIONALE :
    # _MATCHPROP fonctionne meme sur un Civil 3D installe en francais.
    "CIVIL3D": [
        K("MATCH", [("text_enter", "_MATCHPROP")]),
        K("HATCH", [("text_enter", "_HATCH")]),
        K("ANNUL", [("combo", ("CTRL", "Z"))],
          long=[("combo", ("CTRL", "Y"))]),                # retablir
        K("ISOLE", [("text_enter", "_ISOLATEOBJECTS")],
          long=[("text_enter", "_UNISOLATEOBJECTS")]),     # tout remontrer
        K("ZOOM",  [("text_enter", "_ZOOM")],
          double=[("text_enter", "_REGEN")]),               # regenerer
        K("ENREG", [("combo", ("CTRL", "S"))]),
    ],

    # -----------------------------------------------------------------
    # RESERVE VALIDEE AVEC TOI : ces raccourcis sont ceux de Word en
    # ANGLAIS. Sur un Word FRANCAIS, Gras se fait avec Ctrl+G et non
    # Ctrl+B. Tu peux corriger cela en trente secondes depuis une page web.
    "WORD": [
        K("GRAS",   [("combo", ("CTRL", "B"))]),
        K("ITAL",   [("combo", ("CTRL", "I"))]),
        K("ENREG",  [("combo", ("CTRL", "S"))]),
        K("ANNUL",  [("combo", ("CTRL", "Z"))],
          long=[("combo", ("CTRL", "Y"))]),
        K("SOULIG", [("combo", ("CTRL", "U"))]),
        K("REFAIR", [("combo", ("CTRL", "Y"))]),
    ],

    # -----------------------------------------------------------------
    "WINDOWS": [
        K("EXPLOR", [("combo", ("WIN", "E"))]),
        K("ALTTAB", [("combo", ("ALT", "TAB"))]),
        K("BUREAU", [("combo", ("WIN", "D"))]),
        K("TACHES", [("combo", ("CTRL", "SHIFT", "ESC"))]),
        K("PRESSE", [("combo", ("WIN", "V"))]),
        K("CAPTUR", [("combo", ("WIN", "SHIFT", "S"))]),
    ],
}

# Nom affiche a l'ecran quand il differe de la cle interne.
TITLES = {"CIVIL3D": "CIVIL 3D"}


# =====================================================================
# ASSOCIATION LOGICIEL -> PROFIL
# =====================================================================
# Utilisee par la detection automatique. Le compagnon PC lit cette table
# sur la carte, ce qui permet de la modifier depuis n'importe laquelle des
# deux pages web : la configuration reste au meme endroit, sur le macropad.
#
#   nom de l'executable : (profil a activer, abreviation affichee)
#
# L'abreviation reste fixe a gauche de l'ecran pendant que le nom du
# fichier defile : tu sais toujours dans quel logiciel tu es.
APPS = [
    ("acad.exe",     "CIVIL3D", "C3D"),
    ("acadlt.exe",   "CIVIL3D", "C3D"),
    ("blender.exe",  "BLENDER", "Blender"),
    ("winword.exe",  "WORD",    "Wrd"),
    ("excel.exe",    "WORD",    "Xls"),
]

# Profil et abreviation utilises pour tout ce qui n'est pas dans la liste.
APPS_REPLI = ("WINDOWS", "Win")


class ProfileManager:
    """Se souvient du profil courant et gere la rotation circulaire.

    "Circulaire" veut dire qu'apres le dernier profil on revient au
    premier, dans les deux sens. C'est l'operateur % (reste de la
    division) qui fait ce travail, sans aucun test if.
    """

    def __init__(self, order, default, profiles=None, keys_expected=None):
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
        """Les touches du profil courant : [(libelle, gestes), ...]."""
        return self.profiles[self.name]

    def move(self, direction):
        """direction vaut +1 (profil suivant) ou -1 (profil precedent)."""
        self.index = (self.index + direction) % len(self.order)
        return self.name


# =====================================================================
# MACROS DE TEST (utilisees seulement si HID_TEST est regle dans config.py)
# =====================================================================
TESTS = {
    "LETTER":   [("text", "a")],
    "ESC":      [("key", "ESC")],
    "UNDO":     [("combo", ("CTRL", "Z"))],
    "AZERTY":   [("text", "_ABCDEFGHIJKLMNOPQRSTUVWXYZ")],
    "COMMANDS": [("text", "_MATCHPROP _HATCH _ISOLATEOBJECTS")],
}
