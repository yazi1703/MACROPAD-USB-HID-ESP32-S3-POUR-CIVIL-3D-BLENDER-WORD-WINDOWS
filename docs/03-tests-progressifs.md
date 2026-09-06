# 3. Mise en service pas à pas

Version détaillée, pour quelqu'un qui débute. Le guide principal
(`GUIDE_FR.md` § 19 à 22) donne la même chose sous forme de tableau.

**Ne branche pas tout d'un coup.** À chaque étape, la rubrique *« ce que tu
dois voir »* te dit quand passer à la suivante. Si l'observation attendue
n'est pas là, ne continue pas : le seul fil que tu viens d'ajouter est le
coupable.

**Avant de souder quoi que ce soit**, lis
[`05-electronique.md`](05-electronique.md) : c'est là que sont expliquées
les erreurs qui détruisent la carte.

---

## Préparation

### Thonny

1. Installe [Thonny](https://thonny.org).
2. `Outils` → `Options` → onglet `Interpréteur`.
3. Interpréteur : **MicroPython (ESP32)**.
4. Port : celui du **port USB-UART** de la carte.
5. Vérifie que le REPL répond :

```
>>> print("bonjour")
bonjour
```

### Les deux ports USB-C

| Port | Relié à | Sert à |
|---|---|---|
| **USB natif / OTG** | directement au S3 (GPIO19/20) | **le clavier HID**, et le REPL |
| **USB-UART / COM** | au pont USB-série puis GPIO43/44 | flasher, et le REPL de secours |

> **Conseil qui te fera gagner beaucoup de temps :** branche **les deux**
> ports en même temps, sur le **même** ordinateur. Thonny se connecte au
> port UART, où le REPL reste stable, pendant que le port natif fait le
> clavier. Tu évites ainsi de voir ton port COM disparaître à chaque fois
> que le clavier USB se déclare.
>
> Sur deux ordinateurs différents en revanche, jamais : les masses ne sont
> pas au même potentiel.

### Copier les fichiers

Dans Thonny, panneau `Fichiers` (`Affichage` → `Fichiers`). Il faut copier
le **contenu** de `device/` à la racine de la carte, pas le dossier
`device` lui-même :

```
/boot.py   /main.py   /config.py   /profiles.py
/inputs.py /hid_keyboard.py        /layouts.py
/display.py /sh1106.py /led.py     /diag.py  /runtime.py
/lib/usb/device/__init__.py
/lib/usb/device/core.py
/lib/usb/device/hid.py
/lib/usb/device/keyboard.py
```

Crée les dossiers `lib`, puis `usb`, puis `device` avec le clic droit.

**Ne copie pas** `tests/`, `docs/`, ni les fichiers `.md` : ils ne servent
que sur le PC.

> **Règle de sécurité pendant toute la mise au point :** garde
> `HID_ENABLED = False` dans `config.py`, et transfère `boot.py` et
> `main.py` **en dernier**, seulement après le test 6. Tant que
> `HID_ENABLED` est à False, le macropad ne peut physiquement rien taper.

---

## TEST 1 — La carte seule

Rien de branché sauf l'USB.

```python
>>> import diag
>>> diag.run(seconds=1)
```

### Ce que tu dois voir
* `MicroPython : ... v1.29.0` — et surtout **jamais en dessous de v1.27.0**,
  sinon le clavier s'énumère mais n'envoie rien (voir `docs/01`) ;
* `Plateforme : esp32` ;
* `machine.USBDevice disponible : True` — si c'est `False`, ce n'est pas le
  bon firmware, rien de la suite ne fonctionnera ;
* la quantité de RAM libre. **Les deux cas sont bons :**
  * plusieurs millions d'octets → variante `SPIRAM_OCT`, la PSRAM est active ;
  * environ **224 000** octets → variante standard, la PSRAM n'est pas
    activée. **Ce n'est pas un problème**, c'est même préférable ici : le
    firmware consomme ~60 Ko, et le bug des rapports HID vides ne touchait
    que les cartes à PSRAM active. Ne reflashe pas.

Teste aussi le redémarrage :

```python
>>> import machine
>>> machine.reset()
```

---

## TEST 2 — L'écran OLED

Débranche l'USB. Câble uniquement l'OLED : **VCC sur 3V3** (jamais 5 V),
GND, SDA sur GPIO8, SCL sur GPIO9. Rebranche.

```python
>>> import diag
>>> diag.run(seconds=1)
```

### Ce que tu dois voir
```
OLED I2C : ['0x3c']
```
et à l'écran : `DIAGNOSTIC` / `HID DISABLED`, **sans décalage horizontal**.

* Liste vide → vérifie l'alimentation, et **inverse SDA et SCL** : c'est
  l'erreur la plus fréquente.
* Texte décalé de deux pixels → le décalage de colonnes du SH1106 ne
  correspond pas à ta dalle (voir `display.py`, la commande `0x02`).
* Attention : une adresse qui répond prouve qu'un écran est là, **pas**
  qu'il s'agit d'un SH1106. Un SSD1306 répond à la même adresse et
  afficherait un texte brouillé.

---

## TEST 3 — Les quatre touches mécaniques

Débranche. Câble B1 à B4 (GPIO4, 5, 6, 7 vers GND). Rebranche.

```python
>>> import diag
>>> diag.run(seconds=30)
```

### Ce que tu dois voir
* état initial : `actif = False` partout ;
* un appui franc → **une seule** ligne `APPUI/TOUCHER`, puis une ligne
  `relachement` ;
* maintien de 5 secondes → **aucune répétition** ;
* le bilan final compte exactement le nombre d'appuis que tu as faits.

Si un appui en compte 2 ou 3 : augmente `DEBOUNCE_MS` (25 → 35) dans
`config.py`, puis **RESET matériel**.

---

## TEST 4 — Les deux TTP223

Débranche. Câble les deux modules : **VCC sur 3V3 impérativement**, GND,
OUT sur GPIO10 et GPIO11. Rebranche **sans poser les doigts dessus** : ces
modules se calibrent à la mise sous tension.

```python
>>> diag.run(seconds=30)
```

### Ce que tu dois voir
* au repos : `PREVIOUS` et `NEXT` avec `actif = False` ;
* un effleurement → **une seule** ligne `APPUI/TOUCHER` ;
* **doigt maintenu 5 secondes → toujours une seule ligne.** C'est le
  comportement voulu : pas de défilement continu des profils.

Si l'état au repos est `actif = True` et devient False au toucher, tes
modules sont en logique inverse : mets `TTP_ACTIVE_HIGH = False` dans
`config.py`.

Si le module réagit une fois sur deux, il est peut-être configuré en mode
bascule (*toggle*) par une pastille soudée au dos. Le réglage logiciel ne
transforme pas un module bascule en module momentané : il faut le
reconfigurer matériellement.

---

## TEST 5 — Le contact du bouton ESC

Débranche. Câble **uniquement le contact** (GPIO14 vers GND), pas encore la
LED. Rebranche.

```python
>>> diag.run(seconds=30)
```

### Ce que tu dois voir
`ESC APPUI/TOUCHER` puis `ESC relachement`, un seul par appui.

Bouge doucement le câble pendant le test : aucun ESC fantôme ne doit
apparaître. S'il y en a, ajoute la résistance de 1 kΩ en série et,
éventuellement, un condensateur de 10 nF (voir `docs/05` § 5.5 et § 5.6).

---

## TEST 6 — La LED du bouton ESC

**Avant tout : hors tension**, vérifie les pattes du BC547 et le sens de la
LED au multimètre (`docs/05` § 5.3). C'est l'étape où une erreur détruit un
composant.

Câble l'étage LED, rebranche, puis :

```python
>>> import diag
>>> diag.run(seconds=30, led_test=True)
```

### Ce que tu dois voir
* 0 à 3 s : LED faiblement allumée (5 %) ;
* 3 à 6 s : nettement plus lumineuse (20 %) ;
* ensuite : respiration douce, sans à-coup ni scintillement ;
* un appui sur ESC déclenche un flash bien visible.

**Touche la LED et la résistance de 330 Ω à chaque étape : tout doit rester
froid.** Si quelque chose chauffe, débranche immédiatement — c'est une
erreur de câblage (résistance oubliée, transistor inversé, court-circuit).

* LED allumée en permanence → transistor probablement mal orienté, ou
  résistance de 10 kΩ absente.
* LED jamais allumée → sens de la LED, ou continuité de la résistance de
  base, ou GPIO15 occupée par un quartz 32 kHz (`docs/05` § 5.8).
* Scintillement visible → passe `PWM_FREQ` à 4000 dans `config.py`.

---

## TEST 7 — Le clavier USB, une lettre et rien d'autre

C'est l'étape décisive. **Branche maintenant aussi le port USB natif.**

### 7a. Vérification AZERTY, sans rien envoyer

```python
>>> import diag
>>> diag.keymap("_MATCHPROP")
```

Le `_` doit ressortir en **touche 37, sans Maj**. S'il ressort en touche 45
avec Maj, `KEYBOARD_LAYOUT` est resté sur `US_QWERTY`.

### 7b. Une seule lettre

Ouvre le **Bloc-notes** et garde un vrai clavier sous la main. Puis dans
`config.py` :

```python
HID_ENABLED = True
HID_TEST = "LETTER"
```

Transfère `config.py`, puis **RESET matériel** (sans maintenir B1, sinon tu
tombes en SAFE MODE). Attends les 2,5 secondes de garde, clique dans le
Bloc-notes, et appuie **une fois** sur B1.

### Ce que tu dois voir
* Windows détecte un périphérique, et un `Périphérique clavier HID`
  supplémentaire apparaît dans le Gestionnaire de périphériques ;
* le REPL affiche `HID : interface ouverte par Windows` ;
* un **`a`** apparaît dans le Bloc-notes ;
* maintenir B1 n'écrit pas une deuxième lettre ;
* B2, B3 et B4 ne font rien : c'est normal en mode test.

**Si rien ne s'écrit**, dans l'ordre : es-tu branché sur le port **natif**
et non le port UART ? Le câble transporte-t-il bien les données (certains
câbles ne font que la charge) ? Le focus est-il dans le Bloc-notes ?
`HID_ENABLED` est-il bien à True ? Le message « interface ouverte » prouve
que Windows a configuré le clavier, **pas** qu'il a reçu un rapport
correct : si l'interface est ouverte et que rien n'arrive, note ta version
exacte de MicroPython et regarde `docs/01` § 1.3.

### 7c. Les autres formes de frappe

Change `HID_TEST` puis fais un RESET à chaque fois :

| HID_TEST | B1 envoie | Où vérifier |
|---|---|---|
| `"ESC"` | Échap | ouvre la boîte Rechercher du Bloc-notes, elle doit se fermer |
| `"UNDO"` | Ctrl+Z | tape une ligne, puis annule |
| `"AZERTY"` | `_ABCDEFGHIJKLMNOPQRSTUVWXYZ` | Bloc-notes, **Verr. Maj éteint** |
| `"COMMANDS"` | `_MATCHPROP _HATCH _ISOLATEOBJECTS` | Bloc-notes |

Les deux modes texte n'ajoutent volontairement pas de touche Entrée : tu
peux relire l'orthographe avant de valider quoi que ce soit.

---

## TEST 8 — Le test AZERTY complet

Vérifie d'abord, à côté de l'horloge Windows, que la disposition active est
bien **FRA**.

Avec `HID_TEST = "COMMANDS"`, tu dois lire exactement :

```
_MATCHPROP _HATCH _ISOLATEOBJECTS
```

| Ce que tu vois | Diagnostic |
|---|---|
| `_MATCHPROP` | parfait |
| `8MATCHPROP` | Verr. Maj est allumé et `CAPS_AFFECTS_DIGIT_ROW` est mal réglé |
| `-MATCHPROP` | `KEYBOARD_LAYOUT` est sur `US_QWERTY` alors que Windows est en FRA |
| `_,ATCHPROP` (le M devient une virgule) | Windows est en QWERTY : mets `KEYBOARD_LAYOUT = "US_QWERTY"` |
| `_MQTCHPROP` (A et Q inversés) | même cause |

Refais ensuite l'essai **Verr. Maj allumé** : le résultat doit être
identique. C'est précisément le bug qui a été corrigé (voir `docs/06`).

---

## TEST 9 — Les profils

Remets `HID_TEST = None` et garde `HID_ENABLED = True`. RESET.

Touche `NEXT` plusieurs fois.

### Ce que tu dois voir
* le nom du profil s'affiche en gros pendant une demi-seconde, puis la
  liste des quatre touches revient ;
* l'enchaînement est `CIVIL 3D` → `WORD` → `WINDOWS` → `BLENDER` →
  `CIVIL 3D` ;
* `PREVIOUS` fait exactement l'inverse ;
* une seule ligne `Profil : ...` par toucher.

---

## TEST 10 — Tout ensemble, puis Civil 3D

Ouvre une copie de dessin **sans importance**, clique dans la zone de
dessin pour lui donner le focus.

| Touche | Attendu |
|---|---|
| B1 | `_MATCHPROP` puis Entrée : la copie de propriétés démarre |
| B2 | `_HATCH` : la boîte de hachures s'ouvre |
| B3 | annulation de la dernière action |
| B4 | `_ISOLATEOBJECTS` : demande de sélection |
| ESC | annule la commande en cours, dans tous les profils |

Vérifie aussi :

* pendant que `_ISOLATEOBJECTS` s'écrit, appuie sur ESC : la fin du texte
  doit être abandonnée et Échap envoyé. Ce qui était déjà tapé reste tapé,
  c'est normal, on ne peut pas revenir en arrière ;
* la LED respire sans interruption pendant les frappes ;
* après un `Alt+Tab`, tape au clavier normal : si des majuscules sortent
  toutes seules, un modificateur serait resté enfoncé — cela ne doit jamais
  arriver.

---

## TEST 11 — Le SAFE MODE

À vérifier **avant** de considérer le montage terminé : c'est ton filet de
sécurité.

1. Débranche.
2. **Maintiens B1.**
3. Rebranche sans relâcher B1.
4. Relâche après 2 secondes.

### Ce que tu dois voir
* à l'écran : `SAFE MODE` / `HID DISABLED` ;
* dans le REPL : `SAFE MODE - HID DISABLED`, puis
  `REPL disponible. Diagnostics : import diag; diag.run()` ;
* **aucune touche envoyée**, même en appuyant partout ;
* Thonny reste connecté et tu peux modifier tes fichiers.

C'est ce mode qu'il faut utiliser si une modification de `profiles.py`
transforme le macropad en clavier fou. Autre porte de sortie : le port
UART, où le REPL reste toujours disponible.
