# -*- coding: utf-8 -*-
"""
profiles.py - Tous les profils et toutes les macros du macropad.

C'EST LE SEUL FICHIER A MODIFIER pour changer le comportement des touches.

FORMAT D'UNE MACRO
------------------
Chaque touche est un dictionnaire :

    {"label": "MATCH", "type": "text_enter", "value": "_MATCHPROP"}

  label : texte affiche sur l'ecran OLED (7 caracteres maximum)
  type  : "key"        -> une touche seule            value = "TAB"
          "combo"      -> une combinaison             value = ("CTRL", "Z")
          "text"       -> ecrire une chaine           value = "_HATCH"
          "text_enter" -> ecrire une chaine + ENTREE  value = "_HATCH"
          "sequence"   -> plusieurs actions a la suite
                          value = [ {...}, {...} ]     (extensible)
          "none"       -> touche inactive

NOMS DE TOUCHES UTILISABLES
---------------------------
  Modificateurs : CTRL, SHIFT, ALT, WIN, ALTGR
  Touches nommees : ENTER, ESC, TAB, SPACE, BACKSPACE, DELETE, INSERT,
                    HOME, END, PAGEUP, PAGEDOWN, UP, DOWN, LEFT, RIGHT,
                    F1..F12, MENU, CAPSLOCK, PRINTSCREEN
  Un seul caractere ("G", "z", "1") : designe la TOUCHE PHYSIQUE qui produit
  ce caractere avec la disposition Windows definie dans config.py.
  C'est important : sur un Windows AZERTY, "CTRL"+"Z" envoie bien Annuler,
  et non CTRL+W qui fermerait le document.

AJOUTER UN PROFIL
-----------------
1. Ajouter une entree dans PROFILES.
2. Ajouter son nom dans PROFILES_ORDER a la position voulue.
Rien d'autre : la navigation circulaire s'adapte automatiquement.
"""

# Ordre de rotation des profils (TTP223 SUIVANT / PRECEDENT).
# Pour ajouter QGIS, AutoTURN, Road Survey... il suffit de completer
# cette liste et le dictionnaire PROFILES ci-dessous.
PROFILES_ORDER = [
    "BLENDER",
    "CIVIL3D",
    "WORD",
    "WINDOWS",
]

PROFILES = {
    # =================================================================
    "BLENDER": {
        "title": "BLENDER",          # 16 caracteres maximum pour l'OLED
        "keys": [
            {"label": "MOVE",  "type": "key", "value": "G"},   # Grab / deplacer
            {"label": "ROTATE", "type": "key", "value": "R"},  # Rotate
            {"label": "SCALE", "type": "key", "value": "S"},   # Scale
            {"label": "TAB",   "type": "key", "value": "TAB"},  # Mode edition
        ],
    },

    # =================================================================
    "CIVIL3D": {
        "title": "CIVIL 3D",
        "keys": [
            # Le prefixe "_" force la commande internationale d'AutoCAD :
            # _MATCHPROP fonctionne meme sur un Civil 3D en francais.
            {"label": "MATCH", "type": "text_enter", "value": "_MATCHPROP"},
            {"label": "HATCH", "type": "text_enter", "value": "_HATCH"},
            {"label": "UNDO",  "type": "combo", "value": ("CTRL", "Z")},
            {"label": "ISOLE", "type": "text_enter", "value": "_ISOLATEOBJECTS"},
        ],
    },

    # =================================================================
    "WORD": {
        "title": "WORD",
        "keys": [
            # ATTENTION : ces raccourcis sont ceux de Word en ANGLAIS.
            # Sur un Word en FRANCAIS, Gras = CTRL+G et Italique = CTRL+I.
            # Les variantes francaises sont pretes juste en dessous.
            {"label": "BOLD",   "type": "combo", "value": ("CTRL", "B")},
            {"label": "ITALIC", "type": "combo", "value": ("CTRL", "I")},
            {"label": "SAVE",   "type": "combo", "value": ("CTRL", "S")},
            {"label": "UNDO",   "type": "combo", "value": ("CTRL", "Z")},
            # Variante Word francais :
            # {"label": "GRAS",   "type": "combo", "value": ("CTRL", "G")},
            # {"label": "ITAL",   "type": "combo", "value": ("CTRL", "I")},
            # {"label": "ENREG",  "type": "combo", "value": ("CTRL", "S")},
            # {"label": "ANNUL",  "type": "combo", "value": ("CTRL", "Z")},
        ],
    },

    # =================================================================
    "WINDOWS": {
        "title": "WINDOWS",
        "keys": [
            {"label": "EXPLOR", "type": "combo", "value": ("WIN", "E")},
            {"label": "ALT-TAB", "type": "combo", "value": ("ALT", "TAB")},
            {"label": "DESKTOP", "type": "combo", "value": ("WIN", "D")},
            {"label": "TASKMGR", "type": "combo",
             "value": ("CTRL", "SHIFT", "ESC")},
        ],
    },
}


# =====================================================================
# Navigation circulaire
# =====================================================================
def next_profile(current):
    """Profil suivant, avec bouclage WINDOWS -> BLENDER."""
    index = PROFILES_ORDER.index(current)
    return PROFILES_ORDER[(index + 1) % len(PROFILES_ORDER)]


def previous_profile(current):
    """Profil precedent, avec bouclage BLENDER -> WINDOWS."""
    index = PROFILES_ORDER.index(current)
    return PROFILES_ORDER[(index - 1) % len(PROFILES_ORDER)]


def get_profile(name):
    """Retourne la definition d'un profil (jamais None : repli sur le premier)."""
    profile = PROFILES.get(name)
    if profile is None:
        print("[profiles] profil inconnu '%s', repli sur %s"
              % (name, PROFILES_ORDER[0]))
        profile = PROFILES[PROFILES_ORDER[0]]
    return profile


def validate():
    """Verifie la coherence entre PROFILES_ORDER et PROFILES.

    Appele par diag.py et par les tests hors materiel. Retourne la liste des
    problemes trouves (liste vide = tout est correct).
    """
    problems = []
    for name in PROFILES_ORDER:
        if name not in PROFILES:
            problems.append("PROFILES_ORDER cite '%s' qui n'existe pas" % name)
    for name in PROFILES:
        if name not in PROFILES_ORDER:
            problems.append("le profil '%s' n'est pas dans PROFILES_ORDER" % name)
    for name, profile in PROFILES.items():
        keys = profile.get("keys", [])
        if len(keys) != 4:
            problems.append("%s : %d touches definies au lieu de 4"
                            % (name, len(keys)))
        if len(profile.get("title", "")) > 16:
            problems.append("%s : titre trop long pour l'ecran" % name)
        for index, key in enumerate(keys):
            if len(key.get("label", "")) > 7:
                problems.append("%s B%d : label '%s' > 7 caracteres"
                                % (name, index + 1, key.get("label")))
            if key.get("type") not in ("key", "combo", "text", "text_enter",
                                       "sequence", "none"):
                problems.append("%s B%d : type inconnu '%s'"
                                % (name, index + 1, key.get("type")))
    return problems
