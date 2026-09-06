# -*- coding: utf-8 -*-
"""
layouts.py - Traduction "caractère que je veux" -> "touche physique à presser".

=====================================================================
A LIRE EN PREMIER SI TU DEBUTES : POURQUOI CE FICHIER EXISTE
=====================================================================

Un clavier USB n'envoie JAMAIS de lettres à l'ordinateur.
Il envoie des NUMEROS DE TOUCHE PHYSIQUE (appelés "usages HID").

Exemple : le numéro 0x1D (29 en décimal), c'est "la touche en bas à gauche,
juste à droite de la touche Maj".

  - Si Windows est réglé en clavier américain (QWERTY), il écrit "z".
  - Si Windows est réglé en clavier français (AZERTY), il écrit "w".

C'est le MEME numéro. C'est Windows qui décide de la lettre.

Conséquences très concrètes pour notre macropad :

1. Pour écrire "_MATCHPROP" dans Civil 3D, il faut savoir sur quelle touche
   physique se trouve le "_" en AZERTY. Réponse : c'est la touche du 8,
   et SANS appuyer sur Maj (numéro 37). En QWERTY c'est Maj + la touche
   du tiret (numéro 45). Rien à voir.

2. Pour envoyer un vrai Ctrl+Z (Annuler), il faut la touche physique qui
   produit un "z". En AZERTY c'est le numéro 26. Si on envoyait bêtement
   le numéro 29 (le "Z" américain), Windows en AZERTY comprendrait
   Ctrl+W... c'est-à-dire FERMER LE DOCUMENT. Le piège est réel, ce
   fichier l'évite.

Ce firmware ne change JAMAIS la configuration clavier de Windows.
C'est KEYBOARD_LAYOUT dans config.py qui doit s'aligner sur Windows.

=====================================================================
CONVENTION D'ECRITURE DANS CE FICHIER
=====================================================================

Une "frappe" est un tuple de nombres, par exemple (-2, 20).
  - un nombre NEGATIF  = une touche modificatrice maintenue
        -1 = Ctrl, -2 = Maj (Shift), -4 = Alt, -8 = Windows, -64 = AltGr
  - un nombre POSITIF  = une touche normale
Cette convention (modificateurs en négatif) vient de la bibliothèque
officielle usb/device/keyboard.py, on la respecte telle quelle.
"""

import config as C

# =====================================================================
# 1. NUMEROS DE TOUCHE (usages HID standard)
# =====================================================================
# Ces numéros viennent du document officiel USB "HID Usage Tables",
# chapitre clavier. Ils sont universels : tous les claviers du monde
# envoient les mêmes.

MOD_CTRL = -1
MOD_SHIFT = -2
MOD_ALT = -4
MOD_WIN = -8
MOD_ALTGR = -64

# Rangée des chiffres, dans l'ordre PHYSIQUE (la 1re touche, la 2e...).
# Attention : "K_ROW[0]" est la touche la plus à gauche, celle qui écrit
# "&" en AZERTY et "1" en QWERTY.
K_ROW = (30, 31, 32, 33, 34, 35, 36, 37, 38, 39)   # les 10 touches 1..0
K_MINUS = 45        # touche juste à droite du 0
K_EQUAL = 46        # touche encore à droite
K_LBRACKET = 47     # touche juste à droite du P
K_RBRACKET = 48
K_BACKSLASH = 49    # touche à droite de la précédente
K_SEMICOLON = 51    # touche juste à droite du L
K_QUOTE = 52
K_GRAVE = 53        # touche tout en haut à gauche, à gauche du 1
K_COMMA = 54
K_DOT = 55
K_SLASH = 56
K_NON_US = 100      # la "102e touche" : le < > à gauche du W sur les claviers FR

# Touches qui sont au même endroit sur TOUS les claviers du monde.
# Elles n'ont donc pas besoin d'être traduites.
SPECIAL = {
    "CTRL": MOD_CTRL, "CONTROL": MOD_CTRL,
    "SHIFT": MOD_SHIFT, "MAJ": MOD_SHIFT,
    "ALT": MOD_ALT,
    "WIN": MOD_WIN, "GUI": MOD_WIN,
    "ALTGR": MOD_ALTGR,
    "ENTER": 40, "ENTREE": 40, "RETURN": 40,
    "ESC": 41, "ESCAPE": 41, "ECHAP": 41,
    "BACKSPACE": 42, "RETOUR": 42,
    "TAB": 43, "TABULATION": 43,
    "SPACE": 44, "ESPACE": 44,
    "CAPSLOCK": 57,
    "F1": 58, "F2": 59, "F3": 60, "F4": 61, "F5": 62, "F6": 63,
    "F7": 64, "F8": 65, "F9": 66, "F10": 67, "F11": 68, "F12": 69,
    "PRINTSCREEN": 70,
    "INSERT": 73, "HOME": 74, "PAGEUP": 75,
    "DELETE": 76, "SUPPR": 76, "END": 77, "PAGEDOWN": 78,
    "RIGHT": 79, "LEFT": 80, "DOWN": 81, "UP": 82,
    "MENU": 101,
}


# =====================================================================
# 2. CONSTRUCTION DES TABLES DE CARACTERES
# =====================================================================
# Chaque entrée est :  caractère -> (numéro de touche, modificateur, caps)
#
#   modificateur : 0, MOD_SHIFT ou MOD_ALTGR
#   caps         : True si la touche Verr. Maj inverse le comportement
#                  de cette touche (voir l'explication au § 3)

def _build_fr():
    """Table du clavier « Français (France) » de Windows, l'AZERTY classique.

    Ni le nouvel AZERTY normalisé AFNOR, ni le belge, ni le canadien.
    """
    table = {}

    # --- Les 26 lettres -------------------------------------------
    # En AZERTY, seules 5 lettres ne sont pas à la même place qu'en QWERTY :
    #   le A prend la place du Q, le Z celle du W, et le M passe à droite du L.
    deplacees = {"a": 20, "q": 4, "z": 26, "w": 29, "m": K_SEMICOLON}
    for i in range(26):
        minuscule = chr(ord("a") + i)
        # 4 = numéro de la touche "A" du QWERTY, 5 = "B", etc.
        code = deplacees.get(minuscule, 4 + i)
        table[minuscule] = (code, 0, True)
        table[minuscule.upper()] = (code, MOD_SHIFT, True)

    # --- La rangée des chiffres -----------------------------------
    # En AZERTY au repos elle donne :   & é " ' ( - è _ ç à
    # et avec la touche Maj :           1 2 3 4 5 6 7 8 9 0
    # C'est l'inverse d'un clavier américain, d'où le "caps=True" :
    # la touche Verr. Maj agit AUSSI sur cette rangée sous Windows FR.
    repos = "&é\"'(-è_çà"        # & é " ' ( - è _ ç à
    chiffres = "1234567890"
    for i in range(10):
        table[repos[i]] = (K_ROW[i], 0, True)
        table[chiffres[i]] = (K_ROW[i], MOD_SHIFT, True)
    table[")"] = (K_MINUS, 0, True)
    table["°"] = (K_MINUS, MOD_SHIFT, True)     # °
    table["="] = (K_EQUAL, 0, True)
    table["+"] = (K_EQUAL, MOD_SHIFT, True)

    # --- Le reste du clavier --------------------------------------
    # Ces touches ne sont PAS affectées par Verr. Maj (caps=False).
    table["$"] = (K_RBRACKET, 0, False)
    table["£"] = (K_RBRACKET, MOD_SHIFT, False)     # £
    table["ù"] = (K_QUOTE, 0, False)                # ù
    table["%"] = (K_QUOTE, MOD_SHIFT, False)
    table["*"] = (K_BACKSLASH, 0, False)
    table["µ"] = (K_BACKSLASH, MOD_SHIFT, False)    # µ
    table["<"] = (K_NON_US, 0, False)
    table[">"] = (K_NON_US, MOD_SHIFT, False)
    # En AZERTY la virgule occupe la place du M américain (touche n° 16).
    table[","] = (16, 0, False)
    table["?"] = (16, MOD_SHIFT, False)
    table[";"] = (K_COMMA, 0, False)
    table["."] = (K_COMMA, MOD_SHIFT, False)
    table[":"] = (K_DOT, 0, False)
    table["/"] = (K_DOT, MOD_SHIFT, False)
    table["!"] = (K_SLASH, 0, False)
    table["§"] = (K_SLASH, MOD_SHIFT, False)        # §

    # --- Les caractères qui demandent AltGr -----------------------
    table["~"] = (K_ROW[1], MOD_ALTGR, False)
    table["#"] = (K_ROW[2], MOD_ALTGR, False)
    table["{"] = (K_ROW[3], MOD_ALTGR, False)
    table["["] = (K_ROW[4], MOD_ALTGR, False)
    table["|"] = (K_ROW[5], MOD_ALTGR, False)
    table["`"] = (K_ROW[6], MOD_ALTGR, False)
    table["\\"] = (K_ROW[7], MOD_ALTGR, False)
    table["^"] = (K_ROW[8], MOD_ALTGR, False)
    table["@"] = (K_ROW[9], MOD_ALTGR, False)
    table["]"] = (K_MINUS, MOD_ALTGR, False)
    table["}"] = (K_EQUAL, MOD_ALTGR, False)

    table[" "] = (44, 0, False)
    table["\n"] = (40, 0, False)
    table["\r"] = (40, 0, False)
    table["\t"] = (43, 0, False)
    return table


def _build_us():
    """Table du clavier « English (United States) », le QWERTY classique."""
    table = {}
    for i in range(26):
        minuscule = chr(ord("a") + i)
        table[minuscule] = (4 + i, 0, True)
        table[minuscule.upper()] = (4 + i, MOD_SHIFT, True)

    # En QWERTY, Verr. Maj n'agit QUE sur les lettres : caps=False partout ailleurs.
    chiffres = "1234567890"
    au_dessus = "!@#$%^&*()"
    for i in range(10):
        table[chiffres[i]] = (K_ROW[i], 0, False)
        table[au_dessus[i]] = (K_ROW[i], MOD_SHIFT, False)

    paires = (("-", "_", K_MINUS), ("=", "+", K_EQUAL),
              ("[", "{", K_LBRACKET), ("]", "}", K_RBRACKET),
              ("\\", "|", K_BACKSLASH), (";", ":", K_SEMICOLON),
              ("'", '"', K_QUOTE), ("`", "~", K_GRAVE),
              (",", "<", K_COMMA), (".", ">", K_DOT), ("/", "?", K_SLASH))
    for bas, haut, code in paires:
        table[bas] = (code, 0, False)
        table[haut] = (code, MOD_SHIFT, False)

    table[" "] = (44, 0, False)
    table["\n"] = (40, 0, False)
    table["\r"] = (40, 0, False)
    table["\t"] = (43, 0, False)
    return table


TABLES = {"FR_AZERTY": _build_fr(), "US_QWERTY": _build_us()}


def _table(layout):
    if layout not in TABLES:
        raise ValueError("Layout inconnu : " + str(layout))
    return TABLES[layout]


# =====================================================================
# 3. TRADUCTION D'UN CARACTERE
# =====================================================================

def letter_code(letter, layout):
    """Numéro de la touche physique qui écrit cette lettre.

    Sert aux raccourcis : letter_code("Z", "FR_AZERTY") vaut 26, c'est-à-dire
    la touche qui écrit un "z" sur un clavier français.
    """
    letter = letter.upper()
    if len(letter) != 1 or not "A" <= letter <= "Z":
        raise ValueError("Lettre non prise en charge : " + letter)
    return _table(layout)[letter.lower()][0]


def character_keys(char, layout, caps_lock=False):
    """Frappe à envoyer pour écrire ce caractère précis.

    LE ROLE DE caps_lock
    --------------------
    Windows nous prévient quand la touche Verr. Maj est allumée (c'est le
    voyant du clavier, l'ordinateur envoie l'information au périphérique).
    Si Verr. Maj est allumé, il faut inverser l'usage de la touche Maj,
    sinon on obtient l'inverse de ce qu'on veut.

    ATTENTION, PIEGE FRANCAIS : sous Windows, sur un clavier français,
    Verr. Maj agit AUSSI sur la rangée des chiffres. Verr. Maj allumé,
    la touche du 8 écrit "8" au lieu de "_". Sans la correction ci-dessous,
    "_MATCHPROP" deviendrait "8MATCHPROP" et Civil 3D ne comprendrait rien.
    C'est pour cela que chaque entrée de la table porte un drapeau "caps".

    Si tu constates que ton Windows ne se comporte pas ainsi, mets
    CAPS_AFFECTS_DIGIT_ROW = False dans config.py.
    """
    entry = _table(layout).get(char)
    if entry is None:
        raise ValueError("Caractere non pris en charge : " + repr(char))
    code, modifier, caps_sensitive = entry

    if caps_lock and caps_sensitive:
        est_lettre = ("a" <= char <= "z") or ("A" <= char <= "Z")
        if est_lettre or getattr(C, "CAPS_AFFECTS_DIGIT_ROW", True):
            # Verr. Maj fait déjà le travail de la touche Maj : on inverse.
            modifier = 0 if modifier == MOD_SHIFT else MOD_SHIFT

    return (modifier, code) if modifier else (code,)


def key_code(name, layout):
    """Traduit un nom de touche utilisé dans une macro.

    Trois cas :
      "CTRL", "TAB", "F5"  -> touche nommée, identique sur tous les claviers
      "G", "z"             -> la touche PHYSIQUE qui écrit cette lettre
      "1", "*"             -> la touche PHYSIQUE qui porte ce caractère

    Pour un RACCOURCI on veut la touche, pas le caractère : on laisse donc
    tomber le Maj / AltGr de la table. Ctrl+"1" veut dire "Ctrl et la touche
    du 1", même si en AZERTY il faut normalement Maj pour écrire un 1.
    """
    name = str(name)
    majuscule = name.upper()
    if majuscule in SPECIAL:
        return SPECIAL[majuscule]
    if len(name) == 1:
        table = _table(layout)
        entry = table.get(name)
        if entry is None:
            entry = table.get(name.lower())
        if entry is not None:
            return entry[0]
    raise ValueError("Touche inconnue dans la macro : " + repr(name))


# =====================================================================
# 4. COMPILATION D'UNE MACRO COMPLETE
# =====================================================================

def compile_actions(actions, layout, caps_lock=False):
    """Transforme une macro de profiles.py en liste de frappes prêtes à envoyer.

    IMPORTANT : cette fonction est appelée AVANT la première frappe.
    Si un caractère est impossible à écrire, elle lève une erreur et RIEN
    n'est tapé. On ne veut surtout pas d'une commande à moitié écrite dans
    Civil 3D.
    """
    result = []
    for kind, value in actions:
        if kind == "key":
            result.append((key_code(value, layout),))
        elif kind == "combo":
            codes = tuple(key_code(name, layout) for name in value)
            # Un rapport HID ne transporte que 6 touches normales à la fois.
            if sum(1 for code in codes if code >= 0) > 6:
                raise ValueError("Plus de six touches dans une combinaison")
            result.append(codes)
        elif kind in ("text", "text_enter"):
            result.extend(character_keys(char, layout, caps_lock)
                          for char in value)
            if kind == "text_enter":
                result.append((40,))       # 40 = touche Entrée
        else:
            raise ValueError("Action inconnue : " + kind)
    return result
