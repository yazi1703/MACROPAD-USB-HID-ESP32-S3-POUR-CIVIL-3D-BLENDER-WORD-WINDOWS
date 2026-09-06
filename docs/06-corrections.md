# 6. Corrections apportées à ton projet

Ton projet a été repris **tel quel** comme base : structure `device/`,
bibliothèques USB officielles recopiées, `DEPENDENCIES.lock.json`,
`HID_ENABLED = False` à la livraison, modes `HID_TEST`. Tout cela est bien
pensé et a été conservé.

Voici ce qui a été corrigé, et pourquoi. Chaque correction est verrouillée
par un test automatique dans `tests/test_logic.py` (classe `Corrections`).

**Vérification faite :** exécutés contre la version d'origine, **12 de ces
14 nouveaux tests échouent** — la preuve que chaque défaut était réel. Les
deux autres (`test_capslock_us_only_affects_letters` et
`test_shortcut_uses_physical_key_not_character`) passent déjà sur ta
version : ils vérifient un comportement qui était correct, et servent de
garde-fou contre une régression future.

---

## Correction 1 — Verr. Maj cassait les commandes Civil 3D (important)

**Fichier :** `device/layouts.py`

**Le défaut.** `character_keys()` tenait compte de la touche Verr. Maj pour
les lettres, mais pas pour le `_` ni pour les chiffres. Or sous Windows,
sur un clavier **français**, Verr. Maj agit aussi sur la rangée des
chiffres. Verr. Maj allumé, la touche du 8 écrit « 8 » et non « _ ».

**La conséquence.** Avec Verr. Maj allumé, `_MATCHPROP` partait en
`8MATCHPROP`, et Civil 3D répondait « commande inconnue ». Le symptôme
était d'autant plus déroutant que les lettres, elles, sortaient
correctement.

**La correction.** Chaque entrée des tables porte maintenant un drapeau
« cette touche est-elle affectée par Verr. Maj ? ». Le calcul du Maj est
unifié : lettres et rangée des chiffres sont traitées de la même façon en
AZERTY, et seules les lettres le sont en QWERTY, ce qui est le comportement
réel des deux dispositions.

Un réglage `CAPS_AFFECTS_DIGIT_ROW = True` a été ajouté dans `config.py`
au cas où ton Windows se comporterait autrement.

**Tests :** `test_capslock_underscore_fr`, `test_capslock_digits_fr`,
`test_capslock_us_only_affects_letters`,
`test_commands_typable_with_capslock_on`.

---

## Correction 2 — Table de caractères très incomplète

**Fichier :** `device/layouts.py`

**Le défaut.** Seuls A-Z, 0-9, l'espace, le `_` et le retour ligne étaient
gérés (une quarantaine de caractères). Toute macro contenant un point, une
virgule, un tiret ou une parenthèse faisait échouer le démarrage de
`main.py`, puisque toutes les macros sont validées au boot.

De plus `key_code()` refusait les chiffres : une macro `Ctrl+1`
(interligne dans Word, par exemple) empêchait la carte de démarrer.

**La correction.** Les deux tables sont maintenant construites en entier :
**107 caractères en AZERTY**, ponctuation et caractères AltGr compris
(`@ # { } [ ] \ | ~ ^` ...). Les combinaisons acceptent les chiffres et les
symboles.

Le comportement « on échoue avant la première frappe plutôt que d'écrire
une commande à moitié » a été conservé : c'était une bonne idée.

**Tests :** `test_extended_characters`, `test_combo_accepts_digits_and_symbols`,
`test_shortcut_uses_physical_key_not_character`.

---

## Correction 3 — Une macro était perdue juste après un changement de profil

**Fichier :** `device/hid_keyboard.py`

**Le défaut.** `submit()` exigeait `ready()`, qui est faux tant qu'un
relâchement est en attente. Or `cancel()` — appelé à chaque changement de
profil et à chaque appui sur ESC — programme justement un relâchement.

**La conséquence.** Si tu touchais le TTP puis appuyais tout de suite sur
une touche, la macro était refusée avec le message « interface non prête »
et rien ne se passait. Un défaut rare mais déroutant, exactement au moment
où tu enchaînes les gestes.

**La correction.** Une méthode `accepting()` a été ajoutée : il suffit que
Windows ait ouvert l'interface et qu'aucune panne ne soit déclarée. Le
relâchement en attente reste bien envoyé en premier par `tick()`, mais il
ne bloque plus l'acceptation d'une nouvelle macro.

**Tests :** `test_submit_accepted_right_after_cancel`,
`test_submit_accepted_right_after_escape`.

---

## Correction 4 — `close()` débranchait l'USB sans raison

**Fichier :** `device/hid_keyboard.py`

**Le défaut.** `close()` finissait systématiquement par
`usb.device.get().active(False)` dès que le relâchement ne pouvait pas
être confirmé, y compris quand **aucune touche n'était enfoncée**. Cas
typique : tu travailles par le port UART, le port natif n'est pas branché,
tu fais Ctrl-C dans Thonny — et l'USB était désactivé pour rien.

**La correction.** Le clavier retient maintenant si le dernier paquet
envoyé laissait des touches enfoncées (`keys_down`). Si rien n'est
enfoncé, `close()` se contente de sortir proprement et **ne touche pas à
l'USB** : le REPL reste disponible. La déconnexion de sécurité subsiste,
mais uniquement dans le cas où elle sert vraiment à quelque chose, c'est-
à-dire quand des touches risquent de rester bloquées côté Windows.

**Tests :** `test_close_keeps_usb_when_nothing_pressed`,
`test_close_after_macro_leaves_nothing_pressed`.

---

## Correction 5 — Le bouton ESC avait 20 ms de retard

**Fichier :** `device/inputs.py`

**Le défaut.** Le filtre anti-rebond attendait 20 ms de stabilité avant de
déclarer l'appui. Pour une macro c'est invisible ; pour une touche
d'annulation que tu veux « instantanée », c'est dommage et cela ne
correspondait pas à l'intention affichée.

**La correction.** Un second mode a été ajouté au `Debouncer` : le mode
**rapide**, qui agit dès le premier front puis ignore les rebonds pendant
la durée de l'anti-rebond. C'est la méthode des vrais claviers. Le retard
passe de 20 ms à ~0 ms, sans perdre la protection contre les rebonds ni la
règle « il faut relâcher avant de réappuyer ».

Activé pour ESC uniquement, par `ESC_FAST_EDGE = True` dans `config.py`.
Les quatre touches et les TTP223 gardent le mode patient, plus tolérant.

**Tests :** `test_esc_fast_edge_is_immediate`, `test_esc_fast_edge_held_at_boot`.

---

## Correction 6 — L'ordre de lecture des entrées n'était pas garanti

**Fichier :** `device/inputs.py`, `device/diag.py`

**Le défaut.** `Inputs.items` était un dictionnaire, parcouru avec
`.items()`, avec le commentaire « ESC en tête de l'ordre de lecture ».
En MicroPython, **l'ordre de parcours d'un dictionnaire n'est pas garanti**
(contrairement à Python sur PC depuis la 3.7). Le commentaire était donc
faux.

En pratique la priorité d'ESC était sauvée par `main.py`, qui teste
`if "ESC" in pressed` sur la liste complète. Mais l'ordre des lignes de
diagnostic, lui, pouvait changer d'un démarrage à l'autre.

**La correction.** Une liste `sequence` garantit maintenant l'ordre
`ESC, B1, B2, B3, B4, PREVIOUS, NEXT`. Le dictionnaire `items` est
conservé pour la compatibilité.

**Test :** `test_input_order_is_deterministic`.

---

## Correction 7 — Détection du SAFE MODE plus robuste

**Fichier :** `device/boot.py`

**Le défaut.** Une lecture unique de GPIO4 juste après avoir activé la
résistance de tirage. Sur un câblage un peu long, la broche n'a pas
toujours fini de se stabiliser : un faux SAFE MODE était possible.

**La correction.** 5 ms d'attente, puis trois lectures concordantes.

---

## Correction 8 — Recherche USB : la correction du bug existe bel et bien

**Fichier :** `GUIDE_FR.md` § 2, détaillé dans `docs/01-recherche-usb-hid.md`

**Ce que disait ton guide.** Que les issues
[micropython-lib #1044](https://github.com/micropython/micropython-lib/issues/1044)
et [MicroPython #18098](https://github.com/micropython/micropython/issues/18098)
paraissaient toujours ouvertes, et que la mise à jour de TinyUSB en 1.29.0
« ne prouve pas la résolution du symptôme ». La prudence était justifiée,
mais il manquait une information.

**Ce qui a été trouvé.** Les notes de version officielles de **MicroPython
v1.27.0** annoncent explicitement la correction, mot pour mot :

> *« TinyUSB integration has been improved, with a bug fix for Zero Length
> Packets that affected REPL reliability, along with a fix for blank USB HID
> reports on boards with PSRAM. »*

— [Release v1.27.0](https://github.com/micropython/micropython/releases/tag/v1.27.0)

Le symptôme décrit (« blank USB HID reports ») et la condition (« on boards
with PSRAM ») correspondent exactement au bug signalé et exactement à ta
carte N16R8.

**Nuance à garder.** Une issue GitHub non fermée ne signifie pas qu'un
correctif n'a pas été livré : les mainteneurs ne referment pas toujours
les tickets. Mais on ne peut pas non plus considérer la correction comme
prouvée sur ton matériel tant que le test LETTER n'a pas écrit un « a ».

**Conclusion pratique.** Ta version 1.29.0 est postérieure à la correction,
c'est la bonne. Le vrai enseignement est un seuil : **ne jamais descendre
en dessous de la v1.27.0** sur cette carte.

---

## Correction 9 — Déplacement de la résistance de 2,2 kΩ (électronique)

**Fichier :** `docs/05-electronique.md`, `GUIDE_FR.md` § 10

Ta version place la résistance de base de 2,2 kΩ dans le boîtier du bouton
ESC. Elle est plus utile **côté macropad**, juste à la sortie de GPIO15 :
le fonctionnement est identique, mais le fil du câble se retrouve derrière
la résistance. Si du +5 V venait à toucher ce fil, le courant atteignant le
GPIO serait limité à 0,77 mA au lieu d'être illimité.

Dans le même esprit, une résistance de **1 kΩ en série sur GPIO14**, côté
macropad, protège l'entrée du contact ESC.

Deux résistances que tu as déjà, pour rendre le câble déporté tolérant aux
fautes. Détail complet et calculs dans `docs/05-electronique.md` § 5.5.

---

## Correction 10 — Un changement de profil bloquait le clavier (trouvée au montage)

**Fichier :** `device/hid_keyboard.py`

**Le symptôme.** En cours d'utilisation, un simple changement de profil
produisait :

```
Profil : WORD
ERREUR CRITIQUE HID : transfert sans progression - macros arretees, RESET requis
```

Et à partir de là, plus aucune macro ne partait : toutes répondaient
`HID : action ignoree, interface non prete`, jusqu'au RESET matériel.

**La cause.** `tick()` surveille les blocages avec un chronomètre :

```python
if ticks_diff(now, self.progress) > C.HID_TIMEOUT_MS and (self.release_needed or ...):
    self._fail("transfert sans progression")
```

`self.progress` mémorise la date de la dernière avancée réelle. Mais quand
le macropad est au repos, **rien ne le rafraîchit** : il vieillit
indéfiniment.

Or `cancel()` — appelé à chaque changement de profil par `main.py` —
positionnait `release_needed = True` **sans toucher à `progress`**. Au tour
de boucle suivant, le garde-fou comparait donc l'instant présent à une date
vieille de plusieurs secondes, voire minutes, et déclarait une panne
instantanément. Rien n'était réellement bloqué.

Il suffisait de laisser le macropad tranquille plus d'une seconde
(`HID_TIMEOUT_MS`) puis de changer de profil pour le tuer. Autant dire :
en permanence.

À noter que `escape()`, lui, faisait bien `self.progress = now` après son
appel à `cancel()`. C'est pour cela que le bouton ESC ne déclenchait
jamais le problème, ce qui rendait le symptôme d'autant plus déroutant.

**La correction.** `cancel()` remet le chronomètre à zéro : le relâchement
qu'il programme est une nouvelle action, elle mérite son propre délai.

**Correction complémentaire.** Une panne était définitive : `fault` ne se
levait jamais et seul un RESET matériel rendait le clavier. C'est excessif
pour un incident passé. Désormais, quand l'hôte USB **reconfigure le
périphérique** (débranchement/rebranchement, réveil du PC), la panne est
effacée : l'hôte a de toute façon oublié toute touche restée enfoncée,
l'état est donc sain par construction.

**Tests :** `test_cancel_apres_repos_ne_declenche_pas_de_panne`,
`test_le_vrai_blocage_declenche_toujours_la_panne` (vérifie que le
garde-fou n'a pas été désarmé), `test_reconnexion_usb_efface_la_panne`.
Les deux premiers échouent sur la version précédente.

**Bug d'origine**, présent dès la première version du projet : mes
corrections antérieures ne l'avaient ni causé ni révélé. Il a fallu
l'usage réel pour le faire sortir.

## Correction 11 — La page de configuration restait vide (trouvée à l'usage)

**Le symptôme.** La page s'ouvre, le titre s'affiche, les boutons sont là…
et il n'y a **rien** : aucun profil, aucune macro, les deux pastilles du
haut restent sur `...`. Aucun message d'erreur, ni dans la page, ni dans
la console. Les deux pages étaient touchées, celle du PC comme celle du
WiFi.

**La cause.** La page est écrite une seule fois dans
`tools/page_config.html`, puis recopiée dans les deux serveurs par
`tools/injecter_page.py`, à l'intérieur d'une chaîne Python. Elle y était
recopiée dans une chaîne **ordinaire**, où l'antislash sert à échapper le
caractère suivant. Ce bout de JavaScript :

```js
say(r.ok ? "Enregistre et applique." : "Refuse :\n" + r.raison, r.ok);
```

devenait, une fois lu par Python :

```js
say(r.ok ? "Enregistre et applique." : "Refuse :
" + r.raison, r.ok);
```

La chaîne JavaScript n'est plus fermée sur sa ligne. Le navigateur
refuse alors **tout le bloc `<script>`** — pas seulement cette ligne. Rien
ne s'exécute, donc rien ne se dessine, et comme le code qui affiche les
erreurs fait lui aussi partie du script, il ne peut même pas se plaindre.
C'est ce silence qui rend la panne difficile à comprendre.

**La correction.** Le préfixe `r` (chaîne *brute*) : `PAGE = r"""…"""`.
Python n'interprète plus l'antislash, la page arrive intacte dans le
navigateur. L'injecteur refuse en plus toute page qu'un tel littéral ne
pourrait pas contenir, et **relit ce qu'il vient d'écrire** pour vérifier
que Python le comprend bien à l'identique.

**Les tests ajoutés** (`PageDeConfigurationIntacte`, 5 tests) :

| Test | Ce qu'il empêche |
|---|---|
| la page de `portal.py` est identique à sa source | une divergence entre les deux serveurs |
| celle de `macropad_auto.py` aussi | idem, côté PC |
| le JavaScript est valide (`node --check`) | exactement le bug ci-dessus |
| la page se construit avec de vraies données | une erreur pendant le rendu (champ absent, faute de frappe) |
| la page prévient quand elle n'a rien reçu | une page vide et muette |

Les deux derniers font tourner le JavaScript **hors navigateur**, avec un
DOM minimal (`tests/page_smoke.js`) : on lui donne les valeurs d'usine, on
le laisse dessiner, et on compte ce qu'il a produit — 4 cartes de profil,
72 listes déroulantes, 7 lignes de logiciels. Si la page ne se construit
plus, le test échoue avant que tu n'ouvres le navigateur.

**Et une amélioration au passage.** Quand la page ne reçoit aucun profil —
macropad débranché, ou compagnon lancé avec `--simuler` — elle l'écrit
maintenant en toutes lettres, avec quoi vérifier. Une page vide ne doit
jamais laisser croire à un projet cassé.

## Ce qui n'a PAS été touché

- La structure `device/` et les quatre fichiers USB officiels recopiés :
  très bonne décision, aucune installation réseau nécessaire sur la carte.
- Le driver `sh1106.py` de robert-hh, repris sans modification.
- `HID_ENABLED = False` à la livraison et les modes `HID_TEST` : c'est la
  meilleure idée du projet, elle est conservée telle quelle.
- La garde de démarrage de 2,5 s, la file de macros bornée, la compilation
  des macros avant la première frappe, la gestion de la déconnexion USB.
- L'affichage OLED « une ligne par touche » : plus lisible que la grille
  2 × 2 d'origine, il permet d'écrire `EXPLORER` en entier.
- `DEPENDENCIES.lock.json`, `licenses/`, le schéma SVG.

En dehors des points ci-dessus, tous les fichiers de `device/` ont été
**recommentés en détail** pour être lisibles par un débutant en
MicroPython : chaque fichier commence par une explication de ce qu'il fait
et pourquoi il le fait ainsi.
