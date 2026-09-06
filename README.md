# Macropad USB HID ESP32-S3 — Civil 3D / Blender / Word / Windows

Firmware MicroPython pour un macropad USB reconnu par Windows comme un
**vrai clavier HID**, avec quatre touches mecaniques a macros, deux touches
capacitives de changement de profil, un ecran OLED SH1106 et un gros bouton
Echap deporte a LED respirante.

---

## 1. Resume de la solution retenue

| Question | Reponse retenue |
|---|---|
| USB HID possible en MicroPython sur ESP32-S3 ? | **Oui**, avec le firmware officiel, sans compilation personnalisee |
| API utilisee | `machine.USBDevice` (integree au firmware) + paquets officiels `usb-device-keyboard` / `usb-device-hid` / `usb-device` de micropython-lib (MIT) |
| Firmware | `ESP32_GENERIC_S3-SPIRAM_OCT`, **v1.27.0 minimum** — derniere stable : v1.29.0 |
| Pourquoi cette version minimale | v1.27.0 corrige le bug *"blank USB HID reports on boards with PSRAM"* qui rend le clavier muet sur une carte N16R8 |
| REPL et clavier en meme temps | Oui, via `builtin_driver=True` ; et le REPL reste aussi disponible sur l'UART0 (second port USB-C) |
| Brochage propose | **Valide sans modification**, verifie broche par broche |
| CircuitPython / Arduino | Non necessaires, non utilises |

Le detail complet de la recherche, avec citations et liens, est dans
**[`docs/01-recherche-usb-hid.md`](docs/01-recherche-usb-hid.md)**.

> **Le point a ne pas rater :** avec MicroPython v1.26.x sur cette carte, tout
> semble fonctionner (Windows detecte un clavier) mais **aucune touche
> n'arrive**. Verifiez votre version avant toute chose.

---

## 2. Materiel

* ESP32-S3 **N16R8** (16 Mo flash, 8 Mo PSRAM octale), USB natif
* Ecran OLED 1,3" **SH1106** 128x64, I2C, alimente en 3,3 V
* 4 switches mecaniques (contact simple vers la masse, pas de matrice)
* 2 modules capacitifs **TTP223** alimentes en 3,3 V
* 1 gros bouton Echap deporte, avec une LED 1 W volontairement utilisee a
  quelques milliamperes
* 1 transistor **BC547**, resistances 330 Ohm / 2,2 kOhm / 10 kOhm

## 3. Brochage

| GPIO | Role |
|---|---|
| 8 / 9 | OLED SDA / SCL (I2C0 par defaut de MicroPython sur cette carte) |
| 4 / 5 / 6 / 7 | Touches B1 / B2 / B3 / B4, contact vers GND, pull-up interne |
| 10 / 11 | TTP223 profil precedent / suivant, actifs a l'etat haut |
| 14 | Contact du gros bouton ESC, vers GND, pull-up interne |
| 15 | PWM de la LED ESC, via BC547 |
| 19 / 20 | **USB D- / D+ — reserves, ne rien brancher** |

Tableau de cablage complet, schema ASCII, verification electrique du montage
BC547 et liste des resistances : **[`docs/02-cablage.md`](docs/02-cablage.md)**.

---

## 4. Arborescence du projet

```
.
├── README.md                     ce fichier
├── boot.py                       volontairement quasi vide (securite)
├── main.py                       orchestration, boucle principale
├── config.py                     TOUS les reglages : GPIO, timings, options
├── profiles.py                   TOUTES les macros (seul fichier a editer)
├── keymaps.py                    codes HID + tables AZERTY / QWERTY
├── hid_keyboard.py               clavier USB HID, file d'attente non bloquante
├── inputs.py                     anti-rebond des switches, ESC et TTP223
├── display.py                    interface utilisateur OLED
├── sh1106.py                     pilote SH1106 avec rafraichissement partiel
├── led.py                        respiration PWM + flash ESC
├── diag.py                       diagnostic materiel, sans envoi de touche
├── docs/
│   ├── 01-recherche-usb-hid.md   recherche, sources, version, flash
│   ├── 02-cablage.md             brochage, schemas, electronique, alimentation
│   ├── 03-tests-progressifs.md   mise en service etape par etape
│   └── 04-checklist.md           checklist finale
└── tools/                        NE PAS COPIER SUR LA CARTE
    ├── mp_stubs.py               faux peripheriques MicroPython
    └── test_logique.py           102 verifications du firmware sur PC
```

Les fichiers `.py` de la racine se copient tels quels a la racine de la carte.

---

## 5. Demarrage rapide

```bat
REM 1. firmware  (port USB-UART de la carte)
pip install esptool
python -m esptool --chip esp32s3 --port COM5 erase_flash
python -m esptool --chip esp32s3 --port COM5 --baud 460800 write_flash -z 0 ESP32_GENERIC_S3-SPIRAM_OCT-<version>.bin

REM 2. bibliotheque USB HID  (aucun Wi-Fi necessaire)
pip install mpremote
mpremote connect COM6 mip install usb-device-keyboard

REM 3. fichiers du projet : via Thonny, "Televerser vers /"
```

Puis suivez **[`docs/03-tests-progressifs.md`](docs/03-tests-progressifs.md)**
sans sauter d'etape.

> Pendant toute la mise au point, gardez le fichier principal nomme
> `macropad.py` sur la carte plutot que `main.py` : rien ne demarre tout seul,
> vous lancez par `import macropad; macropad.run()`. Renommez-le en `main.py`
> seulement a la fin.

---

## 6. Fonctionnement

### Profils

Ordre circulaire, defini dans `profiles.py` :

```
BLENDER -> CIVIL3D -> WORD -> WINDOWS -> BLENDER
```

`TTP SUIVANT` avance, `TTP PRECEDENT` recule. Profil au demarrage : **CIVIL3D**
(`DEFAULT_PROFILE` dans `config.py`). Rien n'est ecrit en flash a chaque
changement.

Ajouter QGIS, AutoTURN ou Road Survey plus tard = ajouter une entree dans
`PROFILES` et son nom dans `PROFILES_ORDER`. La navigation s'adapte seule.

### Macros de depart

| | BLENDER | CIVIL 3D | WORD | WINDOWS |
|---|---|---|---|---|
| **B1** | `G` | `_MATCHPROP` + Entree | Ctrl+B | Win+E |
| **B2** | `R` | `_HATCH` + Entree | Ctrl+I | Alt+Tab |
| **B3** | `S` | Ctrl+Z | Ctrl+S | Win+D |
| **B4** | `Tab` | `_ISOLATEOBJECTS` + Entree | Ctrl+Z | Ctrl+Maj+Echap |

> **Remarque sur Word :** les raccourcis ci-dessus sont ceux de Word en
> **anglais**. Sur un Word en francais, Gras est `Ctrl+G` et non `Ctrl+B`. Les
> variantes francaises sont deja ecrites en commentaire dans `profiles.py`, il
> suffit de les decommenter. J'ai laisse par defaut ce que vous aviez demande.

### Le bouton ESC

Actif dans **tous** les profils, traite en premier dans la boucle principale.
Un appui :

1. **annule immediatement** ce que le clavier etait en train de taper (une
   commande Civil 3D en cours d'ecriture, par exemple) ;
2. envoie `Echap` ;
3. declenche un flash lumineux de 130 ms, suivi d'un retour progressif a la
   respiration.

### La LED

Respiration permanente : entre 4 % et 25 % de rapport cyclique, cycle de
3 secondes, courbe en cosinus surelevee par un exposant 2,2 pour un rendu
naturel. PWM a 1 kHz, aucun scintillement visible. Reglable dans `config.py`.

### SAFE MODE

**Maintenez B1 pendant la mise sous tension.** Le clavier HID n'est alors
jamais initialise : aucune touche ne peut partir. L'ecran, la LED et la lecture
des entrees continuent de fonctionner pour le diagnostic. C'est le moyen de
recuperer la carte si une macro mal ecrite la transforme en clavier fou.

Deuxieme filet de securite : une temporisation de 1,5 s (`HID_START_DELAY_MS`)
avant l'activation du HID au demarrage.

---

## 7. Le probleme AZERTY, et comment il est traite

En USB, un clavier n'envoie pas des caracteres mais des **numeros de touche
physique**. C'est Windows qui traduit, selon sa disposition. Le meme code 0x1D
donne `z` en QWERTY et `w` en AZERTY.

Consequences, toutes prises en charge par `keymaps.py` :

* `Ctrl+Z` en AZERTY doit envoyer le code **0x1A** (la touche `W` du QWERTY).
  Envoyer 0x1D fermerait le document par un `Ctrl+W` — le firmware ne fait pas
  cette erreur, et un test automatise le verifie ;
* le `_` de `_MATCHPROP` est en AZERTY la touche `8` **sans SHIFT** (code 0x25),
  alors qu'en QWERTY c'est SHIFT + tiret ;
* les raccourcis (`combo`) visent la **touche physique** qui produit la lettre,
  le texte (`type_text`) vise le **caractere** avec ses modificateurs.

Reglage unique, dans `config.py` :

```python
KEYBOARD_LAYOUT = "FR_AZERTY"     # ou "US_QWERTY"
```

Ce reglage doit correspondre a la disposition **de Windows**. Le firmware ne
modifie jamais la configuration clavier du PC.

---

## 8. Ce qui a ete verifie, et comment

Distinction volontairement explicite :

### Reellement execute dans mon environnement

`tools/test_logique.py` installe de faux peripheriques MicroPython
(`tools/mp_stubs.py` : `machine`, `framebuf`, `usb.device`, horloge virtuelle)
puis **importe et execute reellement les modules du firmware**, y compris la
boucle principale de `main.py`.

```
$ python3 tools/test_logique.py
102 verifications executees
TOUT EST CONFORME
```

Ce qui est verifie :

1. coherence des profils, rotation circulaire dans les deux sens ;
2. traduction AZERTY de **toutes** les macros des 4 profils ;
3. les rapports USB HID reellement produits, **octet par octet** :
   `Ctrl+Z` -> `01 00 1A ...`, `Ctrl+Maj+Echap` -> `03 00 29 ...`, la suite
   complete de `_MATCHPROP`, `_HATCH`, `_ISOLATEOBJECTS` ;
4. qu'aucune des 16 macros ne laisse un modificateur enfonce ;
5. la priorite du bouton ESC (vidage de la file en cours) ;
6. l'anti-rebond : contact avec 6 rebonds = 1 appui ; doigt pose 3 s sur un
   TTP223 = 1 seul changement de profil ; deux touchers = deux evenements ;
7. la courbe de respiration : bornes 4 % / 25 %, periodicite, progression sans
   cassure, flash de 130 ms puis retour exact a la respiration ;
8. le rendu OLED : aucun debordement hors des 128x64 pixels, et un service
   d'affichage limite a 256 octets d'I2C (~5,8 ms) ;
9. la boucle principale complete : boot -> aucune touche envoyee -> B1 tape
   `_MATCHPROP` -> TTP NEXT passe en WORD -> B1 envoie `Ctrl+B` -> ESC ;
10. le SAFE MODE : aucune interface USB creee, aucun rapport possible ;
11. la tolerance aux pannes : ecran absent, bibliotheque HID absente.

### Verifie statiquement, sans execution

* syntaxe de tous les fichiers ;
* API `usb.device` / `usb.device.keyboard` relue dans la source officielle
  (signatures, modificateurs negatifs, `builtin_driver`) ;
* brochage confronte a la documentation GPIO d'ESP-IDF pour l'ESP32-S3 ;
* sequence d'initialisation SH1106 et decalage de 2 colonnes.

### A tester obligatoirement sur votre materiel

**Je n'ai pas d'ESP32 : rien de ce qui suit n'a ete teste physiquement.**

* l'enumeration USB reelle sous Windows ;
* l'adresse et le fonctionnement de votre OLED ;
* la polarite reelle de vos TTP223 (`TTP_ACTIVE_HIGH`) ;
* le brochage de votre BC547 et le comportement thermique de la LED ;
* le comportement de Civil 3D, Blender et Word.

---

## 9. Licences

* Code de ce projet : libre d'usage et de modification.
* `sh1106.py` est adapte de [robert-hh/SH1106](https://github.com/robert-hh/SH1106)
  et du pilote `ssd1306.py` de micropython-lib, tous deux sous **licence MIT**
  (Radomir Dopieralski, Damien P. George, Robert Hammelrath, Tim Weber).
  L'attribution figure en tete du fichier.
* La bibliotheque `usb-device-keyboard` n'est **pas** incluse ici : elle
  s'installe depuis micropython-lib (**MIT**, Copyright 2023-2024 Angus Gratton).

---

## 10. Extensions prevues

L'architecture supporte sans reecriture : profils supplementaires (QGIS,
AutoTURN, Road Survey), macros multi-etapes (le type `sequence` existe deja),
et l'ajout de touches. Un encodeur EC11, l'appui long, le double clic et une
matrice de clavier demanderaient d'etendre `inputs.py`, sans toucher au reste.

**Pas d'encodeur dans cette V0**, comme demande.
