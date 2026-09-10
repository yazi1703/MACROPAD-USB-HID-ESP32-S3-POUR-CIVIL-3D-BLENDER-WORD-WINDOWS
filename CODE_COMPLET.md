# Code complet du firmware


Copie lisible de tous les fichiers de `device/`.
**Ce document est genere automatiquement** par
`tools/generer_code_complet.py` : ne le modifie pas a la main,
modifie les fichiers `.py` puis relance le script.

Pour transferer le firmware sur la carte, utilise les fichiers `.py`
de `device/`, pas ce document.

## Sommaire

- [`device/config.py`](#deviceconfigpy)
- [`device/profiles.py`](#deviceprofilespy)
- [`device/boot.py`](#devicebootpy)
- [`device/main.py`](#devicemainpy)
- [`device/runtime.py`](#deviceruntimepy)
- [`device/inputs.py`](#deviceinputspy)
- [`device/gestures.py`](#devicegesturespy)
- [`device/layouts.py`](#devicelayoutspy)
- [`device/store.py`](#devicestorepy)
- [`device/stats.py`](#devicestatspy)
- [`device/portal.py`](#deviceportalpy)
- [`device/link.py`](#devicelinkpy)
- [`device/hid_keyboard.py`](#devicehidkeyboardpy)
- [`device/display.py`](#devicedisplaypy)
- [`device/led.py`](#deviceledpy)
- [`device/rgb.py`](#devicergbpy)
- [`device/diag.py`](#devicediagpy)
- [`device/sh1106.py`](#devicesh1106py)
- [`device/lib/usb/device/__init__.py`](#devicelibusbdeviceinitpy)
- [`device/lib/usb/device/core.py`](#devicelibusbdevicecorepy)
- [`device/lib/usb/device/hid.py`](#devicelibusbdevicehidpy)
- [`device/lib/usb/device/keyboard.py`](#devicelibusbdevicekeyboardpy)


---

## device/config.py

`312 lignes - sha256 11be7f8df615035d`

```python
# -*- coding: utf-8 -*-
"""
config.py - Le seul fichier de réglages du macropad.

=====================================================================
COMMENT L'UTILISER
=====================================================================
Tu modifies une valeur ici, tu enregistres, puis tu fais un RESET MATERIEL
(le petit bouton RST de la carte). Le RESET est important : MicroPython
garde les modules déjà importés en mémoire, un simple STOP dans Thonny ne
relit pas toujours ce fichier.

Aucun numéro de GPIO ne doit être écrit ailleurs que dans ce fichier.

=====================================================================
RAPPEL DE SECURITE SUR LES GPIO DE L'ESP32-S3
=====================================================================
Certaines broches sont déjà prises et ne doivent JAMAIS être utilisées :

  GPIO19 / GPIO20 : les deux fils de données USB (D- et D+).
                    Y brancher quoi que ce soit casse l'USB.
  GPIO26 à GPIO32 : la mémoire flash interne.
  GPIO33 à GPIO37 : la PSRAM octale (c'est le "R8" de ton N16R8).
  GPIO0/3/45/46   : broches dites de "strapping", lues au démarrage.
                    Un niveau parasite dessus empêche la carte de démarrer.
  GPIO43 / GPIO44 : la liaison série UART0 (le REPL du port USB-UART).

Les broches choisies ci-dessous évitent toutes ces broches.
Détail de la vérification : docs/02-cablage.md
"""

# =====================================================================
# 1. BROCHAGE
# =====================================================================

# Les touches mécaniques. Chaque interrupteur relie sa broche à GND.
# L'ordre de la liste donne B1, B2, B3... Il suffit d'ajouter ou de retirer
# un numéro ici pour changer le nombre de touches : le reste du firmware
# s'adapte tout seul (écran compris).
#
# B1 = SAFE MODE   si maintenu au démarrage (aucun HID ne sera créé)
# B2 = MODE CONFIG si maintenu au démarrage (WiFi + page web, pas de HID)
#
# GPIO12 et GPIO13 sont les deux ajouts pour passer de 4 à 6 touches.
# VÉRIFIE sur ta carte qu'ils ne sont pas utilisés par le connecteur caméra.
# Replis sûrs si besoin : 1, 2, 21, 47, 48.
BUTTON_PINS = (4, 5, 6, 7, 12, 13)

# Les deux modules capacitifs TTP223 qui changent de profil.
TTP_PREVIOUS_PIN = 10
TTP_NEXT_PIN = 11
# True = la sortie OUT du module monte à 3,3 V quand tu poses le doigt.
# C'est le comportement d'usine. Si tes modules font l'inverse (pastille
# "AHLB" soudée au dos), mets False.
TTP_ACTIVE_HIGH = True

# Le gros bouton ESC déporté : un simple contact vers GND.
ESC_PIN = 14

# La LED du bouton ESC. ATTENTION : cette broche ne pilote PAS la LED
# directement, elle pilote la base d'un transistor BC547. Brancher une LED
# 1 W en direct sur un GPIO le détruirait (voir docs/05-electronique.md).
LED_PIN = 15

# =====================================================================
# 2. ECRAN OLED (bus I2C)
# =====================================================================
I2C_ID = 0
OLED_SDA = 8        # ce sont les broches I2C par défaut de MicroPython
OLED_SCL = 9        # sur cette carte : bon choix, on les garde
I2C_FREQ = 400000   # 400 kHz : quatre fois plus rapide que le mode standard
I2C_TIMEOUT_US = 5000   # si l'écran ne répond pas en 5 ms, on abandonne
                        # l'échange plutôt que de bloquer tout le macropad
OLED_ENABLED = True     # False = démarrer sans écran, le clavier fonctionne quand même
OLED_CONTRAST = 128     # 0 à 255

# =====================================================================
# 3. PROFILS
# =====================================================================
# L'ordre de rotation des profils. Pour ajouter QGIS, AutoTURN ou Road
# Survey plus tard : ajoute le nom ici ET la liste de macros dans
# profiles.py. La navigation circulaire s'adapte toute seule.
PROFILES_ORDER = ["BLENDER", "CIVIL3D", "WORD", "WINDOWS"]
DEFAULT_PROFILE = "CIVIL3D"     # profil actif au branchement

# =====================================================================
# 4. CLAVIER
# =====================================================================
KEYBOARD_LAYOUT = "FR_AZERTY"  # Français France classique ; ou US_QWERTY.
# Cette valeur doit correspondre à la disposition réglée DANS WINDOWS
# (indicateur FRA / ENG à côté de l'horloge). Le firmware ne change jamais
# le réglage de Windows.

# Sous Windows, sur un clavier FRANCAIS, la touche Verr. Maj agit aussi sur
# la rangée des chiffres : Verr. Maj allumé, la touche du 8 écrit "8" au
# lieu de "_". Le firmware compense automatiquement. Mets False si ton
# Windows ne se comporte pas ainsi (c'est le cas des claviers américains).
CAPS_AFFECTS_DIGIT_ROW = True

# --- LES DEUX INTERRUPTEURS DE SECURITE LES PLUS IMPORTANTS ----------
# False = le macropad n'envoie AUCUNE touche, jamais. Tout le reste
# fonctionne (écran, boutons, LED, REPL) et les macros s'affichent dans le
# REPL. C'est la position de livraison : ne la change qu'à l'étape 7 des
# tests, quand tu es sûr du câblage.
HID_ENABLED = False

# None = macros normales.
# Sinon "LETTER", "ESC", "UNDO", "AZERTY" ou "COMMANDS" : dans ce mode
# SEUL B1 agit, et il déclenche l'action de test choisie. Cela permet de
# valider le clavier une brique à la fois sans risquer une commande
# applicative involontaire.
HID_TEST = None

# =====================================================================
# 4 bis. MODE CONFIGURATION (WiFi + page web)
# =====================================================================
# Maintiens B2 pendant le RESET : le macropad n'crée AUCUN clavier USB,
# allume son propre réseau WiFi et sert une page web où tu peux modifier
# les profils et les macros. Un RESET normal applique les changements.
#
# POURQUOI UN MODE SÉPARÉ ET PAS DU WIFI EN PERMANENCE
# Ce boîtier tape dans ton ordinateur. Une radio allumée en permanence
# permettrait à quelqu'un à portée de reprogrammer ce qu'il tape. Ici la
# radio ne s'allume que si TU maintiens un bouton, et dans ce mode le
# clavier USB n'existe même pas.
SAFE_MODE_BUTTON_INDEX = 0          # index dans BUTTON_PINS : 0 = B1
CONFIG_MODE_BUTTON_INDEX = 1        # index dans BUTTON_PINS : 1 = B2

AP_SSID = "MACROPAD"                # nom du réseau créé par le macropad
AP_PASSWORD = "macropad2026"        # >>> CHANGE-MOI <<< 8 caractères minimum
AP_CHANNEL = 6
AP_PORT = 80                        # page web sur http://192.168.4.1

# Fichier où sont enregistrés tes profils personnalisés. Tant qu'il
# n'existe pas, ce sont les profils d'usine de profiles.py qui servent.
PROFILES_FILE = "profils.json"

# =====================================================================
# 4 ter. LIAISON AVEC LE PC (detection automatique du logiciel)
# =====================================================================
# Le macropad expose un port serie en plus du clavier. Le script
# tools/macropad_auto.py, lance sur le PC, s'en sert pour :
#   * dire quel logiciel est au premier plan -> changement de profil auto
#   * envoyer le nom du document ouvert -> affiche sur l'ecran
#   * transmettre tes modifications de macros, appliquees sans redemarrer
#
# Mettre False desactive completement cette ecoute.
LINK_ENABLED = True

# Au-dela de ce delai sans nouvelle du PC, on considere que le script n'est
# plus la et l'ecran cesse d'afficher "AUTO".
AUTO_TIMEOUT_MS = 15000

# =====================================================================
# 4 quater. COMPTEUR D'USAGE ET ECONOMISEUR D'ECRAN
# =====================================================================
# Le macropad compte les appuis sur chaque macro. La page de configuration
# te les classe : tu sais quelles touches meritent la premiere rangee de
# ton boitier, et lesquelles ne servent jamais.
STATS_ENABLED = True
STATS_FILE = "stats.json"
# On n'ecrit sur la flash que toutes les N frappes : la memoire d'un
# microcontroleur supporte un nombre limite d'ecritures, inutile de l'user
# pour une statistique. Au pire on perd les N-1 derniers appuis.
STATS_SAVE_EVERY = 25

# --- Anti-marquage de l'ecran ---------------------------------------
# Un OLED qui affiche la meme image pendant des heures MARQUE : les pixels
# allumes en permanence vieillissent plus vite et laissent un fantome
# visible. Le bandeau inverse du haut est exactement le pire cas.
# Apres un moment sans appui on baisse le contraste, puis on eteint.
# N'importe quelle touche reveille l'ecran instantanement.
# =====================================================================
# LES LED RGB SOUS LES TOUCHES
# =====================================================================
# Livre a False : rien ne s'allume tant que tu n'as pas cable et choisi
# ton type de LED. Lis docs/10-led-rgb.md AVANT de brancher quoi que ce
# soit - il y a une histoire de courant qui peut faire redemarrer la
# carte en pleine frappe.
RGB_ENABLED = False

# "WS2812" : LED adressables, un seul fil de donnees, une couleur par
#            touche. C'est ce qu'il faut pour eclairer six touches.
# "PWM"    : UNE LED RGB ordinaire a quatre pattes, sur trois broches.
#            Une seule couleur pour tout le macropad.
RGB_TYPE = "WS2812"

# --- montage WS2812 ---------------------------------------------------
RGB_PIN = 16                # fil de donnees (via 330 a 470 ohms en serie)
RGB_COUNT = 6               # une LED par touche
RGB_ORDRE = "GRB"           # ordre des couleurs de TES LED (voir la doc)

# --- montage PWM (une seule LED RGB) ----------------------------------
RGB_PIN_R = 16
RGB_PIN_V = 17
RGB_PIN_B = 18
RGB_ANODE_COMMUNE = True    # patte commune au + : True. Au GND : False.

# --- luminosite : C'EST LA SECURITE COURANT ---------------------------
# Chaque canal est multiplie par RGB_LUMINOSITE / 255 avant d'etre
# envoye. A 40, six WS2812 tirent environ 60 mA au total. A 255, elles
# en tireraient 360 : le 5 V d'un port USB s'effondre, la carte redemarre
# et le clavier disparait. Ne monte pas ce chiffre sans mesurer.
RGB_LUMINOSITE = 40

# --- couleurs ---------------------------------------------------------
# Un profil = une couleur. Tu sais ou tu es sans lire l'ecran.
RGB_COULEURS = {
    "BLENDER": (255, 110, 0),      # orange Blender
    "CIVIL3D": (0, 160, 255),      # bleu cyan
    "WORD":    (40, 70, 255),      # bleu Word
    "WINDOWS": (0, 200, 90),       # vert
}
RGB_COULEUR_DEFAUT = (120, 120, 120)   # profil sans couleur declaree
RGB_COULEUR_ERREUR = (255, 0, 0)       # panne HID : visible sans lire

# --- respiration ------------------------------------------------------
# La couleur monte et redescend doucement, comme la LED du bouton ESC.
# Meme courbe, meme douceur (voir rgb.py). Mets False pour une couleur
# fixe. Le plancher evite que le pad s'eteigne completement en bas de
# cycle : a 0.35, il reste toujours un tiers de luminosite.
RGB_RESPIRATION = True
RGB_RESPIRATION_MS = 4000   # duree d'un cycle complet
RGB_RESPIRATION_MIN = 0.35  # luminosite au creux de la respiration

# --- reaction a l'appui ------------------------------------------------
# Un appui fait monter la LED de la touche, et elle redescend toute seule.
# L'impulsion S'AJOUTE a ce qui reste : deux appuis coup sur coup montent
# deux fois plus haut. Le plafond du courant reste RGB_LUMINOSITE, quoi
# qu'il arrive.
RGB_IMPULSION = 1.0         # ce qu'un appui ajoute (1.0 = double la clarte)
RGB_IMPULSION_MAX = 3.0     # au-dela, ca ne monte plus
RGB_RETOMBEE_MS = 700       # duree du retour au calme, PAR unite

RGB_MS = 16                 # un envoi au plus toutes les 16 ms (~60 par
                            # seconde) : c'est ce qui rend la retombee
                            # fluide sans occuper le processeur
RGB_VEILLE_MS = 300000      # 5 minutes sans appui -> extinction

SCREEN_DIM_MS = 180000      # 3 minutes  -> contraste minimal
SCREEN_OFF_MS = 900000      # 15 minutes -> ecran eteint
SCREEN_DIM_CONTRAST = 1     # 0 a 255

# =====================================================================
# 5. TEMPS ET REACTIVITE (millisecondes)
# =====================================================================
# Délai entre la mise sous tension et la prise en compte des touches.
# Sert de filet : si une macro devenait folle, tu as 2,5 s pour débrancher.
BOOT_GUARD_MS = 2500

# --- Gestes : appui court, appui long, double appui ------------------
# Une touche maintenue au-delà de ce délai déclenche sa macro « longue »,
# si elle en a une. La macro part dès le franchissement du seuil, sans
# attendre le relâchement : tu la sens partir sous le doigt.
GESTE_LONG_MS = 400
# Deux appuis séparés de moins que ce délai forment un double appui.
# ATTENTION : seules les touches qui ont RÉELLEMENT une macro de double
# appui attendent ce délai. Les autres partent instantanément.
GESTE_DOUBLE_MS = 260

DEBOUNCE_MS = 25        # anti-rebond des touches B1 à B4
ESC_DEBOUNCE_MS = 20    # anti-rebond du bouton ESC
# True : le bouton ESC agit dès le premier front (retard ~0 ms) puis ignore
# les rebonds pendant ESC_DEBOUNCE_MS. C'est le comportement d'un vrai
# clavier. Mets False pour revenir au filtrage patient si ton contact ESC
# est de mauvaise qualité et déclenche parfois deux fois.
ESC_FAST_EDGE = True
TTP_DEBOUNCE_MS = 35    # anti-rebond des touches capacitives

LOOP_MS = 2             # durée d'un tour de la boucle principale

# Durée pendant laquelle une touche reste "enfoncée" pour Windows, puis
# temps de repos avant la touche suivante. 12 + 12 ms = environ 24 ms par
# caractère. Descendre trop bas fait perdre des caractères à Windows.
KEY_HOLD_MS = 12
KEY_GAP_MS = 12

# Si plus rien n'avance pendant ce délai alors qu'une macro est en cours,
# on considère l'USB bloqué : tout est relâché et les macros s'arrêtent.
HID_TIMEOUT_MS = 1000

# Nombre maximal de macros en attente. Au-delà, les appuis sont ignorés
# plutôt que mémorisés : mieux vaut perdre un appui que voir dix commandes
# partir en rafale une minute plus tard.
MACRO_QUEUE_LIMIT = 4

PROFILE_SPLASH_MS = 500     # durée d'affichage du nom du profil en grand

# --- Le tableau des gestes ------------------------------------------
# L'écran affiche un tableau : une ligne par touche, trois colonnes
# (appui court, appui long, double appui). Quatre lignes tiennent à
# l'écran ; s'il y a plus de touches, le tableau défile tout seul.
TABLE_SCROLL_MS = 2500      # temps d'affichage avant de faire défiler d'un cran
HIGHLIGHT_MS = 1300         # durée du surlignage de la touche utilisée

# Défilement du nom de document, quand il est trop long pour l'écran.
# Le nom va-et-vient doucement, avec une pause à chaque extrémité pour te
# laisser le temps de lire le début puis la fin.
DOC_SCROLL_MS = 70          # millisecondes par pixel (plus grand = plus lent)
DOC_SCROLL_PAUSE_MS = 1600  # pause en début et en fin de course

# =====================================================================
# 6. LED RESPIRANTE
# =====================================================================
PWM_FREQ = 2000         # 2 kHz : aucun scintillement visible à l'oeil
LED_MIN = 0.04          # luminosité basse de la respiration (4 %)
LED_MAX = 0.25          # luminosité haute de la respiration (25 %)
LED_PERIOD_MS = 3000    # durée d'un cycle inspiration + expiration
LED_FLASH_MS = 120      # durée de l'éclat quand tu appuies sur ESC
LED_RETURN_MS = 350     # retour progressif du flash vers la respiration
# Note : le flash monte à 100 %, sans aucun risque, parce que le courant
# est limité par la résistance de 330 ohms montée en série avec la LED.
```

---

## device/profiles.py

`260 lignes - sha256 7dd14aa0f86a01e0`

```python
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
```

---

## device/boot.py

`81 lignes - sha256 22722123b48903aa`

```python
# -*- coding: utf-8 -*-
"""
boot.py - Premier fichier exécuté par MicroPython au démarrage.

=====================================================================
POURQUOI CE FICHIER EST AUSSI COURT
=====================================================================
boot.py s'exécute AVANT tout le reste et avant que le REPL ne soit
disponible. S'il plante ou s'il part en boucle, la carte devient pénible
à récupérer. On y met donc le strict minimum.

=====================================================================
LES TROIS MODES DE DÉMARRAGE
=====================================================================
Ce que tu maintiens pendant le RESET décide de tout :

  rien           -> MACROPAD : clavier USB actif, usage normal
  B1 maintenu    -> SAFE MODE : le clavier n'est même pas créé.
                    Impossible de taper quoi que ce soit, même avec une
                    macro mal écrite. C'est ton filet de secours.
  B2 maintenu    -> MODE CONFIG : pas de clavier non plus, mais le WiFi
                    s'allume et une page web permet de modifier tes
                    macros depuis un navigateur.

Dans les deux modes spéciaux, `create_interface()` n'est jamais appelé :
le macropad est PHYSIQUEMENT incapable d'envoyer une touche.

AUCUNE TOUCHE N'EST ENVOYÉE ICI, dans aucun des trois cas. boot.py se
contente d'exister en tant que clavier ; c'est main.py qui décide quoi
envoyer, et seulement sur un appui de ta part.
"""

from machine import Pin
from time import sleep_ms
import config as C
import runtime


def _maintenu(index):
    """True si la touche d'index donné est maintenue enfoncée.

    La résistance de tirage interne met la broche à 3,3 V (valeur 1) ;
    appuyer la relie à la masse (valeur 0). On laisse 5 ms à la broche
    pour se stabiliser, puis on lit trois fois : un seul parasite ne doit
    pas nous faire croire à un appui.
    """
    broche = Pin(C.BUTTON_PINS[index], Pin.IN, Pin.PULL_UP)
    sleep_ms(5)
    for _ in range(3):
        if broche.value() != 0:
            return False
        sleep_ms(3)
    return True


# --- 1. LED éteinte, quoi qu'il arrive -------------------------------
# Au démarrage un GPIO est dans un état indéfini ; on force un 0 franc
# pour que la LED ne s'allume pas bêtement pendant l'initialisation.
Pin(C.LED_PIN, Pin.OUT, value=0)

# --- 2. Quel mode de démarrage ? -------------------------------------
runtime.safe_mode = _maintenu(C.SAFE_MODE_BUTTON_INDEX)
if not runtime.safe_mode:
    runtime.config_mode = _maintenu(C.CONFIG_MODE_BUTTON_INDEX)

# --- 3. Création du clavier USB, ou pas ------------------------------
if runtime.safe_mode:
    print("SAFE MODE - HID DISABLED")
elif runtime.config_mode:
    print("MODE CONFIG - WiFi actif, HID desactive")
elif C.HID_ENABLED:
    try:
        from hid_keyboard import create_interface
        runtime.interface = create_interface()
    except Exception as exc:
        # On n'avale jamais silencieusement une erreur de clavier :
        # elle est affichée et mémorisée pour que main.py la signale.
        runtime.hid_error = str(exc)
        print("ERREUR CRITIQUE INITIALISATION HID :", exc)
else:
    print("HID_ENABLED = False : le macropad ne tapera aucune touche.")
```

---

## device/main.py

`392 lignes - sha256 529ad66f9c83615f`

```python
# -*- coding: utf-8 -*-
"""
main.py - Le chef d'orchestre. Lance automatiquement apres boot.py.

=====================================================================
LES TROIS MODES
=====================================================================
boot.py a deja decide lequel s'applique, selon ce que tu maintenais
pendant le RESET :

  SAFE MODE   (B1) : ecran d'alerte, retour au REPL. Aucun clavier.
  MODE CONFIG (B2) : WiFi + page web de configuration. Aucun clavier.
  NORMAL           : le macropad fait son travail.

=====================================================================
LE PRINCIPE DU MODE NORMAL : UNE SEULE BOUCLE, JAMAIS D'ATTENTE
=====================================================================
Tout tient dans une boucle qui tourne environ 500 fois par seconde. A
chaque tour on fait un tout petit peu de chaque travail :

    0. ecouter le PC (profil automatique, configuration)
    1. lire les entrees
    2. traiter ESC en priorite
    3. profils, verrouillage, gestes des touches
    4. envoyer AU PLUS un paquet clavier
    5. mettre a jour la LED
    6. envoyer AU PLUS une page d'ecran
    7. dormir 2 ms, et on recommence

C'est une boucle cooperative : chaque tache prend un petit morceau de
temps puis rend la main volontairement. Ecrire une commande de seize
caracteres (400 ms) n'empeche donc jamais le bouton ESC de repondre.

=====================================================================
TROIS GESTES PAR TOUCHE
=====================================================================
Appui court, appui long, double appui : voir gestures.py. Une touche sans
macro double part instantanement au relachement ; on ne paie le delai
d'attente que la ou on s'en sert.
"""

from time import ticks_ms, ticks_diff, sleep_ms
import config as C
import runtime
import store
from inputs import Inputs
from profiles import ProfileManager, TESTS, COURT
from gestures import Gestes, FIN
from stats import Stats
from display import Display
from hid_keyboard import HIDKeyboard
from layouts import compile_actions
from link import Link, EVT_PROFIL, EVT_DOCUMENT, EVT_RECHARGER

NB_TOUCHES = len(C.BUTTON_PINS)


# =====================================================================
# MODE CONFIG : WiFi + page web
# =====================================================================
def mode_config(display):
    """Allume le point d'acces et sert la page de configuration.

    Aucun clavier n'a ete cree par boot.py : ce mode ne peut rien taper.
    On en sort par un RESET normal.
    """
    from portal import demarrer_ap, arreter_ap, Portail

    print("=" * 46)
    print(" MODE CONFIGURATION")
    print("=" * 46)

    # LED allumee fixe, differente de la respiration habituelle : d'un
    # coup d'oeil tu sais que le macropad n'est pas un clavier.
    led = None
    try:
        from led import Led
        led = Led()
        led.set_level(C.LED_MAX)
    except Exception as exc:
        print("LED desactivee :", exc)

    portail = None
    try:
        ssid, cle, adresse = demarrer_ap()
        display.config_screen(ssid, cle, adresse)
        display.flush_startup()
        print("1. Connecte-toi au reseau WiFi :", ssid)
        print("2. Cle :", cle)
        print("3. Ouvre http://%s dans un navigateur" % adresse)
        print("4. Modifie tes macros, enregistre, puis fais un RESET.")

        portail = Portail(NB_TOUCHES, Stats(NB_TOUCHES))
        portail.ouvrir()
        while True:
            portail.service()          # rend la main au bout de 0,25 s
    except KeyboardInterrupt:
        print("Mode configuration interrompu.")
    except Exception as exc:
        print("MODE CONFIG en echec :", exc)
        display.message("CONFIG KO", str(exc)[:16])
        display.flush_startup()
    finally:
        if portail:
            portail.fermer()
        arreter_ap()
        if led:
            led.close()


# =====================================================================
# MODE NORMAL
# =====================================================================
def run():
    display = Display()

    if runtime.safe_mode:
        display.message("SAFE MODE", "HID DISABLED", "", "Boutons lisibles",
                        "Aucune frappe")
        display.flush_startup()
        print("SAFE MODE : le clavier n'existe pas.")
        print("REPL disponible. Diagnostics : import diag; diag.run()")
        return

    if runtime.config_mode:
        mode_config(display)
        return

    # --- Chargement de la configuration --------------------------------
    profils, ordre, titres, couleurs, apps, repli, origine = \
        store.charger(NB_TOUCHES)
    print("Macros chargees depuis :", origine)

    manager = ProfileManager(ordre, C.DEFAULT_PROFILE, profils, NB_TOUCHES)

    # Verification de TOUTES les macros avant la moindre frappe. Une macro
    # impossible a taper doit echouer ici, pas au milieu d'une commande.
    for nom in ordre:
        for label, gestes_touche in profils[nom]:
            for actions in (gestes_touche or {}).values():
                compile_actions(actions, C.KEYBOARD_LAYOUT)
    if C.HID_TEST is not None and C.HID_TEST not in TESTS:
        raise ValueError("HID_TEST invalide")

    controls = Inputs()
    keyboard = HIDKeyboard(runtime.interface) if runtime.interface else None
    stats = Stats(NB_TOUCHES)
    gestes = Gestes(NB_TOUCHES, C.GESTE_LONG_MS, C.GESTE_DOUBLE_MS)
    gestes.configurer(manager.macros)

    led = None
    try:
        from led import Led
        led = Led()
    except Exception as exc:
        print("LED desactivee :", exc)

    # Les LED RGB des touches. Rgb() se desactive tout seul si le materiel
    # n'est pas la ou si RGB_ENABLED vaut False : rien a proteger ici.
    from rgb import Rgb
    rgb = Rgb()

    lien = Link(NB_TOUCHES, stats=stats) if C.LINK_ENABLED else None
    verrouille = False          # True = l'auto ne peut plus changer de profil
    dernier_auto = None

    def afficher(splash):
        display.profile(titres.get(manager.name, manager.name),
                        manager.macros, ticks_ms(),
                        manager.index, len(ordre), splash)
        gestes.configurer(manager.macros)
        # La couleur suit le logiciel : c'est le profil actif qui la donne,
        # et le PC change de profil tout seul selon la fenetre active.
        rgb.profil(couleurs.get(manager.name))

    def recharger_profils():
        """Relit profils.json et applique la nouvelle configuration.

        Appele quand une page web vient d'enregistrer : les changements
        prennent effet immediatement, sans RESET.
        """
        nonlocal manager, titres, ordre, couleurs
        try:
            (neufs, ordre_neuf, titres_neufs, couleurs_neuves,
             _apps, _repli, origine_neuve) = store.charger(NB_TOUCHES)
            nouveau = ProfileManager(ordre_neuf, manager.name, neufs, NB_TOUCHES)
        except Exception as exc:
            print("[main] configuration refusee, on garde l'ancienne :", exc)
            return
        manager, titres, ordre = nouveau, titres_neufs, ordre_neuf
        couleurs = couleurs_neuves
        afficher(False)
        print("Macros rechargees depuis :", origine_neuve)

    def declencher(index, geste):
        """Execute la macro correspondant a un geste sur une touche."""
        if geste == FIN:
            # Une touche modificatrice vient d'etre relachee : on remonte
            # Ctrl ou Maj cote PC. Rien a afficher, rien a compter.
            if keyboard:
                keyboard.relacher_maintien()
            return

        label, gestes_touche = manager.macros[index]
        actions = (gestes_touche or {}).get(geste)
        if C.HID_TEST is not None:
            # En mode test, seul l'appui court sur B1 agit.
            if index != 0 or geste != COURT:
                return
            label, actions = C.HID_TEST, TESTS[C.HID_TEST]

        print("%s B%d %s %s" % (manager.name, index + 1, geste, label or "-"))
        # L'ecran et les LED ont deja reagi au moment de l'appui.
        if not actions:
            print("   (aucune macro sur ce geste)")
            return
        stats.compter(manager.name, index)
        if not keyboard:
            print("   (HID desactive : rien n'est tape)")
            return
        if actions[0][0] == "maintien":
            # Touche modificatrice : on enfonce et on GARDE enfonce
            # jusqu'au relachement (voir gestures.py).
            keyboard.maintenir(actions)
        else:
            keyboard.submit(actions)

    afficher(False)
    print("Profil :", manager.name,
          "HID :", "initialise" if keyboard else "DESACTIVE")
    if runtime.hid_error:
        display.message("HID ERROR", "VOIR REPL")

    demarre = ticks_ms()
    arme = False
    etait_pret = False
    etat_affiche = None
    dernier_controle = demarre

    try:
        while True:
            now = ticks_ms()
            fronts = controls.poll(now)

            # --- 0. Ce que dit le PC ---------------------------------
            if lien:
                for genre, valeur in lien.service():
                    if genre == EVT_PROFIL:
                        dernier_auto = now
                        # Le verrou te rend la main : si tu l'as active,
                        # le PC ne peut plus imposer de profil.
                        if (not verrouille and valeur in manager.order
                                and valeur != manager.name):
                            manager.index = manager.order.index(valeur)
                            if keyboard:
                                keyboard.cancel()
                            afficher(True)
                            print("Profil (auto) :", manager.name)
                    elif genre == EVT_DOCUMENT:
                        dernier_auto = now
                        display.set_document(valeur)
                    elif genre == EVT_RECHARGER:
                        recharger_profils()

            # --- Fin de la garde de demarrage ------------------------
            if not arme and ticks_diff(now, demarre) >= C.BOOT_GUARD_MS:
                arme = True
                controls.disarm_held()
                fronts = []
                print("Entrees actives ; HID_TEST =", C.HID_TEST)

            if arme:
                for nom, front in fronts:
                    display.reveiller(now)      # tout appui reveille l'ecran

                    # --- 1. ESC : priorite absolue --------------------
                    if nom == "ESC":
                        if front == 1:
                            if keyboard:
                                keyboard.escape(now)
                                # tick() tout de suite : le paquet part dans
                                # le meme tour de boucle.
                                keyboard.tick(now)
                            if led:
                                led.flash(now)
                            print("ESC")
                        continue

                    # --- 2. Profils et verrouillage -------------------
                    if nom in ("PREVIOUS", "NEXT"):
                        if front != 1:
                            continue
                        # Les deux TTP touches EN MEME TEMPS : on bascule le
                        # verrou. Profil verrouille = le PC ne peut plus le
                        # changer tout seul, tu gardes la main.
                        if (controls.items["PREVIOUS"].active()
                                and controls.items["NEXT"].active()):
                            verrouille = not verrouille
                            print("Verrouillage du profil :",
                                  "ACTIF" if verrouille else "inactif")
                            afficher(False)
                        else:
                            manager.move(1 if nom == "NEXT" else -1)
                            if keyboard:
                                # Hors de question que la fin d'une commande
                                # de l'ancien profil continue de s'ecrire.
                                keyboard.cancel()
                            afficher(True)
                            print("Profil :", manager.name)
                        continue

                    # --- 3. Les touches de macro ----------------------
                    if nom.startswith("B"):
                        index = int(nom[1:]) - 1
                        if front == 1:
                            # L'ECRAN ET LES LED REAGISSENT ICI, sur le
                            # front physique, et pas dans declencher().
                            # Une touche qui a un double appui attend
                            # GESTE_DOUBLE_MS avant de savoir quelle macro
                            # envoyer : attendre cela pour allumer la LED
                            # donnait un quart de seconde de retard, tres
                            # perceptible sous le doigt.
                            display.surligner(index, now)
                            rgb.touche(index, now)
                            geste = gestes.appui(index, now)
                        else:
                            geste = gestes.relachement(index, now)
                        if geste:
                            declencher(index, geste)

                # Appuis longs et doubles appuis arrives a echeance.
                for index, geste in gestes.service(now):
                    declencher(index, geste)

            # --- 4. Travaux de fond, tous non bloquants -------------
            if keyboard:
                keyboard.tick(now)
                pret = keyboard.ready()
                if pret and not etait_pret:
                    controls.disarm_held()
                etait_pret = pret

            if ticks_diff(now, dernier_controle) >= 250:
                dernier_controle = now
                auto = (dernier_auto is not None
                        and ticks_diff(now, dernier_auto) < C.AUTO_TIMEOUT_MS)
                if verrouille:
                    etat = "LOCK"          # tu as verrouille le profil
                elif keyboard is None:
                    etat = "OFF"
                elif keyboard.fault:
                    etat = "ERR"
                elif not keyboard.ready():
                    etat = "..."
                elif auto:
                    etat = "AUTO"          # le PC pilote les profils
                else:
                    etat = "HID"
                if etat != etat_affiche:
                    etat_affiche = etat
                    display.set_etat(etat)
                    rgb.etat(etat)

            if led:
                try:
                    led.tick(now)
                except Exception as exc:
                    print("LED arretee :", exc)
                    try:
                        led.close()
                    except Exception:
                        pass
                    led = None

            rgb.tick(now)
            display.tick(now)
            sleep_ms(C.LOOP_MS)

    finally:
        # Ce bloc s'execute TOUJOURS : arret normal, Ctrl-C, ou erreur.
        # C'est la qu'on garantit qu'aucune touche ne reste enfoncee cote
        # Windows, que la LED est eteinte et que les compteurs sont sauves.
        if keyboard:
            keyboard.close()
        if led:
            led.close()
        rgb.close()
        stats.enregistrer()


if __name__ == "__main__":
    run()
```

---

## device/runtime.py

`17 lignes - sha256 bec7ef35eb2d5495`

```python
# -*- coding: utf-8 -*-
"""
runtime.py - Petite mémoire partagée entre boot.py et main.py.

MicroPython exécute d'abord boot.py, puis main.py. Ce sont deux fichiers
séparés qui ne peuvent pas se passer de variables directement. On utilise
donc ce module comme une boîte aux lettres : boot.py y dépose ce qu'il a
constaté, main.py vient le lire.

Rien n'est écrit dans la mémoire flash : tout est perdu au RESET, ce qui
est voulu (aucune usure de la flash, aucun état bizarre qui survivrait).
"""

safe_mode = False    # True si B1 était maintenu au démarrage
config_mode = False  # True si B2 était maintenu au démarrage (WiFi + page web)
interface = None     # l'objet clavier USB, ou None si HID désactivé
hid_error = None     # message d'erreur si la création du clavier a échoué
```

---

## device/inputs.py

`166 lignes - sha256 bc8cce45dea26cb6`

```python
# -*- coding: utf-8 -*-
"""
inputs.py - Lecture des boutons, du bouton ESC et des touches capacitives.

=====================================================================
LE PROBLEME DU REBOND, EXPLIQUE SIMPLEMENT
=====================================================================

Quand tu appuies sur un interrupteur mécanique, les deux lamelles de métal
ne se touchent pas franchement du premier coup : elles se cognent et
rebondissent pendant 1 à 10 millisecondes. Électriquement, l'ESP32 voit :

    appuyé - relâché - appuyé - relâché - appuyé ... puis stable

L'ESP32 lit l'état des milliers de fois par seconde : sans précaution, un
seul appui de ton doigt déclencherait la macro cinq fois. C'est ce qu'on
appelle le rebond, et le filtrer s'appelle l'anti-rebond (debounce).

Ce fichier propose DEUX filtres, au choix selon la touche :

1. MODE PATIENT (par défaut, pour B1 à B4 et les TTP223)
   On attend que l'état reste identique pendant DEBOUNCE_MS avant de le
   croire. Très robuste. Inconvénient : la macro part avec 25 ms de retard,
   ce qui est imperceptible pour une macro.

2. MODE RAPIDE (pour le bouton ESC)
   On croit le tout premier changement, on agit immédiatement, PUIS on
   ferme les yeux pendant DEBOUNCE_MS pour ignorer les rebonds. Le retard
   tombe à zéro. C'est la méthode des vrais claviers, et c'est ce qu'on
   veut pour une touche d'annulation.

Dans les deux cas, un nouvel appui n'est accepté qu'APRES un relâchement :
garder le doigt appuyé ne répète jamais l'action.

=====================================================================
POURQUOI IL N'Y A AUCUN FIL DE PLUS SUR LES BOUTONS
=====================================================================

Un interrupteur relie simplement le GPIO à la masse (GND). Au repos, le
GPIO ne serait relié à rien : on dit qu'il "flotte", et il lirait n'importe
quoi. On active donc la résistance de tirage interne de l'ESP32 (PULL_UP) :
elle maintient doucement le GPIO à 3,3 V au repos. Appuyer met le GPIO à
0 V. Le bouton est donc "actif à l'état bas" (active LOW).

Pour les TTP223, c'est l'inverse : le module pilote lui-même sa sortie et
la met à 3,3 V au toucher. On active alors un tirage vers le bas
(PULL_DOWN) pour que l'entrée lise 0 si le module est débranché.
"""

from machine import Pin
from time import ticks_ms, ticks_diff, ticks_add
import config as C


class Debouncer:
    """Filtre anti-rebond. Renvoie 1 (appui), -1 (relâchement) ou 0 (rien)."""

    def __init__(self, initial, delay_ms, now, fast=False):
        self.raw = self.stable = bool(initial)
        self.changed_at = now
        self.delay_ms = delay_ms
        self.fast = fast
        self.locked_until = now
        # Si la touche est déjà enfoncée au démarrage (cas du SAFE MODE où
        # tu maintiens B1), on refuse d'en faire un appui : il faudra la
        # relâcher d'abord. Sinon une macro partirait toute seule au boot.
        self.armed = not self.stable

    def update(self, active, now):
        active = bool(active)

        if self.fast:
            # --- Mode rapide : on croit le premier front, puis on ignore
            # tout pendant delay_ms le temps que les rebonds se calment.
            if ticks_diff(now, self.locked_until) < 0:
                return 0
            if active == self.stable:
                return 0
            self.stable = self.raw = active
            self.locked_until = ticks_add(now, self.delay_ms)
            if not active:
                self.armed = True
                return -1
            if self.armed:
                self.armed = False
                return 1
            return 0

        # --- Mode patient : on exige delay_ms de stabilité.
        if active != self.raw:
            self.raw = active
            self.changed_at = now
        if self.stable != self.raw and ticks_diff(now, self.changed_at) >= self.delay_ms:
            self.stable = self.raw
            if not self.stable:
                self.armed = True
                return -1
            if self.armed:
                self.armed = False
                return 1
        return 0


class Input:
    """Une entrée physique : une broche + son filtre."""

    def __init__(self, number, active_high, delay, fast=False):
        # PULL_DOWN pour une sortie active haute (TTP223),
        # PULL_UP pour un contact vers la masse (boutons, ESC).
        pull = Pin.PULL_DOWN if active_high else Pin.PULL_UP
        self.pin = Pin(number, Pin.IN, pull)
        self.active_high = active_high
        self.filter = Debouncer(self.active(), delay, ticks_ms(), fast)

    def active(self):
        """True si la touche est actionnée, quelle que soit sa polarité."""
        return bool(self.pin.value()) == self.active_high

    def poll(self, now):
        return self.filter.update(self.active(), now)


class Inputs:
    """Toutes les entrées du macropad, lues dans un ordre garanti."""

    def __init__(self):
        # ATTENTION : on garde une LISTE, pas seulement un dictionnaire.
        # En MicroPython, l'ordre de parcours d'un dictionnaire n'est pas
        # garanti (contrairement à Python sur PC). Une liste assure que ESC
        # est toujours lu en premier, et que les logs sortent toujours dans
        # le même ordre.
        self.sequence = [
            ("ESC", Input(C.ESC_PIN, False, C.ESC_DEBOUNCE_MS,
                          fast=getattr(C, "ESC_FAST_EDGE", True))),
        ]
        for index, pin in enumerate(C.BUTTON_PINS):
            self.sequence.append(
                ("B" + str(index + 1), Input(pin, False, C.DEBOUNCE_MS)))
        self.sequence.append(
            ("PREVIOUS", Input(C.TTP_PREVIOUS_PIN, C.TTP_ACTIVE_HIGH,
                               C.TTP_DEBOUNCE_MS)))
        self.sequence.append(
            ("NEXT", Input(C.TTP_NEXT_PIN, C.TTP_ACTIVE_HIGH,
                           C.TTP_DEBOUNCE_MS)))
        # Dictionnaire de confort pour retrouver une entrée par son nom.
        self.items = dict(self.sequence)

    def poll(self, now):
        """Renvoie la liste des changements détectés à cet instant."""
        result = []
        for name, item in self.sequence:
            edge = item.poll(now)
            if edge:
                result.append((name, edge))
        return result

    def disarm_held(self):
        """Ignore ce qui est maintenu à cet instant.

        Utilisé après la garde de démarrage et après une reconnexion USB :
        si tu tenais encore une touche, elle ne déclenchera rien tant que tu
        ne l'auras pas relâchée.
        """
        for _, item in self.sequence:
            if item.active():
                item.filter.armed = False
```

---

## device/gestures.py

`217 lignes - sha256 db0b9643634fc182`

```python
# -*- coding: utf-8 -*-
"""
gestures.py - Appui court, appui long, double appui.

=====================================================================
CE QUE CA APPORTE
=====================================================================
Chaque touche peut declencher TROIS macros differentes selon la facon
dont tu appuies :

    appui court   -> macro 1
    appui long    -> macro 2   (maintenu au-dela de GESTE_LONG_MS)
    double appui  -> macro 3   (deux appuis rapprochés)

Six touches deviennent donc dix-huit actions, sans un seul composant de
plus.

=====================================================================
LE PIEGE DU DOUBLE APPUI, ET COMMENT ON L'EVITE
=====================================================================
Pour savoir si un appui est simple ou double, il faut attendre : "est-ce
qu'un second appui arrive dans les 250 ms ?". Naivement, cela ajoute donc
250 ms de retard a TOUTES les touches. Inacceptable pour un macropad.

La solution : on ne fait attendre que les touches qui ont VRAIMENT une
macro de double appui. Une touche qui n'en a pas part instantanement au
relachement, exactement comme avant. Meme raisonnement pour l'appui long :
sans macro longue, on ne surveille rien.

C'est main.py qui declare les capacites de chaque touche, a chaque
changement de profil, avec configurer().

=====================================================================
LA MACHINE A ETATS, TOUCHE PAR TOUCHE
=====================================================================
    REPOS      --appui-->        ENFONCE
    ENFONCE    --maintenu-->     LONG_ENVOYE   (emet LONG)
    ENFONCE    --relache-->      REPOS         (emet COURT)
             ou ATTENTE_DOUBLE   si la touche a une macro double
    ATTENTE_DOUBLE --appui-->    REPOS         (emet DOUBLE)
    ATTENTE_DOUBLE --delai-->    REPOS         (emet COURT, tardif)
    LONG_ENVOYE    --relache-->  REPOS         (rien : deja emis)

L'appui long est emis DES QUE le seuil est franchi, sans attendre le
relachement : tu sens la macro partir sous ton doigt, c'est bien plus
agreable que d'attendre d'avoir relache.

=====================================================================
LE MODE MODIFICATEUR : UNE TOUCHE QUI FAIT CTRL ET MAJ
=====================================================================
Une touche dont l'appui court est du type "maintien" ne fonctionne plus
comme les autres. Elle devient une vraie touche modificatrice :

    1 appui maintenu                     -> Ctrl reste enfonce
    1 appui bref, puis 1 appui maintenu  -> Maj reste enfonce

Tu gardes le doigt dessus, le modificateur reste enfonce cote PC ; tu
relaches, il remonte. Tu peux donc cliquer a la souris pendant ce temps,
ce qui est exactement l'usage recherche dans Civil 3D (Ctrl+clic pour
selectionner, Maj+clic pour deselectionner).

Deux choix importants :

  * le modificateur descend DES L'APPUI, sans le moindre delai. Attendre
    260 ms pour savoir si un second appui arrive rendrait la touche
    inutilisable ;
  * consequence assumee : le premier appui bref de la sequence "bref puis
    maintenu" envoie un Ctrl seul, tres bref. Un Ctrl seul n'a aucun effet
    dans Windows, Civil 3D, Blender ou Word - contrairement a Alt, qui
    ouvre la barre de menus. Evite donc de mettre ALT sur le premier
    appui.

    REPOS      --appui-->        TENU1        (emet COURT : on maintient)
    TENU1      --relache-->      ATTENTE2     (emet FIN : on relache)
                              ou REPOS        s'il n'y a pas de second
    ATTENTE2   --appui-->        TENU2        (emet DOUBLE : on maintient)
    ATTENTE2   --delai-->        REPOS        (rien)
    TENU2      --relache-->      REPOS        (emet FIN)
"""

from time import ticks_diff, ticks_add

# Les trois gestes
COURT = "court"
LONG = "long"
DOUBLE = "double"
# Un quatrieme evenement, qui n'est pas un geste enregistrable : il dit
# a main.py de relacher les touches maintenues.
FIN = "fin"

# Etats internes
_REPOS = 0
_ENFONCE = 1
_ATTENTE_DOUBLE = 2
_LONG_ENVOYE = 3
_TENU1 = 4                  # mode modificateur : premier maintien
_ATTENTE_MAINTIEN2 = 5      # relache, on guette le second appui
_TENU2 = 6                  # mode modificateur : second maintien


class Gestes:
    """Transforme des appuis/relachements bruts en gestes."""

    def __init__(self, nb_touches, long_ms=400, double_ms=260):
        self.nb_touches = nb_touches
        self.long_ms = long_ms
        self.double_ms = double_ms
        self.etats = [_REPOS] * nb_touches
        self.instants = [0] * nb_touches          # debut d'appui / fin d'attente
        # Capacites, mises a jour a chaque changement de profil.
        self.a_long = [False] * nb_touches
        self.a_double = [False] * nb_touches
        # Mode modificateur (voir en tete de fichier).
        self.a_maintien = [False] * nb_touches
        self.a_maintien2 = [False] * nb_touches

    # ------------------------------------------------------------------
    def configurer(self, macros):
        """Declare quelles touches ont une macro longue ou double.

        macros est la liste (libelle, gestes) du profil courant. Une touche
        sans macro longue ne surveillera pas le maintien ; une touche sans
        macro double ne fera pas attendre le second appui.
        """
        for index in range(self.nb_touches):
            gestes = {}
            if index < len(macros):
                gestes = macros[index][1] or {}
            self.a_long[index] = bool(gestes.get(LONG))
            self.a_double[index] = bool(gestes.get(DOUBLE))
            self.a_maintien[index] = _est_maintien(gestes.get(COURT))
            self.a_maintien2[index] = _est_maintien(gestes.get(DOUBLE))
        self.reinitialiser()

    def reinitialiser(self):
        for index in range(self.nb_touches):
            self.etats[index] = _REPOS

    # ------------------------------------------------------------------
    def appui(self, index, now):
        """Un appui vient d'etre detecte. Retourne un geste ou None."""
        if not (0 <= index < self.nb_touches):
            return None
        etat = self.etats[index]

        if self.a_maintien[index]:
            # Mode modificateur : on enfonce tout de suite, sans attendre.
            if etat == _ATTENTE_MAINTIEN2:
                self.etats[index] = _TENU2
                return DOUBLE           # second maintien (Maj)
            self.etats[index] = _TENU1
            return COURT                # premier maintien (Ctrl)

        if etat == _ATTENTE_DOUBLE:
            # Second appui dans le delai : c'est un double.
            self.etats[index] = _REPOS
            return DOUBLE
        self.etats[index] = _ENFONCE
        self.instants[index] = now
        return None

    def relachement(self, index, now):
        """Un relachement vient d'etre detecte. Retourne un geste ou None."""
        if not (0 <= index < self.nb_touches):
            return None
        etat = self.etats[index]

        if etat == _TENU1:
            # On relache le modificateur, et on guette un second appui.
            if self.a_maintien2[index]:
                self.etats[index] = _ATTENTE_MAINTIEN2
                self.instants[index] = ticks_add(now, self.double_ms)
            else:
                self.etats[index] = _REPOS
            return FIN
        if etat == _TENU2:
            self.etats[index] = _REPOS
            return FIN

        if etat == _LONG_ENVOYE:
            self.etats[index] = _REPOS      # la macro longue est deja partie
            return None
        if etat != _ENFONCE:
            return None
        if self.a_double[index]:
            # On attend un eventuel second appui avant de conclure.
            self.etats[index] = _ATTENTE_DOUBLE
            self.instants[index] = ticks_add(now, self.double_ms)
            return None
        self.etats[index] = _REPOS
        return COURT

    def service(self, now):
        """A appeler a chaque tour de boucle. Retourne [(index, geste), ...]."""
        resultats = []
        for index in range(self.nb_touches):
            etat = self.etats[index]
            if etat == _ENFONCE:
                if (self.a_long[index]
                        and ticks_diff(now, self.instants[index]) >= self.long_ms):
                    self.etats[index] = _LONG_ENVOYE
                    resultats.append((index, LONG))
            elif etat == _ATTENTE_DOUBLE:
                if ticks_diff(now, self.instants[index]) >= 0:
                    self.etats[index] = _REPOS
                    resultats.append((index, COURT))
            elif etat == _ATTENTE_MAINTIEN2:
                # Le second appui n'est pas venu : rien a emettre, le
                # premier maintien a deja ete relache.
                if ticks_diff(now, self.instants[index]) >= 0:
                    self.etats[index] = _REPOS
        return resultats


def _est_maintien(actions):
    """Cette macro est-elle du type 'maintien' (touche gardee enfoncee) ?"""
    return bool(actions) and actions[0][0] == "maintien"
```

---

## device/layouts.py

`335 lignes - sha256 9aa1e8c9e849a622`

```python
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
        elif kind in ("combo", "maintien"):
            # "maintien" se traduit exactement comme une combinaison : ce
            # sont les memes codes de touches. La difference n'est pas ici
            # mais dans la facon de les ENVOYER - voir hid_keyboard.py :
            # une combinaison est appuyee puis relachee, un maintien reste
            # enfonce tant que tu gardes le doigt sur la touche.
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
```

---

## device/store.py

`374 lignes - sha256 e4c0a8b55ab817ea`

```python
# -*- coding: utf-8 -*-
"""
store.py - Enregistrement de la configuration sur la carte.

=====================================================================
A QUOI CA SERT
=====================================================================
Les pages web modifient tes profils, tes macros et ta liste de logiciels.
Il faut bien ranger tout cela quelque part pour que ca survive au
debranchement : c'est le role de ce module. Il lit et ecrit un fichier
JSON sur la memoire flash (`profils.json` par defaut).

Le JSON est un format texte simple, lisible, que tu peux ouvrir dans
Thonny pour voir ce que contient ta configuration.

C'est aussi ici qu'est definie la forme d'echange avec les deux pages web
(vers_json / depuis_json) : le portail WiFi et le compagnon USB parlent
donc exactement le meme langage.

=====================================================================
DEUX REGLES DE SECURITE
=====================================================================
1. **Rien n'est enregistre sans avoir ete verifie.** Chaque macro est
   traduite en codes clavier AVANT l'ecriture. Si un caractere est
   impossible a taper ou si un nom de touche est inconnu, l'enregistrement
   est refuse avec un message clair. Impossible d'enregistrer une
   configuration qui planterait au prochain demarrage.

2. **Le fichier n'est jamais indispensable.** S'il est absent, illisible
   ou incoherent, le firmware repart sur les valeurs d'usine de
   profiles.py en le signalant dans le REPL. Une carte ne peut pas
   devenir inutilisable a cause de ce fichier ; au pire, efface-le.

=====================================================================
FORME DU FICHIER
=====================================================================
    {
      "version": 2,
      "ordre": ["BLENDER", "CIVIL3D", "WORD", "WINDOWS"],
      "profils": {
        "CIVIL3D": {
          "titre": "CIVIL 3D",
          "couleur": "#00a0ff",
          "touches": [
            {"label": "MATCH",
             "court":  {"type": "text_enter", "valeur": "_MATCHPROP"},
             "long":   {"type": "none", "valeur": ""},
             "double": {"type": "none", "valeur": ""}},
            ...
          ]
        }
      },
      "apps": {
        "repli": {"profil": "WINDOWS", "abrege": "Win"},
        "liste": [{"exe": "acad.exe", "profil": "CIVIL3D", "abrege": "C3D"}]
      }
    }

Le "type" vaut "key", "combo", "maintien", "text", "text_enter" ou "none".
Pour un "combo", la valeur s'ecrit avec des plus : "CTRL+SHIFT+ESC".
Un "maintien" s'ecrit pareil, mais la touche reste ENFONCEE tant que tu
gardes le doigt dessus : c'est ainsi qu'une touche du macropad devient une
vraie touche Ctrl ou Maj.
"""

import json
import config as C
import profiles as P
from layouts import compile_actions

TYPES = ("key", "combo", "maintien", "text", "text_enter", "none")


# =====================================================================
# Conversion entre la forme des pages web et la forme interne
# =====================================================================
def action_vers_json(actions):
    """Forme interne -> (type, valeur texte) pour les formulaires."""
    if not actions:
        return "none", ""
    genre, valeur = actions[0]
    if genre in ("combo", "maintien"):
        # Les deux transportent une liste de touches : CTRL+MAJ, ou juste CTRL.
        return genre, "+".join(valeur)
    return genre, str(valeur)


def action_depuis_json(genre, valeur):
    """(type, valeur texte) -> forme interne."""
    if genre == "none" or (genre in ("text", "text_enter") and not valeur):
        return []
    if genre in ("combo", "maintien"):
        touches = tuple(p.strip() for p in str(valeur).split("+") if p.strip())
        if not touches:
            raise ValueError("combinaison vide")
        return [(genre, touches)]
    if genre in ("key", "text", "text_enter"):
        if not str(valeur).strip():
            return []
        return [(genre, str(valeur))]
    raise ValueError("type inconnu : " + str(genre))


# =====================================================================
# Les couleurs des LED RGB
# =====================================================================
# Dans le fichier et dans les pages web, une couleur s'ecrit comme en
# HTML : "#00a0ff". C'est ce que comprend le selecteur de couleur du
# navigateur, et c'est lisible a l'oeil nu dans profils.json.
def couleur_vers_texte(couleur):
    r, v, b = (int(c) & 255 for c in couleur)
    return "#%02x%02x%02x" % (r, v, b)


def couleur_depuis_texte(texte, defaut=None):
    """Accepte "#00a0ff" ou "00a0ff". Retombe sur defaut si c'est illisible.

    On ne leve PAS d'exception ici : une couleur fausse ne doit pas
    empecher d'enregistrer des macros parfaitement valables. Au pire, le
    pad s'allume dans la couleur par defaut.
    """
    if defaut is None:
        defaut = tuple(C.RGB_COULEUR_DEFAUT)
    texte = str(texte or "").strip().lstrip("#")
    if len(texte) != 6:
        return tuple(defaut)
    try:
        return tuple(int(texte[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return tuple(defaut)


def couleur_usine(nom):
    """Couleur d'usine d'un profil, ou la couleur par defaut."""
    return tuple(getattr(C, "RGB_COULEURS", {}).get(
        nom, C.RGB_COULEUR_DEFAUT))


# =====================================================================
# Verification
# =====================================================================
def verifier(profils, ordre, nb_touches):
    """Retourne la liste des problemes. Liste vide = configuration saine."""
    problemes = []

    if not ordre:
        problemes.append("l'ordre des profils est vide")
    if len(set(ordre)) != len(ordre):
        problemes.append("un profil apparait deux fois dans l'ordre")
    for nom in ordre:
        if nom not in profils:
            problemes.append("l'ordre cite '%s' qui n'existe pas" % nom)

    for nom, touches in profils.items():
        if len(touches) != nb_touches:
            problemes.append("%s : %d touches au lieu de %d"
                             % (nom, len(touches), nb_touches))
        for index, (label, gestes) in enumerate(touches):
            if len(label) > P.LABEL_MAX:
                problemes.append("%s B%d : libelle '%s' depasse %d caracteres"
                                 % (nom, index + 1, label, P.LABEL_MAX))
            if not (gestes or {}).get(P.COURT):
                # Un appui court vide est autorise : la touche est inactive.
                pass
            for geste, actions in (gestes or {}).items():
                if geste not in P.GESTES:
                    problemes.append("%s B%d : geste inconnu '%s'"
                                     % (nom, index + 1, geste))
                    continue
                try:
                    # La verification qui compte : la macro est-elle
                    # reellement tapable avec la disposition choisie ?
                    compile_actions(actions, C.KEYBOARD_LAYOUT)
                except Exception as exc:
                    problemes.append("%s B%d %s (%s) : %s"
                                     % (nom, index + 1, geste, label, exc))
    return problemes


# =====================================================================
# Valeurs d'usine
# =====================================================================
def defauts():
    """Copie des valeurs d'usine, dans la forme interne."""
    profils = {}
    for nom, touches in P.PROFILES.items():
        profils[nom] = [(label, dict(gestes)) for label, gestes in touches]
    apps = [tuple(a) for a in P.APPS]
    couleurs = dict((nom, couleur_usine(nom)) for nom in profils)
    return (profils, list(C.PROFILES_ORDER), dict(P.TITLES), couleurs,
            apps, tuple(P.APPS_REPLI))


# =====================================================================
# Conversion vers et depuis les pages web
# =====================================================================
def vers_json(nb_touches, stats=None):
    """Configuration complete, prete a etre envoyee a une page web."""
    profils, ordre, titres, couleurs, apps, repli, origine = charger(nb_touches)
    blocs = {}
    for nom, touches in profils.items():
        liste = []
        for index, (label, gestes) in enumerate(touches):
            entree = {"label": label}
            for geste in P.GESTES:
                genre, valeur = action_vers_json((gestes or {}).get(geste))
                entree[geste] = {"type": genre, "valeur": valeur}
            if stats is not None:
                entree["usages"] = stats.pour(nom)[index]
            liste.append(entree)
        blocs[nom] = {
            "titre": titres.get(nom, nom),
            "couleur": couleur_vers_texte(
                couleurs.get(nom) or couleur_usine(nom)),
            "touches": liste,
        }

    return {
        "version": 2,
        "ordre": ordre,
        "profils": blocs,
        "apps": {
            "repli": {"profil": repli[0], "abrege": repli[1]},
            "liste": [{"exe": e, "profil": p, "abrege": a} for e, p, a in apps],
        },
        "touches": nb_touches,
        "gestes": list(P.GESTES),
        "origine": origine,
    }


def depuis_json(data, nb_touches):
    """Forme web -> forme interne. Leve une exception si c'est illisible."""
    ordre = [str(n) for n in data["ordre"]]
    profils, titres, couleurs = {}, {}, {}
    for nom, bloc in data["profils"].items():
        touches = []
        for entree in bloc["touches"][:nb_touches]:
            gestes = {}
            if "type" in entree and not any(g in entree for g in P.GESTES):
                # Fichier de version 1 : une seule macro par touche, ecrite
                # a plat. On la reprend comme appui court, les deux autres
                # gestes restent libres. Personne ne perd sa configuration
                # en mettant le firmware a jour.
                entree = dict(entree)
                entree[P.COURT] = {"type": entree.get("type", "none"),
                                   "valeur": entree.get("valeur", "")}
            for geste in P.GESTES:
                champ = entree.get(geste) or {}
                actions = action_depuis_json(champ.get("type", "none"),
                                             champ.get("valeur", ""))
                if actions:
                    gestes[geste] = actions
            touches.append((str(entree.get("label", ""))[:P.LABEL_MAX], gestes))
        while len(touches) < nb_touches:
            touches.append(("", {}))
        profils[str(nom)] = touches
        titres[str(nom)] = str(bloc.get("titre", nom))
        couleurs[str(nom)] = couleur_depuis_texte(bloc.get("couleur"),
                                                  couleur_usine(str(nom)))

    bloc_apps = data.get("apps") or {}
    apps = []
    for entree in bloc_apps.get("liste", []):
        exe = str(entree.get("exe", "")).strip().lower()
        if exe:
            apps.append((exe, str(entree.get("profil", "")).strip().upper(),
                         str(entree.get("abrege", ""))[:7]))
    bloc_repli = bloc_apps.get("repli") or {}
    repli = (str(bloc_repli.get("profil", P.APPS_REPLI[0])).upper(),
             str(bloc_repli.get("abrege", P.APPS_REPLI[1]))[:7])
    return profils, ordre, titres, couleurs, apps, repli


# =====================================================================
# Lecture et ecriture du fichier
# =====================================================================
def charger(nb_touches):
    """Retourne (profils, ordre, titres, couleurs, apps, repli, origine).

    origine vaut "fichier" ou "usine" : main.py s'en sert pour te dire d'ou
    viennent les macros actives.
    """
    try:
        with open(C.PROFILES_FILE) as fichier:
            data = json.load(fichier)
    except OSError:
        return defauts() + ("usine",)              # fichier absent : normal
    except Exception as exc:
        print("[store] %s illisible (%s), retour aux valeurs d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + ("usine",)

    try:
        profils, ordre, titres, couleurs, apps, repli = depuis_json(
            data, nb_touches)
    except Exception as exc:
        print("[store] %s mal forme (%s), retour aux valeurs d'usine"
              % (C.PROFILES_FILE, exc))
        return defauts() + ("usine",)

    problemes = verifier(profils, ordre, nb_touches)
    if problemes:
        print("[store] %s refuse, retour aux valeurs d'usine :" % C.PROFILES_FILE)
        for probleme in problemes:
            print("   -", probleme)
        return defauts() + ("usine",)

    return profils, ordre, titres, couleurs, apps, repli, "fichier"


def enregistrer(profils, ordre, titres, couleurs, apps, repli, nb_touches):
    """Verifie puis ecrit. Retourne (True, "") ou (False, raison)."""
    problemes = verifier(profils, ordre, nb_touches)
    if problemes:
        return False, " ; ".join(problemes)

    blocs = {}
    for nom, touches in profils.items():
        liste = []
        for label, gestes in touches:
            entree = {"label": label}
            for geste in P.GESTES:
                genre, valeur = action_vers_json((gestes or {}).get(geste))
                entree[geste] = {"type": genre, "valeur": valeur}
            liste.append(entree)
        blocs[nom] = {
            "titre": titres.get(nom, nom),
            "couleur": couleur_vers_texte(
                (couleurs or {}).get(nom) or couleur_usine(nom)),
            "touches": liste,
        }

    data = {"version": 2, "ordre": list(ordre), "profils": blocs,
            "apps": {"repli": {"profil": repli[0], "abrege": repli[1]},
                     "liste": [{"exe": e, "profil": p, "abrege": a}
                               for e, p, a in apps]}}
    try:
        # On ecrit d'abord un fichier temporaire, puis on le renomme : une
        # coupure de courant en plein enregistrement ne peut donc pas
        # laisser un profils.json a moitie ecrit.
        temporaire = C.PROFILES_FILE + ".tmp"
        with open(temporaire, "w") as fichier:
            json.dump(data, fichier)
        import os
        try:
            os.remove(C.PROFILES_FILE)
        except OSError:
            pass
        os.rename(temporaire, C.PROFILES_FILE)
    except Exception as exc:
        return False, "ecriture impossible : %s" % exc
    return True, ""


def enregistrer_json(data, nb_touches):
    """Enregistre directement une configuration recue d'une page web."""
    try:
        profils, ordre, titres, couleurs, apps, repli = depuis_json(
            data, nb_touches)
    except Exception as exc:
        return False, "donnees illisibles : %s" % exc
    return enregistrer(profils, ordre, titres, couleurs, apps, repli,
                       nb_touches)


def effacer():
    """Supprime le fichier : retour aux valeurs d'usine au prochain RESET."""
    try:
        import os
        os.remove(C.PROFILES_FILE)
        return True
    except OSError:
        return False
```

---

## device/stats.py

`120 lignes - sha256 5e43688b4770aaf3`

```python
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
```

---

## device/portal.py

`472 lignes - sha256 84f7a9d5d17496fd`

```python
# -*- coding: utf-8 -*-
"""
portal.py - Le mode configuration : point d'accès WiFi + page web.

=====================================================================
COMMENT ÇA S'UTILISE
=====================================================================
1. Maintiens **B2** pendant que tu appuies sur RESET.
2. L'écran affiche le nom du réseau, la clé WiFi et l'adresse à ouvrir.
3. Sur ton PC ou ton téléphone, connecte-toi à ce réseau WiFi.
4. Ouvre **http://192.168.4.1** dans un navigateur.
5. Modifie tes profils et tes macros, puis « Enregistrer ».
6. RESET normal : le macropad redémarre avec tes nouvelles macros.

=====================================================================
POURQUOI C'EST UN MODE SÉPARÉ, ET PAS DU WIFI EN PERMANENCE
=====================================================================
Ce boîtier tape dans ton ordinateur. Si une radio était allumée en
permanence, quelqu'un à portée pourrait y déposer des commandes qui
s'exécuteraient ensuite chez toi. Ici :

* la radio ne s'allume que si TU maintiens un bouton au démarrage ;
* dans ce mode, le clavier USB n'est même pas créé : le macropad est
  physiquement incapable de taper quoi que ce soit ;
* le réseau est protégé par une clé WPA2 affichée sur l'écran, il faut
  donc voir l'appareil pour s'y connecter.

Change quand même `AP_PASSWORD` dans config.py.

=====================================================================
CE QUE LA PAGE SAIT FAIRE, ET CE QU'ELLE NE SAIT PAS
=====================================================================
Elle gère une action par touche : une touche seule, une combinaison, un
texte, ou un texte suivi d'Entrée. C'est ce qui couvre l'immense majorité
des besoins.

Les séquences à plusieurs actions (par exemple `_ZOOM` puis `E`) restent
réservées à profiles.py : les écrire dans un formulaire deviendrait vite
illisible. Si tu en as créé une à la main et que tu enregistres depuis la
page, elle sera remplacée par sa première action.
"""

import json
import socket
import time

import config as C
import store

# La page web. Volontairement compacte : elle tient dans la RAM de la carte.
PAGE = r"""<!DOCTYPE html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Macropad</title><style>
*{box-sizing:border-box}
body{margin:0;padding:0 0 40px;background:#0e1014;color:#e8eaee;
font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:9;background:#151922;
border-bottom:1px solid #262c3a;padding:14px 18px;display:flex;
align-items:center;gap:14px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;letter-spacing:.4px}
header .tag{font:11px ui-monospace,monospace;color:#8b94a6;
border:1px solid #2b3242;border-radius:99px;padding:3px 9px}
main{max-width:940px;margin:0 auto;padding:18px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:1px;
color:#8b94a6;margin:26px 0 10px;font-weight:600}
.card{background:#151922;border:1px solid #262c3a;border-radius:12px;
padding:14px;margin-bottom:12px}
.ph{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.ph .grow{flex:1;min-width:110px}
input,select{background:#0b0d12;color:#e8eaee;border:1px solid #2b3242;
border-radius:7px;padding:7px 9px;font:13px/1.2 ui-monospace,monospace;
width:100%}
input[type=color]{width:42px;flex:0 0 42px;padding:2px;height:33px;
cursor:pointer}
input:focus,select:focus{outline:0;border-color:#3d7bfd}
table{width:100%;border-collapse:collapse}
td,th{padding:3px 5px 3px 0;vertical-align:middle}
th{font:11px system-ui;color:#6f7788;text-align:left;font-weight:600;
text-transform:uppercase;letter-spacing:.6px;padding-bottom:6px}
td.k{width:30px;color:#3d7bfd;font:700 13px ui-monospace,monospace}
td.g{width:58px;color:#6f7788;font:11px system-ui}
td.lab{width:110px}td.ty{width:132px}
tr.sep td{border-top:1px solid #1f2531;padding-top:8px}
.use{width:64px;text-align:right;font:11px ui-monospace,monospace;color:#6f7788}
.bar{height:3px;background:#3d7bfd;border-radius:2px;margin-top:3px}
button{background:#2b3242;color:#e8eaee;border:0;border-radius:8px;
padding:9px 14px;font:600 13px system-ui;cursor:pointer}
button:hover{filter:brightness(1.25)}
button.p{background:#3d7bfd;color:#fff}button.d{background:#6d2233}
button.s{padding:6px 10px;font-size:12px}
.bar2{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
#msg{margin-top:16px;padding:11px 13px;border-radius:9px;display:none;
white-space:pre-wrap;font:13px ui-monospace,monospace}
.ok{background:#0f2e20;border:1px solid #1d6f47;color:#8ee0b4}
.ko{background:#33131d;border:1px solid #7d2a3c;color:#f0a6b6}
.hint{color:#6f7788;font-size:12px;margin:0 0 14px}
.vide{text-align:center;padding:26px 14px}
.vide b{display:block;font-size:15px;margin-bottom:8px;color:#e8eaee}
.vide p{color:#8b94a6;margin:5px 0;font-size:13px}
</style></head><body>
<header>
<h1>Macropad</h1>
<span class=tag id=src>...</span>
<span class=tag id=cnt>...</span>
</header>
<main>
<p class=hint>Libelles : 6 caracteres maximum. Combinaison :
<b>CTRL+MAJ+ESC</b>. Chaque touche accepte trois gestes : appui court,
appui long et double appui.</p>
<p class=hint>Le carre de couleur a cote du titre donne la couleur des
LED RGB de ce profil. Comme le PC change de profil selon le logiciel au
premier plan, <b>le macropad prend la couleur du logiciel</b> ou tu
travailles, en respiration douce.</p>
<p class=hint><b>maintenir</b> transforme la touche en vraie touche
modificatrice : mets <b>CTRL</b> sur l'appui court et <b>MAJ</b> sur le
double appui, et tu obtiens <i>appui maintenu = Ctrl</i>,
<i>appui bref puis maintenu = Maj</i>. Le modificateur reste enfonce tant
que ton doigt reste sur la touche, ce qui permet de cliquer a la souris
pendant ce temps.</p>

<h2>Profils et macros</h2>
<div id=profs></div>
<div class=bar2><button class=s onclick=addProfil()>+ Profil</button></div>

<h2>Logiciels detectes</h2>
<p class=hint>Le compagnon PC lit cette table sur le macropad. Le nom
abrege reste affiche a gauche de l'ecran pendant que le nom du fichier
defile.</p>
<div class=card id=apps></div>

<div class=bar2>
<button class=p onclick=save()>Enregistrer</button>
<button onclick=dl()>Telecharger la sauvegarde</button>
<button class=d onclick=usine()>Valeurs d'usine</button>
</div>
<div id=msg></div>
</main>
<script>
var D={ordre:[],profils:{},apps:{repli:{profil:"WINDOWS",abrege:"Win"},liste:[]}};
var N=6,GESTES=["court","long","double"];
var LIB={court:"court",long:"long",double:"double"};
var TYPES=[["none","inactive"],["key","touche"],["combo","combinaison"],
["maintien","maintenir (Ctrl, Maj...)"],
["text","texte"],["text_enter","texte + Entree"]];

function el(tag,attrs,kids){var e=document.createElement(tag);
 for(var k in attrs||{}){if(k=="cls")e.className=attrs[k];
  else if(k.slice(0,2)=="on")e[k]=attrs[k];else e.setAttribute(k,attrs[k]);}
 (kids||[]).forEach(function(c){
  e.appendChild(typeof c=="string"?document.createTextNode(c):c);});
 return e;}
// fin=true : on previent quand tu QUITTES le champ, pas a chaque
// frappe. Indispensable pour le nom d'un profil, qui redessine la page.
// Le selecteur de couleur du navigateur : c'est lui qui pilote la
// couleur des LED RGB du profil. Il rend une valeur du genre "#00a0ff".
function col(val,cb){var i=el("input",{type:"color"});
 i.value=val||"#808080";i.title="couleur des LED de ce profil";
 i.oninput=function(){cb(i.value);};return i;}

function inp(val,max,cb,fin){var i=el("input");i.value=val||"";
 if(max)i.maxLength=max;
 if(fin)i.onchange=function(){cb(i.value);};
 else i.oninput=function(){cb(i.value);};
 return i;}
function sel(val,cb){var s=el("select");TYPES.forEach(function(t){
 var o=el("option",{value:t[0]},[t[1]]);if(t[0]==val)o.selected=true;
 s.appendChild(o);});s.onchange=function(){cb(s.value);render();};return s;}

function maxUse(){var m=1;for(var n in D.profils)
 (D.profils[n].touches||[]).forEach(function(t){if(t.usages>m)m=t.usages;});
 return m;}

function vide(){
 var c=el("div",{cls:"card vide"},[]);
 c.appendChild(el("b",{},["Aucun profil recu du macropad."]));
 if(D.origine=="simulation"){
  c.appendChild(el("p",{},["Le compagnon tourne en mode --simuler : il "+
   "n'est relie a aucune carte."]));
  c.appendChild(el("p",{},["Relance-le sans --simuler, macropad branche."]));
 }else{
  c.appendChild(el("p",{},["Verifie qu'il est branche sur son port USB "+
   "NATIF, et que Thonny n'occupe pas ce port."]));
  c.appendChild(el("p",{},["La console du compagnon dit ce qu'elle voit ; "+
   "avec --journal, tout est dans macropad_auto.log."]));
 }
 c.appendChild(el("p",{},["Tu peux aussi partir des valeurs d'usine avec le "+
  "bouton rouge, ou ajouter un profil ci-dessous."]));
 return c;}

// Une fonction a part, et ce n'est pas cosmetique : en JavaScript,
// « var » appartient a la FONCTION, pas au bloc. Ecrite dans la boucle,
// la variable k etait la MEME pour les six touches, si bien que tous les
// champs finissaient par ecrire dans la derniere. Ici chaque appel a sa
// propre variable k : chaque champ modifie bien sa touche.
function ligne(p,i,tb,mx){
 if(!p.touches[i])p.touches[i]={label:"",usages:0};
 var k=p.touches[i];
 GESTES.forEach(function(g,gi){
  if(!k[g])k[g]={type:"none",valeur:""};
  var tr=el("tr",{cls:gi==0?"sep":""},[]);
  if(gi==0)tr.appendChild(el("td",{cls:"k",rowspan:3},["B"+(i+1)]));
  tr.appendChild(el("td",{cls:"g"},[LIB[g]]));
  if(gi==0){
   var cl=el("td",{cls:"lab",rowspan:3},[]);
   cl.appendChild(inp(k.label,6,function(v){k.label=v;}));
   tr.appendChild(cl);
  }
  var ct=el("td",{cls:"ty"},[]);
  ct.appendChild(sel(k[g].type,function(v){k[g].type=v;}));
  tr.appendChild(ct);
  var cv=el("td",{},[]);
  cv.appendChild(inp(k[g].valeur,60,function(v){k[g].valeur=v;}));
  tr.appendChild(cv);
  if(gi==0){
   var u=k.usages||0;
   var box=el("td",{cls:"use",rowspan:3},[String(u)]);
   var b=el("div",{cls:"bar"});b.style.width=Math.round(60*u/mx)+"px";
   box.appendChild(b);tr.appendChild(box);
  }
  tb.appendChild(tr);
 });
}

function render(){
 var zone=document.getElementById("profs");zone.innerHTML="";
 var mx=maxUse();
 if(!D.ordre.length){zone.appendChild(vide());renderApps();return;}
 D.ordre.forEach(function(nom){
  var p=D.profils[nom];if(!p)return;
  var head=el("div",{cls:"ph"},[]);
  head.appendChild(inp(nom,20,function(v){ren(nom,v);},true));
  head.firstChild.className="grow";head.firstChild.title="nom interne";
  var t=inp(p.titre,16,function(v){p.titre=v;});t.className="grow";
  t.title="titre affiche sur l'ecran";head.appendChild(t);
  head.appendChild(col(p.couleur,function(v){p.couleur=v;}));
  head.appendChild(el("button",{cls:"d s",onclick:function(){del(nom);}},
   ["Supprimer"]));
  var tb=el("table",{},[el("tr",{},[el("th",{},["#"]),el("th",{},["Geste"]),
   el("th",{},["Libelle"]),el("th",{},["Type"]),el("th",{},["Valeur"]),
   el("th",{},["Usage"])])]);
  for(var i=0;i<N;i++)ligne(p,i,tb,mx);
  zone.appendChild(el("div",{cls:"card"},[head,tb]));
 });
 renderApps();
}

function renderApps(){
 var z=document.getElementById("apps");z.innerHTML="";
 var tb=el("table",{},[el("tr",{},[el("th",{},["Programme (.exe)"]),
  el("th",{},["Profil"]),el("th",{},["Abrege ecran"]),el("th",{},[""])])]);
 D.apps.liste.forEach(function(a,i){
  var tr=el("tr",{},[]);
  var c1=el("td",{},[]);c1.appendChild(inp(a.exe,40,function(v){a.exe=v;}));
  var c2=el("td",{},[]);c2.appendChild(inp(a.profil,20,function(v){a.profil=v;}));
  var c3=el("td",{},[]);c3.appendChild(inp(a.abrege,7,function(v){a.abrege=v;}));
  var c4=el("td",{cls:"use"},[el("button",{cls:"d s",onclick:function(){
   D.apps.liste.splice(i,1);renderApps();}},["x"])]);
  tr.appendChild(c1);tr.appendChild(c2);tr.appendChild(c3);tr.appendChild(c4);
  tb.appendChild(tr);
 });
 var tr=el("tr",{cls:"sep"},[]);
 tr.appendChild(el("td",{},["tout le reste"]));
 var r1=el("td",{},[]);r1.appendChild(inp(D.apps.repli.profil,20,
  function(v){D.apps.repli.profil=v;}));
 var r2=el("td",{},[]);r2.appendChild(inp(D.apps.repli.abrege,7,
  function(v){D.apps.repli.abrege=v;}));
 tr.appendChild(r1);tr.appendChild(r2);tr.appendChild(el("td",{},[]));
 tb.appendChild(tr);
 z.appendChild(tb);
 z.appendChild(el("div",{cls:"bar2"},[el("button",{cls:"s",onclick:function(){
  D.apps.liste.push({exe:"",profil:D.ordre[0]||"",abrege:""});renderApps();}},
  ["+ Logiciel"])]));
}

function ren(anc,nv){nv=(nv||"").trim();if(!nv||D.profils[nv])return;
 D.profils[nv]=D.profils[anc];delete D.profils[anc];
 D.ordre=D.ordre.map(function(x){return x==anc?nv:x});render();}
function del(n){if(D.ordre.length<2)return say("Il faut au moins un profil",0);
 delete D.profils[n];D.ordre=D.ordre.filter(function(x){return x!=n});render();}
function addProfil(){var n="PROFIL",i=1;while(D.profils[n])n="PROFIL"+(++i);
 var t=[];for(var k=0;k<N;k++)t.push({label:"",usages:0});
 D.profils[n]={titre:n,couleur:"#808080",touches:t};
 D.ordre.push(n);render();}
function say(t,ok){var m=document.getElementById("msg");
 m.textContent=t;m.className=ok?"ok":"ko";m.style.display="block";
 window.scrollTo(0,document.body.scrollHeight);}
function dl(){var a=document.createElement("a");
 a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,2)],
  {type:"application/json"}));
 a.download="macropad_config.json";a.click();}
function usine(){if(!confirm("Revenir aux valeurs d'usine ?"))return;
 fetch("/api/usine",{method:"POST"}).then(function(){location.reload();});}
function save(){fetch("/api/profils",{method:"POST",
 body:JSON.stringify(D)}).then(function(r){return r.json();})
 .then(function(r){say(r.ok?"Enregistre et applique.":"Refuse :\n"+r.raison,
  r.ok);if(r.ok)charger();})
 .catch(function(e){say("Erreur : "+e,0);});}
function charger(){fetch("/api/profils").then(function(r){return r.json();})
 .then(function(d){
  if(d.erreur)return say("Lecture impossible : "+d.erreur,0);
  D=d;N=d.touches||6;if(!D.apps)D.apps={repli:{profil:"WINDOWS",abrege:"Win"},
   liste:[]};
  document.getElementById("src").textContent="source : "+(d.origine||"?");
  var tot=0;for(var n in D.profils)(D.profils[n].touches||[]).forEach(
   function(t){tot+=t.usages||0;});
  document.getElementById("cnt").textContent=tot+" appuis comptes";
  render();}).catch(function(e){say("Erreur : "+e,0);});}
charger();
</script></body></html>
"""


# =====================================================================
# Point d'accès WiFi
# =====================================================================
def demarrer_ap():
    """Allume le réseau WiFi du macropad. Retourne (ssid, cle, adresse)."""
    import network
    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    if len(C.AP_PASSWORD) < 8:
        print("[portal] ATTENTION : AP_PASSWORD fait moins de 8 caracteres,")
        print("[portal] le WiFi risque de refuser de demarrer.")

    reglages = {"essid": C.AP_SSID, "password": C.AP_PASSWORD,
                "channel": C.AP_CHANNEL}
    try:
        # WPA2 explicite. Le nom de la constante a varié selon les versions,
        # d'où le getattr avec une valeur de repli.
        reglages["authmode"] = getattr(network, "AUTH_WPA_WPA2_PSK", 4)
        ap.config(**reglages)
    except Exception:
        del reglages["authmode"]
        ap.config(**reglages)

    attente = 0
    while not ap.active() and attente < 5000:
        time.sleep_ms(100)
        attente += 100
    adresse = ap.ifconfig()[0]
    print("[portal] reseau '%s' actif, page sur http://%s" % (C.AP_SSID, adresse))
    return C.AP_SSID, C.AP_PASSWORD, adresse


def arreter_ap():
    try:
        import network
        network.WLAN(network.AP_IF).active(False)
    except Exception:
        pass


# =====================================================================
# Serveur web minimal
# =====================================================================
class Portail:

    def __init__(self, nb_touches, stats=None):
        self.nb_touches = nb_touches
        self.stats = stats
        self.serveur = None
        self.clients = 0

    def ouvrir(self):
        adresse = socket.getaddrinfo("0.0.0.0", C.AP_PORT)[0][-1]
        self.serveur = socket.socket()
        self.serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serveur.bind(adresse)
        self.serveur.listen(2)
        # Court délai d'attente : on rend la main régulièrement pour que la
        # LED continue de respirer même sans visiteur.
        self.serveur.settimeout(0.25)

    def fermer(self):
        if self.serveur:
            try:
                self.serveur.close()
            except Exception:
                pass
            self.serveur = None

    # ------------------------------------------------------------------
    def _etat_json(self):
        return store.vers_json(self.nb_touches, self.stats)

    def _enregistrer(self, data):
        return store.enregistrer_json(data, self.nb_touches)

    # ------------------------------------------------------------------
    def _repondre(self, client, corps, type_mime="text/html", code="200 OK"):
        entete = ("HTTP/1.0 %s\r\nContent-Type: %s; charset=utf-8\r\n"
                  "Cache-Control: no-store\r\nConnection: close\r\n\r\n"
                  % (code, type_mime))
        client.write(entete.encode())
        if isinstance(corps, str):
            corps = corps.encode()
        # Envoi par morceaux : la page fait plusieurs kilo-octets et la pile
        # réseau de l'ESP32 n'avale pas tout d'un coup.
        for debut in range(0, len(corps), 512):
            client.write(corps[debut:debut + 512])

    def _traiter(self, client):
        ligne = client.readline()
        if not ligne:
            return
        try:
            methode, chemin, _ = ligne.decode().split(" ", 2)
        except ValueError:
            return

        taille = 0
        while True:
            entete = client.readline()
            if not entete or entete in (b"\r\n", b"\n"):
                break
            bas = entete.decode().lower()
            if bas.startswith("content-length:"):
                try:
                    taille = int(bas.split(":", 1)[1].strip())
                except ValueError:
                    taille = 0

        corps = client.read(taille) if taille else b""

        if chemin.startswith("/api/profils"):
            if methode == "POST":
                try:
                    data = json.loads(corps)
                except Exception as exc:
                    self._repondre(client,
                                   json.dumps({"ok": False,
                                               "raison": "JSON invalide : %s" % exc}),
                                   "application/json")
                    return
                ok, raison = self._enregistrer(data)
                print("[portal] enregistrement :", "OK" if ok else raison)
                self._repondre(client, json.dumps({"ok": ok, "raison": raison}),
                               "application/json")
            else:
                self._repondre(client, json.dumps(self._etat_json()),
                               "application/json")
        elif chemin.startswith("/api/usine") and methode == "POST":
            store.effacer()
            print("[portal] retour aux profils d'usine")
            self._repondre(client, json.dumps({"ok": True}), "application/json")
        elif chemin == "/" or chemin.startswith("/index"):
            self._repondre(client, PAGE)
        else:
            self._repondre(client, "introuvable", "text/plain", "404 Not Found")

    # ------------------------------------------------------------------
    def service(self):
        """Traite au plus un visiteur. Ne bloque jamais plus de 0,25 s."""
        if not self.serveur:
            return False
        try:
            client, _ = self.serveur.accept()
        except OSError:
            return False        # personne pour l'instant, c'est normal
        self.clients += 1
        try:
            client.settimeout(3)
            self._traiter(client)
        except Exception as exc:
            print("[portal] client abandonne :", exc)
        finally:
            try:
                client.close()
            except Exception:
                pass
        return True
```

---

## device/link.py

`230 lignes - sha256 7f3d5d937ddfcfb6`

```python
# -*- coding: utf-8 -*-
"""
link.py - Le dialogue avec le PC par le port serie USB.

=====================================================================
A QUOI CA SERT
=====================================================================
Ton macropad expose DEUX choses sur le meme cable USB :

  * un clavier HID, qui tape dans la fenetre active ;
  * un port serie (celui du REPL), jusqu'ici inutilise par le firmware.

Ce module se sert de ce second canal pour parler avec un petit programme
qui tourne sur le PC (tools/macropad_auto.py). Ce programme :

  * regarde quelle application est au premier plan et le dit au macropad,
    qui change alors de profil tout seul ;
  * envoie le nom du document ouvert, que l'ecran affiche ;
  * sert une page de configuration sur http://127.0.0.1:8765, et transmet
    tes modifications au macropad, qui les applique SANS redemarrer.

=====================================================================
POURQUOI LA LECTURE NE BLOQUE JAMAIS
=====================================================================
Lire une ligne sur un port serie, normalement, ca attend. Si on faisait
cela dans la boucle principale, le macropad se figerait des que le PC ne
dit rien - c'est-a-dire tout le temps.

On utilise donc select.poll() qui repond "y a-t-il un caractere pret ?"
sans jamais attendre, et on lit caractere par caractere. Deux precautions :

  * on lit AU PLUS 256 caracteres par tour de boucle, pour qu'un gros
    envoi de configuration (2 a 3 ko) s'etale sur quelques tours au lieu
    de bloquer les touches pendant 40 ms ;
  * on ne se sert jamais de readline(), qui attendrait le passage a la
    ligne meme si le message est incomplet.

=====================================================================
LE PROTOCOLE, EN CLAIR
=====================================================================
Une commande par ligne. Du PC vers le macropad :

  P:CIVIL3D          le logiciel actif correspond a ce profil
  T:Projet_A12.dwg   nom du document a afficher (vide = efface)
  ?VER               demande l'etat du macropad
  ?CFG               demande la configuration complete
  !CFGBEGIN          debut d'un envoi de configuration
  !C:<morceau>       un morceau de JSON (on decoupe pour ne pas saturer)
  !CFGEND            fin de l'envoi : on verifie, on enregistre, on applique
  !RELOAD            relire profils.json sans redemarrer

Du macropad vers le PC, toujours prefixe par # pour que le script les
distingue des messages de debogage ordinaires :

  #VER:...  #CFGBEGIN  #C:<morceau>  #CFGEND  #OK:...  #KO:<raison>

Aucun caractere de controle n'est utilise : Ctrl-C continue donc
d'interrompre le programme normalement, tu ne perds pas cette porte de
sortie.
"""

import json

import config as C
import store

# Evenements rendus a main.py
EVT_PROFIL = "profil"        # le PC demande un profil
EVT_DOCUMENT = "document"    # nom du document a afficher
EVT_RECHARGER = "recharger"  # la configuration a change, il faut la relire

_MAX_PAR_TOUR = 256          # caracteres lus au maximum par tour de boucle
_MAX_LIGNE = 512             # au-dela, la ligne est jetee (protection RAM)
_MAX_CONFIG = 8192           # taille maximale d'une configuration recue
_TAILLE_MORCEAU = 180        # taille des morceaux envoyes au PC


class SourceStdin:
    """Lecture non bloquante du port serie (le REPL) sous MicroPython."""

    def __init__(self):
        import select
        import sys
        self._sys = sys
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)

    def lire(self, maximum):
        morceaux = []
        while len(morceaux) < maximum and self._poll.poll(0):
            caractere = self._sys.stdin.read(1)
            if not caractere:
                break
            morceaux.append(caractere)
        return "".join(morceaux)


class Link:
    """Analyse les lignes venant du PC et repond."""

    def __init__(self, nb_touches, source=None, sortie=None, stats=None):
        self.nb_touches = nb_touches
        self.stats = stats            # pour joindre les compteurs d'usage
        self.actif = False
        self.source = source
        self.sortie = sortie or print
        self._tampon = ""        # ligne en cours de reception
        self._config = None      # configuration en cours de reception
        self.dernier_profil = None
        self.document = ""

        if self.source is None:
            try:
                self.source = SourceStdin()
            except Exception as exc:
                print("[link] port serie indisponible :", exc)
                return
        self.actif = True

    # ------------------------------------------------------------------
    def service(self):
        """A appeler a chaque tour de boucle. Retourne une liste d'evenements."""
        if not self.actif:
            return ()
        try:
            recu = self.source.lire(_MAX_PAR_TOUR)
        except Exception as exc:
            print("[link] lecture impossible :", exc)
            self.actif = False
            return ()
        if not recu:
            return ()

        evenements = []
        for caractere in recu:
            if caractere == "\n":
                ligne, self._tampon = self._tampon, ""
                evenement = self._traiter(ligne.strip())
                if evenement:
                    evenements.append(evenement)
            elif caractere != "\r":
                if len(self._tampon) < _MAX_LIGNE:
                    self._tampon += caractere
                else:
                    self._tampon = ""     # ligne aberrante : on la jette
        return evenements

    # ------------------------------------------------------------------
    def _traiter(self, ligne):
        if not ligne:
            return None

        if ligne.startswith("P:"):
            self.dernier_profil = ligne[2:].strip().upper()
            return (EVT_PROFIL, self.dernier_profil)

        if ligne.startswith("T:"):
            self.document = ligne[2:].strip()
            return (EVT_DOCUMENT, self.document)

        if ligne == "?VER":
            self.sortie("#VER:macropad %d touches, layout %s"
                        % (self.nb_touches, C.KEYBOARD_LAYOUT))
            return None

        if ligne == "?CFG":
            self._envoyer_config()
            return None

        if ligne == "!CFGBEGIN":
            self._config = []
            return None

        if ligne.startswith("!C:"):
            if self._config is not None:
                morceau = ligne[3:]
                total = sum(len(m) for m in self._config)
                if total + len(morceau) <= _MAX_CONFIG:
                    self._config.append(morceau)
                else:
                    self._config = None
                    self.sortie("#KO:configuration trop volumineuse")
            return None

        if ligne == "!CFGEND":
            return self._recevoir_config()

        if ligne == "!RELOAD":
            self.sortie("#OK:rechargement")
            return (EVT_RECHARGER, None)

        return None

    # ------------------------------------------------------------------
    def _envoyer_config(self):
        """Envoie la configuration au PC, decoupee en morceaux."""
        try:
            texte = json.dumps(store.vers_json(self.nb_touches, self.stats))
        except Exception as exc:
            self.sortie("#KO:lecture impossible : %s" % exc)
            return

        self.sortie("#CFGBEGIN")
        for debut in range(0, len(texte), _TAILLE_MORCEAU):
            self.sortie("#C:" + texte[debut:debut + _TAILLE_MORCEAU])
        self.sortie("#CFGEND")

    def _recevoir_config(self):
        """Verifie et enregistre la configuration recue du PC."""
        if self._config is None:
            self.sortie("#KO:aucun envoi en cours")
            return None
        texte = "".join(self._config)
        self._config = None

        try:
            data = json.loads(texte)
        except Exception as exc:
            self.sortie("#KO:JSON invalide : %s" % exc)
            return None

        # store refuse toute macro qui ne serait pas tapable : impossible
        # d'enregistrer depuis le PC une configuration qui planterait au
        # demarrage suivant.
        ok, raison = store.enregistrer_json(data, self.nb_touches)
        if ok:
            self.sortie("#OK:configuration enregistree")
            return (EVT_RECHARGER, None)
        self.sortie("#KO:" + raison)
        return None
```

---

## device/hid_keyboard.py

`393 lignes - sha256 10aa759f9f53fa01`

```python
# -*- coding: utf-8 -*-
"""
hid_keyboard.py - Le clavier USB proprement dit.

=====================================================================
CE QUE FAIT CE FICHIER, EN LANGAGE SIMPLE
=====================================================================

Il s'appuie sur la bibliothèque OFFICIELLE de MicroPython, recopiée telle
quelle dans device/lib/usb/device/ (licence MIT, auteur Angus Gratton).
Nous ne réécrivons pas l'USB : nous l'utilisons.

Son travail à lui, c'est de transformer

    "appuie sur Ctrl+Z"        (ce que dit profiles.py)

en une suite de RAPPORTS USB, c'est-à-dire des petits paquets de 8 octets
envoyés à Windows :

    paquet 1 : Ctrl enfoncé + touche Z enfoncée
    paquet 2 : plus rien d'enfoncé          <-- INDISPENSABLE

Le paquet 2 s'appelle le "relâchement". S'il n'est pas envoyé, Windows croit
que tu tiens Ctrl appuyé pour toujours : tes clics deviennent des sélections
multiples, ta souris zoome au lieu de défiler... C'est LA panne classique
d'un clavier programmable. Ce fichier garantit qu'un relâchement suit
toujours un appui, y compris quand une erreur se produit.

=====================================================================
POURQUOI CE CODE N'ATTEND JAMAIS
=====================================================================

Écrire "_ISOLATEOBJECTS" demande 32 paquets USB espacés d'environ 24 ms,
soit près de 400 ms au total. Si on faisait cela avec des sleep(), pendant
400 ms le macropad serait sourd : l'écran figé, le bouton ESC inopérant.

Alors on découpe. La méthode tick() est appelée en boucle par main.py et
n'envoie qu'UN paquet, celui qui est dû à cet instant, puis rend la main.
C'est ce qu'on appelle une machine à états : la variable self.phase se
souvient où on en est ("press" = il faut appuyer, "release" = il faut
relâcher).

=====================================================================
VOCABULAIRE DES VARIABLES
=====================================================================
  queue           : les macros en attente
  current         : la macro en cours, déjà traduite en frappes
  position        : où on en est dans current
  phase           : "idle" (rien à faire), "press" ou "release"
  due             : l'instant avant lequel il ne faut rien envoyer
  progress        : dernier instant où quelque chose a réellement avancé
                    (sert à détecter un blocage)
  release_needed  : il faut envoyer un paquet "plus rien d'enfoncé"
  keys_down       : vrai si le dernier paquet envoyé tenait des touches
  fault           : une panne grave est survenue, on n'envoie plus rien
"""

from time import ticks_ms, ticks_diff, ticks_add, sleep_ms
import config as C
from layouts import compile_actions


class HIDKeyboard:

    def __init__(self, interface):
        self.interface = interface     # l'objet clavier de la bibliothèque officielle
        self.queue = []
        self.current = []
        self.position = 0
        self.phase = "idle"
        self.due = ticks_ms()
        self.progress = self.due
        self.opened = False            # Windows a-t-il configuré le clavier ?
        self.release_needed = True     # par sécurité on commence par tout relâcher
        self.keys_down = False         # des touches sont-elles enfoncées côté PC ?
        # Touches MAINTENUES : elles sont ajoutées à chaque rapport envoyé,
        # tant que tu gardes le doigt sur la touche du macropad. C'est ce
        # qui permet à une touche du pad de se comporter comme la touche
        # Ctrl d'un vrai clavier : Ctrl reste enfoncé pendant que tu
        # cliques à la souris.
        self.tenus = ()
        self.fault = False

    # ------------------------------------------------------------------
    # Etats
    # ------------------------------------------------------------------
    def accepting(self):
        """Peut-on accepter une nouvelle macro ?

        Il suffit que Windows ait ouvert l'interface et qu'aucune panne ne
        soit déclarée. On n'exige PAS que le relâchement en attente soit
        déjà parti : sinon une touche pressée juste après un changement de
        profil ou après ESC serait perdue (c'était un défaut de la version
        précédente, la macro disparaissait sans explication).
        """
        return self.opened and not self.fault

    def ready(self):
        """Vrai quand le clavier est ouvert ET au repos complet."""
        return self.opened and not self.release_needed and not self.fault

    def idle(self):
        return self.phase == "idle" and not self.queue and not self.release_needed

    # ------------------------------------------------------------------
    # Entrée des macros
    # ------------------------------------------------------------------
    def submit(self, actions):
        """Met une macro en file d'attente. Ne tape rien tout de suite."""
        if not self.accepting():
            print("HID : action ignoree, interface non prete")
            return False
        # On traduit la macro TOUT DE SUITE, uniquement pour la vérifier.
        # Si un caractère est impossible, l'erreur remonte ici et rien n'a
        # encore été tapé. Mieux vaut ne rien écrire qu'écrire à moitié.
        compile_actions(actions, C.KEYBOARD_LAYOUT)
        if len(self.queue) >= C.MACRO_QUEUE_LIMIT:
            # On refuse plutôt que d'empiler : sinon un appui nerveux sur
            # une touche déclencherait dix commandes une minute plus tard.
            print("HID : file pleine, action ignoree")
            return False
        self.queue.append(actions)
        return True

    def maintenir(self, actions):
        """Enfonce des touches et les GARDE enfoncées (Ctrl, Maj...).

        Rien n'est tapé : les touches sont simplement ajoutées à tous les
        rapports suivants, jusqu'à relacher_maintien(). Le relâchement est
        prioritaire dans tick(), donc Ctrl descend en deux ou trois
        millisecondes : à l'échelle d'un doigt, c'est instantané.
        """
        if not self.accepting():
            print("HID : maintien ignore, interface non prete")
            return False
        # Traduit tout de suite pour verifier, comme submit().
        frappes = compile_actions(actions, C.KEYBOARD_LAYOUT)
        codes = ()
        for frappe in frappes:
            codes += frappe
        self.tenus = codes
        self.release_needed = True     # provoque l'envoi de l'etat courant
        self.progress = ticks_ms()
        return True

    def relacher_maintien(self):
        """Relâche les touches maintenues. Sans effet s'il n'y en a pas."""
        if not self.tenus:
            return
        self.tenus = ()
        self.release_needed = True
        self.progress = ticks_ms()

    def cancel(self):
        """Oublie tout ce qui était prévu et programme un relâchement."""
        self.queue = []
        self.current = []
        self.phase = "idle"
        # Un ESC, un changement de profil ou une panne doivent TOUT
        # relâcher, y compris un Ctrl resté enfoncé. Sinon le PC garde un
        # modificateur bloqué, ce qui est la pire panne possible.
        self.tenus = ()
        self.release_needed = True
        # INDISPENSABLE : le relâchement qu'on vient de programmer est une
        # NOUVELLE action, le chronomètre du garde-fou doit repartir de zéro.
        #
        # Sans cette ligne, self.progress gardait la date de la dernière
        # frappe. Un changement de profil survenant après quelques secondes
        # de repos déclenchait donc instantanément « transfert sans
        # progression » et bloquait le clavier jusqu'au RESET, alors que
        # rien n'était en panne. Panne constatée sur le matériel.
        self.progress = ticks_ms()

    def escape(self, now):
        """Bouton ESC : priorité absolue.

        On jette ce qui était en cours (une commande Civil 3D à moitié
        tapée, par exemple), on relâche tout, puis on envoie Échap.
        C'est le comportement attendu d'une touche d'annulation.
        """
        self.cancel()
        self.due = now              # autorise un envoi dès le prochain tick
        self.progress = now
        if self.opened and not self.fault:
            self.queue.append([("key", "ESC")])

    # ------------------------------------------------------------------
    # Envoi bas niveau
    # ------------------------------------------------------------------
    def _send(self, keys):
        """Envoie un paquet, ou renonce immédiatement si l'USB est occupé.

        timeout_ms=0 veut dire « n'attends pas ». La bibliothèque rend la
        main tout de suite si le précédent paquet n'est pas encore parti ;
        on réessaiera au tour de boucle suivant. C'est ce qui garantit que
        le macropad ne se fige jamais.
        """
        if self.interface.busy():
            return False
        paquet = self._avec_tenus(keys)
        if not self.interface.send_keys(paquet, timeout_ms=0):
            return False
        # On mémorise si ce paquet laissait des touches enfoncées.
        self.keys_down = bool(paquet)
        return True

    def _avec_tenus(self, keys):
        """Ajoute les touches maintenues au paquet, sans doublon.

        Un rapport HID ne transporte que six touches ordinaires (les
        modificateurs, eux, sont des bits et ne comptent pas). Si le
        maintien et la macro en demandent davantage, on garde les
        maintenues : ce sont elles que le doigt réclame.
        """
        if not self.tenus:
            return keys
        paquet = tuple(self.tenus)
        ordinaires = sum(1 for code in paquet if code >= 0)
        for code in keys:
            if code in paquet:
                continue
            if code >= 0:
                if ordinaires >= 6:
                    continue
                ordinaires += 1
            paquet += (code,)
        return paquet

    def _fail(self, error):
        if not self.fault:
            print("ERREUR CRITIQUE HID :", error, "- macros arretees, RESET requis")
        self.fault = True
        self.cancel()

    # ------------------------------------------------------------------
    # Le coeur : appelé à chaque tour de la boucle principale
    # ------------------------------------------------------------------
    def tick(self, now):
        try:
            opened = self.interface.is_open()

            if not opened:
                # Câble débranché, PC en veille, ou Windows a réinitialisé
                # le port. On jette la file : hors de question qu'une macro
                # reparte toute seule au rebranchement.
                if self.opened:
                    print("HID : deconnexion/reset USB, file annulee")
                self.opened = False
                self.keys_down = False   # le PC a de toute façon tout oublié
                self.cancel()
                self.progress = now
                return

            if not self.opened:
                print("HID : interface ouverte par Windows")
                self.opened = True
                self.progress = now
                if self.fault:
                    # L'hôte vient de reconfigurer le périphérique : il a
                    # forcément oublié toute touche restée enfoncée. On peut
                    # donc repartir d'un état sain, plutôt que d'exiger un
                    # RESET matériel pour un incident déjà passé.
                    print("HID : reconnexion USB, reprise apres panne")
                    self.fault = False

            # Garde-fou : si plus rien n'avance alors qu'on a du travail,
            # c'est que l'USB est bloqué. On arrête tout plutôt que de
            # laisser une touche enfoncée indéfiniment.
            if (ticks_diff(now, self.progress) > C.HID_TIMEOUT_MS
                    and (self.release_needed or self.phase != "idle")):
                self._fail("transfert sans progression")

            # Priorité n° 1 : relâcher.
            if self.release_needed:
                if self._send(()):
                    self.release_needed = False
                    self.progress = now
                return

            if self.fault or ticks_diff(now, self.due) < 0:
                return

            # Priorité n° 2 : démarrer la macro suivante.
            if self.phase == "idle":
                if not self.queue:
                    return
                actions = self.queue.pop(0)
                # Windows nous dit si Verr. Maj est allumé (voyant du clavier).
                # On en tient compte au moment de traduire (voir layouts.py).
                caps = bool(getattr(self.interface, "led_mask", 0) & 2)
                self.current = compile_actions(actions, C.KEYBOARD_LAYOUT, caps)
                self.position = 0
                self.progress = now
                self.phase = "press"

            # Priorité n° 3 : dérouler la macro, une frappe par tick.
            if self.phase == "press":
                if self.position >= len(self.current):
                    self.phase = "idle"      # macro terminée
                    return
                if self._send(self.current[self.position]):
                    self.phase = "release"
                    self.due = ticks_add(now, C.KEY_HOLD_MS)
                    self.progress = now
            elif self.phase == "release":
                if self._send(()):
                    self.position += 1
                    self.phase = "press"
                    self.due = ticks_add(now, C.KEY_GAP_MS)
                    self.progress = now

        except Exception as exc:
            # Aucune exception ne doit remonter jusqu'à la boucle principale.
            self._fail(exc)

    # ------------------------------------------------------------------
    # Arrêt
    # ------------------------------------------------------------------
    def close(self):
        """Appelé quand main.py s'arrête (Ctrl-C dans Thonny, ou erreur).

        Objectif : ne JAMAIS laisser Ctrl, Alt, Maj ou Windows enfoncés
        côté PC. On dispose de 150 ms pour envoyer le paquet de relâchement.
        """
        self.cancel()

        if not self.keys_down:
            # Rien n'était enfoncé : il n'y a rien à réparer, on s'arrête
            # proprement sans toucher à l'USB. Le REPL de Thonny reste
            # disponible. (La version précédente coupait l'USB dans tous les
            # cas, ce qui faisait disparaître le port COM sans raison.)
            return

        start = ticks_ms()
        try:
            while ticks_diff(ticks_ms(), start) < 150:
                if self.interface.is_open() and self._send(()):
                    while (self.interface.busy()
                           and ticks_diff(ticks_ms(), start) < 150):
                        sleep_ms(1)
                    if not self.interface.busy():
                        return       # relâchement confirmé, tout va bien
                sleep_ms(1)
        except Exception as exc:
            print("HID : liberation finale echouee", exc)

        # Dernier recours : impossible de relâcher, et des touches restent
        # enfoncées côté PC. On débranche logiquement le clavier : pour
        # Windows le périphérique disparaît, donc les touches aussi.
        # Effet de bord assumé : le port COM du REPL natif disparaît aussi,
        # un RESET matériel le fait revenir.
        print("HID : touches encore enfoncees, deconnexion USB de securite")
        print("HID : appuyer sur RESET pour recuperer le port")
        import usb.device
        usb.device.get().active(False)


def create_interface():
    """Crée le clavier USB et le déclare à Windows.

    Appelé UNE SEULE FOIS depuis boot.py. À cet instant Windows découvre un
    nouveau périphérique : le port COM du REPL natif se ferme et se rouvre.
    C'est normal, ce n'est pas une panne.

    builtin_driver=True demande à MicroPython de GARDER le port série CDC
    en plus du clavier. Sans lui, on perdrait le REPL sur le port natif.
    """
    import machine
    if not hasattr(machine, "USBDevice"):
        raise RuntimeError(
            "machine.USBDevice absent : utiliser MicroPython >= 1.27 "
            "ESP32_GENERIC_S3 SPIRAM octale")
    import usb.device
    from usb.device.keyboard import KeyboardInterface

    class KeyboardWithLEDs(KeyboardInterface):
        """Même clavier, mais qui retient l'état des voyants du PC.

        Windows envoie au clavier l'état de Verr. Maj / Verr. Num. On s'en
        sert dans layouts.py pour taper le bon caractère (voir l'explication
        du piège Verr. Maj sur les claviers français).
        """

        def __init__(self):
            self.led_mask = 0
            super().__init__()

        def on_led_update(self, mask):
            self.led_mask = mask

    interface = KeyboardWithLEDs()
    usb.device.get().init(interface, builtin_driver=True)
    return interface
```

---

## device/display.py

`502 lignes - sha256 7f977eaa772823dd`

```python
# -*- coding: utf-8 -*-
"""
display.py - L'interface sur l'ecran OLED SH1106 128x64.

=====================================================================
L'ECRAN N'EST JAMAIS INDISPENSABLE
=====================================================================
S'il est absent, debranche, ou s'il tombe en panne en cours de route, on
l'abandonne proprement (self.oled = None) et le macropad continue de
fonctionner comme clavier. Un ecran ne doit jamais empecher de taper.

=====================================================================
LA VUE PRINCIPALE : UN TABLEAU DES GESTES
=====================================================================
    +------------------------+
    |#CIVIL 3D#########AUTO##|  bandeau inverse : profil + etat
    |   CRT   LNG   DBL      |  en-tete des trois colonnes
    |#1#MATC  ---   ---      |  ligne surlignee = touche qui vient de servir
    | 2 HATC  ---   ---      |
    | 3 ANNU  REFA  ---      |
    | 4 ISOL  UNIS  ---      |
    |------------------------|
    |C3D Projet_A12_Phas...  |  logiciel fixe + nom de fichier qui defile
    +------------------------+

Chaque ligne montre les trois macros d'une touche :
  CRT = appui court, LNG = appui long, DBL = double appui.
Un tiret signale un geste sans macro.

Quatre lignes tiennent a l'ecran. Avec six touches, le tableau **defile
tout seul** d'un cran toutes les TABLE_SCROLL_MS.

Et surtout : **des que tu appuies sur une touche, le tableau saute
instantanement dessus et la surligne**. Tu vois donc ce que tu viens de
declencher, et les deux autres gestes disponibles sur cette meme touche.

=====================================================================
POURQUOI UNE SEULE PAGE PAR TOUR DE BOUCLE
=====================================================================
L'ecran fait 1024 octets. Les envoyer d'un coup prend environ 23 ms,
pendant lesquelles le processeur ne fait rien d'autre : on sentirait le
macropad accrocher a chaque changement d'affichage.

Le SH1106 range sa memoire en 8 bandes horizontales de 8 pixels, les
"pages". On en envoie UNE par tour de boucle, soit environ 3 ms. L'image
complete se met a jour en 8 tours, environ 16 ms : invisible a l'oeil.

Le defilement du nom de fichier, lui, ne touche que la derniere ligne :
on ne reenvoie donc que la page 7, huit fois moins de trafic.

Particularite du SH1106 : 132 colonnes de memoire pour une dalle de 128
pixels. Il faut decaler l'ecriture de 2 colonnes, sinon toute l'image est
decalee. C'est le role de la commande 0x02 dans tick().

=====================================================================
ANTI-MARQUAGE
=====================================================================
Un OLED qui affiche la meme image pendant des heures MARQUE : les pixels
allumes en permanence vieillissent plus vite et laissent un fantome
definitif. Le bandeau inverse du haut est exactement le pire cas.

Apres SCREEN_DIM_MS sans appui on baisse le contraste, apres
SCREEN_OFF_MS on eteint la dalle. N'importe quelle touche reveille tout
instantanement.
"""

from time import ticks_ms, ticks_diff, ticks_add
import config as C

# Geometrie
_ENTETE_Y = 12                      # ligne des titres de colonnes
_LIGNE_Y = (21, 29, 37, 45)         # les quatre lignes visibles du tableau
_LIGNES_VISIBLES = len(_LIGNE_Y)
_SEPARATEUR_Y = 53
_BAS_Y = 55                         # ligne du document
# Les trois colonnes du tableau : abscisse en pixels, largeur en
# caracteres. La police fait 8 pixels de large, donc :
#   1 chiffre (8) + 6 caracteres (48) + 4 (32) + 4 (32) = 120 sur 128.
# La premiere colonne est la plus large parce qu'elle porte le libelle,
# que tu as le droit d'ecrire sur 6 caracteres (LABEL_MAX).
_COL_X = (8, 58, 92)                # colonnes court / long / double
_COL_LARGEUR = (6, 4, 4)            # caracteres par colonne

# Etats de l'economiseur d'ecran
_VEILLE_NORMALE = 0
_VEILLE_ATTENUEE = 1
_VEILLE_ETEINTE = 2


class Display:

    def __init__(self):
        self.oled = None
        self.titre = ""
        self.macros = []
        self.etat = ""
        self.doc_abrege = ""
        self.doc_nom = ""

        self._defil_x = 0           # decalage du nom de fichier, en pixels
        self._defil_sens = 1
        self._defil_max = 0
        self._defil_t = 0

        self.fenetre = 0            # index de la premiere touche affichee
        self._fenetre_t = 0         # prochain defilement automatique
        self.surbrillance = -1      # touche surlignee, -1 = aucune
        self._surbrillance_t = 0

        self.splash_until = None
        self.pending_page = 8       # 8 = rien a envoyer ; 0 = tout a renvoyer

        self._veille = _VEILLE_NORMALE
        self._activite = 0

        if not C.OLED_ENABLED:
            return
        try:
            from machine import Pin, I2C
            from sh1106 import SH1106_I2C
            # timeout : si l'ecran ne repond pas, l'echange est abandonne
            # au lieu de bloquer indefiniment toute la boucle principale.
            bus = I2C(C.I2C_ID, sda=Pin(C.OLED_SDA), scl=Pin(C.OLED_SCL),
                      freq=C.I2C_FREQ, timeout=C.I2C_TIMEOUT_US)
            adresses = bus.scan()
            print("OLED I2C :", [hex(a) for a in adresses])
            adresse = next((a for a in (0x3c, 0x3d) if a in adresses), None)
            if adresse is None:
                raise OSError("SH1106 absent (0x3C/0x3D)")
            self.oled = SH1106_I2C(128, 64, bus, addr=adresse, rotate=0)
            self.oled.contrast(C.OLED_CONTRAST)
            self._activite = ticks_ms()
        except Exception as exc:
            self.disable(exc)

    def disable(self, erreur):
        """Abandonne l'ecran sans arreter le macropad."""
        print("OLED desactive :", erreur)
        self.oled = None

    # ==================================================================
    # Briques de dessin
    # ==================================================================
    def _bandeau(self):
        o = self.oled
        o.fill_rect(0, 0, 128, 11, 1)
        o.text(self.titre[:13], 2, 2, 0)
        if self.etat:
            o.text(self.etat[:4], 128 - 8 * len(self.etat[:4]) - 2, 2, 0)

    def _entete(self):
        o = self.oled
        o.text("CRT", _COL_X[0], _ENTETE_Y, 1)
        o.text("LNG", _COL_X[1], _ENTETE_Y, 1)
        o.text("DBL", _COL_X[2], _ENTETE_Y, 1)

    def _abrege_geste(self, gestes, nom, largeur):
        """Libelle court d'un geste, ou un tiret s'il n'a pas de macro."""
        actions = (gestes or {}).get(nom)
        if not actions:
            return "-"
        genre, valeur = actions[0]
        if genre in ("combo", "maintien"):
            # D'une combinaison, on montre la derniere touche : dans
            # CTRL+SHIFT+Z, c'est le Z qui distingue la macro des autres.
            # Pour un maintien, c'est le modificateur lui-meme : CTRL, MAJ.
            texte = valeur[-1] if valeur else "?"
        elif genre == "key":
            texte = str(valeur)
        else:
            # Les commandes AutoCAD commencent par un underscore, qui ne
            # sert qu'a forcer la version anglaise : inutile a l'ecran.
            texte = str(valeur).lstrip("_")
        return texte[:largeur].upper()

    def _ligne_tableau(self, rang, index):
        """Dessine une ligne du tableau. rang = position a l'ecran."""
        o = self.oled
        y = _LIGNE_Y[rang]
        label, gestes = self.macros[index]
        surligne = (index == self.surbrillance)

        if surligne:
            o.fill_rect(0, y - 1, 128, 9, 1)
        fond, encre = (1, 0) if surligne else (0, 1)

        o.text(str(index + 1), 0, y, encre)
        # Colonne 1 : le libelle de la touche, plus lisible que la macro
        # elle-meme ("MATCH" parle mieux que "MATC" de "_MATCHPROP").
        o.text(label[:_COL_LARGEUR[0]].upper(), _COL_X[0], y, encre)
        o.text(self._abrege_geste(gestes, "long", _COL_LARGEUR[1]),
               _COL_X[1], y, encre)
        o.text(self._abrege_geste(gestes, "double", _COL_LARGEUR[2]),
               _COL_X[2], y, encre)

    def _zone_document(self):
        """Ou commence le nom du fichier, et quelle largeur lui reste."""
        depart = 2
        if self.doc_abrege:
            depart = 2 + len(self.doc_abrege) * 8 + 5
        return depart, max(0, 128 - depart - 2)

    def _dessiner_bas(self):
        """Redessine UNIQUEMENT la derniere ligne (page 7).

        Elle change souvent a cause du defilement ; la redessiner seule
        divise par huit le trafic I2C.
        """
        o = self.oled
        o.fill_rect(0, 56, 128, 8, 0)
        if not self.doc_nom and not self.doc_abrege:
            return
        depart, _ = self._zone_document()
        if self.doc_nom:
            # framebuf decoupe tout seul ce qui depasse de l'ecran : on peut
            # donc dessiner a une abscisse negative, le debut sort par la
            # gauche. C'est tout le principe du defilement.
            o.text(self.doc_nom, depart - self._defil_x, _BAS_Y + 1, 1)
        if self.doc_abrege:
            # On efface ce que le nom a deborde sur la zone reservee, puis
            # on ecrit l'abreviation par-dessus : elle reste toujours lisible.
            o.fill_rect(0, 56, depart - 2, 8, 0)
            o.text(self.doc_abrege, 2, _BAS_Y + 1, 1)

    def _vue_principale(self):
        o = self.oled
        o.fill(0)
        self._bandeau()
        self._entete()
        for rang in range(_LIGNES_VISIBLES):
            index = self.fenetre + rang
            if index < len(self.macros):
                self._ligne_tableau(rang, index)
        o.hline(0, _SEPARATEUR_Y, 128, 1)
        self._dessiner_bas()

    def _texte_double(self, texte):
        """Ecrit un texte en police doublee, centre.

        MicroPython ne fournit qu'une police 8x8. Pour l'agrandir on dessine
        le texte dans une petite image en memoire, puis on recopie chaque
        pixel sous forme d'un carre de 2x2 sur l'ecran.
        """
        import framebuf
        o = self.oled
        o.fill(0)
        echelle = 2 if len(texte) <= 8 else 1
        largeur = len(texte) * 8
        tampon = framebuf.FrameBuffer(bytearray(128), 128, 8,
                                      framebuf.MONO_HLSB)
        tampon.text(texte, 0, 0, 1)
        x0 = max(0, (128 - largeur * echelle) // 2)
        y0 = (64 - 8 * echelle) // 2
        for x in range(min(128, largeur)):
            for y in range(8):
                if tampon.pixel(x, y):
                    o.fill_rect(x0 + x * echelle, y0 + y * echelle,
                                echelle, echelle, 1)

    # ==================================================================
    # Rafraichissements
    # ==================================================================
    def _redessiner(self):
        if not self.oled or self.splash_until is not None:
            return
        try:
            self._vue_principale()
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def _rafraichir_bas(self):
        """Redessine la derniere ligne et ne reenvoie que sa page."""
        if not self.oled or self.splash_until is not None:
            return
        try:
            self._dessiner_bas()
            # 8 = aucun envoi en cours. On ne se glisse dans la file que si
            # un rafraichissement complet n'est pas deja en route, sinon on
            # lui ferait sauter des pages.
            if self.pending_page >= 8:
                self.pending_page = 7
        except Exception as exc:
            self.disable(exc)

    # ==================================================================
    # API publique
    # ==================================================================
    def message(self, *lignes):
        """Quelques lignes de texte brut : SAFE MODE, erreurs, diagnostic."""
        if not self.oled:
            return
        try:
            self.reveiller(ticks_ms())
            self.splash_until = None
            self.oled.fill(0)
            y = 4
            for ligne in lignes[:6]:
                self.oled.text(str(ligne)[:16], 2, y, 1)
                y += 10
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def config_screen(self, ssid, mot_de_passe, adresse):
        """Ecran du mode configuration : tout pour se connecter."""
        if not self.oled:
            return
        try:
            self.reveiller(ticks_ms())
            o = self.oled
            o.fill(0)
            self.titre, self.etat = "MODE CONFIG", "WIFI"
            self._bandeau()
            o.text("Reseau :", 2, 15, 1)
            o.text(str(ssid)[:16], 2, 25, 1)
            o.text("Cle :", 2, 36, 1)
            o.text(str(mot_de_passe)[:16], 2, 46, 1)
            o.hline(0, _SEPARATEUR_Y, 128, 1)
            o.text(str(adresse)[:16], 2, _BAS_Y + 1, 1)
            self.splash_until = None
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def set_etat(self, etat):
        """Petit texte en haut a droite : HID, AUTO, LOCK, ERR..."""
        if etat == self.etat:
            return
        self.etat = etat
        self._redessiner()

    def set_document(self, texte):
        """Ce que le PC nous dit du document ouvert.

        Format recu : "C3D|Projet_A12_Phase2.dwg"
        La partie avant la barre verticale est l'abreviation du logiciel,
        qui reste fixe a gauche. Ce qui suit est le nom du fichier, qui
        defilera doucement s'il est trop long. Sans barre, tout est pris
        pour le nom.
        """
        texte = texte or ""
        if "|" in texte:
            abrege, nom = texte.split("|", 1)
        else:
            abrege, nom = "", texte
        abrege, nom = abrege.strip()[:7], nom.strip()[:48]
        if abrege == self.doc_abrege and nom == self.doc_nom:
            return
        self.doc_abrege, self.doc_nom = abrege, nom

        # De combien faut-il defiler pour voir la fin du nom ?
        _, dispo = self._zone_document()
        self._defil_max = max(0, len(nom) * 8 - dispo)
        self._defil_x = 0
        self._defil_sens = 1
        self._defil_t = ticks_add(ticks_ms(), C.DOC_SCROLL_PAUSE_MS)
        self._rafraichir_bas()

    def profile(self, titre, macros, now, index=0, total=1, splash=False):
        """Affiche un profil. splash=True montre d'abord son nom en gros."""
        self.titre = titre
        self.macros = list(macros)
        self.fenetre = 0
        self.surbrillance = -1
        self._fenetre_t = ticks_add(now, C.TABLE_SCROLL_MS)
        if not self.oled:
            return
        try:
            self.reveiller(now)
            if splash:
                self._texte_double(titre[:8])
                self.splash_until = ticks_add(now, C.PROFILE_SPLASH_MS)
            else:
                self.splash_until = None
                self._vue_principale()
            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def surligner(self, index, now):
        """La touche vient de servir : on saute dessus et on la surligne.

        C'est le retour visuel immediat : tu vois ce que tu as declenche,
        et du meme coup les deux autres gestes disponibles sur cette touche.
        """
        self.reveiller(now)
        if not self.oled or not (0 <= index < len(self.macros)):
            return
        self.surbrillance = index
        self._surbrillance_t = ticks_add(now, C.HIGHLIGHT_MS)
        # On amene la touche dans la fenetre visible si elle n'y est pas.
        if index < self.fenetre:
            self.fenetre = index
        elif index >= self.fenetre + _LIGNES_VISIBLES:
            self.fenetre = index - _LIGNES_VISIBLES + 1
        # Pas de defilement automatique pendant qu'on regarde la touche.
        self._fenetre_t = ticks_add(now, C.HIGHLIGHT_MS + C.TABLE_SCROLL_MS)
        self._redessiner()

    # ==================================================================
    # Economiseur d'ecran
    # ==================================================================
    def reveiller(self, now):
        """A appeler des qu'une touche est actionnee."""
        self._activite = now
        if self._veille == _VEILLE_NORMALE or not self.oled:
            return
        try:
            if self._veille == _VEILLE_ETEINTE:
                self.oled.sleep(False)
            self.oled.contrast(C.OLED_CONTRAST)
            self._veille = _VEILLE_NORMALE
            self.pending_page = 0        # l'image doit etre reenvoyee
        except Exception as exc:
            self.disable(exc)

    def _service_veille(self, now):
        if not self.oled:
            return
        inactif = ticks_diff(now, self._activite)
        try:
            if self._veille == _VEILLE_NORMALE and inactif > C.SCREEN_DIM_MS:
                self.oled.contrast(C.SCREEN_DIM_CONTRAST)
                self._veille = _VEILLE_ATTENUEE
            elif self._veille == _VEILLE_ATTENUEE and inactif > C.SCREEN_OFF_MS:
                self.oled.sleep(True)
                self._veille = _VEILLE_ETEINTE
        except Exception as exc:
            self.disable(exc)

    # ==================================================================
    # A appeler a chaque tour de boucle
    # ==================================================================
    def tick(self, now):
        if not self.oled:
            return

        # --- fin de l'ecran "nom du profil en gros" --------------------
        if self.splash_until is not None and ticks_diff(now, self.splash_until) >= 0:
            self.splash_until = None
            self._redessiner()

        if self._veille == _VEILLE_ETEINTE:
            return          # ecran eteint : plus rien a animer ni a envoyer

        if self.splash_until is None:
            # --- fin du surlignage ------------------------------------
            if (self.surbrillance >= 0
                    and ticks_diff(now, self._surbrillance_t) >= 0):
                self.surbrillance = -1
                self._redessiner()

            # --- defilement automatique du tableau --------------------
            elif (len(self.macros) > _LIGNES_VISIBLES
                    and ticks_diff(now, self._fenetre_t) >= 0):
                maximum = len(self.macros) - _LIGNES_VISIBLES
                self.fenetre = 0 if self.fenetre >= maximum else self.fenetre + 1
                self._fenetre_t = ticks_add(now, C.TABLE_SCROLL_MS)
                self._redessiner()

            # --- defilement du nom de fichier -------------------------
            elif self._defil_max > 0 and ticks_diff(now, self._defil_t) >= 0:
                self._defil_x += self._defil_sens
                if self._defil_x >= self._defil_max:
                    self._defil_x = self._defil_max
                    self._defil_sens = -1
                    self._defil_t = ticks_add(now, C.DOC_SCROLL_PAUSE_MS)
                elif self._defil_x <= 0:
                    self._defil_x = 0
                    self._defil_sens = 1
                    self._defil_t = ticks_add(now, C.DOC_SCROLL_PAUSE_MS)
                else:
                    self._defil_t = ticks_add(now, C.DOC_SCROLL_MS)
                self._rafraichir_bas()

        self._service_veille(now)

        # --- envoi d'AU PLUS une page a l'ecran ------------------------
        if self.pending_page >= 8:
            return
        try:
            page = self.pending_page
            self.oled.write_cmd(0xB0 | page)   # choisir la bande n° page
            self.oled.write_cmd(0x02)          # colonne de depart, poids faibles
            self.oled.write_cmd(0x10)          # colonne de depart, poids forts
            #        ^ 0x02 = le decalage de 2 colonnes propre au SH1106
            self.oled.write_data(
                self.oled.displaybuf[page * 128:(page + 1) * 128])
            self.pending_page += 1
        except Exception as exc:
            # Un ecran arrache en cours de route ne doit pas arreter le clavier.
            self.disable(exc)

    def flush_startup(self):
        """Envoie l'image entiere d'un coup.

        Reserve aux moments ou l'on peut se permettre d'attendre : avant que
        les touches ne deviennent actives, en SAFE MODE, en mode config.
        """
        for _ in range(9):
            self.tick(ticks_ms())
```

---

## device/led.py

`119 lignes - sha256 ea663083b7591be3`

```python
# -*- coding: utf-8 -*-
"""
led.py - La LED du gros bouton ESC : respiration douce et flash à l'appui.

=====================================================================
CE QU'EST LE PWM, EN DEUX PHRASES
=====================================================================
Un GPIO ne sait faire que deux choses : 0 V ou 3,3 V. Pour obtenir une
demi-luminosité, on allume et on éteint très vite : 2000 fois par seconde
ici. Si on est allumé 25 % du temps, l'oeil voit une LED à 25 % de
luminosité. Ce pourcentage s'appelle le rapport cyclique.

2000 Hz est choisi assez haut pour qu'aucun scintillement ne soit visible,
même du coin de l'oeil ou devant une caméra.

=====================================================================
RAPPEL DE SECURITE ELECTRIQUE
=====================================================================
Ce GPIO ne pilote PAS la LED. Il pilote la base d'un transistor BC547 à
travers une résistance de 2,2 kilo-ohms, et c'est le transistor qui laisse
passer le courant de la LED. Le GPIO ne fournit qu'environ 1,2 mA.

Brancher une LED 1 W directement sur un GPIO détruirait la broche : un
GPIO d'ESP32-S3 ne supporte qu'environ 40 mA, et une LED sans résistance
en tirerait beaucoup plus. Voir docs/05-electronique.md.

=====================================================================
POURQUOI UN COSINUS ET PAS UNE SIMPLE MONTEE
=====================================================================
Une rampe qui monte puis redescend en ligne droite donne un effet
"clignotant triangulaire" assez désagréable : les changements de sens sont
brutaux. Le cosinus, lui, arrive en douceur aux extrémités, exactement
comme une respiration.

L'exposant 1,6 accentue encore l'effet : la LED s'attarde dans les valeurs
basses et ne fait que passer par le maximum. C'est ce qui rend l'animation
naturelle plutôt que mécanique.

Aucune méthode de ce fichier n'attend : tick() calcule la valeur qui
correspond à l'instant présent et rend la main aussitôt. La respiration ne
ralentit donc jamais les touches.
"""

from machine import Pin, PWM
from time import ticks_ms, ticks_diff
from math import cos, pi
import config as C


def breath(phase_ms):
    """Luminosité voulue (de 0.0 à 1.0) à un instant donné du cycle.

    phase_ms va de 0 à LED_PERIOD_MS. La fonction est "pure" : elle ne
    dépend que de son argument, ce qui permet de la tester sur PC sans
    aucun matériel.
    """
    # (1 - cos(x)) / 2 dessine une courbe qui part de 0, monte doucement
    # jusqu'à 1 au milieu du cycle, puis redescend en douceur jusqu'à 0.
    wave = (1 - cos(2 * pi * phase_ms / C.LED_PERIOD_MS)) / 2
    return C.LED_MIN + (C.LED_MAX - C.LED_MIN) * wave ** 1.6


class Led:

    def __init__(self):
        self.pwm = PWM(Pin(C.LED_PIN), freq=C.PWM_FREQ, duty_u16=0)
        self.last = ticks_ms()
        self.phase = 0            # où on en est dans le cycle de respiration
        self.flashed_at = None    # instant du dernier appui sur ESC

    def flash(self, now):
        """Éclat lumineux immédiat, déclenché par le bouton ESC.

        On monte à 100 % tout de suite, sans attendre le prochain tick :
        l'éclat doit être perçu comme simultané à l'appui.
        Aucun risque de surchauffe : le courant reste limité à quelques
        milliampères par la résistance de 330 ohms.
        """
        self.flashed_at = now
        self.set_level(1.0)

    def set_level(self, value):
        """Applique une luminosité de 0.0 à 1.0 au PWM."""
        # duty_u16 attend un nombre de 0 à 65535. Le min/max est une
        # ceinture de sécurité contre une valeur de calcul aberrante.
        self.pwm.duty_u16(int(max(0, min(1, value)) * 65535))

    def tick(self, now):
        """Appelé à chaque tour de la boucle principale."""
        # On avance la phase du temps réellement écoulé. ticks_diff gère
        # correctement le "retour à zéro" du compteur de millisecondes de
        # MicroPython, qui repart de 0 au bout d'environ 12 jours.
        self.phase = (self.phase + max(0, ticks_diff(now, self.last))) % C.LED_PERIOD_MS
        self.last = now
        level = breath(self.phase)

        if self.flashed_at is not None:
            age = ticks_diff(now, self.flashed_at)
            if age < C.LED_FLASH_MS:
                level = 1.0                      # plein éclat
            elif age < C.LED_FLASH_MS + C.LED_RETURN_MS:
                # Retour progressif vers la respiration. La formule
                # x*x*(3-2x) est un lissage classique : elle démarre et
                # finit tout en douceur au lieu de "casser".
                x = (age - C.LED_FLASH_MS) / C.LED_RETURN_MS
                smooth = x * x * (3 - 2 * x)
                level = 1.0 + (level - 1.0) * smooth
            else:
                self.flashed_at = None           # flash terminé

        self.set_level(level)

    def close(self):
        """Extinction propre quand le programme s'arrête."""
        self.set_level(0)
        self.pwm.deinit()
        # deinit() relâche la broche ; on la repasse en sortie à 0 pour
        # être certain que le transistor reste bloqué et la LED éteinte.
        Pin(C.LED_PIN, Pin.OUT, value=0)
```

---

## device/rgb.py

`332 lignes - sha256 8f0ccc9c278280cd`

```python
# -*- coding: utf-8 -*-
"""
rgb.py - Les LED RGB sous les touches.

=====================================================================
CE QUE CA FAIT
=====================================================================
* chaque profil a sa couleur : d'un coup d'oeil, tu sais si le macropad
  est en CIVIL 3D ou en BLENDER, sans lire l'ecran. Comme le PC dit au
  macropad quel logiciel est au premier plan, la couleur suit le logiciel
  tout seul : tu cliques dans Civil 3D, le pad devient bleu ;
* la couleur RESPIRE doucement, comme la LED du bouton ESC : elle monte
  et redescend sur RGB_RESPIRATION_MS. Une couleur fixe se remarque une
  fois puis s'oublie ; une couleur qui respire reste vivante sans jamais
  clignoter ni attirer l'oeil au mauvais moment ;
* la touche sur laquelle tu appuies S'INTENSIFIE aussitot, puis revient
  a la couleur du profil en douceur. Deux appuis coup sur coup montent
  deux fois plus haut : l'impulsion s'ajoute a ce qui reste de la
  precedente, au lieu de la remplacer. La LED reagit au DOIGT, sur le
  front d'appui, sans attendre de savoir quelle macro partira ;
* apres RGB_VEILLE_MS sans rien toucher, tout s'eteint - pour les yeux,
  pour la duree de vie des LED, et surtout pour le courant.

=====================================================================
DEUX MONTAGES POSSIBLES, ET UN SEUL FIL DE CODE POUR LES DEUX
=====================================================================
RGB_TYPE = "WS2812"   LED adressables (NeoPixel, SK6812...). UN seul fil
                      de donnees pour toute la guirlande, et une couleur
                      DIFFERENTE par touche. C'est ce qu'il faut pour
                      eclairer six touches.

RGB_TYPE = "PWM"      UNE LED RGB ordinaire a quatre pattes, sur trois
                      broches. Une seule couleur pour tout le macropad :
                      la couleur du profil. Pas de couleur par touche -
                      il faudrait trois broches PAR touche, soit dix-huit.

Livre avec RGB_ENABLED = False : rien ne bouge tant que tu n'as pas
cable et choisi ton type.

=====================================================================
CE QUI RISQUE DE CRAMER, OU DE FAIRE REDEMARRER LA CARTE
=====================================================================
1. LE COURANT, C'EST LE VRAI DANGER. Une WS2812 en blanc a fond tire
   60 mA. Six touches = 360 mA, plus la carte, plus l'ecran : on depasse
   les 500 mA que fournit un port USB ordinaire. Le 5 V s'effondre, la
   carte redemarre, et ton clavier disparait en pleine frappe.

   La parade est dans le code : RGB_LUMINOSITE plafonne CHAQUE canal
   avant l'envoi. A la valeur livree (40 sur 255), six LED tirent environ
   60 mA au total. Ne monte pas ce chiffre sans mesurer.

2. LES WS2812 SE NOURRISSENT EN 5 V, PAS EN 3,3 V. Le regulateur 3,3 V
   de la carte n'a pas la marge ; il faut prendre le 5 V (VBUS).

3. LE FIL DE DONNEES SORT EN 3,3 V. Une WS2812 alimentee en 5 V attend
   un niveau haut d'au moins 3,5 V : on est JUSTE en dessous. Souvent ca
   passe, parfois non - et quand ca ne passe pas, les couleurs sautent au
   hasard. Deux remedes eprouves :
     * une resistance de 220 a 470 ohms EN SERIE sur le fil de donnees,
       au plus pres de la premiere LED (elle protege aussi le GPIO). Sa
       valeur exacte n'a aucune importance : elle amortit le signal, elle
       ne fixe aucun courant ;
     * si ca scintille encore, alimente la guirlande en ~4,3 V en
       intercalant une diode 1N4148 entre le 5 V et son VCC : le seuil
       descend a 3,0 V et le probleme disparait.

4. UN CONDENSATEUR DE 470 uF entre 5 V et GND, au plus pres des LED.
   Elles commutent tres vite et tirent des pointes de courant ; sans
   reservoir local, ces pointes se voient sur toute l'alimentation.
   100 uF suffisent pour six LED ; les valeurs de 1000 uF qu'on lit
   partout visent des rubans de cinquante ou cent LED. ATTENTION A LA
   POLARITE : un chimique monte a l'envers gonfle et explose.

5. NE JAMAIS brancher le fil de donnees sur une LED deja alimentee alors
   que la carte est hors tension : le courant passerait par la diode de
   protection du GPIO. Alimente les deux ensemble.
"""

from math import cos, pi
from time import ticks_ms, ticks_diff, ticks_add
import config as C

def respiration(phase_ms):
    """Facteur de luminosite (0.0 a 1.0) a un instant du cycle.

    C'est exactement la courbe de la LED du bouton ESC (voir led.py) :
    (1 - cos) / 2 part de zero, monte en douceur, redescend en douceur.
    L'exposant 1.6 fait s'attarder la couleur dans les valeurs basses et
    ne fait que passer par le maximum - c'est ce qui donne une
    respiration plutot qu'un clignotement.

    Fonction pure : elle ne depend que de son argument, donc elle se teste
    sans la moindre LED.
    """
    periode = getattr(C, "RGB_RESPIRATION_MS", 4000)
    plancher = getattr(C, "RGB_RESPIRATION_MIN", 0.35)
    onde = (1 - cos(2 * pi * (phase_ms % periode) / periode)) / 2
    return plancher + (1.0 - plancher) * onde ** 1.6


class Rgb:
    """Pilote les LED RGB. Se desactive toute seule en cas de probleme."""

    def __init__(self):
        self.actif = False
        self.materiel = None
        self.type = None
        self.nb = 0
        self.base = (0, 0, 0)          # couleur du profil courant
        self._erreur = False           # panne HID : tout passe au rouge
        # Une "energie" par touche : elle monte a chaque appui et redescend
        # toute seule. C'est ce qui fait qu'un appui se voit tout de suite
        # et que deux appuis montent deux fois plus haut.
        self.niveaux = [0.0] * max(int(getattr(C, "RGB_COUNT", 6)), 1)
        self._activite = ticks_ms()
        self._eteint = False
        self._a_redessiner = True
        self._prochain = 0
        self._phase = 0            # ou on en est dans la respiration
        self._dernier = ticks_ms()
        if not getattr(C, "RGB_ENABLED", False):
            return
        try:
            self._demarrer()
            self.actif = True
        except Exception as exc:
            # Une LED absente ou mal cablee ne doit JAMAIS empecher le
            # macropad de taper. Meme regle que pour l'ecran.
            print("RGB desactive :", exc)

    # ------------------------------------------------------------------
    def _demarrer(self):
        from machine import Pin
        self.type = getattr(C, "RGB_TYPE", "WS2812")
        if self.type == "WS2812":
            from neopixel import NeoPixel
            self.nb = int(getattr(C, "RGB_COUNT", 6))
            self.materiel = NeoPixel(Pin(C.RGB_PIN, Pin.OUT), self.nb)
        elif self.type == "PWM":
            from machine import PWM
            self.nb = 1
            self.materiel = tuple(
                PWM(Pin(broche, Pin.OUT), freq=1000, duty_u16=0)
                for broche in (C.RGB_PIN_R, C.RGB_PIN_V, C.RGB_PIN_B))
        else:
            raise ValueError("RGB_TYPE inconnu : " + str(self.type))

    def desactiver(self, exc):
        print("RGB desactive :", exc)
        self.actif = False

    # ------------------------------------------------------------------
    # Ce que main.py appelle
    # ------------------------------------------------------------------
    def profil(self, couleur):
        """Nouvelle couleur de fond : celle du logiciel qui vient d'etre pris.

        C'est main.py qui choisit la couleur, a partir de la configuration :
        rgb.py ne connait pas les noms de profils, seulement des couleurs.
        """
        self.base = tuple(couleur or C.RGB_COULEUR_DEFAUT)
        for index in range(len(self.niveaux)):
            self.niveaux[index] = 0.0
        self._a_redessiner = True
        self.reveiller(ticks_ms())

    def etat(self, texte):
        """Le bandeau de l'ecran change : on en profite pour signaler.

        ERR est le seul cas ou la couleur du profil s'efface : quand le
        clavier est en panne, tu dois le voir sans lire l'ecran.
        """
        erreur = (texte == "ERR")
        if erreur != self._erreur:
            self._erreur = erreur
            self._a_redessiner = True

    def touche(self, index, now):
        """Un appui vient d'avoir lieu : la LED de cette touche s'intensifie.

        On AJOUTE l'impulsion a ce qui reste de la precedente, plafonnee :
        deux appuis rapides montent deux fois plus haut, dix appuis ne
        montent pas dix fois plus haut. Le plafond du courant, lui, reste
        celui de limiter() - personne ne peut faire redemarrer la carte a
        force d'appuyer.
        """
        self.reveiller(now)
        if 0 <= index < len(self.niveaux):
            plafond = getattr(C, "RGB_IMPULSION_MAX", 3.0)
            niveau = self.niveaux[index] + getattr(C, "RGB_IMPULSION", 1.0)
            self.niveaux[index] = plafond if niveau > plafond else niveau
            self._a_redessiner = True

    def reveiller(self, now):
        self._activite = now
        if self._eteint:
            self._eteint = False
            self._a_redessiner = True

    # ------------------------------------------------------------------
    def tick(self, now):
        """A appeler a chaque tour de boucle. N'attend jamais."""
        if not self.actif:
            return

        if (not self._eteint
                and ticks_diff(now, self._activite) > C.RGB_VEILLE_MS):
            self._eteint = True
            self._a_redessiner = True

        # La respiration avance avec le TEMPS ECOULE, pas avec le nombre de
        # tours de boucle : le rythme reste le meme quoi que fasse le
        # macropad par ailleurs.
        ecoule = ticks_diff(now, self._dernier)
        self._dernier = now
        if not (0 < ecoule < 1000):
            ecoule = 0                 # un saut d'horloge ne fait rien sauter
        if getattr(C, "RGB_RESPIRATION", True) and not self._eteint:
            self._phase += ecoule
            self._a_redessiner = True

        # Les impulsions redescendent toutes seules, proportionnellement au
        # temps ecoule : la retombee dure RGB_RETOMBEE_MS par unite, quelle
        # que soit la vitesse de la boucle.
        if ecoule:
            perte = float(ecoule) / getattr(C, "RGB_RETOMBEE_MS", 700)
            for index in range(len(self.niveaux)):
                if self.niveaux[index] > 0:
                    reste = self.niveaux[index] - perte
                    self.niveaux[index] = reste if reste > 0 else 0.0
                    self._a_redessiner = True

        if not self._a_redessiner or ticks_diff(now, self._prochain) < 0:
            return
        self._prochain = ticks_add(now, C.RGB_MS)
        self._a_redessiner = False
        try:
            self._envoyer()
        except Exception as exc:
            self.desactiver(exc)

    def _envoyer(self):
        if self._eteint:
            self._peindre_tout((0, 0, 0))
            return
        fond = tuple(C.RGB_COULEUR_ERREUR) if self._erreur else self.base
        # Le souffle de la respiration, entre son plancher et 1.0. Les
        # impulsions des touches s'AJOUTENT par-dessus : un appui monte
        # donc pareil, que la respiration soit en haut ou en bas de son
        # cycle. C'est ce qu'on attend d'un retour visuel.
        souffle = 1.0
        if getattr(C, "RGB_RESPIRATION", True):
            souffle = respiration(self._phase)

        if self.type == "PWM":
            # Une seule LED pour tout le pad : elle prend l'impulsion la
            # plus forte du moment.
            plus_haut = 0.0
            for niveau in self.niveaux:
                if niveau > plus_haut:
                    plus_haut = niveau
            self._peindre_tout(_attenuer(fond, souffle + plus_haut))
            return

        for index in range(self.nb):
            niveau = self.niveaux[index] if index < len(self.niveaux) else 0.0
            self._pixel(index, _attenuer(fond, souffle + niveau))
        self.materiel.write()

    def _peindre_tout(self, couleur):
        if self.type == "PWM":
            self._pwm(couleur)
            return
        for index in range(self.nb):
            self._pixel(index, couleur)
        self.materiel.write()

    # ------------------------------------------------------------------
    # Bas niveau
    # ------------------------------------------------------------------
    def _pixel(self, index, couleur):
        r, v, b = limiter(couleur)
        # Les WS2812 attendent l'ordre VERT, ROUGE, BLEU. C'est la cause
        # n°1 des "mes rouges sortent verts" : si tes couleurs sont
        # permutees, c'est RGB_ORDRE qu'il faut changer, pas ton cablage.
        ordre = getattr(C, "RGB_ORDRE", "GRB")
        valeurs = {"R": r, "G": v, "B": b}
        self.materiel[index] = tuple(valeurs[lettre] for lettre in ordre)

    def _pwm(self, couleur):
        valeurs = limiter(couleur)
        for canal, valeur in zip(self.materiel, valeurs):
            rapport = valeur * 257            # 0..255 -> 0..65535
            if getattr(C, "RGB_ANODE_COMMUNE", True):
                # Anode commune : la patte commune est au +, le GPIO tire
                # vers le bas. Zero volt = allume, d'ou l'inversion.
                rapport = 65535 - rapport
            canal.duty_u16(rapport)

    def close(self):
        """Tout eteindre en partant. Une LED oubliee allumee, ca se voit."""
        if not self.actif:
            return
        try:
            self._peindre_tout((0, 0, 0))
        except Exception:
            pass
        self.actif = False


def _attenuer(couleur, facteur):
    """Multiplie une couleur par un facteur de 0.0 a 1.0."""
    return tuple(int(valeur * facteur) for valeur in couleur)


def limiter(couleur):
    """Plafonne la couleur a RGB_LUMINOSITE. C'EST LA SECURITE COURANT.

    Elle est ici, dans le code, et pas laissee au bon vouloir de celui qui
    choisit les couleurs : personne ne peut demander du blanc a fond sur
    six LED et faire redemarrer la carte en pleine frappe.
    """
    plafond = getattr(C, "RGB_LUMINOSITE", 40)
    sortie = []
    for valeur in couleur:
        valeur = int(valeur)
        if valeur < 0:
            valeur = 0
        elif valeur > 255:
            valeur = 255
        sortie.append(valeur * plafond // 255)
    return tuple(sortie)
```

---

## device/diag.py

`236 lignes - sha256 2cf878a374912173`

```python
# -*- coding: utf-8 -*-
"""
diag.py - Diagnostic du matériel. N'ENVOIE JAMAIS AUCUNE TOUCHE.

=====================================================================
A QUOI CA SERT
=====================================================================
C'est l'outil à utiliser pour les étapes 1 à 6 des tests, quand tu montes
le matériel morceau par morceau. Il n'initialise même pas le clavier USB :
il est donc impossible qu'il tape quelque chose dans Thonny pendant que tu
travailles.

=====================================================================
COMMENT L'UTILISER DANS THONNY
=====================================================================
Dans la zone du bas (le REPL, celle où il y a ">>>"). Tape les commandes
SANS le ">>>" : c'est l'invite, Thonny l'affiche tout seul, et la coller
avec la commande donne "SyntaxError: invalid syntax".


    import diag
    diag.run()              # 20 secondes de surveillance des entrées
    diag.run(seconds=60)    # plus long
    diag.run(led_test=True) # ajoute le test de la LED

Test par test :

    diag.keymap()               # vérifie l'AZERTY, sans matériel
    diag.keymap("_ISOLATEOBJECTS")
    diag.rgb()                  # câblage des LED RGB, une par une

Pour arrêter avant la fin : Ctrl-C, ou le bouton STOP de Thonny.
"""

import sys
from time import ticks_ms, ticks_diff, sleep_ms
import config as C


def keymap(text="_MATCHPROP"):
    """Montre comment chaque caractère sera tapé. Aucun matériel requis.

    C'est le test à faire en premier si Civil 3D reçoit des lettres
    fausses : il affiche le numéro de touche envoyé pour chaque caractère.
    """
    from layouts import character_keys, TABLES
    print("-" * 46)
    print("DISPOSITION :", C.KEYBOARD_LAYOUT,
          "(%d caracteres connus)" % len(TABLES[C.KEYBOARD_LAYOUT]))
    print("Chaine testee :", text)
    print("  Verr. Maj ETEINT :")
    for char in text:
        print("    %-4r -> %s" % (char, character_keys(char, C.KEYBOARD_LAYOUT)))
    print("  Verr. Maj ALLUME (Windows FR inverse la rangee des chiffres) :")
    for char in text[:3]:
        print("    %-4r -> %s" % (char,
                                  character_keys(char, C.KEYBOARD_LAYOUT, True)))
    print("Rappel : en AZERTY le '_' doit sortir en touche 37 sans Maj.")
    return True


def rgb(nb=None, broche=None, luminosite=12):
    """Teste le cablage des LED RGB, une LED a la fois.

    A faire APRES avoir soude et AVANT de passer RGB_ENABLED a True. Ce
    test n'utilise pas rgb.py : il parle directement aux LED, pour que ce
    soit bien TON cablage qui soit teste, et pas la configuration.

        diag.rgb()          # utilise RGB_PIN et RGB_COUNT
        diag.rgb(6, 16)     # six LED sur GPIO16

    Ce que tu dois voir, dans l'ordre :

      1. les LED s'allument UNE PAR UNE, de la premiere a la derniere.
         Compte-les : si tu en as soude six et qu'il s'en allume quatre,
         la suite du ruban ne recoit pas les donnees ;
      2. puis ROUGE, VERT, BLEU sur toutes. Si les couleurs ne
         correspondent pas aux noms annonces, note l'ordre reel et
         corrige RGB_ORDRE dans config.py ;
      3. enfin une montee en luminosite. Si la carte redemarre pendant
         cette phase, c'est le courant : condensateur manquant, ou
         alimentation trop faible.

    La luminosite est volontairement basse (12 sur 255) : on teste un
    cablage, pas un eclairage. Ne la monte pas pour "mieux voir".
    """
    from machine import Pin
    try:
        from neopixel import NeoPixel
    except ImportError:
        print("neopixel absent de ce firmware MicroPython.")
        return

    if nb is None:
        nb = getattr(C, "RGB_COUNT", 6)
    if broche is None:
        broche = getattr(C, "RGB_PIN", 16)
    print("-" * 46)
    print("TEST RGB : %d LED sur GPIO%d" % (nb, broche))
    print("Luminosite de test :", luminosite, "sur 255")
    print("-" * 46)

    bande = NeoPixel(Pin(broche, Pin.OUT), nb)

    def tout(couleur):
        for index in range(nb):
            bande[index] = couleur
        bande.write()

    try:
        # 1. Une par une : on compte, et on verifie que la chaine passe.
        print("1. Chenillard : compte les LED qui s'allument")
        for index in range(nb):
            tout((0, 0, 0))
            bande[index] = (luminosite, luminosite, luminosite)
            bande.write()
            print("   LED %d" % (index + 1))
            sleep_ms(500)

        # 2. Les trois couleurs, pour verifier l'ordre des octets.
        print("2. Couleurs : annonce -> ce que tu dois voir")
        ordre = getattr(C, "RGB_ORDRE", "GRB")
        for nom, valeurs in (("ROUGE", {"R": luminosite}),
                             ("VERT", {"G": luminosite}),
                             ("BLEU", {"B": luminosite})):
            couleur = tuple(valeurs.get(lettre, 0) for lettre in ordre)
            print("   %s   (RGB_ORDRE = %s)" % (nom, ordre))
            tout(couleur)
            sleep_ms(1200)

        # 3. Montee en luminosite : c'est ici que le courant se voit.
        print("3. Montee en luminosite - la carte doit rester stable")
        for niveau in range(0, 41, 4):
            tout((niveau, niveau, niveau))
            sleep_ms(200)
        print("   (on redescend)")
        tout((0, 0, 0))
        print("-" * 46)
        print("Si tout est bon : RGB_ENABLED = True dans config.py.")
        print("Si les couleurs sont permutees : change RGB_ORDRE.")
    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        # On n'abandonne JAMAIS les LED allumees.
        try:
            tout((0, 0, 0))
        except Exception:
            pass


def run(seconds=20, led_test=False):
    """Diagnostic complet du matériel branché."""
    import machine
    import runtime
    from inputs import Inputs
    from display import Display

    # --- 1. Informations sur le firmware ---------------------------
    print("-" * 46)
    print("MicroPython :", sys.version)
    print("Implementation :", sys.implementation)
    print("Plateforme :", sys.platform)
    # Si cette ligne affiche False, le clavier USB est impossible :
    # ce n'est pas le bon firmware.
    print("machine.USBDevice disponible :", hasattr(machine, "USBDevice"))
    print("HID initialise au boot :", runtime.interface is not None)
    print("Envois HID : DESACTIVES en diagnostic")

    # --- 2. Ecran ---------------------------------------------------
    print("I2C bus", C.I2C_ID, "SDA", C.OLED_SDA, "SCL", C.OLED_SCL)
    print("OLED : attention, un ACK I2C prouve qu'un ecran repond,")
    print("       pas que son controleur est bien un SH1106.")
    display = Display()
    display.message("DIAGNOSTIC", "HID DISABLED")
    display.flush_startup()

    # --- 3. Etat instantané des entrées ----------------------------
    controls = Inputs()
    print("Etat initial des entrees :")
    for name, item in controls.sequence:
        print("  %-9s actif = %-5s  niveau electrique = %d"
              % (name, item.active(), item.pin.value()))
    print("Au repos, tout doit afficher 'actif = False'.")
    print("Si une entree est active sans que tu y touches, verifie son cablage.")

    # --- 4. LED (facultatif) ---------------------------------------
    led = None
    if led_test:
        from led import Led
        led = Led()
        print("LED : 0-3 s a 5 %, 3-6 s a 20 %, puis respiration.")
        print("      Appuie sur ESC pour declencher le flash.")
        print("      TOUCHE la LED et la resistance : elles doivent rester froides.")

    # --- 5. Surveillance des entrées -------------------------------
    print("Actionne maintenant chaque touche, une par une (%d s) :" % seconds)
    start = ticks_ms()
    compteur = {}
    try:
        while ticks_diff(ticks_ms(), start) < int(seconds * 1000):
            now = ticks_ms()
            for name, edge in controls.poll(now):
                if edge == 1:
                    compteur[name] = compteur.get(name, 0) + 1
                    print("  %-9s APPUI/TOUCHER  (total %d)"
                          % (name, compteur[name]))
                    if led and name == "ESC":
                        led.flash(now)
                else:
                    print("  %-9s relachement" % name)
            if led:
                age = ticks_diff(now, start)
                if age < 3000:
                    led.set_level(0.05)
                elif age < 6000:
                    led.set_level(0.20)
                else:
                    led.tick(now)
            sleep_ms(5)
    except KeyboardInterrupt:
        print("  interrompu")
    finally:
        if led:
            led.close()

    # --- 6. Bilan ---------------------------------------------------
    print("Bilan des appuis detectes :")
    for name, _ in controls.sequence:
        print("  %-9s : %d" % (name, compteur.get(name, 0)))
    print("Un appui franc doit compter EXACTEMENT 1.")
    print("S'il en compte 2 ou 3 : augmente DEBOUNCE_MS dans config.py.")
    print("Diagnostic termine, retour REPL")


if __name__ == "__main__":
    run()
```

---

## device/sh1106.py

> Fichier TIERS repris sans modification (robert-hh/SH1106, MIT).

`318 lignes - sha256 a0b7c0465eb05fb7`

```python
#
# MicroPython SH1106 OLED driver, I2C and SPI interfaces
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Radomir Dopieralski (@deshipu),
#               2017-2021 Robert Hammelrath (@robert-hh)
#               2021 Tim Weber (@scy)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Sample code sections for ESP8266 pin assignments
# ------------ SPI ------------------
# Pin Map SPI
#   - 3v - xxxxxx   - Vcc
#   - G  - xxxxxx   - Gnd
#   - D7 - GPIO 13  - Din / MOSI fixed
#   - D5 - GPIO 14  - Clk / Sck fixed
#   - D8 - GPIO 4   - CS (optional, if the only connected device)
#   - D2 - GPIO 5   - D/C
#   - D1 - GPIO 2   - Res
#
# for CS, D/C and Res other ports may be chosen.
#
# from machine import Pin, SPI
# import sh1106

# spi = SPI(1, baudrate=1000000)
# display = sh1106.SH1106_SPI(128, 64, spi, Pin(5), Pin(2), Pin(4))
# display.sleep(False)
# display.fill(0)
# display.text('Testing 1', 0, 0, 1)
# display.show()
#
# --------------- I2C ------------------
#
# Pin Map I2C
#   - 3v - xxxxxx   - Vcc
#   - G  - xxxxxx   - Gnd
#   - D2 - GPIO 5   - SCK / SCL
#   - D1 - GPIO 4   - DIN / SDA
#   - D0 - GPIO 16  - Res
#   - G  - xxxxxx     CS
#   - G  - xxxxxx     D/C
#
# Pin's for I2C can be set almost arbitrary
#
# from machine import Pin, I2C
# import sh1106
#
# i2c = I2C(scl=Pin(5), sda=Pin(4), freq=400000)
# display = sh1106.SH1106_I2C(128, 64, i2c, Pin(16), 0x3c)
# display.sleep(False)
# display.fill(0)
# display.text('Testing 1', 0, 0, 1)
# display.show()

from micropython import const
import utime as time
import framebuf


# a few register definitions
_SET_CONTRAST        = const(0x81)
_SET_NORM_INV        = const(0xa6)
_SET_DISP            = const(0xae)
_SET_SCAN_DIR        = const(0xc0)
_SET_SEG_REMAP       = const(0xa0)
_LOW_COLUMN_ADDRESS  = const(0x00)
_HIGH_COLUMN_ADDRESS = const(0x10)
_SET_PAGE_ADDRESS    = const(0xB0)


class SH1106(framebuf.FrameBuffer):

    def __init__(self, width, height, external_vcc, rotate=0):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.flip_en = rotate == 180 or rotate == 270
        self.rotate90 = rotate == 90 or rotate == 270
        self.pages = self.height // 8
        self.bufsize = self.pages * self.width
        self.renderbuf = bytearray(self.bufsize)
        self.pages_to_update = 0
        self.delay = 0

        if self.rotate90:
            self.displaybuf = bytearray(self.bufsize)
            # HMSB is required to keep the bit order in the render buffer
            # compatible with byte-for-byte remapping to the display buffer,
            # which is in VLSB. Else we'd have to copy bit-by-bit!
            super().__init__(self.renderbuf, self.height, self.width,
                             framebuf.MONO_HMSB)
        else:
            self.displaybuf = self.renderbuf
            super().__init__(self.renderbuf, self.width, self.height,
                             framebuf.MONO_VLSB)

        # flip() was called rotate() once, provide backwards compatibility.
        self.rotate = self.flip
        self.init_display()

    # abstractmethod
    def write_cmd(self, *args, **kwargs): 
        raise NotImplementedError

    # abstractmethod
    def write_data(self,  *args, **kwargs):
        raise NotImplementedError

    def init_display(self):
        self.reset()
        self.fill(0)
        self.show()
        self.poweron()
        # rotate90 requires a call to flip() for setting up.
        self.flip(self.flip_en)

    def poweroff(self):
        self.write_cmd(_SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(_SET_DISP | 0x01)
        if self.delay:
            time.sleep_ms(self.delay)

    def flip(self, flag=None, update=True):
        if flag is None:
            flag = not self.flip_en
        mir_v = flag ^ self.rotate90
        mir_h = flag
        self.write_cmd(_SET_SEG_REMAP | (0x01 if mir_v else 0x00))
        self.write_cmd(_SET_SCAN_DIR | (0x08 if mir_h else 0x00))
        self.flip_en = flag
        if update:
            self.show(True) # full update

    def sleep(self, value):
        self.write_cmd(_SET_DISP | (not value))

    def contrast(self, contrast):
        self.write_cmd(_SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(_SET_NORM_INV | (invert & 1))

    def show(self, full_update = False):
        # self.* lookups in loops take significant time (~4fps).
        (w, p, db, rb) = (self.width, self.pages,
                          self.displaybuf, self.renderbuf)
        if self.rotate90:
            for i in range(self.bufsize):
                db[w * (i % p) + (i // p)] = rb[i]
        if full_update:
            pages_to_update = (1 << self.pages) - 1
        else:
            pages_to_update = self.pages_to_update
        #print("Updating pages: {:08b}".format(pages_to_update))
        for page in range(self.pages):
            if (pages_to_update & (1 << page)):
                self.write_cmd(_SET_PAGE_ADDRESS | page)
                self.write_cmd(_LOW_COLUMN_ADDRESS | 2)
                self.write_cmd(_HIGH_COLUMN_ADDRESS | 0)
                self.write_data(db[(w*page):(w*page+w)])
        self.pages_to_update = 0

    def pixel(self, x, y, color=None):
        if color is None:
            return super().pixel(x, y)
        else:
            super().pixel(x, y , color)
            page = y // 8
            self.pages_to_update |= 1 << page

    def text(self, text, x, y, color=1):
        super().text(text, x, y, color)
        self.register_updates(y, y+7)

    def line(self, x0, y0, x1, y1, color):
        super().line(x0, y0, x1, y1, color)
        self.register_updates(y0, y1)

    def hline(self, x, y, w, color):
        super().hline(x, y, w, color)
        self.register_updates(y)

    def vline(self, x, y, h, color):
        super().vline(x, y, h, color)
        self.register_updates(y, y+h-1)

    def fill(self, color):
        super().fill(color)
        self.pages_to_update = (1 << self.pages) - 1

    def blit(self, fbuf, x, y, key=-1, palette=None):
        super().blit(fbuf, x, y, key, palette)
        self.register_updates(y, y+self.height)

    def scroll(self, x, y):
        # my understanding is that scroll() does a full screen change
        super().scroll(x, y)
        self.pages_to_update =  (1 << self.pages) - 1

    def fill_rect(self, x, y, w, h, color):
        super().fill_rect(x, y, w, h, color)
        self.register_updates(y, y+h-1)

    def rect(self, x, y, w, h, color):
        super().rect(x, y, w, h, color)
        self.register_updates(y, y+h-1)

    def ellipse(self, x, y, xr, yr, color):
        super().ellipse(x, y, xr, yr, color)
        self.register_updates(y-yr, y+yr-1)

    def register_updates(self, y0, y1=None):
        # this function takes the top and optional bottom address of the changes made
        # and updates the pages_to_change list with any changed pages
        # that are not yet on the list
        start_page = max(0, y0 // 8)
        end_page = max(0, y1 // 8) if y1 is not None else start_page
        # rearrange start_page and end_page if coordinates were given from bottom to top
        if start_page > end_page:
            start_page, end_page = end_page, start_page
        for page in range(start_page, end_page+1):
            self.pages_to_update |= 1 << page

    def reset(self, res=None):
        if res is not None:
            res(1)
            time.sleep_ms(1)
            res(0)
            time.sleep_ms(20)
            res(1)
            time.sleep_ms(20)


class SH1106_I2C(SH1106):
    def __init__(self, width, height, i2c, res=None, addr=0x3c,
                 rotate=0, external_vcc=False, delay=0):
        self.i2c = i2c
        self.addr = addr
        self.res = res
        self.temp = bytearray(2)
        self.delay = delay
        if res is not None:
            res.init(res.OUT, value=1)
        super().__init__(width, height, external_vcc, rotate)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40'+buf)

    def reset(self,res=None):
        super().reset(self.res)


class SH1106_SPI(SH1106):
    def __init__(self, width, height, spi, dc, res=None, cs=None,
                 rotate=0, external_vcc=False, delay=0):
        dc.init(dc.OUT, value=0)
        if res is not None:
            res.init(res.OUT, value=0)
        if cs is not None:
            cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        self.delay = delay
        super().__init__(width, height, external_vcc, rotate)

    def write_cmd(self, cmd):
        if self.cs is not None:
            self.cs(1)
            self.dc(0)
            self.cs(0)
            self.spi.write(bytearray([cmd]))
            self.cs(1)
        else:
            self.dc(0)
            self.spi.write(bytearray([cmd]))

    def write_data(self, buf):
        if self.cs is not None:
            self.cs(1)
            self.dc(1)
            self.cs(0)
            self.spi.write(buf)
            self.cs(1)
        else:
            self.dc(1)
            self.spi.write(buf)

    def reset(self, res=None):
        super().reset(self.res)
```

---

## device/lib/usb/device/__init__.py

> Fichier TIERS repris sans modification (micropython-lib, MIT).

`2 lignes - sha256 c8d3315a67057aa5`

```python
from . import core
from .core import get  # Singleton _Device getter
```

---

## device/lib/usb/device/core.py

> Fichier TIERS repris sans modification (micropython-lib, MIT).

`885 lignes - sha256 b1402506cda2ac3d`

```python
# MicroPython Library runtime USB device implementation
#
# These contain the classes and utilities that are needed to
# implement a USB device, not any complete USB drivers.
#
# MIT license; Copyright (c) 2022-2024 Angus Gratton
from micropython import const
import machine
import struct

try:
    from _thread import get_ident
except ImportError:

    def get_ident():
        return 0  # Placeholder, for no threading support


_EP_IN_FLAG = const(1 << 7)

# USB descriptor types
_STD_DESC_DEV_TYPE = const(0x1)
_STD_DESC_CONFIG_TYPE = const(0x2)
_STD_DESC_STRING_TYPE = const(0x3)
_STD_DESC_INTERFACE_TYPE = const(0x4)
_STD_DESC_ENDPOINT_TYPE = const(0x5)
_STD_DESC_INTERFACE_ASSOC = const(0xB)

_ITF_ASSOCIATION_DESC_TYPE = const(0xB)  # Interface Association descriptor

# Standard USB descriptor lengths
_STD_DESC_CONFIG_LEN = const(9)
_STD_DESC_ENDPOINT_LEN = const(7)
_STD_DESC_INTERFACE_LEN = const(9)

_DESC_OFFSET_LEN = const(0)
_DESC_OFFSET_TYPE = const(1)

_DESC_OFFSET_INTERFACE_NUM = const(2)  # for _STD_DESC_INTERFACE_TYPE
_DESC_OFFSET_ENDPOINT_NUM = const(2)  # for _STD_DESC_ENDPOINT_TYPE

# Standard control request bmRequest fields, can extract by calling split_bmRequestType()
_REQ_RECIPIENT_DEVICE = const(0x0)
_REQ_RECIPIENT_INTERFACE = const(0x1)
_REQ_RECIPIENT_ENDPOINT = const(0x2)
_REQ_RECIPIENT_OTHER = const(0x3)

# Offsets into the standard configuration descriptor, to fixup
_OFFS_CONFIG_iConfiguration = const(6)

_INTERFACE_CLASS_VENDOR = const(0xFF)
_INTERFACE_SUBCLASS_NONE = const(0x00)
_PROTOCOL_NONE = const(0x00)

# These need to match the constants in tusb_config.h
_USB_STR_MANUF = const(0x01)
_USB_STR_PRODUCT = const(0x02)
_USB_STR_SERIAL = const(0x03)

# Error constant to match mperrno.h
_MP_EINVAL = const(22)

_dev = None  # Singleton _Device instance


def get():
    # Getter to access the singleton instance of the
    # MicroPython _Device object
    #
    # (note this isn't the low-level machine.USBDevice object, the low-level object is
    # get()._usbd.)
    global _dev
    if not _dev:
        _dev = _Device()
    return _dev


class _Device:
    # Class that implements the Python parts of the MicroPython USBDevice.
    #
    # This class should only be instantiated by the singleton getter
    # function usb.device.get(), never directly.
    def __init__(self):
        self._itfs = {}  # Mapping from interface number to interface object, set by init()
        self._eps = {}  # Mapping from endpoint address to interface object, set by _open_cb()
        self._ep_cbs = {}  # Mapping from endpoint address to Optional[xfer callback]
        self._cb_thread = None  # Thread currently running endpoint callback
        self._cb_ep = None  # Endpoint number currently running callback
        self._usbd = machine.USBDevice()  # low-level API

    def init(self, *itfs, **kwargs):
        # Helper function to configure the USB device and activate it in a single call
        self.active(False)
        self.config(*itfs, **kwargs)
        self.active(True)

    def config(  # noqa: PLR0913
        self,
        *itfs,
        builtin_driver=False,
        manufacturer_str=None,
        product_str=None,
        serial_str=None,
        configuration_str=None,
        id_vendor=None,
        id_product=None,
        bcd_device=None,
        device_class=0,
        device_subclass=0,
        device_protocol=0,
        config_str=None,
        max_power_ma=None,
        remote_wakeup=False,
    ):
        # Configure the USB device with a set of interfaces, and optionally reconfiguring the
        # device and configuration descriptor fields

        _usbd = self._usbd

        if self.active():
            raise OSError(_MP_EINVAL)  # Must set active(False) first

        # Convenience: Allow builtin_driver to be True, False or one of
        # the machine.USBDevice.BUILTIN_ constants
        if isinstance(builtin_driver, bool):
            builtin_driver = _usbd.BUILTIN_DEFAULT if builtin_driver else _usbd.BUILTIN_NONE
        _usbd.builtin_driver = builtin_driver

        # Putting None for any strings that should fall back to the "built-in" value
        # Indexes in this list depends on _USB_STR_MANUF, _USB_STR_PRODUCT, _USB_STR_SERIAL
        strs = [None, manufacturer_str, product_str, serial_str]

        # Build the device descriptor
        FMT = "<BBHBBBBHHHBBBB"
        # read the static descriptor fields
        f = struct.unpack(FMT, builtin_driver.desc_dev)

        def maybe_set(value, idx):
            # Override a numeric descriptor value or keep builtin value f[idx] if 'value' is None
            if value is not None:
                return value
            return f[idx]

        # Either copy each descriptor field directly from the builtin device descriptor, or 'maybe'
        # set it to the custom value from the object
        desc_dev = struct.pack(
            FMT,
            f[0],  # bLength
            f[1],  # bDescriptorType
            f[2],  # bcdUSB
            device_class,  # bDeviceClass
            device_subclass,  # bDeviceSubClass
            device_protocol,  # bDeviceProtocol
            f[6],  # bMaxPacketSize0, TODO: allow overriding this value?
            maybe_set(id_vendor, 7),  # idVendor
            maybe_set(id_product, 8),  # idProduct
            maybe_set(bcd_device, 9),  # bcdDevice
            _USB_STR_MANUF,  # iManufacturer
            _USB_STR_PRODUCT,  # iProduct
            _USB_STR_SERIAL,  # iSerialNumber
            1,
        )  # bNumConfigurations

        # Iterate interfaces to build the configuration descriptor

        # Keep track of the interface and endpoint indexes
        itf_num = builtin_driver.itf_max
        ep_num = max(builtin_driver.ep_max, 1)  # Endpoint 0 always reserved for control
        while len(strs) < builtin_driver.str_max:
            strs.append(None)  # Reserve other string indexes used by builtin drivers
        initial_cfg = builtin_driver.desc_cfg or (b"\x00" * _STD_DESC_CONFIG_LEN)

        self._itfs = {}

        # Determine the total length of the configuration descriptor, by making dummy
        # calls to build the config descriptor
        desc = Descriptor(None)
        desc.extend(initial_cfg)
        for itf in itfs:
            itf.desc_cfg(desc, 0, 0, [])

        # Allocate the real Descriptor helper to write into it, starting
        # after the standard configuration descriptor
        desc = Descriptor(bytearray(desc.o))
        desc.extend(initial_cfg)
        for itf in itfs:
            itf.desc_cfg(desc, itf_num, ep_num, strs)

            for _ in range(itf.num_itfs()):
                self._itfs[itf_num] = itf  # Mapping from interface numbers to interfaces
                itf_num += 1

            ep_num += itf.num_eps()

        # Go back and update the Standard Configuration Descriptor
        # header at the start with values based on the complete
        # descriptor.
        #
        # See USB 2.0 specification section 9.6.3 p264 for details.
        bmAttributes = (
            (1 << 7)  # Reserved
            | (0 if max_power_ma else (1 << 6))  # Self-Powered
            | ((1 << 5) if remote_wakeup else 0)
        )

        # Configuration string is optional but supported
        iConfiguration = 0
        if configuration_str:
            iConfiguration = len(strs)
            strs.append(configuration_str)

        if max_power_ma is not None:
            # Convert from mA to the units used in the descriptor
            max_power_ma //= 2
        else:
            try:
                # Default to whatever value the builtin driver reports
                max_power_ma = _usbd.BUILTIN_DEFAULT.desc_cfg[8]
            except IndexError:
                # If no built-in driver, default to 250mA
                max_power_ma = 125

        desc.pack_into(
            "<BBHBBBBB",
            0,
            _STD_DESC_CONFIG_LEN,  # bLength
            _STD_DESC_CONFIG_TYPE,  # bDescriptorType
            len(desc.b),  # wTotalLength
            itf_num,
            1,  # bConfigurationValue
            iConfiguration,
            bmAttributes,
            max_power_ma,
        )

        _usbd.config(
            desc_dev,
            desc.b,
            strs,
            self._open_itf_cb,
            self._reset_cb,
            self._control_xfer_cb,
            self._xfer_cb,
        )

    def active(self, *optional_value):
        # Thin wrapper around the USBDevice active() function.
        #
        # Note: active only means the USB device is available, not that it has
        # actually been connected to and configured by a USB host. Use the
        # Interface.is_open() function to check if the host has configured an
        # interface of the device.
        return self._usbd.active(*optional_value)

    def _open_itf_cb(self, desc):
        # Callback from TinyUSB lower layer, when USB host does Set
        # Configuration. Called once per interface or IAD.

        # Note that even if the configuration descriptor contains an IAD, 'desc'
        # starts from the first interface descriptor in the IAD and not the IAD
        # descriptor.

        itf_num = desc[_DESC_OFFSET_INTERFACE_NUM]
        itf = self._itfs[itf_num]

        # Scan the full descriptor:
        # - Build _eps and _ep_addr from the endpoint descriptors
        # - Find the highest numbered interface provided to the callback
        #   (which will be the first interface, unless we're scanning
        #   multiple interfaces inside an IAD.)
        offs = 0
        max_itf = itf_num
        while offs < len(desc):
            dl = desc[offs + _DESC_OFFSET_LEN]
            dt = desc[offs + _DESC_OFFSET_TYPE]
            if dt == _STD_DESC_ENDPOINT_TYPE:
                ep_addr = desc[offs + _DESC_OFFSET_ENDPOINT_NUM]
                self._eps[ep_addr] = itf
                self._ep_cbs[ep_addr] = None
            elif dt == _STD_DESC_INTERFACE_TYPE:
                max_itf = max(max_itf, desc[offs + _DESC_OFFSET_INTERFACE_NUM])
            offs += dl

        # If 'desc' is not the inside of an Interface Association Descriptor but
        # 'itf' object still represents multiple USB interfaces (i.e. MIDI),
        # defer calling 'itf.on_open()' until this callback fires for the
        # highest numbered USB interface.
        #
        # This means on_open() is only called once, and that it can
        # safely submit transfers on any of the USB interfaces' endpoints.
        if self._itfs.get(max_itf + 1, None) != itf:
            itf.on_open()

    def _reset_cb(self):
        # TinyUSB lower layer callback when the USB device is reset by the host

        # Allow interfaces to respond to the reset
        for itf in self._itfs.values():
            itf.on_reset()

        # Rebuilt when host re-enumerates
        self._eps = {}
        self._ep_cbs = {}

    def _submit_xfer(self, ep_addr, data, done_cb=None):
        # Submit a USB transfer (of any type except control) to TinyUSB lower layer.
        #
        # Generally, drivers should call Interface.submit_xfer() instead. See
        # that function for documentation about the possible parameter values.
        if ep_addr not in self._eps:
            raise ValueError("ep_addr")
        if self._xfer_pending(ep_addr):
            raise RuntimeError("xfer_pending")

        # USBDevice callback may be called immediately, before Python execution
        # continues, so set it first.
        #
        # To allow xfer_pending checks to work, store True instead of None.
        self._ep_cbs[ep_addr] = done_cb or True
        return self._usbd.submit_xfer(ep_addr, data)

    def _xfer_pending(self, ep_addr):
        # Returns True if a transfer is pending on this endpoint.
        #
        # Generally, drivers should call Interface.xfer_pending() instead. See that
        # function for more documentation.
        return self._ep_cbs[ep_addr] or (self._cb_ep == ep_addr and self._cb_thread != get_ident())

    def _xfer_cb(self, ep_addr, result, xferred_bytes):
        # Callback from TinyUSB lower layer when a transfer completes.
        cb = self._ep_cbs.get(ep_addr, None)
        self._cb_thread = get_ident()
        self._cb_ep = ep_addr  # Track while callback is running
        self._ep_cbs[ep_addr] = None

        # In most cases, 'cb' is a callback function for the transfer. Can also be:
        # - True (for a transfer with no callback)
        # - None (TinyUSB callback arrived for invalid endpoint, or no transfer.
        #   Generally unlikely, but may happen in transient states.)
        try:
            if callable(cb):
                cb(ep_addr, result, xferred_bytes)
        finally:
            self._cb_ep = None

    def _control_xfer_cb(self, stage, request):
        # Callback from TinyUSB lower layer when a control
        # transfer is in progress.
        #
        # stage determines appropriate responses (possible values
        # utils.STAGE_SETUP, utils.STAGE_DATA, utils.STAGE_ACK).
        #
        # The TinyUSB class driver framework only calls this function for
        # particular types of control transfer, other standard control transfers
        # are handled by TinyUSB itself.
        wIndex = request[4] + (request[5] << 8)
        recipient, _, _ = split_bmRequestType(request[0])

        itf = None
        result = None

        if recipient == _REQ_RECIPIENT_DEVICE:
            itf = self._itfs.get(wIndex & 0xFFFF, None)
            if itf:
                result = itf.on_device_control_xfer(stage, request)
        elif recipient == _REQ_RECIPIENT_INTERFACE:
            itf = self._itfs.get(wIndex & 0xFFFF, None)
            if itf:
                result = itf.on_interface_control_xfer(stage, request)
        elif recipient == _REQ_RECIPIENT_ENDPOINT:
            ep_num = wIndex & 0xFFFF
            itf = self._eps.get(ep_num, None)
            if itf:
                result = itf.on_endpoint_control_xfer(stage, request)

        if not itf:
            # At time this code was written, only the control transfers shown
            # above are passed to the class driver callback. See
            # invoke_class_control() in tinyusb usbd.c
            raise RuntimeError(f"Unexpected control request type {request[0]:#x}")

        # Expecting any of the following possible replies from
        # on_NNN_control_xfer():
        #
        # True - Continue transfer, no data
        # False - STALL transfer
        # Object with buffer interface - submit this data for the control transfer
        return result


class Interface:
    # Abstract base class to implement USB Interface (and associated endpoints),
    # or a collection of USB Interfaces, in Python
    #
    # (Despite the name an object of type Interface can represent multiple
    # associated interfaces, with or without an Interface Association Descriptor
    # prepended to them. Override num_itfs() if assigning >1 USB interface.)

    def __init__(self):
        self._open = False

    def desc_cfg(self, desc, itf_num, ep_num, strs):
        # Function to build configuration descriptor contents for this interface
        # or group of interfaces. This is called on each interface from
        # USBDevice.init().
        #
        # This function should insert:
        #
        # - At least one standard Interface descriptor (can call
        # - desc.interface()).
        #
        # Plus, optionally:
        #
        # - One or more endpoint descriptors (can call desc.endpoint()).
        # - An Interface Association Descriptor, prepended before.
        # - Other class-specific configuration descriptor data.
        #
        # This function is called twice per call to USBDevice.init(). The first
        # time the values of all arguments are dummies that are used only to
        # calculate the total length of the descriptor. Therefore, anything this
        # function does should be idempotent and it should add the same
        # descriptors each time. If saving interface numbers or endpoint numbers
        # for later
        #
        # Parameters:
        #
        # - desc - Descriptor helper to write the configuration descriptor bytes into.
        #   The first time this function is called 'desc' is a dummy object
        #   with no backing buffer (exists to count the number of bytes needed).
        #
        # - itf_num - First bNumInterfaces value to assign. The descriptor
        #   should contain the same number of interfaces returned by num_itfs(),
        #   starting from this value.
        #
        # - ep_num - Address of the first available endpoint number to use for
        #   endpoint descriptor addresses. Subclasses should save the
        #   endpoint addresses selected, to look up later (although note the first
        #   time this function is called, the values will be dummies.)
        #
        # - strs - list of string descriptors for this USB device. This function
        #   can append to this list, and then insert the index of the new string
        #   in the list into the configuration descriptor.
        raise NotImplementedError

    def num_itfs(self):
        # Return the number of actual USB Interfaces represented by this object
        # (as set in desc_cfg().)
        #
        # Only needs to be overridden if implementing a Interface class that
        # represents more than one USB Interface descriptor (i.e. MIDI), or an
        # Interface Association Descriptor (i.e. USB-CDC).
        return 1

    def num_eps(self):
        # Return the number of USB Endpoint numbers represented by this object
        # (as set in desc_cfg().)
        #
        # Note for each count returned by this function, the interface may
        # choose to have both an IN and OUT endpoint (i.e. IN flag is not
        # considered a value here.)
        #
        # This value can be zero, if the USB Host only communicates with this
        # interface using control transfers.
        return 0

    def on_open(self):
        # Callback called when the USB host accepts the device configuration.
        #
        # Override this function to initiate any operations that the USB interface
        # should do when the USB device is configured to the host.
        self._open = True

    def on_reset(self):
        # Callback called on every registered interface when the USB device is
        # reset by the host. This can happen when the USB device is unplugged,
        # or if the host triggers a reset for some other reason.
        #
        # Override this function to cancel any pending operations specific to
        # the interface (outstanding USB transfers are already cancelled).
        #
        # At this point, no USB functionality is available - on_open() will
        # be called later if/when the USB host re-enumerates and configures the
        # interface.
        self._open = False

    def is_open(self):
        # Returns True if the interface has been configured by the host and is in
        # active use.
        return self._open

    def on_device_control_xfer(self, stage, request):
        # Control transfer callback. Override to handle a non-standard device
        # control transfer where bmRequestType Recipient is Device, Type is
        # utils.REQ_TYPE_CLASS, and the lower byte of wIndex indicates this interface.
        #
        # (See USB 2.0 specification 9.4 Standard Device Requests, p250).
        #
        # This particular request type seems pretty uncommon for a device class
        # driver to need to handle, most hosts will not send this so most
        # implementations won't need to override it.
        #
        # Parameters:
        #
        # - stage is one of utils.STAGE_SETUP, utils.STAGE_DATA, utils.STAGE_ACK.
        #
        # - request is a memoryview into a USB request packet, as per USB 2.0
        #   specification 9.3 USB Device Requests, p250.  the memoryview is only
        #   valid while the callback is running.
        #
        # The function can call split_bmRequestType(request[0]) to split
        # bmRequestType into (Recipient, Type, Direction).
        #
        # Result, any of:
        #
        # - True to continue the request, False to STALL the endpoint.
        # - Buffer interface object to provide a buffer to the host as part of the
        #   transfer, if applicable.
        return False

    def on_interface_control_xfer(self, stage, request):
        # Control transfer callback. Override to handle a device control
        # transfer where bmRequestType Recipient is Interface, and the lower byte
        # of wIndex indicates this interface.
        #
        # (See USB 2.0 specification 9.4 Standard Device Requests, p250).
        #
        # bmRequestType Type field may have different values. It's not necessary
        # to handle the mandatory Standard requests (bmRequestType Type ==
        # utils.REQ_TYPE_STANDARD), if the driver returns False in these cases then
        # TinyUSB will provide the necessary responses.
        #
        # See on_device_control_xfer() for a description of the arguments and
        # possible return values.
        return False

    def on_endpoint_control_xfer(self, stage, request):
        # Control transfer callback. Override to handle a device
        # control transfer where bmRequestType Recipient is Endpoint and
        # the lower byte of wIndex indicates an endpoint address associated
        # with this interface.
        #
        # bmRequestType Type will generally have any value except
        # utils.REQ_TYPE_STANDARD, as Standard endpoint requests are handled by
        # TinyUSB. The exception is the the Standard "Set Feature" request. This
        # is handled by Tiny USB but also passed through to the driver in case it
        # needs to change any internal state, but most drivers can ignore and
        # return False in this case.
        #
        # (See USB 2.0 specification 9.4 Standard Device Requests, p250).
        #
        # See on_device_control_xfer() for a description of the parameters and
        # possible return values.
        return False

    def xfer_pending(self, ep_addr):
        # Return True if a transfer is already pending on ep_addr.
        #
        # Only one transfer can be submitted at a time.
        #
        # The transfer is marked pending while a completion callback is running
        # for that endpoint, unless this function is called from the callback
        # itself. This makes it simple to submit a new transfer from the
        # completion callback.
        return _dev and _dev._xfer_pending(ep_addr)

    def submit_xfer(self, ep_addr, data, done_cb=None):
        # Submit a USB transfer (of any type except control)
        #
        # Parameters:
        #
        # - ep_addr. Address of the endpoint to submit the transfer on. Caller is
        #   responsible for ensuring that ep_addr is correct and belongs to this
        #   interface. Only one transfer can be active at a time on each endpoint.
        #
        # - data. Buffer containing data to send, or for data to be read into
        #   (depending on endpoint direction).
        #
        # - done_cb. Optional callback function for when the transfer completes.
        # The callback is called with arguments (ep_addr, result, xferred_bytes)
        # where result is an integer equal to one of machine.USBDevice.XFER_nnn
        # enums, and xferred_bytes is an integer.
        #
        # If the function returns, the transfer is queued.
        #
        # The function will raise RuntimeError under the following conditions:
        #
        # - The interface is not "open" (i.e. has not been enumerated and configured
        #   by the host yet.)
        #
        # - A transfer is already pending on this endpoint (use xfer_pending() to check
        #   before sending if needed.)
        #
        # - A DCD error occurred when queueing the transfer on the hardware.
        #
        #
        # Will raise TypeError if 'data' isn't he correct type of buffer for the
        # endpoint transfer direction.
        #
        # Note that done_cb may be called immediately, possibly before this
        # function has returned to the caller.
        if not self._open:
            raise RuntimeError("Not open")
        if not _dev._submit_xfer(ep_addr, data, done_cb):
            raise RuntimeError("DCD error")

    def stall(self, ep_addr, *args):
        # Set or get the endpoint STALL state.
        #
        # To get endpoint stall stage, call with a single argument.
        # To set endpoint stall state, call with an additional boolean
        # argument to set or clear.
        #
        # Generally endpoint STALL is handled automatically, but there are some
        # device classes that need to explicitly stall or un-stall an endpoint
        # under certain conditions.
        if not self._open or ep_addr not in self._eps:
            raise RuntimeError
        _dev._usbd.stall(ep_addr, *args)


class Descriptor:
    # Wrapper class for writing a descriptor in-place into a provided buffer
    #
    # Doesn't resize the buffer.
    #
    # Can be initialised with b=None to perform a dummy pass that calculates the
    # length needed for the buffer.
    def __init__(self, b):
        self.b = b
        self.o = 0  # offset of data written to the buffer

    def pack(self, fmt, *args):
        # Utility function to pack new data into the descriptor
        # buffer, starting at the current offset.
        #
        # Arguments are the same as struct.pack(), but it fills the
        # pre-allocated descriptor buffer (growing if needed), instead of
        # returning anything.
        self.pack_into(fmt, self.o, *args)

    def pack_into(self, fmt, offs, *args):
        # Utility function to pack new data into the descriptor at offset 'offs'.
        #
        # If the data written is before 'offs' then self.o isn't incremented,
        # otherwise it's incremented to point at the end of the written data.
        end = offs + struct.calcsize(fmt)
        if self.b:
            struct.pack_into(fmt, self.b, offs, *args)
        self.o = max(self.o, end)

    def extend(self, a):
        # Extend the descriptor with some bytes-like data
        if self.b:
            self.b[self.o : self.o + len(a)] = a
        self.o += len(a)

    # TODO: At the moment many of these arguments are named the same as the relevant field
    # in the spec, as this is easier to understand. Can save some code size by collapsing them
    # down.

    def interface(
        self,
        bInterfaceNumber,
        bNumEndpoints,
        bInterfaceClass=_INTERFACE_CLASS_VENDOR,
        bInterfaceSubClass=_INTERFACE_SUBCLASS_NONE,
        bInterfaceProtocol=_PROTOCOL_NONE,
        iInterface=0,
    ):
        # Utility function to append a standard Interface descriptor, with
        # the properties specified in the parameter list.
        #
        # Defaults for bInterfaceClass, SubClass and Protocol are a "vendor"
        # device.
        #
        # Note that iInterface is a string index number. If set, it should be set
        # by the caller Interface to the result of self._get_str_index(s),
        # where 's' is a string found in self.strs.
        self.pack(
            "BBBBBBBBB",
            _STD_DESC_INTERFACE_LEN,  # bLength
            _STD_DESC_INTERFACE_TYPE,  # bDescriptorType
            bInterfaceNumber,
            0,  # bAlternateSetting, not currently supported
            bNumEndpoints,
            bInterfaceClass,
            bInterfaceSubClass,
            bInterfaceProtocol,
            iInterface,
        )

    def endpoint(self, bEndpointAddress, bmAttributes, wMaxPacketSize, bInterval=1):
        # Utility function to append a standard Endpoint descriptor, with
        # the properties specified in the parameter list.
        #
        # See USB 2.0 specification section 9.6.6 Endpoint p269
        #
        # As well as a numeric value, bmAttributes can be a string value to represent
        # common endpoint types: "control", "bulk", "interrupt".
        if bmAttributes == "control":
            bmAttributes = 0
        elif bmAttributes == "bulk":
            bmAttributes = 2
        elif bmAttributes == "interrupt":
            bmAttributes = 3

        self.pack(
            "<BBBBHB",
            _STD_DESC_ENDPOINT_LEN,
            _STD_DESC_ENDPOINT_TYPE,
            bEndpointAddress,
            bmAttributes,
            wMaxPacketSize,
            bInterval,
        )

    def interface_assoc(
        self,
        bFirstInterface,
        bInterfaceCount,
        bFunctionClass,
        bFunctionSubClass,
        bFunctionProtocol=_PROTOCOL_NONE,
        iFunction=0,
    ):
        # Utility function to append an Interface Association descriptor,
        # with the properties specified in the parameter list.
        #
        # See USB ECN: Interface Association Descriptor.
        self.pack(
            "<BBBBBBBB",
            8,
            _ITF_ASSOCIATION_DESC_TYPE,
            bFirstInterface,
            bInterfaceCount,
            bFunctionClass,
            bFunctionSubClass,
            bFunctionProtocol,
            iFunction,
        )


def split_bmRequestType(bmRequestType):
    # Utility function to split control transfer field bmRequestType into a tuple of 3 fields:
    #
    # Recipient
    # Type
    # Data transfer direction
    #
    # See USB 2.0 specification section 9.3 USB Device Requests and 9.3.1 bmRequestType, p248.
    return (
        bmRequestType & 0x1F,
        (bmRequestType >> 5) & 0x03,
        (bmRequestType >> 7) & 0x01,
    )


class Buffer:
    # An interrupt-safe producer/consumer buffer that wraps a bytearray object.
    #
    # Kind of like a ring buffer, but supports the idea of returning a
    # memoryview for either read or write of multiple bytes (suitable for
    # passing to a buffer function without needing to allocate another buffer to
    # read into.)
    #
    # Consumer can call pend_read() to get a memoryview to read from, and then
    # finish_read(n) when done to indicate it read 'n' bytes from the
    # memoryview. There is also a readinto() convenience function.
    #
    # Producer must call pend_write() to get a memorybuffer to write into, and
    # then finish_write(n) when done to indicate it wrote 'n' bytes into the
    # memoryview. There is also a normal write() convenience function.
    #
    # - Only one producer and one consumer is supported.
    #
    # - Calling pend_read() and pend_write() is effectively idempotent, they can be
    #   called more than once without a corresponding finish_x() call if necessary
    #   (provided only one thread does this, as per the previous point.)
    #
    # - Calling finish_write() and finish_read() is hard interrupt safe (does
    #   not allocate). pend_read() and pend_write() each allocate 1 block for
    #   the memoryview that is returned.
    #
    # The buffer contents are always laid out as:
    #
    # - Slice [:_n] = bytes of valid data waiting to read
    # - Slice [_n:_w] = unused space
    # - Slice [_w:] = bytes of pending write buffer waiting to be written
    #
    # This buffer should be fast when most reads and writes are balanced and use
    # the whole buffer. When this doesn't happen, performance degrades to
    # approximate a Python-based single byte ringbuffer.
    #
    def __init__(self, length):
        self._b = memoryview(bytearray(length))
        # number of bytes in buffer read to read, starting at index 0. Updated
        # by both producer & consumer.
        self._n = 0
        # start index of a pending write into the buffer, if any. equals
        # len(self._b) if no write is pending. Updated by producer only.
        self._w = length

    def writable(self):
        # Number of writable bytes in the buffer. Assumes no pending write is outstanding.
        return len(self._b) - self._n

    def readable(self):
        # Number of readable bytes in the buffer. Assumes no pending read is outstanding.
        return self._n

    def pend_write(self, wmax=None):
        # Returns a memoryview that the producer can write bytes into.
        # start the write at self._n, the end of data waiting to read
        #
        # If wmax is set then the memoryview is pre-sliced to be at most
        # this many bytes long.
        #
        # (No critical section needed as self._w is only updated by the producer.)
        self._w = self._n
        end = (self._w + wmax) if wmax else len(self._b)
        return self._b[self._w : end]

    def finish_write(self, nbytes):
        # Called by the producer to indicate it wrote nbytes into the buffer.
        ist = machine.disable_irq()
        try:
            assert nbytes <= len(self._b) - self._w  # can't say we wrote more than was pended
            if self._n == self._w:
                # no data was read while the write was happening, so the buffer is already in place
                # (this is the fast path)
                self._n += nbytes
            else:
                # Slow path: data was read while the write was happening, so
                # shuffle the newly written bytes back towards index 0 to avoid fragmentation
                #
                # As this updates self._n we have to do it in the critical
                # section, so do it byte by byte to avoid allocating.
                while nbytes > 0:
                    self._b[self._n] = self._b[self._w]
                    self._n += 1
                    self._w += 1
                    nbytes -= 1

            self._w = len(self._b)
        finally:
            machine.enable_irq(ist)

    def write(self, w):
        # Helper method for the producer to write into the buffer in one call
        pw = self.pend_write()
        to_w = min(len(w), len(pw))
        if to_w:
            pw[:to_w] = w[:to_w]
            self.finish_write(to_w)
        return to_w

    def pend_read(self):
        # Return a memoryview slice that the consumer can read bytes from
        return self._b[: self._n]

    def finish_read(self, nbytes):
        # Called by the consumer to indicate it read nbytes from the buffer.
        if not nbytes:
            return
        ist = machine.disable_irq()
        try:
            assert nbytes <= self._n  # can't say we read more than was available
            i = 0
            self._n -= nbytes
            while i < self._n:
                # consumer only read part of the buffer, so shuffle remaining
                # read data back towards index 0 to avoid fragmentation
                self._b[i] = self._b[i + nbytes]
                i += 1
        finally:
            machine.enable_irq(ist)

    def readinto(self, b):
        # Helper method for the consumer to read out of the buffer in one call
        pr = self.pend_read()
        to_r = min(len(pr), len(b))
        if to_r:
            b[:to_r] = pr[:to_r]
            self.finish_read(to_r)
        return to_r
```

---

## device/lib/usb/device/hid.py

> Fichier TIERS repris sans modification (micropython-lib, MIT).

`248 lignes - sha256 16a5226a9d7909f2`

```python
# MicroPython USB hid module
#
# This implements a base HIDInterface class that can be used directly,
# or subclassed into more specific HID interface types.
#
# MIT license; Copyright (c) 2023 Angus Gratton
from micropython import const
import machine
import struct
import time
from .core import Interface, Descriptor, split_bmRequestType

_EP_IN_FLAG = const(1 << 7)

# Control transfer stages
_STAGE_IDLE = const(0)
_STAGE_SETUP = const(1)
_STAGE_DATA = const(2)
_STAGE_ACK = const(3)

# Request types
_REQ_TYPE_STANDARD = const(0x0)
_REQ_TYPE_CLASS = const(0x1)
_REQ_TYPE_VENDOR = const(0x2)
_REQ_TYPE_RESERVED = const(0x3)

# Descriptor types
_DESC_HID_TYPE = const(0x21)
_DESC_REPORT_TYPE = const(0x22)
_DESC_PHYSICAL_TYPE = const(0x23)

# Interface and protocol identifiers
_INTERFACE_CLASS = const(0x03)
_INTERFACE_SUBCLASS_NONE = const(0x00)
_INTERFACE_SUBCLASS_BOOT = const(0x01)

# These values will only make sense when interface subclass
# is 0x01, which indicates boot protocol support.
_INTERFACE_PROTOCOL_NONE = const(0x00)
_INTERFACE_PROTOCOL_KEYBOARD = const(0x01)
_INTERFACE_PROTOCOL_MOUSE = const(0x02)

# bRequest values for HID control requests
_REQ_CONTROL_GET_REPORT = const(0x01)
_REQ_CONTROL_GET_IDLE = const(0x02)
_REQ_CONTROL_GET_PROTOCOL = const(0x03)
_REQ_CONTROL_GET_DESCRIPTOR = const(0x06)
_REQ_CONTROL_SET_REPORT = const(0x09)
_REQ_CONTROL_SET_IDLE = const(0x0A)
_REQ_CONTROL_SET_PROTOCOL = const(0x0B)

# Standard descriptor lengths
_STD_DESC_INTERFACE_LEN = const(9)
_STD_DESC_ENDPOINT_LEN = const(7)


class HIDInterface(Interface):
    # Abstract base class to implement a USB device HID interface in Python.

    def __init__(
        self,
        report_descriptor,
        extra_descriptors=[],
        set_report_buf=None,
        protocol=_INTERFACE_PROTOCOL_NONE,
        interface_str=None,
        interval_ms=8,
    ):
        # Construct a new HID interface.
        #
        # - report_descriptor is the only mandatory argument, which is the binary
        # data consisting of the HID Report Descriptor. See Device Class
        # Definition for Human Interface Devices (HID) v1.11 section 6.2.2 Report
        # Descriptor, p23.
        #
        # - extra_descriptors is an optional argument holding additional HID
        #   descriptors, to append after the mandatory report descriptor. Most
        #   HID devices do not use these.
        #
        # - set_report_buf is an optional writable buffer object (i.e.
        #   bytearray), where SET_REPORT requests from the host can be
        #   written. Only necessary if the report_descriptor contains Output
        #   entries. If set, the size must be at least the size of the largest
        #   Output entry.
        #
        # - protocol can be set to a specific value as per HID v1.11 section 4.3 Protocols, p9.
        #
        # - interface_str is an optional string descriptor to associate with the HID USB interface.
        #
        # - interval_ms this is the polling rate the device will request the host use in milliseconds.
        super().__init__()
        self.report_descriptor = report_descriptor
        self.extra_descriptors = extra_descriptors
        self._set_report_buf = set_report_buf
        self.protocol = protocol
        self.interface_str = interface_str
        self.interval_ms = interval_ms

        self._int_ep = None  # set during enumeration

    def get_report(self):
        return False

    def on_set_report(self, report_data, report_id, report_type):
        # Override this function in order to handle SET REPORT requests from the host,
        # where it sends data to the HID device.
        #
        # This function will only be called if the Report descriptor contains at least one Output entry,
        # and the set_report_buf argument is provided to the constructor.
        #
        # Return True to complete the control transfer normally, False to abort it.
        return True

    def busy(self):
        # Returns True if the interrupt endpoint is busy (i.e. existing transfer is pending)
        return self.is_open() and self.xfer_pending(self._int_ep)

    def send_report(self, report_data, timeout_ms=100):
        # Helper function to send a HID report in the typical USB interrupt
        # endpoint associated with a HID interface.
        #
        # Returns True if successful, False if HID device is not active or timeout
        # is reached without being able to queue the report for sending.
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while self.busy():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return False
            machine.idle()
        if not self.is_open():
            return False
        self.submit_xfer(self._int_ep, report_data)
        return True

    def desc_cfg(self, desc, itf_num, ep_num, strs):
        # Add the standard interface descriptor
        desc.interface(
            itf_num,
            1,
            _INTERFACE_CLASS,
            _INTERFACE_SUBCLASS_NONE
            if self.protocol == _INTERFACE_PROTOCOL_NONE
            else _INTERFACE_SUBCLASS_BOOT,
            self.protocol,
            len(strs) if self.interface_str else 0,
        )

        if self.interface_str:
            strs.append(self.interface_str)

        # As per HID v1.11 section 7.1 Standard Requests, return the contents of
        # the standard HID descriptor before the associated endpoint descriptor.
        self.get_hid_descriptor(desc)

        # Add the typical single USB interrupt endpoint descriptor associated
        # with a HID interface.
        self._int_ep = ep_num | _EP_IN_FLAG
        desc.endpoint(self._int_ep, "interrupt", 8, self.interval_ms)

        self.idle_rate = 0

        # This variable is reused to track boot protocol status.
        # 0 for boot protocol, 1 for report protocol
        # According to Device Class Definition for Human Interface Devices (HID) v1.11
        # Appendix F.5, the device comes up in non-boot mode by default.
        self.protocol = 1

    def num_eps(self):
        return 1

    def get_hid_descriptor(self, desc=None):
        # Append a full USB HID descriptor from the object's report descriptor
        # and optional additional descriptors.
        #
        # See HID Specification Version 1.1, Section 6.2.1 HID Descriptor p22

        l = 9 + 3 * len(self.extra_descriptors)  # total length

        if desc is None:
            desc = Descriptor(bytearray(l))

        desc.pack(
            "<BBHBBBH",
            l,  # bLength
            _DESC_HID_TYPE,  # bDescriptorType
            0x111,  # bcdHID
            0,  # bCountryCode
            len(self.extra_descriptors) + 1,  # bNumDescriptors
            0x22,  # bDescriptorType, Report
            len(self.report_descriptor),  # wDescriptorLength, Report
        )
        # Fill in any additional descriptor type/length pairs
        #
        # TODO: unclear if this functionality is ever used, may be easier to not
        # support in base class
        for dt, dd in self.extra_descriptors:
            desc.pack("<BH", dt, len(dd))

        return desc.b

    def on_interface_control_xfer(self, stage, request):
        # Handle standard and class-specific interface control transfers for HID devices.
        bmRequestType, bRequest, wValue, _, wLength = struct.unpack("BBHHH", request)

        recipient, req_type, _ = split_bmRequestType(bmRequestType)

        if stage == _STAGE_SETUP:
            if req_type == _REQ_TYPE_STANDARD:
                # HID Spec p48: 7.1 Standard Requests
                if bRequest == _REQ_CONTROL_GET_DESCRIPTOR:
                    desc_type = wValue >> 8
                    if desc_type == _DESC_HID_TYPE:
                        return self.get_hid_descriptor()
                    if desc_type == _DESC_REPORT_TYPE:
                        # Reset to report protocol when report descriptor is requested
                        self.protocol = 1
                        return self.report_descriptor
            elif req_type == _REQ_TYPE_CLASS:
                # HID Spec p50: 7.2 Class-Specific Requests
                if bRequest == _REQ_CONTROL_GET_REPORT:
                    print("GET_REPORT?")
                    return False  # Unsupported for now
                if bRequest == _REQ_CONTROL_GET_IDLE:
                    return bytes([self.idle_rate])
                if bRequest == _REQ_CONTROL_GET_PROTOCOL:
                    return bytes([self.protocol])
                if bRequest in (_REQ_CONTROL_SET_IDLE, _REQ_CONTROL_SET_PROTOCOL):
                    return True
                if bRequest == _REQ_CONTROL_SET_REPORT:
                    return self._set_report_buf  # If None, request will stall
            return False  # Unsupported request

        if stage == _STAGE_ACK:
            if req_type == _REQ_TYPE_CLASS:
                if bRequest == _REQ_CONTROL_SET_IDLE:
                    self.idle_rate = wValue >> 8
                elif bRequest == _REQ_CONTROL_SET_PROTOCOL:
                    self.protocol = wValue
                elif bRequest == _REQ_CONTROL_SET_REPORT:
                    report_id = wValue & 0xFF
                    report_type = wValue >> 8
                    report_data = self._set_report_buf
                    if wLength < len(report_data):
                        # need to truncate the response in the callback if we got less bytes
                        # than allowed for in the buffer
                        report_data = memoryview(self._set_report_buf)[:wLength]
                    self.on_set_report(report_data, report_id, report_type)

        return True  # allow DATA/ACK stages to complete normally
```

---

## device/lib/usb/device/keyboard.py

> Fichier TIERS repris sans modification (micropython-lib, MIT).

`239 lignes - sha256 8e6fd53c299a34b5`

```python
# MIT license; Copyright (c) 2023-2024 Angus Gratton
from micropython import const
import time
import usb.device
from usb.device.hid import HIDInterface

_INTERFACE_PROTOCOL_KEYBOARD = const(0x01)

_KEY_ARRAY_LEN = const(6)  # Size of HID key array, must match report descriptor
_KEY_REPORT_LEN = const(_KEY_ARRAY_LEN + 2)  # Modifier Byte + Reserved Byte + Array entries


class KeyboardInterface(HIDInterface):
    # Synchronous USB keyboard HID interface

    def __init__(self):
        super().__init__(
            _KEYBOARD_REPORT_DESC,
            set_report_buf=bytearray(1),
            protocol=_INTERFACE_PROTOCOL_KEYBOARD,
            interface_str="MicroPython Keyboard",
        )
        self._key_reports = [
            bytearray(_KEY_REPORT_LEN),
            bytearray(_KEY_REPORT_LEN),
        ]  # Ping/pong report buffers
        self.numlock = False

    def on_set_report(self, report_data, _report_id, _report_type):
        self.on_led_update(report_data[0])

    def on_led_update(self, led_mask):
        # Override to handle keyboard LED updates. led_mask is bitwise ORed
        # together values as defined in LEDCode.
        pass

    def send_keys(self, down_keys, timeout_ms=100):
        # Update the state of the keyboard by sending a report with down_keys
        # set, where down_keys is an iterable (list or similar) of integer
        # values such as the values defined in KeyCode.
        #
        # Will block for up to timeout_ms if a previous report is still
        # pending to be sent to the host. Returns True on success.
        #
        # After passing a keycode value in down_keys, it's necessary to call the
        # function again without that key code set in order to release the key.
        #
        # Calling send_keys(()) (i.e. empty down_keys argument) will release all
        # keys.

        r, s = self._key_reports  # next report buffer to send, spare report buffer
        r[0] = 0  # modifier byte
        i = 2  # index for next key array item to write to
        for k in down_keys:
            if k < 0:  # Modifier key
                r[0] |= -k
            elif i < _KEY_REPORT_LEN:
                r[i] = k
                i += 1
            else:  # Excess rollover! Can't report
                r[0] = 0
                for i in range(2, _KEY_REPORT_LEN):
                    r[i] = 0xFF
                break

        while i < _KEY_REPORT_LEN:
            r[i] = 0
            i += 1

        if self.send_report(r, timeout_ms):
            # Swap buffers if the previous one is newly queued to send, so
            # any subsequent call can't modify that buffer mid-send
            self._key_reports[0] = s
            self._key_reports[1] = r
            return True
        return False


# HID keyboard report descriptor
#
# From p69 of http://www.usb.org/developers/devclass_docs/HID1_11.pdf
#
# fmt: off
_KEYBOARD_REPORT_DESC = (
    b'\x05\x01'     # Usage Page (Generic Desktop),
        b'\x09\x06'     # Usage (Keyboard),
    b'\xA1\x01'     # Collection (Application),
        b'\x05\x07'         # Usage Page (Key Codes);
            b'\x19\xE0'         # Usage Minimum (224),
            b'\x29\xE7'         # Usage Maximum (231),
            b'\x15\x00'         # Logical Minimum (0),
            b'\x25\x01'         # Logical Maximum (1),
            b'\x75\x01'         # Report Size (1),
            b'\x95\x08'         # Report Count (8),
            b'\x81\x02'         # Input (Data, Variable, Absolute), ;Modifier byte
            b'\x95\x01'         # Report Count (1),
            b'\x75\x08'         # Report Size (8),
            b'\x81\x01'         # Input (Constant), ;Reserved byte
            b'\x95\x05'         # Report Count (5),
            b'\x75\x01'         # Report Size (1),
        b'\x05\x08'         # Usage Page (Page# for LEDs),
            b'\x19\x01'         # Usage Minimum (1),
            b'\x29\x05'         # Usage Maximum (5),
            b'\x91\x02'         # Output (Data, Variable, Absolute), ;LED report
            b'\x95\x01'         # Report Count (1),
            b'\x75\x03'         # Report Size (3),
            b'\x91\x01'         # Output (Constant), ;LED report padding
            b'\x95\x06'         # Report Count (6),
            b'\x75\x08'         # Report Size (8),
            b'\x15\x00'         # Logical Minimum (0),
            b'\x25\x65'         # Logical Maximum(101),
        b'\x05\x07'         # Usage Page (Key Codes),
            b'\x19\x00'         # Usage Minimum (0),
            b'\x29\x65'         # Usage Maximum (101),
            b'\x81\x00'         # Input (Data, Array), ;Key arrays (6 bytes)
    b'\xC0'     # End Collection
)
# fmt: on


# Standard HID keycodes, as a pseudo-enum class for easy access
#
# Modifier keys are encoded as negative values
class KeyCode:
    A = 4
    B = 5
    C = 6
    D = 7
    E = 8
    F = 9
    G = 10
    H = 11
    I = 12
    J = 13
    K = 14
    L = 15
    M = 16
    N = 17
    O = 18
    P = 19
    Q = 20
    R = 21
    S = 22
    T = 23
    U = 24
    V = 25
    W = 26
    X = 27
    Y = 28
    Z = 29
    N1 = 30  # Standard number row keys
    N2 = 31
    N3 = 32
    N4 = 33
    N5 = 34
    N6 = 35
    N7 = 36
    N8 = 37
    N9 = 38
    N0 = 39
    ENTER = 40
    ESCAPE = 41
    BACKSPACE = 42
    TAB = 43
    SPACE = 44
    MINUS = 45  # - _
    EQUAL = 46  # = +
    OPEN_BRACKET = 47  # [ {
    CLOSE_BRACKET = 48  # ] }
    BACKSLASH = 49  # \ |
    HASH = 50  # # ~
    SEMICOLON = 51  # ; :
    QUOTE = 52  # ' "
    GRAVE = 53  # ` ~
    COMMA = 54  # , <
    DOT = 55  # . >
    SLASH = 56  # / ?
    CAPS_LOCK = 57
    F1 = 58
    F2 = 59
    F3 = 60
    F4 = 61
    F5 = 62
    F6 = 63
    F7 = 64
    F8 = 65
    F9 = 66
    F10 = 67
    F11 = 68
    F12 = 69
    PRINTSCREEN = 70
    SCROLL_LOCK = 71
    PAUSE = 72
    INSERT = 73
    HOME = 74
    PAGEUP = 75
    DELETE = 76
    END = 77
    PAGEDOWN = 78
    RIGHT = 79  # Arrow keys
    LEFT = 80
    DOWN = 81
    UP = 82
    KP_NUM_LOCK = 83
    KP_DIVIDE = 84
    KP_AT = 85
    KP_MULTIPLY = 85
    KP_MINUS = 86
    KP_PLUS = 87
    KP_ENTER = 88
    KP_1 = 89
    KP_2 = 90
    KP_3 = 91
    KP_4 = 92
    KP_5 = 93
    KP_6 = 94
    KP_7 = 95
    KP_8 = 96
    KP_9 = 97
    KP_0 = 98

    # HID modifier values (negated to allow them to be passed along with the normal keys)
    LEFT_CTRL = -0x01
    LEFT_SHIFT = -0x02
    LEFT_ALT = -0x04
    LEFT_UI = -0x08
    RIGHT_CTRL = -0x10
    RIGHT_SHIFT = -0x20
    RIGHT_ALT = -0x40
    RIGHT_UI = -0x80


# HID LED values
class LEDCode:
    NUM_LOCK = 0x01
    CAPS_LOCK = 0x02
    SCROLL_LOCK = 0x04
    COMPOSE = 0x08
    KANA = 0x10
```

