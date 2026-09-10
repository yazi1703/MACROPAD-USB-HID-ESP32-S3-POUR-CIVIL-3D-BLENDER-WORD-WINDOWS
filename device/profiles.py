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


# =====================================================================
# LA TOUCHE 1 EST LA MEME PARTOUT
# =====================================================================
# Copier / coller / annuler : les trois gestes les plus utilises de toute
# l'informatique, et ils marchent dans absolument tous les logiciels. Les
# mettre sur la meme touche dans tous les profils, c'est un reflexe que tu
# n'as plus jamais a reapprendre - comme ESC, qui est deja global.
#
#   appui court  -> Ctrl+C   copier
#   double appui -> Ctrl+V   coller
#   appui long   -> Ctrl+Z   annuler
#
# A savoir : c'est la SEULE touche a avoir un double appui dans les
# valeurs d'usine. Une touche qui en a un attend GESTE_DOUBLE_MS (260 ms)
# avant de conclure "c'etait un appui court" - ici, avant de copier. Sur
# une touche ou tu veux zero attente, laisse la colonne "double" vide et
# sers-toi de l'appui long, qui lui ne coute rien.
def presse_papiers():
    return K("COPIER", [("combo", ("CTRL", "C"))],
             long=[("combo", ("CTRL", "Z"))],
             double=[("combo", ("CTRL", "V"))])


PROFILES = {

    # -----------------------------------------------------------------
    "BLENDER": [
        presse_papiers(),
        K("ROT",    [("key", "R")]),
        K("SCALE",  [("key", "S")]),
        K("TAB",    [("key", "TAB")]),
        K("EXTRUD", [("key", "E")]),
        # G (deplacer) est la touche la plus utilisee de Blender : elle
        # n'a pas de double appui, donc elle part sans la moindre attente.
        K("MOVE",   [("key", "G")],
          long=[("combo", ("CTRL", "SHIFT", "Z"))]),      # retablir
    ],

    # -----------------------------------------------------------------
    # Le "_" devant les commandes AutoCAD force la commande INTERNATIONALE :
    # _MATCHPROP fonctionne meme sur un Civil 3D installe en francais.
    "CIVIL3D": [
        presse_papiers(),
        # LA TOUCHE MODIFICATRICE. Elle ne tape rien : elle enfonce Ctrl
        # ou Maj et les GARDE enfonces tant que ton doigt reste dessus.
        #   appui maintenu             -> Ctrl  (Ctrl+clic : selectionner)
        #   appui bref puis maintenu   -> Maj   (Maj+clic : deselectionner)
        # Ta main gauche tient le modificateur, ta main droite reste a la
        # souris. Voir gestures.py pour le detail.
        K("CTRL",   [("maintien", ("CTRL",))],
          double=[("maintien", ("SHIFT",))]),
        K("MATCH",  [("text_enter", "_MATCHPROP")],
          long=[("combo", ("CTRL", "Y"))]),                # retablir
        K("ISOLE",  [("text_enter", "_ISOLATEOBJECTS")],
          long=[("text_enter", "_UNISOLATEOBJECTS")]),     # tout remontrer
        # "_ZOOM E" en une seule ligne : dans la ligne de commande
        # AutoCAD, l'espace vaut Entree. Le E choisit donc l'option
        # Etendu, et tu vois tout le dessin d'un seul appui. Si ta
        # version ne suit pas, remets simplement "_ZOOM".
        K("ZOOM",   [("text_enter", "_ZOOM E")],
          double=[("text_enter", "_REGEN")]),              # regenerer
        # _HATCH etait sur B2, que la touche modificatrice occupe
        # desormais : il passe en appui long, ou il ne coute aucun retard.
        K("ENREG",  [("combo", ("CTRL", "S"))],
          long=[("text_enter", "_HATCH")]),                # hachures
    ],

    # -----------------------------------------------------------------
    # RESERVE VALIDEE AVEC TOI : ces raccourcis sont ceux de Word en
    # ANGLAIS. Sur un Word FRANCAIS, Gras se fait avec Ctrl+G et non
    # Ctrl+B. Tu peux corriger cela en trente secondes depuis une page web.
    "WORD": [
        presse_papiers(),
        K("GRAS",   [("combo", ("CTRL", "B"))]),
        K("ITAL",   [("combo", ("CTRL", "I"))]),
        K("SOULIG", [("combo", ("CTRL", "U"))]),
        K("ENREG",  [("combo", ("CTRL", "S"))],
          long=[("key", "F12")]),                          # enregistrer sous
        # L'equivalent Word de MATCHPROP : copier une mise en forme, puis
        # l'appliquer ailleurs. Peu connu, et il fait gagner un temps fou.
        K("FORMAT", [("combo", ("CTRL", "SHIFT", "C"))],
          long=[("combo", ("CTRL", "Y"))],                 # refaire
          double=[("combo", ("CTRL", "SHIFT", "V"))]),     # appliquer
    ],

    # -----------------------------------------------------------------
    "WINDOWS": [
        presse_papiers(),
        K("ALTTAB", [("combo", ("ALT", "TAB"))]),
        K("EXPLOR", [("combo", ("WIN", "E"))],
          long=[("combo", ("WIN", "D"))]),                 # afficher le bureau
        # Verrouiller est sur un appui LONG : impossible de verrouiller
        # l'ecran par megarde en voulant ouvrir le gestionnaire.
        K("TACHES", [("combo", ("CTRL", "SHIFT", "ESC"))],
          long=[("combo", ("WIN", "L"))]),                 # verrouiller
        # Win+V = historique du presse-papiers (a activer une fois dans
        # Windows). Win+H = dictee vocale, tres peu connue.
        K("PRESSE", [("combo", ("WIN", "V"))],
          long=[("combo", ("WIN", "H"))]),                 # dictee
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
