# -*- coding: utf-8 -*-
"""
keymaps.py - Codes HID et tables de correspondance caractere -> touche.

POURQUOI CE FICHIER EXISTE
--------------------------
En USB HID un clavier n'envoie PAS de caracteres, il envoie des NUMEROS DE
TOUCHE PHYSIQUE (usage IDs du HID Usage Table, chapitre "Keyboard/Keypad").
C'est Windows qui traduit ensuite ce numero en caractere, selon la disposition
choisie dans Windows.

Exemple concret : le code 0x1D est "la touche en bas a gauche".
  - Windows en US QWERTY  -> 'z'
  - Windows en FR AZERTY  -> 'w'

Consequence : pour ecrire "_MATCHPROP" dans Civil 3D, ou pour envoyer un vrai
CTRL+Z, il faut connaitre la disposition Windows. D'ou KEYBOARD_LAYOUT dans
config.py et les tables ci-dessous.
"""

# =====================================================================
# 1. CODES HID BRUTS (USB HID Usage Table 1.12, page 53 "Keyboard Page")
# =====================================================================
K_A = 0x04
K_B = 0x05
K_C = 0x06
K_D = 0x07
K_E = 0x08
K_F = 0x09
K_G = 0x0A
K_H = 0x0B
K_I = 0x0C
K_J = 0x0D
K_K = 0x0E
K_L = 0x0F
K_M = 0x10
K_N = 0x11
K_O = 0x12
K_P = 0x13
K_Q = 0x14
K_R = 0x15
K_S = 0x16
K_T = 0x17
K_U = 0x18
K_V = 0x19
K_W = 0x1A
K_X = 0x1B
K_Y = 0x1C
K_Z = 0x1D

# Rangee des chiffres, dans l'ordre physique 1 2 3 4 5 6 7 8 9 0
K_1 = 0x1E
K_2 = 0x1F
K_3 = 0x20
K_4 = 0x21
K_5 = 0x22
K_6 = 0x23
K_7 = 0x24
K_8 = 0x25
K_9 = 0x26
K_0 = 0x27

K_ENTER = 0x28
K_ESC = 0x29
K_BACKSPACE = 0x2A
K_TAB = 0x2B
K_SPACE = 0x2C
K_MINUS = 0x2D          # touche a droite du 0
K_EQUAL = 0x2E          # touche a droite de la precedente
K_LBRACKET = 0x2F       # touche a droite du P
K_RBRACKET = 0x30
K_BACKSLASH = 0x31      # touche a droite du "]"
K_SEMICOLON = 0x33      # touche a droite du L
K_QUOTE = 0x34
K_GRAVE = 0x35          # touche a gauche du 1
K_COMMA = 0x36
K_DOT = 0x37
K_SLASH = 0x38
K_CAPSLOCK = 0x39
K_F1 = 0x3A
K_F2 = 0x3B
K_F3 = 0x3C
K_F4 = 0x3D
K_F5 = 0x3E
K_F6 = 0x3F
K_F7 = 0x40
K_F8 = 0x41
K_F9 = 0x42
K_F10 = 0x43
K_F11 = 0x44
K_F12 = 0x45
K_PRINTSCREEN = 0x46
K_INSERT = 0x49
K_HOME = 0x4A
K_PAGEUP = 0x4B
K_DELETE = 0x4C
K_END = 0x4D
K_PAGEDOWN = 0x4E
K_RIGHT = 0x4F
K_LEFT = 0x50
K_DOWN = 0x51
K_UP = 0x52
K_NON_US = 0x64         # "102e touche" : le < > \ a gauche du W sur les claviers FR
K_APPLICATION = 0x65    # touche menu contextuel

# =====================================================================
# 2. MODIFICATEURS (masque de bits du 1er octet du rapport HID)
# =====================================================================
MOD_CTRL = 0x01
MOD_SHIFT = 0x02
MOD_ALT = 0x04
MOD_WIN = 0x08          # touche Windows gauche (GUI)
MOD_RCTRL = 0x10
MOD_RSHIFT = 0x20
MOD_ALTGR = 0x40        # Alt droite = AltGr sur clavier francais
MOD_RWIN = 0x80

MODIFIERS = {
    "CTRL": MOD_CTRL,
    "CONTROL": MOD_CTRL,
    "SHIFT": MOD_SHIFT,
    "MAJ": MOD_SHIFT,
    "ALT": MOD_ALT,
    "WIN": MOD_WIN,
    "GUI": MOD_WIN,
    "CMD": MOD_WIN,
    "ALTGR": MOD_ALTGR,
    "RCTRL": MOD_RCTRL,
    "RSHIFT": MOD_RSHIFT,
}

# =====================================================================
# 3. TOUCHES NOMMEES (independantes de la disposition clavier)
# =====================================================================
# Ces touches sont au meme endroit sur tous les claviers : leur code HID
# peut donc etre envoye tel quel, quelle que soit la langue de Windows.
NAMED_KEYS = {
    "ENTER": K_ENTER, "RETURN": K_ENTER, "ENTREE": K_ENTER,
    "ESC": K_ESC, "ESCAPE": K_ESC, "ECHAP": K_ESC,
    "TAB": K_TAB, "TABULATION": K_TAB,
    "SPACE": K_SPACE, "ESPACE": K_SPACE,
    "BACKSPACE": K_BACKSPACE, "RETOUR": K_BACKSPACE,
    "DELETE": K_DELETE, "SUPPR": K_DELETE,
    "INSERT": K_INSERT, "HOME": K_HOME, "END": K_END,
    "PAGEUP": K_PAGEUP, "PAGEDOWN": K_PAGEDOWN,
    "UP": K_UP, "DOWN": K_DOWN, "LEFT": K_LEFT, "RIGHT": K_RIGHT,
    "CAPSLOCK": K_CAPSLOCK,
    "PRINTSCREEN": K_PRINTSCREEN,
    "MENU": K_APPLICATION,
    "F1": K_F1, "F2": K_F2, "F3": K_F3, "F4": K_F4,
    "F5": K_F5, "F6": K_F6, "F7": K_F7, "F8": K_F8,
    "F9": K_F9, "F10": K_F10, "F11": K_F11, "F12": K_F12,
}


# =====================================================================
# 4. TABLE FR AZERTY (Windows "Francais (France)")
# =====================================================================
def _build_fr_azerty():
    """Construit la table caractere -> (code HID, masque modificateur)."""
    table = {}

    # --- Lettres ---------------------------------------------------
    # En AZERTY seules 5 lettres changent de place par rapport au QWERTY :
    #   a <-> q,  z <-> w,  et le m passe a droite du l.
    exceptions = {
        "a": K_Q,
        "q": K_A,
        "z": K_W,
        "w": K_Z,
        "m": K_SEMICOLON,
    }
    for i in range(26):
        c = chr(ord("a") + i)
        code = exceptions.get(c, K_A + i)   # sinon meme position qu'en QWERTY
        table[c] = (code, 0)
        table[c.upper()] = (code, MOD_SHIFT)

    # --- Rangee des chiffres ---------------------------------------
    # En AZERTY la rangee donne  & e " ' ( - e _ c a ) =  au repos,
    # et les chiffres 1..0 avec SHIFT.
    row = (K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0)
    unshifted = "&é\"'(-è_çà"      # & é " ' ( - è _ ç à
    digits = "1234567890"
    for i in range(10):
        table[unshifted[i]] = (row[i], 0)
        table[digits[i]] = (row[i], MOD_SHIFT)

    table[")"] = (K_MINUS, 0)
    table["°"] = (K_MINUS, MOD_SHIFT)             # °
    table["="] = (K_EQUAL, 0)
    table["+"] = (K_EQUAL, MOD_SHIFT)

    # --- Rangee du haut (apres le P) -------------------------------
    table["$"] = (K_RBRACKET, 0)
    table["£"] = (K_RBRACKET, MOD_SHIFT)          # £

    # --- Rangee du milieu (apres le M) -----------------------------
    table["ù"] = (K_QUOTE, 0)                     # ù
    table["%"] = (K_QUOTE, MOD_SHIFT)
    table["*"] = (K_BACKSLASH, 0)
    table["µ"] = (K_BACKSLASH, MOD_SHIFT)         # µ

    # --- Rangee du bas ---------------------------------------------
    table["<"] = (K_NON_US, 0)
    table[">"] = (K_NON_US, MOD_SHIFT)
    table[","] = (K_M, 0)
    table["?"] = (K_M, MOD_SHIFT)
    table[";"] = (K_COMMA, 0)
    table["."] = (K_COMMA, MOD_SHIFT)
    table[":"] = (K_DOT, 0)
    table["/"] = (K_DOT, MOD_SHIFT)
    table["!"] = (K_SLASH, 0)
    table["§"] = (K_SLASH, MOD_SHIFT)             # §

    # --- Caracteres AltGr ------------------------------------------
    table["~"] = (K_2, MOD_ALTGR)
    table["#"] = (K_3, MOD_ALTGR)
    table["{"] = (K_4, MOD_ALTGR)
    table["["] = (K_5, MOD_ALTGR)
    table["|"] = (K_6, MOD_ALTGR)
    table["`"] = (K_7, MOD_ALTGR)
    table["\\"] = (K_8, MOD_ALTGR)
    table["^"] = (K_9, MOD_ALTGR)
    table["@"] = (K_0, MOD_ALTGR)
    table["]"] = (K_MINUS, MOD_ALTGR)
    table["}"] = (K_EQUAL, MOD_ALTGR)

    table[" "] = (K_SPACE, 0)
    table["\n"] = (K_ENTER, 0)
    table["\t"] = (K_TAB, 0)
    return table


# =====================================================================
# 5. TABLE US QWERTY (Windows "English (United States)")
# =====================================================================
def _build_us_qwerty():
    table = {}
    for i in range(26):
        c = chr(ord("a") + i)
        table[c] = (K_A + i, 0)
        table[c.upper()] = (K_A + i, MOD_SHIFT)

    row = (K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0)
    digits = "1234567890"
    shifted = "!@#$%^&*()"
    for i in range(10):
        table[digits[i]] = (row[i], 0)
        table[shifted[i]] = (row[i], MOD_SHIFT)

    pairs = (
        ("-", "_", K_MINUS),
        ("=", "+", K_EQUAL),
        ("[", "{", K_LBRACKET),
        ("]", "}", K_RBRACKET),
        ("\\", "|", K_BACKSLASH),
        (";", ":", K_SEMICOLON),
        ("'", '"', K_QUOTE),
        ("`", "~", K_GRAVE),
        (",", "<", K_COMMA),
        (".", ">", K_DOT),
        ("/", "?", K_SLASH),
    )
    for low, high, code in pairs:
        table[low] = (code, 0)
        table[high] = (code, MOD_SHIFT)

    table[" "] = (K_SPACE, 0)
    table["\n"] = (K_ENTER, 0)
    table["\t"] = (K_TAB, 0)
    return table


LAYOUTS = {
    "FR_AZERTY": _build_fr_azerty(),
    "US_QWERTY": _build_us_qwerty(),
}


def get_layout(name):
    """Retourne la table demandee, avec repli sur FR_AZERTY si le nom est inconnu."""
    if name in LAYOUTS:
        return LAYOUTS[name]
    print("[keymaps] disposition inconnue '%s', repli sur FR_AZERTY" % name)
    return LAYOUTS["FR_AZERTY"]
