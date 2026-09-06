# -*- coding: utf-8 -*-
"""
config.py - Configuration centrale du macropad ESP32-S3.

TOUT ce qui est reglable se trouve ici : brochage, timings, options.
Aucun autre fichier ne doit contenir de numero de GPIO en dur.

Carte cible : ESP32-S3 N16R8 (16 Mo flash, 8 Mo PSRAM octale)
Firmware    : MicroPython ESP32_GENERIC_S3-SPIRAM_OCT >= v1.27.0
              (voir docs/01-recherche-usb-hid.md pour le pourquoi de la version)
"""

# =====================================================================
# 1. BROCHAGE (GPIO)
# =====================================================================
# Verification faite pin par pin dans docs/02-cablage.md.
# Rappels ESP32-S3 :
#   - GPIO19 / GPIO20 = USB D- / D+  -> INTERDITS (reserves USB natif)
#   - GPIO26..GPIO32  = flash SPI    -> INTERDITS
#   - GPIO33..GPIO37  = PSRAM octale (variante R8) -> INTERDITS
#   - GPIO0/3/45/46   = strapping    -> a eviter
#   - GPIO43 / GPIO44 = UART0 (REPL de secours sur le port USB-UART) -> a eviter

# --- Ecran OLED SH1106 (I2C) ---
PIN_I2C_SDA = 8          # correspond au I2C(0) par defaut de MicroPython sur S3
PIN_I2C_SCL = 9
I2C_BUS = 0
I2C_FREQ = 400000       # 400 kHz : rafraichissement OLED ~2.5x plus rapide qu'a 100 kHz
OLED_ADDRESSES = (0x3C, 0x3D)   # adresses testees lors du scan
OLED_WIDTH = 128
OLED_HEIGHT = 64

# --- 4 touches mecaniques principales (switch entre GPIO et GND) ---
PIN_BUTTONS = (4, 5, 6, 7)      # B1, B2, B3, B4

# --- 2 modules capacitifs TTP223 (changement de profil) ---
PIN_TTP_PREV = 10
PIN_TTP_NEXT = 11
TTP_ACTIVE_HIGH = True   # TTP223 standard = sortie HAUTE au toucher.
                         # Passer a False si vos modules sont cables autrement
                         # (pastille "AHLB" soudee sur le module).

# --- Gros bouton ESC deporte ---
PIN_ESC = 14             # switch entre GPIO14 et GND, pull-up interne

# --- LED du bouton ESC (via transistor BC547, voir docs/02-cablage.md) ---
PIN_LED = 15

# =====================================================================
# 2. ANTI-REBOND / REACTIVITE
# =====================================================================
# Strategie : l'evenement est emis SUR LE FRONT (latence ~0 ms), puis la
# lecture de l'entree est gelee pendant DEBOUNCE_MS. Un nouvel appui n'est
# accepte qu'apres un relachement detecte -> aucune repetition parasite.
DEBOUNCE_MS = 25         # touches mecaniques B1..B4
DEBOUNCE_ESC_MS = 15     # ESC : plus court car il doit etre tres reactif
DEBOUNCE_TTP_MS = 40     # TTP223 : sortie deja propre, on filtre les frolements

# Periode de la boucle principale. 1 ms = tres reactif et laisse du temps CPU.
LOOP_PERIOD_MS = 1

# =====================================================================
# 3. CLAVIER USB HID
# =====================================================================
# Disposition du clavier configuree DANS WINDOWS (et non sur le macropad).
# Valeurs possibles : "FR_AZERTY", "US_QWERTY"  (voir keymaps.py)
KEYBOARD_LAYOUT = "FR_AZERTY"

# Chaines d'identification vues par Windows.
USB_MANUFACTURER = "Yazid"
USB_PRODUCT = "Macropad CAO"

# Delai de securite entre le boot et l'activation du HID.
# Laisse le temps de couper l'alimentation si le firmware part en boucle.
HID_START_DELAY_MS = 1500

# Espacement minimal entre deux rapports HID (touche pressee / relachee).
# 8 ms = periode d'interrogation USB classique de Windows. Ne pas descendre
# en dessous de 4 ms : des caracteres seraient perdus.
HID_REPORT_INTERVAL_MS = 8

# Nombre maximal de rapports en attente. Au-dela la file est videe et toutes
# les touches sont relachees (securite anti-touche-bloquee).
HID_QUEUE_MAX = 96

# Si aucun rapport ne part pendant ce delai alors que la file n'est pas vide,
# on considere l'hote perdu : on vide la file et on relache tout.
HID_STALL_TIMEOUT_MS = 2000

# =====================================================================
# 4. PROFILS
# =====================================================================
DEFAULT_PROFILE = "CIVIL3D"
# L'ordre de rotation est defini dans profiles.py (PROFILES_ORDER).

# =====================================================================
# 5. ECRAN OLED
# =====================================================================
SPLASH_MS = 500          # duree de l'ecran "nom du profil" en grand (400-600 ms)
MACRO_HIGHLIGHT_MS = 160 # duree du surlignage de la case quand une macro part
OLED_PAGES_PER_SERVICE = 2   # pages (128 octets) envoyees par tour de boucle.
                             # 2 pages ~= 6 ms d'I2C : l'affichage ne bloque jamais
                             # les entrees plus de quelques millisecondes.

# =====================================================================
# 6. LED RESPIRANTE
# =====================================================================
LED_PWM_FREQ = 1000      # 1 kHz : aucun scintillement visible, resolution 16 bits OK
LED_BREATH_MIN_PCT = 4.0     # rapport cyclique minimum (%)
LED_BREATH_MAX_PCT = 25.0    # rapport cyclique maximum (%)
LED_BREATH_PERIOD_MS = 3000  # duree d'un cycle complet inspiration + expiration
LED_BREATH_GAMMA = 2.2       # >1 : la LED s'attarde en bas -> respiration naturelle
LED_FLASH_PCT = 100.0        # eclat lors de l'appui ESC (la resistance serie limite
                             # deja fortement le courant : aucun risque)
LED_FLASH_MS = 130           # duree du flash (100-150 ms demandes)
LED_RECOVER_MS = 350         # retour progressif du flash vers la respiration
LED_SAFE_MODE_MAX_PCT = 8.0  # respiration tres faible en SAFE MODE

# =====================================================================
# 7. SAFE MODE
# =====================================================================
# Maintenir B1 (GPIO4) enfonce pendant la mise sous tension -> SAFE MODE :
# aucune touche HID n'est jamais envoyee.
SAFE_MODE_BUTTON_INDEX = 0   # index dans PIN_BUTTONS -> 0 = B1

# =====================================================================
# 8. DIVERS
# =====================================================================
VERBOSE = True           # traces dans le REPL
