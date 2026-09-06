# 3. Mise en service progressive

Ne branchez pas tout d'un coup et ne lancez pas `main.py` directement.
Suivez les etapes dans l'ordre. A chaque etape, la section **"Ce que vous devez
observer"** vous dit quand passer a la suivante.

> **Regle d'or pendant toute la mise au point :** branchez les **deux** ports
> USB-C. Thonny sur le port UART (le REPL y reste stable), le clavier HID sur
> le port natif.

---

## Preparation : Thonny

1. Installez Thonny (<https://thonny.org>).
2. `Outils` -> `Options` -> onglet `Interpreteur`.
3. Interpreteur : **MicroPython (ESP32)**.
4. Port : celui du **port USB-UART** de la carte.
5. `OK`. Le REPL doit repondre :

```
>>> print("bonjour")
bonjour
```

### Copier les fichiers sur la carte

Dans Thonny, panneau `Fichiers` (`Affichage` -> `Fichiers`). Ouvrez le dossier
du projet dans la partie haute, puis pour chaque fichier : clic droit ->
**Televerser vers /**.

Fichiers a copier a la racine de la carte :

```
boot.py   main.py   config.py   profiles.py
inputs.py hid_keyboard.py       keymaps.py
display.py sh1106.py led.py     diag.py
```

**Ne copiez pas** le dossier `tools/` ni le dossier `docs/` : ils servent
uniquement sur le PC.

> **Astuce importante :** tant que la mise au point n'est pas finie, renommez
> `main.py` en `macropad.py` sur la carte. Rien ne demarre alors automatiquement
> et vous lancez le firmware a la demande par `import macropad; macropad.run()`.
> Vous ne pourrez jamais vous retrouver bloque par un clavier qui tape tout
> seul. Renommez-le en `main.py` seulement a la toute fin.

---

## TEST 1 — ESP32-S3 et MicroPython seuls

**Rien de branche sur la carte, sauf l'USB.**

```python
>>> import diag
>>> diag.info()
```

### Ce que vous devez observer
* une version MicroPython **>= 1.27.0** (voir `docs/01-recherche-usb-hid.md`
  paragraphe 1.3 : en dessous, le HID enverra des rapports vides) ;
* `plateforme : esp32` ;
* `machine : ESP32S3 module with Octal-SPIRAM` ou equivalent — la mention
  **Octal-SPIRAM** confirme que vous avez flashe la bonne variante ;
* une RAM libre de plusieurs millions d'octets (grace a la PSRAM).

Testez aussi le redemarrage :

```python
>>> import machine
>>> machine.reset()
```
Thonny se reconnecte et affiche le message de `boot.py`.

---

## TEST 2 — Ecran OLED

Cablez uniquement l'OLED (VCC 3V3, GND, SDA GPIO8, SCL GPIO9).

```python
>>> import diag
>>> diag.test_i2c()
```

### Ce que vous devez observer
```
BUS I2C  (SDA=GPIO8, SCL=GPIO9, 400000 Hz)
  0x3C (60)   <-- OLED SH1106 probable
  ecran retenu : 0x3C
```

Si `aucun peripherique detecte` : verifiez l'alimentation, inversez SDA et SCL
(erreur la plus frequente), et controlez vos soudures.

Puis la mire :

```python
>>> diag.test_oled()
```

L'ecran doit afficher `DIAG OLED`, `SH1106 128x64`, `0x3C` et `OK`, **sans
decalage horizontal**. Un texte decale de 2 pixels signifierait que le
`COLUMN_OFFSET` du pilote ne correspond pas a votre dalle : il se regle en tete
de `sh1106.py`.

---

## TEST 3 — Les 4 touches mecaniques

Cablez B1 a B4 (GPIO4, 5, 6, 7 vers GND). **Aucun HID n'est envoye.**

```python
>>> import diag
>>> diag.test_inputs(30)
```

### Ce que vous devez observer
* l'etat initial de toutes les entrees doit etre `repos` ;
* chaque appui franc affiche **une seule** ligne `B1  APPUI` puis
  `B1  relache` ;
* le bilan final doit compter exactement autant d'appuis que ce que vous avez
  reellement fait.

Si un appui compte 2 ou 3 : augmentez `DEBOUNCE_MS` dans `config.py`
(25 -> 35 ou 40).

---

## TEST 4 — Les 2 TTP223

Cablez les deux modules (VCC **3,3 V**, GND, OUT sur GPIO10 et GPIO11).

```python
>>> diag.test_inputs(30)
```

### Ce que vous devez observer
* au repos : `TTP-PREV=repos` et `TTP-NEXT=repos` ;
* un effleurement -> **une seule** ligne `APPUI` ;
* **doigt maintenu 5 secondes -> toujours une seule ligne `APPUI`**. C'est le
  comportement demande : pas de defilement continu.

Si l'etat au repos est `APPUI` et devient `repos` au toucher, vos modules sont
cables en logique inverse : passez `TTP_ACTIVE_HIGH = False` dans `config.py`.

Si les touchers sont erratiques : eloignez les cables des modules de la LED et
du cable ESC, et augmentez `DEBOUNCE_TTP_MS`.

---

## TEST 5 — Le bouton ESC

Cablez uniquement le contact (GPIO14 vers GND), **pas encore la LED**.

```python
>>> diag.test_inputs(20)
```

### Ce que vous devez observer
`ESC  APPUI` puis `ESC  relache`, un seul par appui. Toujours aucun HID.

---

## TEST 6 — La LED du bouton ESC

Cablez l'etage BC547 comme dans `docs/02-cablage.md`, **apres avoir verifie le
brochage du transistor**.

```python
>>> import diag
>>> diag.test_led()
```

### Ce que vous devez observer
* paliers a 0 %, 5 %, 20 %, 50 %, 100 % : luminosite croissante et reguliere ;
* **touchez la LED et la resistance de 330 Ohm a chaque palier : tout doit
  rester froid, y compris a 100 %.** Si quelque chose chauffe, coupez tout :
  c'est une erreur de cablage (resistance oubliee, court-circuit, transistor
  inverse) ;
* 6 secondes de respiration : montee et descente douces, sans a-coups ni
  scintillement ;
* 3 flashs bien visibles, chacun suivi d'un retour progressif a la respiration.

Si la LED reste allumee en permanence : le transistor est probablement mal
oriente, ou la resistance de 10 kOhm manque.
Si elle ne s'allume jamais : verifiez le sens de la LED (anode vers le +5 V) et
la continuite de la resistance de base.
Si elle scintille : augmentez `LED_PWM_FREQ` a 2000 dans `config.py`.

---

## TEST 7 — Le clavier USB HID

C'est l'etape decisive. **Branchez maintenant le port USB natif** en plus du
port UART.

### 7a. La bibliotheque est-elle installee ?

```python
>>> import diag
>>> diag.test_hid()
```

Doit afficher :
```
  bibliotheque usb.device.keyboard : PRESENTE
  machine.USBDevice : DISPONIBLE
  HID volontairement NON initialise (diagnostic sans risque).
```

Si `ABSENTE` : depuis le PC, `mpremote connect COMx mip install usb-device-keyboard`
(voir `docs/01-recherche-usb-hid.md`, paragraphe 1.6).

### 7b. Envoi d'une seule lettre

Ouvrez le **Bloc-notes**, puis dans Thonny :

```python
>>> diag.test_hid(send_letter=True)
```

Vous avez 8 secondes pour cliquer dans le Bloc-notes.

### Ce que vous devez observer
* Windows detecte un nouveau peripherique (un petit son) ;
* un **`a`** apparait dans le Bloc-notes ;
* dans le Gestionnaire de peripheriques, rubrique **Claviers**, un
  `Peripherique clavier HID` supplementaire.

**Si rien n'arrive :** dans neuf cas sur dix, soit vous etes branche sur le
port UART au lieu du port natif, soit votre MicroPython est anterieur a la
v1.27.0 (bug des rapports vides sur les cartes a PSRAM).

### 7c. Les autres formes de frappe

```python
>>> import hid_keyboard, time, config
>>> k = hid_keyboard.Keyboard(layout_name=config.KEYBOARD_LAYOUT)
>>> k.start()
>>> def envoyer():
...     fin = time.ticks_add(time.ticks_ms(), 3000)
...     while k.pending() and time.ticks_diff(fin, time.ticks_ms()) > 0:
...         k.service(time.ticks_ms()); time.sleep_ms(1)
...
>>> k.tap("ESC");            envoyer()    # Echap
>>> k.combo("CTRL", "Z");    envoyer()    # Annuler
>>> k.combo("WIN", "E");     envoyer()    # Explorateur de fichiers
>>> k.combo("ALT", "TAB");   envoyer()    # Bascule de fenetre
```

### Ce que vous devez observer
* `WIN+E` ouvre l'Explorateur ;
* `ALT+TAB` change de fenetre **et la relache correctement** : aucune fenetre
  ne doit rester "collee" ;
* apres chaque test, tapez du texte au clavier normal : si des majuscules
  sortent toutes seules ou si les clics deviennent des selections, un
  modificateur serait reste coince — cela ne doit jamais arriver.

---

## TEST 8 — Test AZERTY et commandes Civil 3D

### 8a. Verification hors materiel

```python
>>> import diag
>>> diag.test_keymap("_MATCHPROP")
>>> diag.test_keymap("_ISOLATEOBJECTS")
```

Le `_` doit ressortir en **code HID 0x25 avec le modificateur 0x00** : en
AZERTY, le soulignement est la touche `8` **sans** SHIFT. S'il ressortait en
`0x2D` avec SHIFT, c'est que `KEYBOARD_LAYOUT` est reste sur `US_QWERTY`.

### 8b. Verification reelle dans le Bloc-notes

Ouvrez le Bloc-notes et verifiez d'abord, en bas a droite de la barre des
taches Windows, que la disposition active est bien **FRA**. Puis :

```python
>>> k.type_text("_MATCHPROP"); envoyer()
```

### Ce que vous devez observer
Le Bloc-notes affiche exactement **`_MATCHPROP`**.

| Ce que vous voyez | Diagnostic |
|---|---|
| `_MATCHPROP` | parfait |
| `8MATCHPROP` ou `-MATCHPROP` | mauvaise disposition selectionnee dans `config.py` |
| `_,ATCHPROP` (le M devient une virgule) | Windows est en QWERTY : mettez `KEYBOARD_LAYOUT = "US_QWERTY"` |
| `_MQTCHPROP` (A/Q inverses) | idem, Windows n'est pas en AZERTY |

Le firmware ne modifie **jamais** la disposition clavier de Windows : c'est
`config.py` qui doit s'aligner sur Windows, pas l'inverse.

---

## TEST 9 — Profils, puis systeme complet

### 9a. Profils seuls

Redemarrez la carte, puis lancez le firmware sans le mettre en `main.py` :

```python
>>> import macropad          # (ou: import main)
>>> macropad.run()
```

Touchez `TTP SUIVANT` plusieurs fois.

### Ce que vous devez observer
* l'ecran affiche brievement le nom du profil en gros caracteres (~0,5 s) puis
  revient a la vue a quatre cases ;
* l'enchainement est bien
  `CIVIL 3D` -> `WORD` -> `WINDOWS` -> `BLENDER` -> `CIVIL 3D` ;
* `TTP PRECEDENT` fait exactement l'inverse ;
* le REPL affiche une ligne `[MAIN] profil : ...` par changement, **une seule**.

### 9b. Tout en meme temps

Ouvrez le Bloc-notes et, dans chaque profil, appuyez sur les quatre touches.

### Ce que vous devez observer
* les touches repondent instantanement, **meme pendant l'affichage du nom de
  profil et pendant un flash de la LED** ;
* un appui sur ESC pendant que `_ISOLATEOBJECTS` est en train de s'ecrire
  interrompt la frappe et envoie Echap : c'est voulu (l'ESC annule) ;
* la LED respire sans interruption et sans a-coup pendant les frappes.

---

## TEST 10 — Test Civil 3D reel

1. Ouvrez Civil 3D, un dessin quelconque.
2. Passez au profil `CIVIL 3D`.
3. Cliquez dans la zone de dessin pour donner le focus a la fenetre.

| Touche | Attendu |
|---|---|
| B1 | la ligne de commande affiche `_MATCHPROP` puis lance la copie de proprietes |
| B2 | `_HATCH` : la boite de hachures s'ouvre |
| B3 | annulation de la derniere action |
| B4 | `_ISOLATEOBJECTS` : demande de selection d'objets a isoler |
| ESC | annule la commande en cours, quelle qu'elle soit |

Si la commande apparait mais avec des lettres fausses, revenez au TEST 8b.
Si la commande s'ecrit correctement mais n'est pas reconnue, verifiez que la
ligne de commande est bien active (touche F2 pour afficher l'historique).

---

## TEST 11 — SAFE MODE

C'est votre filet de securite : a verifier **avant** de renommer le fichier en
`main.py`.

1. Debranchez la carte.
2. **Maintenez B1 enfonce.**
3. Rebranchez sans relacher B1.
4. Relachez B1 apres 2 secondes.

### Ce que vous devez observer
* l'ecran affiche :
  ```
  SAFE MODE
  HID DISABLED
  ```
* le REPL affiche `[MAIN] SAFE MODE ACTIF : le clavier HID est desactive.` ;
* **aucune touche n'est envoyee**, meme en appuyant sur B1 a B4 ou sur ESC : le
  REPL affiche `[SAFE] B2 (HATCH) ignore : HID desactive` ;
* la LED respire tres faiblement (8 % au lieu de 25 %) ;
* Thonny reste connecte et vous pouvez modifier et televerser des fichiers.

C'est le mode a utiliser si une modification de `profiles.py` transforme le
macropad en clavier fou.

---

## Passage en service definitif

Une fois les tests 1 a 11 valides :

1. renommez `macropad.py` en `main.py` sur la carte (Thonny, clic droit ->
   `Renommer`) ;
2. debranchez, rebranchez ;
3. l'ecran doit afficher `CIVIL 3D` apres environ 1,5 seconde (temporisation de
   securite reglee par `HID_START_DELAY_MS`).

Pour revenir en developpement : maintenez B1 au demarrage (SAFE MODE), ou
connectez-vous par le port UART et interrompez avec `Ctrl-C` dans le REPL.
