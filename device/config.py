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

# --- Sous quel doigt se trouve chaque touche -------------------------
# Le pad est posé sous la main GAUCHE : une touche par doigt, DEUX pour
# l'index. Le pouce est à DROITE du groupe, l'auriculaire à GAUCHE.
#
#   gauche <------------------------------------------------> droite
#   B6            B5           B4        B3 + B2       B1
#   auriculaire   annulaire    majeur    index         pouce
#
# À QUOI ÇA SERT, ET CE N'EST PAS DÉCORATIF : deux touches placées sous
# le MÊME doigt ne peuvent pas être appuyées en même temps. Sans cette
# table, la page web te laisserait configurer une combinaison B2+B3 qui
# ne partirait JAMAIS, sans un mot d'explication — elle enverrait
# simplement les deux macros l'une après l'autre. Avec elle,
# l'enregistrement est refusé en te disant pourquoi.
#
# Les noms sont libres : seule l'ÉGALITÉ compte. Si tu remontes le pad
# autrement, corrige cette ligne. Mets None pour ne rien vérifier.
DOIGTS = ("pouce", "index", "index", "majeur", "annulaire", "auriculaire")

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
# GPIO17 et pas GPIO16 : sur l'ESP32-S3, GPIO15 et GPIO16 sont les
# broches prevues pour un quartz horloger 32,768 kHz (XTAL_32K_P et
# XTAL_32K_N). Toutes les cartes ne le montent pas, mais GPIO17 n'a
# aucune fonction speciale : c'est un choix plus sur, et c'est celui
# qui est reellement soude sur ce macropad.
RGB_PIN = 17                # fil de donnees (via 330 a 470 ohms en serie)
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
RGB_RESPIRATION_MIN = 0.25  # luminosite au creux de la respiration
# ET SURTOUT LE PLAFOND. Au repos, la respiration ne monte pas plus haut
# que ca : tout ce qui reste au-dessus est RESERVE a l'appui.
#
# Pourquoi ce n'etait pas 1.0 : une couleur dont un canal vaut 255 - le
# bleu de CIVIL3D - atteignait deja le plafond de courant au sommet du
# cycle. L'appui ne pouvait plus l'eclaircir, il delavait seulement les
# autres canaux : +23 % de lumiere, et un changement de TEINTE plutot que
# de clarte. On ne voyait plus quelle touche on venait d'utiliser.
#
# Monte-le si tu veux un pad plus lumineux au repos, mais tu reprends
# d'autant la place de l'appui. 1.0 rend le probleme d'origine.
RGB_RESPIRATION_MAX = 0.55

# --- reaction a l'appui ------------------------------------------------
# Un appui fait monter la LED de la touche, et elle redescend toute seule.
# L'impulsion S'AJOUTE a ce qui reste : deux appuis coup sur coup montent
# deux fois plus haut. Le plafond du courant reste RGB_LUMINOSITE, quoi
# qu'il arrive.
# 0.45 n'est pas un chiffre au hasard : 0.55 (le sommet de la
# respiration) + 0.45 = 1.00, c'est-a-dire la couleur PLEINE du profil.
# Un appui amene donc la touche exactement a sa couleur nominale, quel
# que soit l'endroit du cycle - et de la pointe de la respiration, cela
# fait +82 % de lumiere, sans toucher a la teinte.
RGB_IMPULSION = 0.45
RGB_IMPULSION_MAX = 1.35    # trois appuis empiles ; au-dela ca ne monte plus
# 1600 et non 700 : cette duree est comptee PAR UNITE d'impulsion, et
# l'impulsion est passee de 1.0 a 0.45 pour laisser la reserve ci-dessus.
# A 700, un appui se serait efface en 315 ms au lieu de 700 - deux fois
# plus vite qu'avant, alors que rien ne le demandait. 0,45 x 1600 = 720 ms
# redonne exactement le rythme d'origine.
RGB_RETOMBEE_MS = 1600      # duree du retour au calme, PAR unite

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
#
# POURQUOI 200 ET PLUS 260 : dans les valeurs d'usine, une seule touche a
# encore un double appui — B1, le presse-papiers, et c'est la touche la
# plus utilisée du pad. Ce délai est exactement le retard de son Ctrl+C.
# 200 ms reste très confortable pour un double appui volontaire (le
# double-clic de Windows est réglé à 500 ms par défaut, mais un doigt qui
# tape deux fois exprès sur un macropad met 100 à 150 ms), et rend 60 ms
# au copier. Si tu rates des collages, remonte-le : c'est sans danger.
GESTE_DOUBLE_MS = 200

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
# Duree maximale d'une pause dans une macro. Une macro qui attendrait
# trente secondes donnerait l'impression que le macropad est fige, alors
# qu'il tourne parfaitement : on plafonne, et l'enregistrement refuse
# au-dela.
PAUSE_MAX_MS = 5000

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
# =====================================================================
# COMBINAISONS DE PLUSIEURS TOUCHES
# =====================================================================
# Deux doigts poses "en meme temps" arrivent en realite a 10 a 40 ms
# d'ecart ; deux appuis volontairement successifs sont a plus de 150 ms.
# 50 ms separe proprement les deux cas.
#
# Cette fenetre ne ralentit AUCUNE touche : voir l'explication en tete de
# combos.py. Seules les touches membres d'une combinaison la traversent,
# et un appui court part de toute facon au relachement.
GESTE_COMBO_MS = 50
COMBO_FLASH_MS = 1200       # duree de l'affichage "B3+B4 / VUE PREC."

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
