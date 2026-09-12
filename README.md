# Macropad USB HID ESP32-S3 — Civil 3D / Blender / Word / Windows

Firmware MicroPython pour un macropad USB reconnu par Windows comme un
**vrai clavier HID** : six touches mécaniques à macros — **trois gestes
chacune**, soit dix-huit commandes par profil — deux touches capacitives
pour changer de profil, un écran OLED SH1106 qui affiche le tableau des
commandes, et un gros bouton Échap déporté à LED respirante.

Le macropad **suit le logiciel actif** sur le PC, affiche le nom du fichier
ouvert, compte les appuis, et se configure entièrement depuis une page web
— par le câble USB ou par son propre WiFi.

---

## Par où commencer

| Tu veux… | Lis |
|---|---|
| **monter et faire fonctionner le macropad** | [`GUIDE_FR.md`](GUIDE_FR.md), du début à la fin |
| **câbler sans rien détruire** | [`docs/05-electronique.md`](docs/05-electronique.md) — **à lire avant de souder** |
| **savoir si une broche est libre, AVANT de souder** | `import diag` puis `diag.broches()` — voir [`docs/02`](docs/02-cablage.md) |
| **« rien ne marche », par où commencer** | `import diag` puis `diag.controle()` — fichiers, réglages, interrupteurs, brochage, mode de démarrage |
| tester étape par étape, en détail | [`docs/03-tests-progressifs.md`](docs/03-tests-progressifs.md) |
| savoir si USB HID marche vraiment en MicroPython | [`docs/01-recherche-usb-hid.md`](docs/01-recherche-usb-hid.md) |
| vérifier le brochage broche par broche | [`docs/02-cablage.md`](docs/02-cablage.md) |
| cocher que tout est bon | [`docs/04-checklist.md`](docs/04-checklist.md) |
| **comprendre l'écran et les trois gestes** | [`docs/09-ecran-et-gestes.md`](docs/09-ecran-et-gestes.md) |
| **deux touches ensemble, et les commandes Civil 3D** | [`docs/11-combinaisons.md`](docs/11-combinaisons.md) + [`civil3d/README.md`](civil3d/README.md) |
| **câbler les LED RGB sans faire redémarrer la carte** | [`docs/10-led-rgb.md`](docs/10-led-rgb.md) + [`SCHEMA_LED_RGB.svg`](SCHEMA_LED_RGB.svg) |
| savoir ce qui a été corrigé et pourquoi | [`docs/06-corrections.md`](docs/06-corrections.md) |
| **que le macropad suive le logiciel actif** | [`docs/08-detection-auto.md`](docs/08-detection-auto.md) — le script PC |
| **modifier les macros depuis le PC** | lancer `pc/macropad_auto.bat`, puis `http://127.0.0.1:8765` |
| **que le compagnon démarre avec Windows** | `pc/demarrage_windows.bat`, choix 1 — voir [`docs/08.7`](docs/08-detection-auto.md) |
| modifier les macros sans PC (téléphone) | maintenir B2 au RESET, puis `http://192.168.4.1` — voir [`docs/07`](docs/07-mode-configuration.md) |
| modifier les macros d'usine | `device/profiles.py` |
| modifier les broches ou les réglages | `device/config.py` |

---

## Les trois choses à ne pas rater

1. **MicroPython v1.27.0 minimum.** En dessous, sur une carte à PSRAM comme
   la N16R8, le clavier s'énumère normalement sous Windows et **aucune
   touche n'arrive jamais**. C'est un bug documenté, corrigé en v1.27.0.
   La variante `SPIRAM_OCT` **et** la variante standard conviennent toutes
   les deux : seule la version compte.

2. **Les TTP223 et l'OLED s'alimentent en 3,3 V, jamais en 5 V.** Leurs
   sorties recopient leur tension d'alimentation : en 5 V, ils détruiraient
   les GPIO de l'ESP32-S3, dont la tension maximale absolue est de 3,6 V.

3. **`HID_ENABLED = False` est la position de livraison.** Le macropad ne
   peut rien taper tant que tu ne l'as pas changée, à l'étape 7. Et
   maintenir **B1 au démarrage** coupe le clavier quoi qu'il arrive
   (SAFE MODE) : c'est ta porte de sortie si une macro devient folle.

## Les trois modes de démarrage

Ce que tu maintiens pendant le RESET décide de tout :

| Maintenu au RESET | Mode | Clavier USB |
|---|---|---|
| rien | **macropad** — usage normal | actif |
| **B1** | **SAFE MODE** — écran d'alerte, REPL libre | jamais créé |
| **B2** | **MODE CONFIG** — WiFi + page web sur `http://192.168.4.1` | jamais créé |

Le mode configuration permet de modifier profils et macros depuis un
navigateur, PC ou téléphone, sans Thonny et sans toucher au code. Détail
complet : [`docs/07-mode-configuration.md`](docs/07-mode-configuration.md).

---

## Ce que ça fait

Ordre de rotation des profils, circulaire dans les deux sens :

```
BLENDER  →  CIVIL3D  →  WORD  →  WINDOWS  →  BLENDER
```

**Appui court** (les valeurs d'usine) :

|  | BLENDER | CIVIL 3D | WORD | WINDOWS |
|---|---|---|---|---|
| **B1** | **Ctrl+C** | **Ctrl+C** | **Ctrl+C** | **Ctrl+C** |
| **B2** | `R` | **Maj / Ctrl maintenus** | Ctrl+B | Alt+Tab |
| **B3** | `S` | **F3** accrochages | Ctrl+I | Win+E |
| **B4** | `Tab` | `_PLINE` + Entrée | Ctrl+U | Ctrl+Maj+Échap |
| **B5** | `E` | `_ISOLATEOBJECTS` + Entrée | Ctrl+S | Win+V |
| **B6** | `G` | `_SELECTSIMILAR` + Entrée | Ctrl+Maj+C | Win+Maj+S |

**La touche 1 est la même dans tous les profils** — copier / coller /
annuler, comme ESC qui est déjà global :

| Geste | B1, partout |
|---|---|
| appui court | **Ctrl+C** copier |
| double appui | **Ctrl+V** coller |
| appui long | **Ctrl+Z** annuler |

Les autres appuis longs et doubles des valeurs d'usine :

| | Appui long | Double appui |
|---|---|---|
| **BLENDER** B6 `G` | Ctrl+Maj+Z rétablir | — |
| **CIVIL 3D** B2 MAJ | — | **Ctrl maintenu** (voir ci-dessous) |
| **CIVIL 3D** B3 F3 | `_ZOOM E` vue globale | — |
| **CIVIL 3D** B4 PLINE | `_SPLINE` | — |
| **CIVIL 3D** B5 ISOLE | `_UNISOLATEOBJECTS` | — |
| **CIVIL 3D** B6 SELSIM | `_MATCHPROP` | — |
| **WORD** B5 ENREG | F12 enregistrer sous | — |
| **WORD** B6 FORMAT | Ctrl+Y refaire | Ctrl+Maj+V appliquer la mise en forme |
| **WINDOWS** B3 EXPLOR | Win+D bureau | — |
| **WINDOWS** B4 TACHES | Win+L verrouiller | — |
| **WINDOWS** B5 PRESSE | Win+H dictée vocale | — |

> **À retenir pour tes propres macros :** seule une touche qui a un
> **double appui** attend (200 ms) avant de conclure « c'était un appui
> court ». L'appui **long**, lui, ne coûte rien. Sur tes touches les plus
> utilisées, laisse la colonne « double » vide.

**La touche B2 de Civil 3D est une vraie touche modificatrice.** Elle ne
tape rien : elle enfonce Ctrl ou Maj et les **garde enfoncés** tant que
ton doigt reste dessus, pour que tu cliques à la souris pendant ce temps.

| Ce que tu fais | Ce que le PC reçoit |
|---|---|
| tu appuies et tu **maintiens** | **Maj** enfoncée, relâchée quand tu lâches |
| tu appuies **brièvement**, puis tu **maintiens** | **Ctrl** enfoncé, relâché quand tu lâches |

**Maj est en premier** parce que c'est le maintien **instantané**, et
c'est celui qu'on utilise le plus, main droite à la souris (Maj+clic pour
désélectionner). Le modificateur descend **dès l'appui**, sans aucun
délai. Détail et limites dans [`docs/09`](docs/09-ecran-et-gestes.md).

**Et deux touches appuyées ensemble font une commande de plus.** Six
touches donnent quinze paires ; six sont utilisées dans Civil 3D, et
**sans ralentir le moindre appui simple**.

Elles suivent la **main gauche** posée sur le pad — une touche par doigt,
deux pour l'index, le pouce à droite du groupe :

```
   gauche  <───────────── main GAUCHE ─────────────>  droite
     B6          B5          B4        B3   B2       B1
   auricul.    annul.      majeur      index         pouce
```

| Touches | Doigts | Écran | Ce que ça fait |
|---|---|---|---|
| **B5 + B6** | voisins | `VUE PREC.` | vue enregistrée précédente |
| **B3 + B4** | voisins | `VUE SUIV.` | vue enregistrée suivante |
| **B4 + B5** | voisins | `PEDIT` | `_PEDIT`, la famille polyligne |
| **B3 + B5** | on saute un doigt | `CALQUE OFF` | éteint le calque de l'objet désigné |
| **B4 + B6** | on saute un doigt | `CALQUE ON` | rallume le dernier calque éteint |
| **B3 + B6** | le grand écart | `HACHURES` | `_HATCH` |

Trois règles à retenir : **doigts voisins** = les gestes fréquents,
**sauter un doigt** = les calques, **le grand écart** = ce qui sert le
moins. Et gauche = précédent, droite = suivant, comme les flèches.

Le firmware **connaît tes doigts** (`DOIGTS` dans `config.py`) : il
refuse une combinaison qui prendrait deux touches du même doigt — elle ne
partirait jamais, sans un mot d'explication.

Les quatre premières passent par **tes propres commandes AutoLISP**, à
charger une fois dans Civil 3D : voir
[`civil3d/README.md`](civil3d/README.md). Pourquoi ça ne ralentit rien,
et comment en ajouter : [`docs/11`](docs/11-combinaisons.md).

**Et si tu as des LED RGB** (`docs/10`) : **le pad prend la couleur du
logiciel où tu travailles**, en respiration douce — bleu dans Civil 3D,
orange dans Blender. La touche utilisée passe au blanc franc, une panne
HID met tout en rouge. Les couleurs se choisissent dans la page de
configuration, une par profil.
L'écran affiche les trois colonnes en permanence, et **saute sur la touche
que tu viens d'utiliser en la surlignant** :

```
┌────────────────┐
│▓CIVIL 3D▓▓▓AUTO│
│ CRT   LNG DBL  │
│1COPIERZ   V    │
│2MAJ   -   CTRL │
│3F3    ZOOM-    │
│4PLINE SPLI-    │
│────────────────│
│C3D A12_Phase2.d│
└────────────────┘

Le tableau défile tout seul pour montrer les six touches. Et quand une
**combinaison** part, l'écran l'annonce une seconde en gros — `B3+B4`
au-dessus de `VUE PREC.` — puis revient tout seul.
```

Ce ne sont que les valeurs d'usine : **tout se change depuis la page web**
(voir ci-dessous), sans toucher au code. Détail de l'écran et des gestes :
[`docs/09`](docs/09-ecran-et-gestes.md).

Le gros bouton **ESC** agit dans tous les profils : il annule la macro en
cours, envoie Échap, et déclenche un flash lumineux.

**Et le macropad peut suivre le logiciel que tu utilises.** Un petit script
sur le PC lui dit quelle application est au premier plan : tu cliques dans
Civil 3D, le profil bascule seul, et l'écran affiche le nom du dessin
ouvert. Touche les deux TTP223 ensemble pour verrouiller et reprendre la
main. Il peut **démarrer tout seul avec Windows**
(`pc/demarrage_windows.bat`), attend patiemment que le macropad soit
branché et se reconnecte tout seul s'il est débranché. Voir
[`docs/08`](docs/08-detection-auto.md).

> **Réserve, que tu as validée :** les raccourcis Word ci-dessus sont ceux
> de Word en **anglais**. Sur un Word **français**, Gras se fait avec
> `Ctrl+G` et non `Ctrl+B`. La variante française est déjà écrite en
> commentaire dans `device/profiles.py`, il suffit de la décommenter.

---

## Arborescence

```
.
├── GUIDE_FR.md                   guide principal, à suivre dans l'ordre
├── README.md                     ce fichier
├── DEPENDENCIES.lock.json        versions et empreintes SHA-256 figées
├── SCHEMA_CABLAGE.svg / .png     schéma de câblage
├── SCHEMA_LED_RGB.svg           schéma du ruban WS2812B
├── CODE_COMPLET.md               copie lisible de tout le firmware
├── RAPPORT_TESTS.md              ce qui a été vérifié, et comment
├── device/                       >>> LE FIRMWARE : contenu à copier sur la carte
│   ├── boot.py                   SAFE MODE, création du clavier USB
│   ├── main.py                   la boucle principale
│   ├── config.py                 tous les réglages
│   ├── profiles.py               macros d'usine (repli)
│   ├── gestures.py               appui court / long / double appui
│   ├── store.py                  lecture/écriture de profils.json
│   ├── stats.py                  compteur d'usage (stats.json)
│   ├── portal.py                 point d'accès WiFi + page web
│   ├── link.py                   dialogue série avec le PC
│   ├── layouts.py                AZERTY / QWERTY, traduction des caractères
│   ├── hid_keyboard.py           envoi des rapports USB, file d'attente
│   ├── inputs.py                 anti-rebond des entrées
│   ├── display.py                écran : tableau, défilement, veille
│   ├── sh1106.py                 pilote de l'écran (MIT, robert-hh)
│   ├── led.py                    respiration et flash du bouton ESC
│   ├── rgb.py                    LED RGB des touches (WS2812 ou PWM)
│   ├── diag.py                   diagnostic, n'envoie jamais de touche
│   ├── runtime.py                mémoire partagée boot.py / main.py
│   └── lib/usb/device/           bibliothèque USB officielle (MIT)
├── pc/                           >>> À LANCER SUR LE PC, pas sur la carte
│   ├── macropad_auto.py          détection du logiciel actif + config USB
│   ├── macropad_auto.bat         lanceur Windows (double-clic)
│   ├── demarrage_windows.py      installe/retire le démarrage automatique
│   ├── demarrage_windows.bat     le même, en double-clic
│   ├── macropad_apps.txt         table de secours (créée au 1er lancement)
│   └── macropad_auto.log         journal (créé si --journal)
├── tools/                        >>> OUTILS DE DÉVELOPPEMENT (PC)
│   ├── page_config.html          la page de configuration, source unique
│   ├── injecter_page.py          l'injecte dans portal.py et macropad_auto.py
│   └── generer_code_complet.py   régénère CODE_COMPLET.md
├── civil3d/                      >>> À CHARGER DANS CIVIL 3D
│   ├── macropad_tools.lsp        les 4 commandes des combinaisons
│   └── README.md                 comment les charger au démarrage
├── docs/                         documentation détaillée
├── tests/
│   ├── test_logic.py             231 tests du firmware, exécutables sur PC
│   ├── test_pc.py                30 tests du compagnon Windows
│   └── page_smoke.js             fait tourner la page web hors navigateur
└── licenses/                     licences des composants tiers
```

> ⚠️ **`config.py` est livré avec `HID_ENABLED = False`** — c'est la position
> de sécurité pour quiconque démarre le projet. Si tu re-téléverses ce
> fichier depuis le dépôt après l'avoir déjà activé, **tu repasses à False**
> et le macropad cesse de taper. Le REPL te le dit au démarrage :
> `HID_ENABLED = False : le macropad ne tapera aucune touche.`
>
> Le réflexe : modifie la copie qui est **sur la carte** (double-clic dans
> le panneau du bas de Thonny), pas celle du dépôt.

**On copie le *contenu* de `device/` à la racine de la carte**, pas le
dossier `device` lui-même. `docs/`, `tests/` et les `.md` restent sur le PC.

---

## Vérifications faites, et non faites

**Réellement exécuté sur PC :**

```
python3 -m unittest discover -s tests
→ Ran 261 tests ... OK
```

Ces tests remplacent le temps, les GPIO, le PWM, l'écran et le transport
USB par des simulations, puis exécutent le vrai code du firmware, jusqu'à
la boucle principale de `main.py`. Ils vérifient entre autres les rapports
USB **octet par octet** (`Ctrl+Z` → `01 00 1A`, c'est-à-dire la touche `z`
de l'AZERTY et non le `Z` américain qui vaudrait `Ctrl+W` = fermer le
document), qu'aucune macro ne laisse un modificateur enfoncé, l'anti-rebond,
la priorité d'ESC, le SAFE MODE, la machine à états des trois gestes, le
protocole série, la relecture d'un ancien `profils.json`, l'absence de
débordement de l'écran, et les neuf corrections listées dans
`docs/06-corrections.md`.

**Non testé, faute de matériel :** l'énumération USB réelle sous Windows,
ton écran, la polarité réelle de tes TTP223, ton BC547 et le comportement
thermique de la LED, et le comportement de Civil 3D, Blender et Word.
Détail dans `RAPPORT_TESTS.md`.

---

## Licences

Le pilote `sh1106.py` (robert-hh) et la bibliothèque `usb/device/`
(micropython-lib, Angus Gratton) sont sous **licence MIT**, repris sans
modification, avec leurs en-têtes d'origine. Textes complets dans
`licenses/`. Versions et empreintes figées dans `DEPENDENCIES.lock.json`.
