# Macropad USB HID ESP32-S3 — Civil 3D / Blender / Word / Windows

Firmware MicroPython pour un macropad USB reconnu par Windows comme un
**vrai clavier HID** : quatre touches mécaniques à macros, deux touches
capacitives pour changer de profil, un écran OLED SH1106, et un gros bouton
Échap déporté à LED respirante.

---

## Par où commencer

| Tu veux… | Lis |
|---|---|
| **monter et faire fonctionner le macropad** | [`GUIDE_FR.md`](GUIDE_FR.md), du début à la fin |
| **câbler sans rien détruire** | [`docs/05-electronique.md`](docs/05-electronique.md) — **à lire avant de souder** |
| tester étape par étape, en détail | [`docs/03-tests-progressifs.md`](docs/03-tests-progressifs.md) |
| savoir si USB HID marche vraiment en MicroPython | [`docs/01-recherche-usb-hid.md`](docs/01-recherche-usb-hid.md) |
| vérifier le brochage broche par broche | [`docs/02-cablage.md`](docs/02-cablage.md) |
| cocher que tout est bon | [`docs/04-checklist.md`](docs/04-checklist.md) |
| savoir ce qui a été corrigé et pourquoi | [`docs/06-corrections.md`](docs/06-corrections.md) |
| **modifier les macros sans coder** | maintenir B2 au RESET, puis `http://192.168.4.1` — voir [`docs/07`](docs/07-mode-configuration.md) |
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

|  | BLENDER | CIVIL 3D | WORD | WINDOWS |
|---|---|---|---|---|
| **B1** | `G` | `_MATCHPROP` + Entrée | Ctrl+B | Win+E |
| **B2** | `R` | `_HATCH` + Entrée | Ctrl+I | Alt+Tab |
| **B3** | `S` | Ctrl+Z | Ctrl+S | Win+D |
| **B4** | `Tab` | `_ISOLATEOBJECTS` + Entrée | Ctrl+Z | Ctrl+Maj+Échap |
| **B5** | `E` | `_ZOOM` + Entrée | Ctrl+U | Win+V |
| **B6** | Ctrl+Z | Ctrl+S | Ctrl+Y | Win+Maj+S |

Ce ne sont que les valeurs d'usine : **tout se change depuis la page web**
(voir ci-dessous), sans toucher au code.

Le gros bouton **ESC** agit dans tous les profils : il annule la macro en
cours, envoie Échap, et déclenche un flash lumineux.

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
├── CODE_COMPLET.md               copie lisible de tout le firmware
├── RAPPORT_TESTS.md              ce qui a été vérifié, et comment
├── device/                       >>> LE FIRMWARE : contenu à copier sur la carte
│   ├── boot.py                   SAFE MODE, création du clavier USB
│   ├── main.py                   la boucle principale
│   ├── config.py                 tous les réglages
│   ├── profiles.py               macros d'usine (repli)
│   ├── store.py                  lecture/écriture de profils.json
│   ├── portal.py                 point d'accès WiFi + page web
│   ├── layouts.py                AZERTY / QWERTY, traduction des caractères
│   ├── hid_keyboard.py           envoi des rapports USB, file d'attente
│   ├── inputs.py                 anti-rebond des entrées
│   ├── display.py                interface OLED
│   ├── sh1106.py                 pilote de l'écran (MIT, robert-hh)
│   ├── led.py                    respiration et flash
│   ├── diag.py                   diagnostic, n'envoie jamais de touche
│   ├── runtime.py                mémoire partagée boot.py / main.py
│   └── lib/usb/device/           bibliothèque USB officielle (MIT)
├── docs/                         documentation détaillée
├── tests/test_logic.py           38 tests exécutables sur PC
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
→ Ran 59 tests ... OK
```

Ces tests remplacent le temps, les GPIO, le PWM, l'écran et le transport
USB par des simulations, puis exécutent le vrai code du firmware, jusqu'à
la boucle principale de `main.py`. Ils vérifient entre autres les rapports
USB **octet par octet** (`Ctrl+Z` → `01 00 1A`, c'est-à-dire la touche `z`
de l'AZERTY et non le `Z` américain qui vaudrait `Ctrl+W` = fermer le
document), qu'aucune macro ne laisse un modificateur enfoncé, l'anti-rebond,
la priorité d'ESC, le SAFE MODE, et les neuf corrections listées dans
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
