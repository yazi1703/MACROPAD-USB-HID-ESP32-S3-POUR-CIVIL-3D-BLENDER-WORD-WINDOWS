# Macropad ESP32-S3 — V0 MicroPython

> **Mise à jour.** Ce guide a été relu et corrigé. Neuf corrections ont été
> apportées au projet ; elles sont listées et expliquées une par une dans
> **`docs/06-corrections.md`**. Les points touchés dans ce guide sont
> signalés par la mention **[CORRIGÉ]**.
>
> Documents complémentaires :
> - `docs/05-electronique.md` — **ce qui risque de cramer**, et où ajouter
>   condensateurs, diodes et zeners. À lire avant de souder.
> - `docs/01-recherche-usb-hid.md` — la recherche USB détaillée et sourcée.
> - `docs/03-tests-progressifs.md` — les tests pas à pas, version détaillée.

Projet préparé le 6 septembre 2026. Lire les étapes dans l'ordre. Les fichiers modifiables sont dans `device/`. **HID_ENABLED est livré à False** : le premier branchement ne tape rien. Ne pas activer les macros avant les tests 1 à 7.

## 1. Solution retenue

MicroPython officiel **1.29.0**, cible **ESP32_GENERIC_S3**, variante **SPIRAM_OCT**, plus les bibliothèques officielles `usb-device`, `usb-device-hid` et `usb-device-keyboard`, incluses en sources. Clavier USB filaire composite avec le port série CDC conservé pour le REPL. Pas de Bluetooth, de Wi-Fi, de CircuitPython ou d'Arduino dans ce projet.

Une seule boucle coopérative gère les entrées, les rapports HID, la respiration et l'écran. Les macros sont décomposées en pressions/relâchements. L'ESC annule la macro et la file en cours, libère les modificateurs, puis envoie Escape. Un changement de profil annule aussi la fin d'une macro de l'ancien profil.

## 2. Résultat de la vérification USB

La documentation versionnée expose réellement `machine.USBDevice` sur ESP32. Dans le code **v1.29.0** du port ESP32, `MICROPY_HW_ENABLE_USB_RUNTIME_DEVICE` vaut 1 par défaut ; le S3 dispose de l'USB OTG requis. L'API Python haute couche retenue est `KeyboardInterface`, initialisée avec `usb.device.get().init(interface, builtin_driver=True)`. Les envois utilisent `send_keys(..., timeout_ms=0)`, `busy()` et `is_open()` : ces noms ont été vérifiés dans les sources incluses. [Documentation USB 1.29.0](https://docs.micropython.org/en/v1.29.0/library/machine.USBDevice.html), [configuration ESP32 au tag retenu](https://github.com/micropython/micropython/blob/v1.29.0/ports/esp32/mpconfigport.h).

**[CORRIGÉ] Limite réelle, précisée.** Les issues [micropython-lib #1044](https://github.com/micropython/micropython-lib/issues/1044) et [MicroPython #18098](https://github.com/micropython/micropython/issues/18098), ouvertes en septembre 2025, décrivent des rapports clavier reçus vides sur ESP32-S3/Windows. Elles apparaissent toujours ouvertes à la consultation, mais **un correctif a bel et bien été publié** : les notes de version officielles de **MicroPython v1.27.0** l'annoncent mot pour mot.

> *« TinyUSB integration has been improved, with a bug fix for Zero Length Packets that affected REPL reliability, along with a fix for blank USB HID reports on boards with PSRAM. »*
> — [Release v1.27.0](https://github.com/micropython/micropython/releases/tag/v1.27.0)

Le symptôme (« blank USB HID reports ») et la condition (« on boards with PSRAM ») correspondent exactement au bug signalé, et exactement à la carte N16R8 qui embarque 8 Mo de PSRAM. Une issue non refermée ne signifie pas qu'aucun correctif n'a été livré : les mainteneurs ne referment pas systématiquement les tickets.

**Ce qu'il faut en retenir concrètement :** la 1.29.0 retenue ici est postérieure au correctif, c'est donc la bonne version. Et il existe un **seuil à ne jamais franchir vers le bas : v1.27.0**. Avec une v1.26.x sur cette carte, le macropad s'énumère normalement, Windows affiche bien un clavier, et **aucune touche n'arrive jamais** — le symptôme le plus trompeur de tout le projet. Le test physique d'une lettre est obligatoire. Cela ne dispense pas du test physique : ce projet est une implémentation basée sur l'API officielle, **pas une certification de fonctionnement sur ton matériel**. Si l'interface s'énumère mais ne tape rien, arrêter à l'étape 7 et relever versions/ports/comportement ; ne pas inventer un correctif ni changer de langage en silence.

| Approche | Compatibilité / entretien | Installation et Windows | Décision |
|---|---|---|---|
| MicroPython 1.29.0 + micropython-lib | API officielle ESP32-S3, texte via notre mapping, raccourcis via HID | Binaire officiel + fichiers Python ; USB filaire ; validation Windows requise | Retenue |
| MicroPython personnalisé + module C TinyUSB | Réalisable mais compilation, maintenance C et USB à assumer ; aucune correction spécifique démontrée ici | Plus difficile à installer et à reproduire | Inutile pour exposer l'API actuelle |
| ESP-IDF / Arduino TinyUSB | Projets S3 existants, accès USB direct ; abandon du firmware Python | Compilation C/C++, clavier filaire standard | Dernier recours, aucun code repris |
| CircuitPython `usb_hid` | Autre interpréteur, API différente | Solution alternative à requalifier pour la carte exacte | Non utilisée ; à discuter seulement si la voie retenue échoue |

## 3. Sources et licences

Les dépendances utilisées sont figées dans `DEPENDENCIES.lock.json`, avec empreintes SHA-256. Aucune installation réseau sur la carte n'est nécessaire.

| Source | Date / activité vérifiée | Usage et licence |
|---|---|---|
| [MicroPython](https://github.com/micropython/micropython/releases/tag/v1.29.0) | Version 1.29.0 publiée le 24/08/2026 | Firmware officiel ; sources MIT ; pas de fork produit |
| [micropython-lib USB](https://github.com/micropython/micropython-lib/tree/dbb3b45fdebb4e3af5c4bc1b993b9ab40ac966c3/micropython/usb) | Dernier commit du sous-arbre USB retrouvé : 29/07/2026 | Quatre fichiers Python copiés sans modification, licence MIT conservée ; adaptateur séparé dans hid_keyboard.py |
| [robert-hh/SH1106](https://github.com/robert-hh/SH1106/tree/fe674238f9e186c4a3801773b2dbd0100a662400) | Dernier commit retrouvé : 22/05/2025 | Driver MicroPython I2C/SPI MIT repris sans modification ; interface framebuffer et machine.I2C compatibles avec la cible ; matériel non testé ici |
| [Espressif : USB Device](https://docs.espressif.com/projects/esp-idf/en/v5.0.5/esp32s3/api-reference/peripherals/usb_device.html) | Documentation officielle consultée | Confirme la capacité USB Device/TinyUSB et les lignes physiques ; pas une preuve de support Python à elle seule |
| [Espressif : GPIO](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html) | Documentation officielle consultée | Restrictions strapping, flash, PSRAM et USB |
| [Espressif : DevKitC-1 v1.1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) | Documentation officielle consultée | Distingue USB-UART et USB OTG ; référence d'architecture, pas identification de ton clone à caméra |
| [QMK, clavier français](https://github.com/qmk/qmk_firmware/blob/master/quantum/keymap_extras/keymap_french.h) | En-tête consulté daté 2026 | GPL-2.0-or-later ; vérification des positions AZERTY uniquement, aucun code QMK distribué/copié ; mapping minimal écrit pour ce projet |
| [KeSp](https://github.com/mornepousse/KeSp_firmware) | Dépôt consulté ; date du dernier commit non relevée | Framework ESP-IDF de clavier S3, GPL-3.0 ; intéressant pour les extensions, non retenu et aucun code copié |
| [ESP32 USB HID Keyboard Series](https://github.com/ChandimaJayaneththi/ESP32-USB-HID-Keyboard-Series) | Dépôt consulté ; date de commit non relevée | Exemples ESP-IDF, pas MicroPython ; licence non vérifiée, aucun code copié |
| [Tontek TTP223](https://www.tontek.com.tw/product/product2?idx=243&lang=en) | Fiche fabricant consultée | Modes direct/toggle et active HIGH/LOW ; aucune bibliothèque requise pour lire OUT |
| [onsemi BC547](https://www.onsemi.com/pdf/datasheet/bc550-d.pdf) | Fiche fabricant consultée | Dimensionnement électrique indicatif ; brochage applicable seulement si ton transistor correspond à cette référence fabricant |

Les commentaires du code écrit pour ce projet sont en français. Les fichiers tiers gardent leurs commentaires et avis de droits d'origine. Les licences tierces complètes figurent dans `licenses/`.

## 4. Version exacte recommandée

**ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin**.

[Télécharger le binaire officiel](https://micropython.org/resources/firmware/ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin). Vérifier également sa présence dans la rubrique « Support for Octal-SPIRAM » de la [page de téléchargement S3](https://micropython.org/download/ESP32_GENERIC_S3/). Ne pas prendre `.app-bin`, `.uf2`, une preview, ou la variante standard sans SPIRAM octale.

N16R8 correspond normalement à 16 Mo de flash et 8 Mo de PSRAM octale sur ce module. Confirmer la flash avec `esptool flash-id` et l'identification/quantité de mémoire au REPL. La capacité totale de flash n'est pas la taille garantie du système de fichiers, qui dépend du partitionnement du binaire.

## 5. Firmware particulier

**Aucun firmware particulier nécessaire pour disposer de l'API.** Le binaire officiel suffit avec les fichiers `lib/` fournis. Cette conclusion concerne la présence de l'API, pas la validation physique de l'issue HID signalée.

Si tu veux reconstruire exactement la base officielle, voie facultative Linux/WSL : installer les prérequis ESP-IDF, cloner ESP-IDF `v5.5.2` avec ses sous-modules, lancer `./install.sh esp32s3`, charger `export.sh`, puis :

```bash
git clone --branch v1.29.0 https://github.com/micropython/micropython.git
cd micropython
make -C mpy-cross
cd ports/esp32
make BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT submodules
make BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT
```

Le résultat attendu est `build-ESP32_GENERIC_S3-SPIRAM_OCT/firmware.bin`. Cette compilation ESP-IDF n'a pas été exécutée ici. Voir le [README ESP32 du tag 1.29.0](https://github.com/micropython/micropython/blob/v1.29.0/ports/esp32/README.md). Aucune modification de configuration USB n'est prescrite.

## 6. Flash sous Windows

1. Laisser la carte seule, sans LED externe ni autres connexions. Utiliser un câble USB **avec données**.
2. Sur la photo fournie, antenne en haut : **USB natif = connecteur de droite « USB » ; UART = connecteur de gauche « UART »**. Vérifier ces inscriptions sur la carte reçue. Ne pas transposer à une autre carte.
3. Brancher un seul port pour commencer. Repérer le COM dans le Gestionnaire de périphériques par débranchement/rebranchement.
4. Fermer Thonny et tout terminal qui utilise ce COM.
5. Ouvrir PowerShell. Installer esptool sur le PC :

```powershell
py -m pip install esptool
```

6. Si nécessaire, maintenir le **BOOT embarqué** (GPIO0), appuyer puis relâcher RESET, puis relâcher BOOT. Cela entre dans le chargeur ROM. Ce n'est pas le SAFE MODE B1 de notre firmware. [Procédure Espressif](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/get-started/establish-serial-connection.html).
7. Remplacer `COM7` ci-dessous par le port réellement identifié. Vérifier la puce :

```powershell
py -m esptool --chip esp32s3 --port COM7 flash-id
```

8. Si la carte contient déjà un projet, sauvegarder ses fichiers avec Thonny. Une image brute complète peut aussi être lue, **après confirmation des 16 Mo** :

```powershell
py -m esptool --chip esp32s3 --port COM7 read-flash 0 0x1000000 sauvegarde_avant_macropad.bin
```

9. L'effacement suivant supprime tout le contenu de la flash. Pour cette installation initiale, après sauvegarde :

```powershell
py -m esptool --chip esp32s3 --port COM7 erase-flash
py -m esptool --chip esp32s3 --port COM7 --baud 460800 write-flash 0 ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin
```

Les versions récentes d'esptool utilisent ces commandes avec tirets ; les anciennes documentations emploient `erase_flash`, `write_flash`, `flash_id`, `read_flash`. En cas de rejet du nom, vérifier `py -m esptool --help`. En cas d'échec de transfert, retirer `--baud 460800`. Ne jamais modifier l'adresse de départ 0 pour ce binaire complet S3.

10. RESET sans maintenir BOOT. Le COM peut changer : sélectionner le nouveau port dans Thonny. Le pont USB-UART ne peut jamais envoyer le clavier HID à lui seul ; le PC doit être relié au port **USB natif** pour l'essai clavier.

## 7. Vérification du brochage

Aucun changement demandé au brochage initial. GPIO0/3/45/46 sont évités (strapping). GPIO26–37 sont évités pour la mémoire, particulièrement GPIO35/36/37 avec la PSRAM octale. GPIO19/20 sont réservés. Les fonctions alternatives ADC/touch/SPI/caméra mentionnées sur un pinout ne réservent pas automatiquement une GPIO lorsque ces périphériques sont inutilisés.

**Photo fournie : deux erreurs à ne pas propager.** Les étiquettes USB D+/D− sont inversées : la réalité du S3 est **GPIO19 = D− et GPIO20 = D+**. L'entrée GPIO46 est aussi une broche de strapping même si le visuel ne la présente pas clairement ainsi. Ne rien câbler sur ces broches pour la V0.

La carte possède une nappe caméra utilisant notamment nos GPIO. **Laisser cette nappe vide** ; aucun driver caméra n'est chargé. **[CORRIGÉ] GPIO15 et le quartz 32 kHz : à vérifier avant de câbler la LED.** Sur l'ESP32-S3, GPIO15 et GPIO16 sont les broches prévues pour un quartz horloger 32,768 kHz (`XTAL_32K_P` / `XTAL_32K_N`). La plupart des cartes de développement ne le montent pas, mais certaines oui. Cherche un petit boîtier métallique allongé marqué `32.768` ou `32K` près du module. Test logiciel en trente secondes, avant tout câblage définitif : branche une LED ordinaire avec une résistance de 1 kΩ entre GPIO15 et GND, puis au REPL `from machine import Pin, PWM ; p = PWM(Pin(15), freq=2000, duty_u16=32768)`. La LED doit s'allumer à mi-luminosité. Si GPIO15 s'avère occupée, il suffit de changer une ligne dans `config.py` : `LED_PIN = 21` (ou 47, ou 48 — vérifie la sérigraphie). Les broches SD, LED RX/TX et WS2812 visibles sur ce modèle sont hors de notre sélection. Le schéma constructeur exact de cette variante n'a pas été fourni : l'essai GPIO reste nécessaire avant assemblage définitif.

## 8. Tableau de câblage final

| Fonction | GPIO / alimentation | Connexion | Validation |
|---|---|---|---|
| B1 / SAFE au démarrage | GPIO4 | Switch vers GND | Entrée pull-up, LOW ; pas de strapping/mémoire/USB |
| B2 | GPIO5 | Switch vers GND | Idem |
| B3 | GPIO6 | Switch vers GND | Idem |
| B4 | GPIO7 | Switch vers GND | Idem |
| OLED SDA | GPIO8 | SDA | I2C ; utilisable si caméra absente |
| OLED SCL | GPIO9 | SCL | I2C ; pas une broche BOOT sur S3 |
| OLED VCC/GND | 3V3 / GND | VCC / GND | Ne pas alimenter en 5 V dans cette configuration |
| TTP précédent | GPIO10 | OUT | Entrée, pull-down si actif HIGH ; caméra absente |
| TTP suivant | GPIO11 | OUT | Idem ; fonction ADC2 inutilisée |
| Deux TTP VCC/GND | 3V3 / GND | VCC / GND | Sortie limitée à 3,3 V |
| ESC | GPIO14 | Contact vers GND | Entrée pull-up, actif LOW ; caméra absente |
| LED PWM | GPIO15 | 2,2 kΩ vers base BC547 | Sortie PWM 2 kHz ; pas de LED directement sur GPIO |
| LED alimentation | 5V / VBUS de la carte | 330 Ω puis anode LED | Vérifier la présence du 5 V lorsque le port natif seul alimente la carte |
| USB D− | GPIO19 | Connecteur natif existant | Aucune connexion ajoutée |
| USB D+ | GPIO20 | Connecteur natif existant | Aucune connexion ajoutée |

Tous les GND sont communs. Les switches utilisent leurs contacts électriques uniquement ; une éventuelle LED intégrée à un switch est un circuit distinct. Pas de matrice ni de diodes requises avec ces entrées individuelles.

## 9. Schéma complet

Voir **`SCHEMA_CABLAGE.svg`**, schéma graphique vectoriel complet ouvrable dans un navigateur. Il remplace le dessin ASCII pour conserver des connexions lisibles. Le câble externe possède exactement quatre conducteurs : 5V, GND, GPIO14, GPIO15. Choisir un connecteur détrompé sans possibilité de contact transitoire 5 V/signal ; brancher/débrancher hors tension pendant le prototype.

## 10. BC547 et LED 1 W à faible courant

Dans le boîtier ESC : +5 V → **330 Ω** → **anode** LED ; **cathode** LED → **collecteur** BC547 ; **émetteur** → GND. GPIO15 → **2,2 kΩ** → **base** ; **10 kΩ entre la base et GND**, du côté transistor après la résistance 2,2 kΩ. Le contact ESC relie GPIO14 à GND sans toucher au 5 V.

**[CORRIGÉ] Où placer la résistance de 2,2 kΩ.** Monte-la **côté macropad**, juste à la sortie de GPIO15, et non dans le boîtier du bouton. Le fonctionnement électrique est rigoureusement identique, mais le fil du câble se retrouve alors *derrière* la résistance : si du +5 V venait à toucher ce fil (connecteur mal enfiché, fil dessoudé, branchement à chaud), le courant atteignant le GPIO serait limité à `(5 − 3,3) / 2200 = 0,77 mA`, ce que les diodes de protection internes de l'ESP32 absorbent sans dommage. Sans cette permutation, le courant serait illimité et la broche détruite.

**[CORRIGÉ] Protège aussi l'entrée ESC.** Ajoute **1 kΩ en série entre GPIO14 et le fil du câble**, côté macropad. Un +5 V accidentel sur ce fil ne fait alors passer que 1,7 mA. En fonctionnement normal la résistance ne gêne pas : le niveau bas mesuré vaut environ 0,07 V.

Ces deux résistances rendent le câble déporté tolérant aux fautes. Explication complète et calculs : `docs/05-electronique.md` § 5.5.

Avant câblage définitif, **lire le marquage complet et identifier le fabricant/boîtier du BC547 ; vérifier E/B/C dans sa datasheet**. Ne pas déduire le brochage de l'orientation de la face plate. La datasheet onsemi citée est un exemple identifié, pas une garantie pour le composant en ta possession. Un testeur de transistor peut aider à identifier E/B/C.

Calcul indicatif, alimentation 5,0 V et saturation de 0,2 V :

- LED rouge Vf≈2,1 V : I≈(5−2,1−0,2)/330 = **8,2 mA** quand le PWM est ON.
- LED Vf≈3,6 V : I≈**3,6 mA**. Vf réel dépend du courant et du composant.
- Courant de commande GPIO : (3,3−0,7)/2200≈1,18 mA ; environ 0,07 mA va dans la 10 kΩ, laissant ≈1,11 mA de base. C'est largement cohérent pour commuter ce faible courant LED.
- Pour la rouge : résistance ≈22 mW et LED ≈17 mW au maximum continu. Une résistance 1/4 W est très suffisante. On est très loin de 1 W.
- Le PWM de 4 à 25 % réduit encore le courant moyen ; le flash 100 % pendant 120 ms conserve **le même courant instantané limité par 330 Ω**.

Le BC547 convient ici ; ce montage **n'est pas dimensionné pour une LED alimentée à 300 mA**. Ne pas enlever/réduire arbitrairement la 330 Ω. Ni diode de roue libre (pas de charge inductive), ni Zener ne sont nécessaires dans ce circuit.

## 11. Résistances, alimentation et condensateurs

> Le détail de tout ce paragraphe — ce qui risque de cramer, les vérifications
> au multimètre avant la première mise sous tension, l'identification des
> pattes du BC547, et où placer précisément condensateurs, diodes et diodes
> Zener — se trouve dans **`docs/05-electronique.md`**.

À monter pour la LED : **1 × 330 Ω, 1 × 2,2 kΩ, 1 × 10 kΩ**, idéalement 1/4 W, plus **1 × 1 kΩ** en série sur GPIO14 (voir § 10). Aucun pull-up externe obligatoire sur les cinq switches pour un prototype court. Si le câble ESC capte du bruit, ajouter **4,7 à 10 kΩ entre GPIO14 et 3V3 côté macropad**, jamais vers 5 V ; refaire le test ESC avec câble et PWM actifs. Éviter un câble long non blindé pour les premiers essais.

Budget additionnel indicatif : OLED annoncé <11 mA à 3,3 V, TTP eux-mêmes de l'ordre du µA mais leurs voyants peuvent ajouter des mA, LED ≤environ 9 mA à 5 V aux valeurs nominales. Les périphériques ajoutent donc typiquement quelques dizaines de mA au plus. **La consommation de la carte ESP32-S3 complète n'est pas déduite de ces chiffres** : CPU, PSRAM, régulateur, pont USB et voyants s'ajoutent. Pas de radio activée par ce projet ; vérifier l'ensemble avec un mesureur USB si possible. Ne pas annoncer un courant total mesuré sans mesure.

Les modules comportent normalement leur découplage ; un prototype à fils courts peut être essayé sans tes propres 100 nF. Pour la version définitive, prévoir un **100 nF entre 3V3 et GND près de chacun des deux modules TTP223 et près de l'OLED**, si non présent ; ils réduisent les variations locales et les faux touchers. Un condensateur électrolytique disponible de 10 à 47 µF, tension ≥10 V, peut aider entre 5 V et GND près du bouton externe si le câble est long (respecter sa polarité) ; il ne remplace pas un 100 nF pour les parasites rapides. Ne pas ajouter de condensateur aux lignes D+/D−.

## 12. Arborescence et rôle des fichiers

| Emplacement | Rôle |
|---|---|
| `device/boot.py` | LED éteinte, SAFE MODE, déclaration du HID sans frappe |
| `device/main.py` | Boucle, priorité ESC, navigation, sécurité initiale |
| `device/config.py` | GPIO, timings, activation HID et layout |
| `device/profiles.py` | Toutes les macros, ordre exploité par ProfileManager et actions de test |
| `device/inputs.py` | Entrées, polarité, anti-rebond et fronts |
| `device/hid_keyboard.py` | Interface officielle, file bornée, pressions/relâchements, erreurs |
| `device/layouts.py` | Mapping logique FR/US et conversion du texte |
| `device/display.py` | SH1106 facultatif, page I2C incrémentale, profils |
| `device/led.py` | PWM, courbe respirante et flash |
| `device/runtime.py` | État partagé du boot, sans écriture flash |
| `device/sh1106.py` | Driver MIT tiers inclus |
| `device/diag.py` | Tests sans envoi clavier |
| `device/lib/usb/device/__init__.py` | Paquet USB officiel |
| `device/lib/usb/device/core.py` | Interface USB officielle |
| `device/lib/usb/device/hid.py` | Classe HID officielle |
| `device/lib/usb/device/keyboard.py` | Clavier officiel et codes HID |
| `tests/test_logic.py` | Tests PC avec simulations, pas à transférer sur la carte |
| `RAPPORT_TESTS.md` | Résultats et limites des vérifications |
| `DEPENDENCIES.lock.json`, `licenses/` | Versions figées, empreintes et licences |
| `CODE_COMPLET.md` | Copie lisible intégrale des sources du firmware |
| `docs/01-recherche-usb-hid.md` | Recherche USB détaillée, sources citées, méthode de flash |
| `docs/02-cablage.md` | Vérification GPIO broche par broche, schéma ASCII, tableau de câblage |
| `docs/03-tests-progressifs.md` | Les onze tests pas à pas, version détaillée pour débutant |
| `docs/04-checklist.md` | Checklist finale à cocher sur le matériel |
| `docs/05-electronique.md` | **Ce qui risque de cramer** ; condensateurs, diodes, zeners ; contrôles au multimètre |
| `docs/06-corrections.md` | Les neuf corrections apportées au projet, avec leur justification |

## 13–15. Code complet, driver et diagnostic

Tous les fichiers exécutables complets sont dans `device/`, sans étapes de génération restantes. **`CODE_COMPLET.md` reproduit chaque fichier Python**, y compris les quatre fichiers USB tiers et le driver SH1106 ; utiliser les `.py` pour le transfert. `diag.py` est indépendant et n'initialise jamais le clavier. Il affiche version, plateforme, capacité USB, état du runtime, scan OLED et transitions des sept entrées.

`HID_ENABLED=False` permet de faire fonctionner le reste et de voir les macros dans le REPL sans frappe. En utilisation normale : le profil initial est CIVIL3D, sans persistance flash. Les quatre profils et seize macros respectent la demande, dont **Ctrl+B dans Word**. Les raccourcis applicatifs personnalisés/localisés peuvent différer : vérifier l'effet dans ton installation avant de changer un mapping. Aucune détection du logiciel actif n'est réalisée ; tu sélectionnes le profil et la fenêtre cible.

## 16. Installation et travail dans Thonny

Installer [Thonny](https://thonny.org/). Choisir l'interpréteur **MicroPython (ESP32)** et le COM correspondant. Vérifier le REPL avant transfert. Afficher le panneau **Fichiers**.

Transférer le **contenu** de `device/` à la racine de l'ESP32, pas un dossier parent `device` sur la carte. Créer `lib/usb/device/` et y déposer les quatre fichiers correspondants, ou téléverser récursivement le dossier `lib` si cette fonction est disponible. Transférer les modules de la racine, en réservant **boot.py et main.py pour après les tests 1–6**. Ensuite envoyer boot.py, puis main.py en dernier. Garder `HID_ENABLED=False`.

Si une ancienne application existe, conserver ses fichiers sur PC avant de remplacer ceux de même nom. Pour les modifications suivantes, STOP/Ctrl+C interrompt `main.py`. Certaines actions Thonny provoquent un soft reset et la réénumération USB ; attendre et resélectionner le COM si nécessaire. Une modification de `config.py`/`boot.py` est suivie d'un **RESET matériel** : cela évite le cache des modules importés et assure le passage dans boot.py.

Ne pas laisser le focus dans le REPL pendant un test HID : le périphérique écrit dans la fenêtre Windows active. Il n'exécute rien automatiquement à l'ouverture de Thonny.

## 17. Premier démarrage

Après les tests élémentaires, placer main.py sur la carte, laisser HID désactivé, RESET sans B1. OLED : CIVIL 3D avec quatre lignes B1–B4. Attendre **2,5 secondes**. Les entrées tenues pendant l'initialisation doivent être relâchées avant de déclencher. Les TTP doivent être configurés en **mode momentané/direct**, pas toggle, et rester libres de doigts pendant la stabilisation au démarrage. Le réglage HIGH/LOW du code ne convertit pas un module toggle en momentané.

Pas de matrice, d'encodeur, de double-clic ou de réseau dans cette V0. L'écran absent/HS est signalé puis désactivé. Le scan I2C reconnaît une adresse 0x3C/0x3D, **il ne prouve pas que le contrôleur est SH1106**. Un écran SSD1306 peut répondre à la même adresse.

## 18. SAFE MODE et récupération

Maintenir **B1 (GPIO4 relié à GND)**, appuyer sur RESET, garder B1 jusqu'au message SAFE MODE puis relâcher. boot.py ne crée pas l'interface HID ; main.py affiche SAFE MODE / HID DISABLED et **rend la main au REPL**. Modifier les fichiers via Thonny ou lancer `import diag; diag.run()`. Sortie : RESET avec B1 relâché.

Ce mode ne garantit pas de réparer un fichier `config.py` syntaxiquement invalide avant sa lecture. Si le port natif devient inaccessible, utiliser le port UART avec Thonny pour interrompre et réparer les fichiers, ou le BOOT embarqué + RESET pour entrer dans le chargeur ROM. Reflasher/effacer est le dernier recours après sauvegarde. Si l'arrêt du programme ne peut pas transmettre un relâchement sous 150 ms, le code désactive l'USB pour supprimer le clavier côté hôte ; le REPL natif peut disparaître : RESET restaure l'accès.

## 19. Tests matériels progressifs

Règle : couper l'alimentation avant d'ajouter/modifier un câblage. Ne passer à la ligne suivante que lorsque l'observation attendue est obtenue. Les tests 1–6 n'exigent pas d'activer le HID.

| Étape | Manipulation | Observation nécessaire |
|---|---|---|
| 1 — Carte seule | Flasher puis au REPL : `import sys, machine; print(sys.version); print(sys.platform); print(hasattr(machine, 'USBDevice'))` ; `machine.reset()` | v1.29.0, esp32, True, retour REPL stable ; aucun périphérique ajouté |
| 2 — OLED seul | Brancher 3V3/GND/8/9. `import diag; diag.run(seconds=5)` | Adresse 0x3C/0x3D annoncée, texte DIAGNOSTIC / HID DISABLED lisible et non décalé |
| 3 — B1…B4 | Brancher 4 switches. `diag.run(seconds=30)` ; presser/retenir/relâcher chaque touche | Repos niveau 1, appui 0 ; un seul APPUI et un RELACHEMENT ; maintien 5 s sans répétition |
| 4 — TTP | Ajouter les deux modules 3,3 V. Ne pas toucher pendant le reset ; `diag.run(seconds=30)` | OUT au repos LOW et HIGH au toucher par défaut ; une transition dans chaque sens ; maintien sans défilement |
| 5 — ESC | Ajouter uniquement le switch externe GPIO14/GND. `diag.run(seconds=30)` | Un appui ESC, un relâchement ; tester en bougeant doucement le câble ; aucun HID |
| 6 — LED | Vérifier référence E/B/C et résistances hors tension. Ajouter circuit. `diag.run(seconds=30, led_test=True)` | 3 s à 5 %, puis 3 s à 20 %, puis respiration ; ESC déclenche le flash après les 6 premières secondes ; pas de chauffe anormale |
| 7 — HID minimal | Suivre section 20, commencer par LETTER | Une seule lettre exacte par B1 ; identification HID/CDC et relâchement fonctionnels |
| 8 — Profils | Remettre HID_ENABLED=False, HID_TEST=None, RESET et démarrer main.py | CIVIL3D → WORD → WINDOWS → BLENDER → CIVIL3D ; sens précédent inverse ; aucun maintien ne répète |
| 9 — Ensemble | Après succès de 7 et 8 : HID_ENABLED=True, HID_TEST=None, RESET | Macros exactes, ESC prioritaire, respiration et flash ; OLED sans ratés d'entrées ; pas de caractères retardés d'un ancien profil |
| 10 — SAFE MODE | Maintenir B1 pendant RESET, puis tester toutes les touches | SAFE MODE / HID DISABLED ; aucune frappe dans le Bloc-notes ; REPL et diag disponibles |

Pour une mesure plus fine de latence, il faudrait un analyseur USB/logique ou un test chronométré sur la carte. L'ESC attend **20 ms de stabilité électrique**, puis libère les modificateurs avant l'envoi : « immédiatement » signifie prioritaire après cet anti-rebond, pas zéro milliseconde garanti. Une page OLED normale demande environ 3 ms à 400 kHz ; la transaction I2C reste synchrone. Son timeout est configuré à 5 ms, et un défaut désactive l'écran. Le GC, l'USB et Windows ajoutent une variabilité : ce n'est pas un système temps réel dur.

## 20. Test USB HID Windows, envois sous contrôle

Après les tests 1–6, conserver un clavier physique et une fenêtre Bloc-notes de test sans contenu important. Modifier `config.py` :

```python
HID_ENABLED = True
HID_TEST = "LETTER"
KEYBOARD_LAYOUT = "FR_AZERTY"
```

Faire RESET. Ne pas maintenir B1 pendant ce boot (sinon SAFE MODE). Vérifier qu'un clavier HID apparaît dans le Gestionnaire de périphériques ; le port série CDC doit rester accessible. Attendre la garde initiale, sélectionner le Bloc-notes puis appuyer **une fois sur B1**. Résultat attendu : **a**. Maintenir B1 ne répète pas. B2–B4 sont inactifs dans ce mode de test ; ESC reste global.

Répéter chaque essai en changeant HID_TEST et en faisant RESET :

| HID_TEST | Action de B1 | Où observer |
|---|---|---|
| LETTER | `a` | Bloc-notes |
| ESC | Escape | Ouvrir la boîte Rechercher du Bloc-notes ; elle se ferme |
| UNDO | Ctrl+Z | Taper une ligne sans importance dans le Bloc-notes, puis annuler |
| AZERTY | `_ABCDEFGHIJKLMNOPQRSTUVWXYZ` | Bloc-notes ; aucun ENTER |
| COMMANDS | `_MATCHPROP _HATCH _ISOLATEOBJECTS` | Bloc-notes ; aucun ENTER |

Les deux modes texte évitent ENTER afin que tu vérifies l'orthographe avant toute commande applicative. Pour tester ENTER sans lancer de commande, utiliser le profil CIVIL3D dans le Bloc-notes après ces essais : chaque commande doit y être suivie d'un retour à la ligne.

Si rien ne s'écrit : vérifier le port USB natif, le câble données, le focus, HID_ENABLED, SAFE MODE et le log « interface ouverte par Windows ». Le log prouve que l'interface est configurée, **pas que Windows a reçu le bon rapport**. Si elle est bien ouverte et les caractères restent absents, collecter `sys.version`, la version du dossier USB fourni et les identifiants Windows ; conserver l'hypothèse de l'issue #18098. Ne pas lancer de macros plus longues pour essayer de masquer ce problème. Si Windows garde d'anciens descripteurs après un essai antérieur, débrancher/rebrancher et supprimer uniquement l'ancienne instance de ce périphérique dans le Gestionnaire de périphériques si nécessaire.

## 21. Test AZERTY

Le layout de texte est **Français (France) AZERTY classique**. Le nouvel AZERTY normalisé, l'AZERTY belge et les layouts canadiens ne sont pas couverts. Choisir manuellement le layout Windows correspondant ; le firmware ne le change jamais.

Le mapping fait notamment A→usage 0x14, Q→0x04, Z→0x1A, W→0x1D, M→0x33, **underscore→0x25 sans Shift**. Les majuscules utilisent Shift ; ENTER utilise 0x28. Les raccourcis sont eux aussi traduits : Ctrl+Z sur AZERTY utilise la position de Z, pas celle du Z américain. Les usages ont été comparés à la référence QMK française ; le texte n'est pas de l'Unicode envoyé directement par USB.

Tester `_ABCDEFGHIJKLMNOPQRSTUVWXYZ` puis les trois commandes, avec **Verr. Maj désactivé en premier**. Le code tient compte du bit Caps Lock envoyé par l'hôte au début de chaque macro, sans appuyer sur Caps Lock. Refaire l'essai Verr. Maj activé pour vérifier que ce retour fonctionne sur Windows ; si l'hôte ne transmet pas son état, conserver Verr. Maj éteint pour les tests. Ne pas basculer Caps Lock ni maintenir Shift/Ctrl/Alt sur un autre clavier pendant une macro.

Le sous-ensemble texte V0 comprend A–Z/a–z, chiffres, espace, underscore et retour ligne. Un caractère non géré provoque une erreur explicite **avant le premier caractère**, plutôt qu'un texte corrompu. US_QWERTY est aussi disponible, mais doit correspondre au layout actif du PC.

## 22. Test Civil 3D et autres profils

Après validation dans le Bloc-notes : HID_TEST=None, HID_ENABLED=True, RESET. Ouvrir une copie de dessin sans importance dans Civil 3D. Le firmware ne sait pas si la ligne de commande possède le focus. Fermer les boîtes de dialogue ; appuyer au besoin sur ESC, puis placer le focus dans Civil 3D.

B1 écrit `_MATCHPROP` + ENTER ; B2 `_HATCH` + ENTER ; B3 Ctrl+Z ; B4 `_ISOLATEOBJECTS` + ENTER. Les commandes avec underscore demandées sont conservées. Préparer les sélections nécessaires pour isoler/copier les propriétés et vérifier les invites de ta version. Ne pas attendre que le clavier choisisse automatiquement une source, des contours ou des objets. ESC n'est pas doublé automatiquement au début des macros : il reste à ta disposition.

Pendant `_ISOLATEOBJECTS`, presser ESC : la fin du texte doit être annulée, les modificateurs relâchés et Escape envoyé ; ce qui a déjà été tapé ne peut pas être retiré rétroactivement. Le flash ne doit pas empêcher le changement de profil suivant.

Blender : fenêtre 3D active, objet de test sélectionné ; G/R/S commencent leurs opérations, TAB bascule le mode, ESC annule. Word : document de test enregistré ; Ctrl+B/I/S/Z conformément à la demande, vérifier les raccourcis réellement configurés dans ton Word. Windows : Win+E ouvre l'Explorateur, Alt+Tab change de fenêtre puis relâche Alt, Win+D affiche le bureau, Ctrl+Shift+Esc ouvre le Gestionnaire des tâches.

Faire ensuite 20 à 30 pressions par touche, alterner rapidement NEXT/PREVIOUS, maintenir les touches, débrancher/rebrancher, puis refaire SAFE MODE. Aucune macro ne doit repartir après reconnexion. En cas de file pleine, le code signale et ignore le nouvel appui ; il ne conserve pas une longue rafale de commandes pour plus tard.

## 23. Checklist finale — à cocher uniquement sur ton matériel

- [ ] ESP32-S3 détecté par Windows
- [ ] Bon port USB natif identifié (droite « USB » sur la photo)
- [ ] Erreur D+/D− du visuel prise en compte
- [ ] MicroPython 1.29.0 SPIRAM_OCT installé
- [ ] REPL fonctionnel
- [ ] GPIO vérifiés ; nappe caméra vide
- [ ] OLED détecté
- [ ] SH1106 affiche correctement
- [ ] B1 fonctionnel
- [ ] B2 fonctionnel
- [ ] B3 fonctionnel
- [ ] B4 fonctionnel
- [ ] TTP PREVIOUS fonctionnel, en mode momentané
- [ ] TTP NEXT fonctionnel, en mode momentané
- [ ] Navigation circulaire des profils OK
- [ ] ESC mécanique détecté
- [ ] Référence du BC547 et E/B/C vérifiés
- [ ] BC547 correctement câblé
- [ ] LED fonctionne sans chauffer anormalement
- [ ] PWM fonctionne
- [ ] Respiration LED fonctionne
- [ ] Flash ESC fonctionne
- [ ] SAFE MODE fonctionne
- [ ] Périphérique USB HID reconnu
- [ ] Une seule lettre « a » reçue par pression
- [ ] Escape fonctionne
- [ ] Ctrl+Z fonctionne
- [ ] Win+E fonctionne
- [ ] Alt+Tab fonctionne
- [ ] Clavier FR AZERTY vérifié
- [ ] `_MATCHPROP` écrit correctement
- [ ] `_HATCH` écrit correctement
- [ ] `_ISOLATEOBJECTS` écrit correctement
- [ ] ENTER fonctionne après chaque commande
- [ ] Profil Blender fonctionnel
- [ ] Profil Civil3D fonctionnel
- [ ] Profil Word fonctionnel
- [ ] Profil Windows fonctionnel
- [ ] Aucun bouton ne se répète involontairement
- [ ] Aucune touche modificatrice HID ne reste bloquée
- [ ] ESC interrompt une macro en cours
- [ ] OLED et LED ne produisent pas de ratés d'entrées observables
- [ ] OLED absent : clavier toujours opérationnel
- [ ] Débranchement/rebranchement sans reprise de macro
- [ ] Fonctionnement général stable
