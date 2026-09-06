# 1. Recherche : USB HID est-il reellement possible en MicroPython sur ESP32-S3 ?

**Reponse courte : OUI, avec MicroPython officiel, sans compilation
personnalisee — mais il faut la version v1.27.0 ou plus recente, et c'est
precisement a cause de votre PSRAM.**

Toutes les affirmations ci-dessous ont ete verifiees dans le code source ou
les notes de version officielles, pas de memoire. Les citations sont
textuelles.

---

## 1.1 La classe `machine.USBDevice` existe et couvre l'ESP32

La documentation officielle de MicroPython (`docs/library/machine.USBDevice.rst`
dans le depot) indique que `USBDevice` est disponible sur les portages
**esp32, rp2 et samd**, avec la reserve : *"Native USB support is required, and
not every board supports native USB."* L'ESP32-S3 possede bien un controleur
USB OTG natif, la condition est donc remplie.

Verification dans le code du portage esp32
(`ports/esp32/mpconfigport.h`, branche master) :

```c
#ifndef MICROPY_HW_ENABLE_USBDEV
#define MICROPY_HW_ENABLE_USBDEV            (SOC_USB_OTG_SUPPORTED)
#endif
...
#ifndef MICROPY_HW_ENABLE_USB_RUNTIME_DEVICE
#define MICROPY_HW_ENABLE_USB_RUNTIME_DEVICE    (1)
#endif
```

`SOC_USB_OTG_SUPPORTED` vaut 1 sur l'ESP32-S3 : le peripherique USB dynamique
(`machine.USBDevice`) est donc **actif par defaut dans le firmware standard**.
Aucune compilation personnalisee n'est necessaire.

## 1.2 Le REPL passe par le port USB natif, et il peut cohabiter avec le HID

Toujours dans `ports/esp32/mpconfigport.h` :

```c
#ifndef MICROPY_HW_USB_CDC
#define MICROPY_HW_USB_CDC                  (MICROPY_HW_ENABLE_USBDEV)
#endif
#ifndef MICROPY_HW_ESP_USB_SERIAL_JTAG
#define MICROPY_HW_ESP_USB_SERIAL_JTAG      (SOC_USB_SERIAL_JTAG_SUPPORTED && (!MICROPY_HW_USB_CDC || SOC_USB_OTG_PERIPH_NUM > 1))
#endif
#if MICROPY_HW_USB_CDC && MICROPY_HW_ESP_USB_SERIAL_JTAG && (SOC_USB_OTG_PERIPH_NUM <= 1)
#error "Invalid build config: Can't enable both native USB and USB Serial/JTAG peripheral"
#endif
```

Consequences concretes pour votre carte :

* le REPL du port USB natif est un **CDC TinyUSB**, pas l'USB-Serial-JTAG ;
* clavier HID et REPL utilisent donc la meme pile TinyUSB et peuvent coexister
  (c'est le role du parametre `builtin_driver=True`, voir 1.4) ;
* le peripherique USB-Serial-JTAG est desactive dans ce firmware.

Et dans `ports/esp32/boards/ESP32_GENERIC_S3/mpconfigboard.h` :

```c
#define MICROPY_HW_ENABLE_UART_REPL         (1)
#define MICROPY_HW_I2C0_SCL                 (9)
#define MICROPY_HW_I2C0_SDA                 (8)
```

Deux informations precieuses :

1. **le REPL est aussi disponible sur l'UART0**, donc sur le second port USB-C
   (celui du pont USB-serie). C'est ce qui permet de garder Thonny connecte
   pendant que le port natif fait le clavier ;
2. les broches I2C0 par defaut sont **GPIO8 (SDA) et GPIO9 (SCL)** : le
   brochage que vous proposiez pour l'OLED correspond exactement au choix
   officiel de MicroPython pour cette carte.

## 1.3 Le piege a connaitre : le bug "rapports HID vides" sur les cartes a PSRAM

C'est le point le plus important de cette recherche, et il concerne
directement votre ESP32-S3 **N16R8** (8 Mo de PSRAM).

* [micropython/micropython#18098 — *USB HID device on ESP32 has a problem!*](https://github.com/micropython/micropython/issues/18098)
  (19 septembre 2025) : sur ESP32-S3, les exemples HID non modifies de la
  bibliotheque envoient des rapports qui **arrivent entierement a zero chez
  l'hote**, verifie a l'analyseur Wireshark. Les rapports LED hote -> carte
  fonctionnent, eux, correctement. Versions touchees : 1.26.1 et 1.27
  pre-version.
* [micropython/micropython-lib#1044 — *USB HID Implementation for ESP32S3 has problems!*](https://github.com/micropython/micropython-lib/issues/1044)
  decrit le meme symptome cote bibliotheque : les octets sont intacts jusque
  dans `dcd_edpt_xfer()`, mais l'hote ne recoit que des zeros.

**Ce bug est corrige.** Les notes de version officielles de MicroPython
**v1.27.0** disent textuellement :

> *"TinyUSB integration has been improved, with a bug fix for Zero Length
> Packets that affected REPL reliability, along with a fix for blank USB HID
> reports on boards with PSRAM."*

— [Release v1.27.0, micropython/micropython](https://github.com/micropython/micropython/releases/tag/v1.27.0)

Le symptome ("rapports HID vides") et la condition ("boards with PSRAM")
correspondent exactement au probleme signale, et exactement a votre carte.

> **A retenir : ne flashez pas une version anterieure a v1.27.0.**
> Avec une v1.26.x, le macropad s'enumerera correctement sous Windows,
> Windows le verra comme un clavier... et aucune touche n'arrivera jamais.
> Le symptome est particulierement trompeur, d'ou l'insistance ici.

## 1.4 La bibliotheque a utiliser par-dessus : `usb-device-keyboard`

MicroPython fournit dans `micropython-lib` des paquets Python purs construits
au-dessus de `machine.USBDevice` :
`usb-device`, `usb-device-hid`, `usb-device-keyboard`, `usb-device-mouse`,
`usb-device-cdc`, `usb-device-midi`.

* Depot : <https://github.com/micropython/micropython-lib/tree/master/micropython/usb>
* Licence : **MIT**, `Copyright (c) 2023-2024 Angus Gratton`
* Ce qui nous interesse : `usb/device/keyboard.py`, classe
  `KeyboardInterface`, methode
  `send_keys(down_keys, timeout_ms=100)` et son descripteur de rapport
  clavier standard 8 octets.
* Detail d'API verifie dans la source : les modificateurs sont passes en
  **valeurs negatives** (`r[0] |= -k` dans `send_keys`). Le firmware en tient
  compte dans `hid_keyboard.py`.
* Detail d'API verifie dans `usb/device/core.py` :

  ```python
  if isinstance(builtin_driver, bool):
      builtin_driver = _usbd.BUILTIN_DEFAULT if builtin_driver else _usbd.BUILTIN_NONE
  ```

  C'est ce qui permet a `usb.device.get().init(clavier, builtin_driver=True)`
  de **conserver le REPL CDC** tout en ajoutant l'interface clavier.

Ce projet n'a donc reecrit ni la couche USB, ni les descripteurs HID : il les
utilise tels quels et n'ajoute que la disposition clavier, la file d'attente
non bloquante et la logique du macropad.

## 1.5 Comparaison des approches envisagees

| Approche | Fiabilite | Installation | Texte + raccourcis | Verdict |
|---|---|---|---|---|
| **MicroPython >= 1.27 + `usb-device-keyboard`** | Bonne, bug PSRAM corrige | firmware standard + 3 fichiers | oui | **retenu** |
| MicroPython < 1.27 sur carte a PSRAM | rapports vides | — | non | a proscrire |
| Build MicroPython personnalise (HID statique en C) | bonne | chaine ESP-IDF a installer | oui | inutile ici |
| CircuitPython (`usb_hid`) | bonne | autre firmware | oui | non retenu : vous voulez MicroPython, qui suffit |
| Arduino / ESP-IDF + TinyUSB | bonne | autre ecosysteme | oui | non retenu, meme raison |

CircuitPython et Arduino ne sont pas necessaires : la solution MicroPython
existe reellement et est officiellement supportee. Aucun basculement
silencieux n'a ete fait.

---

## 1.6 Version exacte recommandee et methode de flash

### Firmware

* Carte : **ESP32-S3 N16R8** = 16 Mo de flash + 8 Mo de PSRAM **octale**.
* Variante MicroPython : **`ESP32_GENERIC_S3-SPIRAM_OCT`**.
  Verifie dans `ports/esp32/boards/ESP32_GENERIC_S3/board.json` :
  `"variants": {"SPIRAM_OCT": "Support for Octal-SPIRAM"}`.
  La variante `FLASH_4M` est marquee obsolete et ne vous concerne pas.
* Version : **v1.27.0 minimum**. Au moment de la redaction, la derniere
  version stable est **v1.29.0 (aout 2026)**, basee sur ESP-IDF v5.5.2 : c'est
  celle a prendre.
* Telechargement : page officielle `ESP32_GENERIC_S3` du site micropython.org,
  section *Firmware*, ligne **SPIRAM_OCT**.

### Flash

Branchez le **port USB-UART** de la carte (celui du pont serie, voir
`docs/02-cablage.md` pour les distinguer), puis depuis un terminal Windows :

```bat
pip install esptool

REM 1. effacer entierement la flash (fortement recommande la premiere fois)
python -m esptool --chip esp32s3 --port COM5 erase_flash

REM 2. ecrire le firmware a l'adresse 0
python -m esptool --chip esp32s3 --port COM5 --baud 460800 ^
    write_flash -z 0 ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin
```

* Remplacez `COM5` par le port reellement affiche dans le Gestionnaire de
  peripheriques, et le nom du `.bin` par celui que vous avez telecharge.
* L'adresse de flash de l'ESP32-S3 est **0**, pas `0x1000` comme sur l'ESP32
  classique.
* Si l'ESP32 n'est pas detecte : maintenez **BOOT**, appuyez brievement sur
  **RESET**, relachez **BOOT**, puis relancez la commande.

### Installation de la bibliotheque USB HID

Elle n'est pas incluse dans le firmware, il faut la copier sur la carte.
La methode officielle passe par `mpremote`, **depuis le PC, sans Wi-Fi** :

```bat
pip install mpremote
mpremote connect COM6 mip install usb-device-keyboard
```

`mip` installe automatiquement les dependances (`usb-device`, `usb-device-hid`)
dans `/lib/usb/device/` sur la carte. Verification :

```
mpremote connect COM6 fs ls /lib/usb/device
```

Vous devez y voir au minimum `core.py`, `hid.py` et `keyboard.py`.

**Methode de secours sans `mpremote`** : telechargez a la main ces trois
fichiers depuis GitHub et copiez-les avec Thonny dans `/lib/usb/device/`
(creez les dossiers `lib`, `usb`, `device`) :

* `micropython/usb/usb-device/usb/device/core.py`
* `micropython/usb/usb-device-hid/usb/device/hid.py`
* `micropython/usb/usb-device-keyboard/usb/device/keyboard.py`

depuis <https://github.com/micropython/micropython-lib>.

---

## 1.7 Sources utilisees

| Source | Ce qu'on en tire |
|---|---|
| [micropython/micropython — `ports/esp32/mpconfigport.h`](https://github.com/micropython/micropython/blob/master/ports/esp32/mpconfigport.h) | `USBDevice` actif par defaut sur S3 ; REPL en CDC natif |
| [micropython/micropython — `ESP32_GENERIC_S3/mpconfigboard.h`](https://github.com/micropython/micropython/blob/master/ports/esp32/boards/ESP32_GENERIC_S3/mpconfigboard.h) | REPL UART actif ; I2C0 = GPIO8/9 |
| [micropython/micropython — `ESP32_GENERIC_S3/board.json`](https://github.com/micropython/micropython/blob/master/ports/esp32/boards/ESP32_GENERIC_S3/board.json) | existence de la variante `SPIRAM_OCT` |
| [Notes de version v1.27.0](https://github.com/micropython/micropython/releases/tag/v1.27.0) | correction des rapports HID vides sur cartes a PSRAM |
| [Notes de version v1.29.0](https://github.com/micropython/micropython/releases/tag/v1.29.0) | derniere version stable, ESP-IDF v5.5.2 |
| [Issue #18098](https://github.com/micropython/micropython/issues/18098) | description du bug des rapports vides |
| [micropython-lib issue #1044](https://github.com/micropython/micropython-lib/issues/1044) | meme bug cote bibliotheque |
| [micropython-lib — paquets USB](https://github.com/micropython/micropython-lib/tree/master/micropython/usb) | bibliotheque HID retenue, licence MIT |
| [micropython-lib — `usb/device/keyboard.py`](https://github.com/micropython/micropython-lib/blob/master/micropython/usb/usb-device-keyboard/usb/device/keyboard.py) | API `send_keys`, modificateurs negatifs |
| [micropython-lib — `usb/device/core.py`](https://github.com/micropython/micropython-lib/blob/master/micropython/usb/usb-device/usb/device/core.py) | `builtin_driver=True` conserve le REPL |
| [espressif/esp-idf — `docs/.../gpio/esp32s3.inc`](https://github.com/espressif/esp-idf/blob/master/docs/en/api-reference/peripherals/gpio/esp32s3.inc) | GPIO26-32 flash, GPIO33-37 PSRAM octale, GPIO19/20 USB |
| [robert-hh/SH1106](https://github.com/robert-hh/SH1106) | sequence d'initialisation SH1106, licence MIT |
