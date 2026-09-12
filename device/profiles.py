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
COMBO_LABEL_MAX = 16   # une combinaison s'affiche sur une ligne entiere


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
# valeurs d'usine. Une touche qui en a un attend GESTE_DOUBLE_MS (200 ms)
# avant de conclure "c'etait un appui court" - ici, avant de copier. Sur
# une touche ou tu veux zero attente, laisse la colonne "double" vide et
# sers-toi de l'appui long, qui lui ne coute rien.
def modificateur(label="CTRL"):
    """B1 : une vraie touche modificatrice, dans TOUS les profils.

    Elle ne tape rien. Elle enfonce Ctrl ou Maj et les GARDE enfonces tant
    que ton doigt reste dessus, pour que tu cliques a la souris pendant ce
    temps.

      appui maintenu             -> CTRL (Ctrl+clic : ajouter a la selection)
      appui bref puis maintenu   -> MAJ  (Maj+clic : deselectionner)

    CTRL EST EN PREMIER parce que c'est le maintien INSTANTANE : il part
    des l'appui, sans le moindre delai. Le second demande un appui bref
    d'abord, donc il arrive apres GESTE_DOUBLE_MS. On met donc devant
    celui qu'on utilise le plus.

    ELLE EST SUR LE POUCE, ET C'EST TOUT L'INTERET. Le pouce se pose sur
    un autre plan que les quatre doigts : il peut donc rester appuye sans
    rendre aucune autre touche inatteignable. Quand ce role etait sur
    l'index (B2), le maintenir bloquait B3 - meme doigt - et donc les
    trois combinaisons qui l'utilisent.

    Les deux se echangent DEPUIS LA PAGE DE CONFIGURATION, sans toucher au
    code : type "maintenir", valeur CTRL sur l'appui court et MAJ sur le
    double appui. Voir docs/07.
    """
    return K(label, [("maintien", ("CTRL",))],
             double=[("maintien", ("SHIFT",))])


def presse_papiers(long=None):
    """B2 : copier et coller, dans TOUS les profils.

    Ctrl+Z n'y est plus : il est passe sur le MAINTIEN DU BOUTON ESC, ou
    on l'atteint sans lacher la souris. L'appui long de B2 reste donc
    disponible pour la commande qui occupait cette touche avant le
    nouveau dessin - on ne perd rien.
    """
    return K("COPIER", [("combo", ("CTRL", "C"))],
             long=long,
             double=[("combo", ("CTRL", "V"))])


PROFILES = {

    # -----------------------------------------------------------------
    "BLENDER": [
        modificateur(),
        # L'appui long garde la rotation, qui occupait cette touche avant.
        presse_papiers(long=[("key", "R")]),
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
    # _PLINE fonctionne meme sur un Civil 3D installe en francais.
    #
    # CHAQUE TOUCHE PORTE UNE FAMILLE : c'est ce qui rend le profil facile
    # a retenir. Appui court et appui long vont toujours ensemble.
    "CIVIL3D": [
        modificateur(),
        # Rien a preserver ici : ce role etait deja sur B2, il est passe
        # sur le pouce. Ctrl+X complete donc la famille du presse-papiers.
        presse_papiers(long=[("combo", ("CTRL", "X"))]),

        # Affichage : accrochages, et vue globale en appui long.
        K("F3",     [("key", "F3")],
          long=[("text_enter", "_ZOOM E")]),

        # Famille polyligne. "_ZOOM E" et "_PLINE" tiennent sur une seule
        # ligne parce que dans la ligne de commande AutoCAD, l'espace vaut
        # Entree : l'option part avec la commande.
        K("PLINE",  [("text_enter", "_PLINE")],
          long=[("text_enter", "_SPLINE")]),

        # Famille isolation.
        K("ISOLE",  [("text_enter", "_ISOLATEOBJECTS")],
          long=[("text_enter", "_UNISOLATEOBJECTS")]),

        # Famille selection : selectionner les semblables, puis reproduire
        # une mise en forme sur ce qui est selectionne.
        K("SELSIM", [("text_enter", "_SELECTSIMILAR")],
          long=[("text_enter", "_MATCHPROP")]),
    ],

    # -----------------------------------------------------------------
    # RESERVE VALIDEE AVEC TOI : ces raccourcis sont ceux de Word en
    # ANGLAIS. Sur un Word FRANCAIS, Gras se fait avec Ctrl+G et non
    # Ctrl+B. Tu peux corriger cela en trente secondes depuis une page web.
    "WORD": [
        modificateur(),
        # L'appui long garde le gras, qui occupait cette touche avant.
        presse_papiers(long=[("combo", ("CTRL", "B"))]),
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
        modificateur(),
        # L'appui long garde Alt+Tab, qui occupait cette touche avant.
        presse_papiers(long=[("combo", ("ALT", "TAB"))]),
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

# =====================================================================
# LES COMBINAISONS
# =====================================================================
# Deux touches appuyees EN MEME TEMPS declenchent une macro a elles, et
# surtout pas celles des deux touches. Voir combos.py pour la mecanique,
# et docs/11-combinaisons.md pour le raisonnement.
#
# Les numeros sont ceux que tu vois sur le pad : COMBO((3, 4), ...) c'est
# bien B3 et B4.
def COMBO(touches, label, actions):
    return (tuple(numero - 1 for numero in touches), label, actions)


# Le pad est sous la MAIN GAUCHE, une touche par doigt et deux pour
# l'index (voir DOIGTS dans config.py). De gauche a droite :
#
#     B6            B5           B4       B3 + B2    B1
#     auriculaire   annulaire    majeur   index      pouce
#
# Les combinaisons suivent cette main, pas un dessin abstrait :
#
#   DEUX DOIGTS VOISINS -> les gestes frequents, les plus faciles
#       B5+B6 annulaire+auriculaire, le bord GAUCHE  -> vue PRECEDENTE
#       B3+B4 index+majeur,          le bord DROIT   -> vue SUIVANTE
#       B4+B5 majeur+annulaire,      le MILIEU       -> la polyligne
#
#   ON SAUTE UN DOIGT -> les calques, cacher et remontrer
#       B3+B5 index+annulaire (on saute le majeur)
#       B4+B6 majeur+auriculaire (on saute l'annulaire)
#
#   LE GRAND ECART -> ce qui sert le moins
#       B3+B6 index+auriculaire, toute la largeur de la main
#
# Gauche = precedent, droite = suivant : c'est le sens des fleches, et
# sur une main gauche l'auriculaire est bien a gauche du majeur.
#
# B1 (pouce) et B2 (index) restent HORS combinaisons. B1 parce que c'est
# le presse-papiers, la touche la plus utilisee des quatre profils, et
# qu'une combinaison par-dessus lui ajouterait un risque de declenchement
# involontaire. B2 parce qu'elle MAINTIENT Maj ou Ctrl : un maintien part
# des l'appui, il ne peut pas attendre la fenetre des combinaisons.
#
# A savoir, et c'est la main qui le decide : tant que tu MAINTIENS B2
# (Maj), ton index ne peut pas atteindre B3. Les trois combinaisons qui
# utilisent B3 sont donc indisponibles pendant ce temps.
#
# _HATCHEDIT n'y figure pas volontairement : dans AutoCAD, un double-clic
# sur une hachure ouvre deja son editeur.
COMBOS = {
    "CIVIL3D": [
        COMBO((5, 6), "VUE PREC.",  [("text_enter", "MPVIEWPREV")]),
        COMBO((3, 4), "VUE SUIV.",  [("text_enter", "MPVIEWNEXT")]),
        COMBO((4, 5), "PEDIT",      [("text_enter", "_PEDIT")]),
        COMBO((3, 5), "CALQUE OFF", [("text_enter", "MPLAYEROFF")]),
        COMBO((4, 6), "CALQUE ON",  [("text_enter", "MPLAYERRESTORE")]),
        COMBO((3, 6), "HACHURES",   [("text_enter", "_HATCH")]),
    ],
}
# MPVIEWPREV, MPVIEWNEXT, MPLAYEROFF et MPLAYERRESTORE sont les commandes
# AutoLISP de civil3d/macropad_tools.lsp. Elles s'ecrivent SANS le "_" :
# le souligne demande la version internationale d'une commande AutoCAD
# native, une commande LISP n'a pas de traduction.


# =====================================================================
# LE GROS BOUTON ESC MAINTENU
# =====================================================================
# Echap part DES L'APPUI, sans le moindre delai : c'est la raison d'etre
# de ce bouton, et rien ne doit la lui prendre. Mais s'il reste enfonce,
# il envoie EN PLUS ceci.
#
# Ctrl+Z apres un Echap, c'est de toute facon la sequence qu'on fait pour
# revenir en arriere : on annule la commande, puis on defait ce qu'elle a
# laisse. Ici, un seul bouton, sans lacher la souris.
#
# Le seuil est dans config.py (ESC_MAINTIEN_MS), et il est plus long que
# celui des touches : un bouton ESC qu'on garde enfonce par reflexe ne
# doit pas declencher une annulation qu'on n'a pas demandee.
#
# Mets None pour n'avoir qu'Echap.
ESC_MAINTIEN = [("combo", ("CTRL", "Z"))]


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
