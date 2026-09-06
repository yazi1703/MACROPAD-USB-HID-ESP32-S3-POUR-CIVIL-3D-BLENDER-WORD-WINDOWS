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
- [`device/layouts.py`](#devicelayoutspy)
- [`device/hid_keyboard.py`](#devicehidkeyboardpy)
- [`device/display.py`](#devicedisplaypy)
- [`device/led.py`](#deviceledpy)
- [`device/diag.py`](#devicediagpy)
- [`device/sh1106.py`](#devicesh1106py)
- [`device/lib/usb/device/__init__.py`](#devicelibusbdeviceinitpy)
- [`device/lib/usb/device/core.py`](#devicelibusbdevicecorepy)
- [`device/lib/usb/device/hid.py`](#devicelibusbdevicehidpy)
- [`device/lib/usb/device/keyboard.py`](#devicelibusbdevicekeyboardpy)


---

## device/config.py

`150 lignes - sha256 a9849560ceb3030a`

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

# Les quatre touches mécaniques. Chaque interrupteur relie sa broche à GND.
# B1 (le premier de la liste) sert aussi de bouton SAFE MODE au démarrage.
BUTTON_PINS = (4, 5, 6, 7)

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
# 5. TEMPS ET REACTIVITE (millisecondes)
# =====================================================================
# Délai entre la mise sous tension et la prise en compte des touches.
# Sert de filet : si une macro devenait folle, tu as 2,5 s pour débrancher.
BOOT_GUARD_MS = 2500

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

`140 lignes - sha256 bca35cac5d37ae1e`

```python
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
```

---

## device/boot.py

`65 lignes - sha256 face5bf5a227dc79`

```python
# -*- coding: utf-8 -*-
"""
boot.py - Premier fichier exécuté par MicroPython au démarrage.

=====================================================================
POURQUOI CE FICHIER EST AUSSI COURT
=====================================================================
boot.py s'exécute AVANT tout le reste et avant que le REPL ne soit
disponible. S'il plante ou s'il part en boucle, la carte devient
pénible à récupérer. On y met donc le strict minimum.

Il fait exactement trois choses :

1. Il éteint la LED du bouton ESC. Au démarrage un GPIO est dans un état
   indéfini ; on force un 0 franc pour que la LED ne s'allume pas
   bêtement pendant l'initialisation.

2. Il regarde si tu maintiens B1 : c'est le SAFE MODE.
   En SAFE MODE, le clavier USB n'est même pas créé. Il devient donc
   physiquement impossible que le macropad tape quoi que ce soit, même si
   une macro est mal écrite. C'est ton filet de secours.

3. Si tout va bien et si HID_ENABLED est True, il déclare le clavier USB
   à Windows. AUCUNE TOUCHE N'EST ENVOYEE ICI : on se contente d'exister
   en tant que clavier.

Ensuite MicroPython lance main.py.
"""

from machine import Pin
from time import sleep_ms
import config as C
import runtime

# --- 1. LED éteinte, quoi qu'il arrive -------------------------------
Pin(C.LED_PIN, Pin.OUT, value=0)

# --- 2. Détection du SAFE MODE ---------------------------------------
# La résistance de tirage interne met la broche à 3,3 V (valeur 1).
# Appuyer sur B1 la relie à la masse (valeur 0).
# On laisse 5 ms à la broche pour se stabiliser, puis on lit trois fois :
# un seul parasite ne doit pas nous faire croire à un appui.
_b1 = Pin(C.BUTTON_PINS[0], Pin.IN, Pin.PULL_UP)
sleep_ms(5)
runtime.safe_mode = True
for _ in range(3):
    if _b1.value() != 0:
        runtime.safe_mode = False
        break
    sleep_ms(3)

# --- 3. Création du clavier USB, ou pas ------------------------------
if runtime.safe_mode:
    print("SAFE MODE - HID DISABLED")
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

`190 lignes - sha256 e454df76b4f4b0c9`

```python
# -*- coding: utf-8 -*-
"""
main.py - Le chef d'orchestre. Lancé automatiquement après boot.py.

=====================================================================
LE PRINCIPE : UNE SEULE BOUCLE, JAMAIS D'ATTENTE
=====================================================================
Tout le macropad tient dans une seule boucle qui tourne environ 500 fois
par seconde. À chaque tour, on fait un tout petit peu de chaque travail :

    1. lire les entrées          (quelques microsecondes)
    2. traiter ESC en priorité
    3. traiter les profils et les macros
    4. envoyer AU PLUS un paquet clavier
    5. mettre à jour la LED
    6. envoyer AU PLUS une page d'écran
    7. dormir 2 ms, et on recommence

C'est ce qu'on appelle une boucle coopérative : chaque tâche prend un
petit morceau de temps puis rend la main volontairement. Aucune tâche ne
peut donc bloquer les autres. C'est pour cela qu'écrire une commande de
16 caractères (400 ms) n'empêche jamais le bouton ESC de répondre.

L'ordre des étapes n'est pas anodin : ESC est traité en tout premier.

=====================================================================
LES TROIS SECURITES AU DEMARRAGE
=====================================================================
1. boot.py n'a même pas créé le clavier si tu maintenais B1 (SAFE MODE).
2. Toutes les macros sont traduites AVANT la première touche : une macro
   mal écrite fait échouer le démarrage avec un message clair, plutôt que
   de taper n'importe quoi.
3. Pendant BOOT_GUARD_MS (2,5 s), les touches sont ignorées. Tu as le
   temps de débrancher si quelque chose se passe mal.
"""

from time import ticks_ms, ticks_diff, sleep_ms
import config as C
import runtime
from inputs import Inputs
from profiles import ProfileManager, PROFILES, TESTS
from display import Display
from hid_keyboard import HIDKeyboard
from layouts import compile_actions


def run():
    display = Display()

    # ---------------------------------------------------------------
    # Cas particulier : SAFE MODE
    # ---------------------------------------------------------------
    # boot.py n'a pas créé le clavier. On l'affiche et on rend la main au
    # REPL pour que tu puisses réparer tes fichiers dans Thonny.
    if runtime.safe_mode:
        display.message("SAFE MODE", "HID DISABLED")
        display.flush_startup()
        print("REPL disponible. Diagnostics : import diag; diag.run()")
        return

    manager = ProfileManager(C.PROFILES_ORDER, C.DEFAULT_PROFILE)

    # Vérification de TOUTES les macros avant la moindre frappe.
    # Si une macro contient un caractère impossible à taper, on préfère
    # une erreur ici plutôt qu'une commande à moitié écrite dans Civil 3D.
    for name in C.PROFILES_ORDER:
        for label, actions in PROFILES[name]:
            compile_actions(actions, C.KEYBOARD_LAYOUT)
    if C.HID_TEST is not None and C.HID_TEST not in TESTS:
        raise ValueError("HID_TEST invalide")

    controls = Inputs()
    keyboard = HIDKeyboard(runtime.interface) if runtime.interface else None

    # La LED est un confort : si son initialisation échoue, on continue.
    led = None
    try:
        from led import Led
        led = Led()
    except Exception as exc:
        print("LED desactivee :", exc)

    display.profile(manager.name, ticks_ms())
    print("Profil :", manager.name,
          "HID :", "initialise" if keyboard else "DESACTIVE")
    if runtime.hid_error:
        display.message("HID ERROR", "VOIR REPL")

    started = ticks_ms()
    armed = False          # False tant que la garde de démarrage n'est pas finie
    was_ready = False

    try:
        while True:
            now = ticks_ms()
            edges = controls.poll(now)

            # --- Fin de la garde de démarrage -----------------------
            if not armed and ticks_diff(now, started) >= C.BOOT_GUARD_MS:
                armed = True
                # Si tu tenais encore une touche, on l'ignore : il faudra
                # la relâcher avant qu'elle ne serve.
                controls.disarm_held()
                edges = []
                print("Entrees actives ; HID_TEST =", C.HID_TEST)

            if armed:
                pressed = [name for name, edge in edges if edge == 1]

                # --- 1. ESC : priorité absolue, avant tout le reste ---
                if "ESC" in pressed:
                    if keyboard:
                        keyboard.escape(now)
                        # On appelle tick() tout de suite : ainsi le paquet
                        # de relâchement part dans le même tour de boucle,
                        # sans attendre 2 ms de plus.
                        keyboard.tick(now)
                    if led:
                        led.flash(now)
                    print("ESC")
                else:
                    # --- 2. Changement de profil ---------------------
                    previous = "PREVIOUS" in pressed
                    following = "NEXT" in pressed
                    # Si les deux TTP sont touchés en même temps, on ne
                    # fait rien : on ne saurait pas dans quel sens aller.
                    if previous != following:
                        manager.move(1 if following else -1)
                        if keyboard:
                            # On annule la macro en cours : hors de question
                            # que la fin d'une commande de l'ancien profil
                            # continue de s'écrire après le changement.
                            keyboard.cancel()
                        display.profile(manager.name, now, True)
                        print("Profil :", manager.name)
                    else:
                        # --- 3. Les quatre touches de macro ----------
                        for i in range(4):
                            if "B" + str(i + 1) in pressed:
                                label, actions = PROFILES[manager.name][i]
                                if C.HID_TEST is not None:
                                    # En mode test, seul B1 agit, et il
                                    # déclenche la macro de test choisie.
                                    if i != 0:
                                        continue
                                    label, actions = C.HID_TEST, TESTS[C.HID_TEST]
                                print(manager.name, "B" + str(i + 1), label)
                                if keyboard:
                                    keyboard.submit(actions)
                                else:
                                    print("   (HID desactive : rien n'est tape)")

            # --- 4. Travaux de fond, tous non bloquants -------------
            if keyboard:
                keyboard.tick(now)
                ready = keyboard.ready()
                # Au moment précis où Windows ouvre le clavier, on ignore
                # ce qui est déjà maintenu : sinon un doigt encore posé
                # déclencherait une macro dès la connexion.
                if ready and not was_ready:
                    controls.disarm_held()
                was_ready = ready

            if led:
                try:
                    led.tick(now)
                except Exception as exc:
                    # Une panne de LED ne doit pas arrêter le clavier.
                    print("LED arretee :", exc)
                    try:
                        led.close()
                    except Exception:
                        pass
                    led = None

            display.tick(now)
            sleep_ms(C.LOOP_MS)

    finally:
        # Ce bloc s'exécute TOUJOURS : arrêt normal, Ctrl-C dans Thonny,
        # ou erreur imprévue. C'est là qu'on garantit qu'aucune touche ne
        # reste enfoncée côté Windows et que la LED est éteinte.
        if keyboard:
            keyboard.close()
        if led:
            led.close()


if __name__ == "__main__":
    run()
```

---

## device/runtime.py

`16 lignes - sha256 83e652193bd9487f`

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

## device/layouts.py

`330 lignes - sha256 b8d52683cee54811`

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
```

---

## device/hid_keyboard.py

`315 lignes - sha256 23e93c4d8439193c`

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

    def cancel(self):
        """Oublie tout ce qui était prévu et programme un relâchement."""
        self.queue = []
        self.current = []
        self.phase = "idle"
        self.release_needed = True

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
        if not self.interface.send_keys(keys, timeout_ms=0):
            return False
        # On mémorise si ce paquet laissait des touches enfoncées.
        self.keys_down = bool(keys)
        return True

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

`156 lignes - sha256 af3a155c4d24f8a3`

```python
# -*- coding: utf-8 -*-
"""
display.py - L'écran OLED. Totalement facultatif.

=====================================================================
L'ECRAN N'EST JAMAIS INDISPENSABLE
=====================================================================
S'il est absent, débranché, ou s'il tombe en panne en cours de route, on
l'abandonne proprement (self.oled = None) et le macropad continue de
fonctionner comme clavier. Un écran ne doit jamais empêcher de taper.

=====================================================================
POURQUOI UNE SEULE PAGE PAR TOUR DE BOUCLE
=====================================================================
L'écran fait 128 x 64 pixels, soit 1024 octets. Les envoyer d'un coup sur
le bus I2C prend environ 23 millisecondes, pendant lesquelles le
processeur ne fait rien d'autre : on sentirait le macropad "accrocher" à
chaque changement d'affichage.

Le SH1106 organise sa mémoire en 8 bandes horizontales de 8 pixels de
haut, appelées "pages". On en envoie UNE par tour de boucle, soit environ
3 ms. L'image complète est donc mise à jour en 8 tours de boucle, c'est-
à-dire environ 16 ms : invisible pour l'oeil, et les touches restent
lues en permanence.

=====================================================================
PARTICULARITE DU SH1106
=====================================================================
Ce contrôleur possède 132 colonnes de mémoire pour une dalle de 128
pixels : les deux premières colonnes ne sont pas visibles. Il faut donc
décaler l'écriture de 2 colonnes, sinon toute l'image est décalée.
C'est le rôle de la commande 0x02 dans tick().
"""

from time import ticks_ms, ticks_diff, ticks_add
import config as C
from profiles import PROFILES, TITLES


class Display:

    def __init__(self):
        self.oled = None
        self.profile_name = C.DEFAULT_PROFILE
        self.splash_until = None
        self.pending_page = 8      # 8 = rien à envoyer ; 0 = tout à renvoyer
        if not C.OLED_ENABLED:
            return
        try:
            from machine import Pin, I2C
            from sh1106 import SH1106_I2C
            # timeout : si l'écran ne répond pas, l'échange est abandonné
            # au lieu de bloquer indéfiniment toute la boucle principale.
            bus = I2C(C.I2C_ID, sda=Pin(C.OLED_SDA), scl=Pin(C.OLED_SCL),
                      freq=C.I2C_FREQ, timeout=C.I2C_TIMEOUT_US)
            addresses = bus.scan()
            print("OLED I2C :", [hex(a) for a in addresses])
            address = next((a for a in (0x3c, 0x3d) if a in addresses), None)
            if address is None:
                raise OSError("SH1106 absent (0x3C/0x3D)")
            self.oled = SH1106_I2C(128, 64, bus, addr=address, rotate=0)
            self.oled.contrast(C.OLED_CONTRAST)
        except Exception as exc:
            self.disable(exc)

    def disable(self, error):
        """Abandonne l'écran sans arrêter le macropad."""
        print("OLED desactive :", error)
        self.oled = None

    def message(self, line1, line2=""):
        """Deux lignes de texte brut : SAFE MODE, erreurs, diagnostic."""
        if not self.oled:
            return
        try:
            self.splash_until = None
            self.oled.fill(0)                    # efface l'image en mémoire
            self.oled.text(line1[:16], 0, 20)    # 16 caractères par ligne max
            self.oled.text(line2[:16], 0, 36)
            self.pending_page = 0                # demande le réaffichage
        except Exception as exc:
            self.disable(exc)

    def profile(self, name, now, splash=False):
        """Affiche un profil.

        splash=True affiche d'abord son nom en gros pendant une demi-seconde,
        puis on revient automatiquement à la liste des quatre touches.
        """
        self.profile_name = name
        if not self.oled:
            return
        try:
            o = self.oled
            o.fill(0)
            title = TITLES.get(name, name)

            if splash:
                # MicroPython ne fournit qu'une seule police, en 8x8 pixels.
                # Pour l'agrandir, on dessine le texte dans une petite image
                # en mémoire, puis on recopie chaque pixel sous forme d'un
                # carré de 2x2 pixels sur l'écran.
                import framebuf
                scale = 2 if len(title) <= 8 else 1
                buf = framebuf.FrameBuffer(bytearray(128), 128, 8,
                                           framebuf.MONO_HLSB)
                buf.text(title, 0, 0, 1)
                x0 = max(0, (128 - len(title) * 8 * scale) // 2)   # centrage
                for x in range(min(128, len(title) * 8)):
                    for y in range(8):
                        if buf.pixel(x, y):
                            o.fill_rect(x0 + x * scale, 24 + y * scale,
                                        scale, scale, 1)
                self.splash_until = ticks_add(now, C.PROFILE_SPLASH_MS)
            else:
                o.text(title[:16], 0, 0)
                o.hline(0, 11, 128, 1)
                # Une ligne par touche : "B1 EXPLORER" tient entièrement,
                # pas besoin d'abréviations difficiles à relire.
                for i, macro in enumerate(PROFILES[name]):
                    o.text("B%d %s" % (i + 1, macro[0]), 0, 16 + i * 12)
                self.splash_until = None

            self.pending_page = 0
        except Exception as exc:
            self.disable(exc)

    def tick(self, now):
        """Envoie au plus UNE page à l'écran. Appelé à chaque tour de boucle."""
        if not self.oled:
            return
        if self.splash_until is not None and ticks_diff(now, self.splash_until) >= 0:
            self.profile(self.profile_name, now)     # fin du nom en gros
        if not self.oled or self.pending_page >= 8:
            return
        try:
            page = self.pending_page
            self.oled.write_cmd(0xB0 | page)   # choisir la bande n° page
            self.oled.write_cmd(0x02)          # colonne de départ, 4 bits bas
            self.oled.write_cmd(0x10)          # colonne de départ, 4 bits hauts
            #        ^ 0x02 = le décalage de 2 colonnes propre au SH1106
            self.oled.write_data(
                self.oled.displaybuf[page * 128:(page + 1) * 128])
            self.pending_page += 1
        except Exception as exc:
            # Un écran arraché en cours de route ne doit pas arrêter le clavier.
            self.disable(exc)

    def flush_startup(self):
        """Envoie l'image entière d'un coup.

        Réservé aux moments où l'on peut se permettre d'attendre : avant que
        les touches ne deviennent actives, et au retour au REPL en SAFE MODE.
        """
        for _ in range(8):
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

## device/diag.py

`143 lignes - sha256 d56ea161612233bc`

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
Dans la zone du bas (le REPL, celle où il y a ">>>") :

    >>> import diag
    >>> diag.run()              # 20 secondes de surveillance des entrées
    >>> diag.run(seconds=60)    # plus long
    >>> diag.run(led_test=True) # ajoute le test de la LED

Test par test :

    >>> diag.keymap()               # vérifie l'AZERTY, sans matériel
    >>> diag.keymap("_ISOLATEOBJECTS")

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

