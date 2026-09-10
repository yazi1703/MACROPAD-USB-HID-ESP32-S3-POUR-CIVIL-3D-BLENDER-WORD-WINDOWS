# 11. Deux touches ensemble — les combinaisons

Six touches, c'est six commandes. Mais **deux touches appuyées en même
temps** en font quinze de plus, sans un composant supplémentaire et sans
rien changer au câblage. C'est ce que fait `device/combos.py`.

Ce fichier explique **pourquoi ça ne ralentit rien** (c'est la question
qui a décidé de toute la conception), ce que les combinaisons font dans
Civil 3D, et comment les modifier toi-même.

---

## 11.1 Le problème, en une phrase

Pour savoir que « B3 seule » n'est pas le début de « B3+B4 », il faut
bien **attendre un peu** après B3.

Naïvement, cela ajoute donc un retard à **toutes** les touches. Ce serait
inacceptable : tu as explicitement demandé que les touches restent
instantanées, et un macropad mou est un macropad qu'on n'utilise plus.

Deux choses sauvent la mise.

### 1. Seules les touches concernées sont surveillées

B1 (le presse-papiers) et B2 (Maj/Ctrl) n'entrent dans **aucune**
combinaison. Elles ne passent même pas par `combos.py` : leur chemin dans
le code est exactement celui d'avant, à l'instruction près.

> C'est aussi pour cela que **B1 et B2 ne doivent jamais entrer dans une
> combinaison** : B2 garde Maj enfoncée, et une combinaison n'a pas de
> touche unique à surveiller pour la relâcher. Un test refuse d'ailleurs
> tout `maintien` dans une combinaison.

### 2. Un appui court part déjà **au relâchement**

C'est le point clé, et il était déjà vrai avant les combinaisons : une
macro courte n'est envoyée qu'au moment où tu **lèves** le doigt. Donc :

| Ce que tu fais | Ce qui se passe |
|---|---|
| tu tapes vite (< 50 ms) | la touche est relâchée **avant la fin de la fenêtre** : tout est libéré immédiatement, **zéro retard** |
| tu gardes le doigt | l'appui est transmis à la fin de la fenêtre, **mais avec son horodatage d'origine** |

Cet **horodatage d'origine** est la pièce maîtresse. Sans lui, un appui
long sur B3 partirait 50 ms trop tard. Avec lui, il part à
`GESTE_LONG_MS` **pile**, comme si les combinaisons n'existaient pas.

> Un test le mesure de bout en bout, dans la vraie boucle de `main.py` :
> `test_un_appui_long_sur_une_touche_membre_part_a_l_heure`. Il échoue si
> on remplace l'horodatage d'origine par l'heure courante.

**Résultat : aucune latence ajoutée, sur aucune touche.**

---

## 11.2 Les combinaisons de Civil 3D

Elles sont pensées pour être **retenues par la géométrie**, pas par
cœur : trois familles, trois formes sur le pad.

| Touches | Écran | Ce que ça fait |
|---|---|---|
| **B3 + B4** | `VUE PREC.` | vue enregistrée précédente |
| **B5 + B6** | `VUE SUIV.` | vue enregistrée suivante |
| **B4 + B5** | `PEDIT` | `_PEDIT` — la famille polyligne, autour de B4 |
| **B3 + B5** | `CALQUE OFF` | éteint le calque de l'objet désigné |
| **B4 + B6** | `CALQUE ON` | rallume le dernier calque éteint |
| **B3 + B6** | `HACHURES` | `_HATCH` — les deux extrêmes |

```
   B3   B4   B5   B6
   └────┘         │     les vues : gauche = avant, droite = après
         └────┘         la polyligne : la paire du milieu, sur B4
   └─────────┘          les calques : les deux diagonales
        └─────────┘
   └──────────────┘     les hachures : les deux extrêmes
```

`_HATCHEDIT` n'y figure pas **volontairement** : dans AutoCAD, un
double-clic sur une hachure ouvre déjà son éditeur.

### Les quatre commandes AutoLISP

`MPVIEWPREV`, `MPVIEWNEXT`, `MPLAYEROFF` et `MPLAYERRESTORE` ne sont pas
des commandes AutoCAD : ce sont **les tiennes**, définies dans
[`civil3d/macropad_tools.lsp`](../civil3d/macropad_tools.lsp). Il faut
donc les charger dans Civil 3D — la marche à suivre est dans
[`civil3d/README.md`](../civil3d/README.md).

> **Elles s'écrivent SANS le `_` de tête.** Le souligné demande la
> version internationale d'une commande **native** d'AutoCAD, pour qu'une
> macro écrite en anglais marche sur un AutoCAD français. Une commande
> LISP, elle, n'a pas de traduction : `_MPVIEWNEXT` ne serait pas trouvé.

**Tant que le LISP n'est pas chargé**, ces quatre combinaisons écriront
simplement un nom de commande inconnu dans la ligne de commande. Rien de
grave, mais rien ne se passera non plus.

---

## 11.3 Ce que tu vois quand une combinaison part

Une combinaison ne correspond à **aucune ligne du tableau** de l'écran :
le surlignage habituel ne peut donc pas la montrer. L'écran affiche à la
place, pendant `COMBO_FLASH_MS` (1,2 s par défaut) :

```
┌────────────────┐
│                │
│     ██ ██      │
│    B3+B4       │   ← les touches, en gros
│                │
│   VUE PREC.    │   ← le libellé de la combinaison
│                │
└────────────────┘
```

puis il revient tout seul au tableau. Rien n'est bloqué pendant ce
temps : c'est le même mécanisme que l'écran « nom du profil » au
changement de profil.

Les LED des **deux** touches réagissent, comme pour un appui normal.

---

## 11.4 Les règles, et pourquoi

| Règle | Pourquoi |
|---|---|
| **ESC annule** une combinaison en train de se former | ESC est prioritaire sur tout, sans exception. Il ne déclenche jamais autre chose au passage. |
| **Changer de profil annule** aussi | Les combinaisons du nouveau profil ne sont pas celles de l'ancien. |
| Un `maintien` (Ctrl, Maj) est **refusé** dans une combinaison | Un maintien se relâche quand **sa** touche se relâche. Une combinaison n'en a pas une seule à surveiller : Ctrl resterait enfoncé côté Windows, et plus rien ne répondrait normalement. |
| Il faut **au moins deux touches** | Une « combinaison » d'une seule touche rendrait cette touche inutilisable seule. |
| Deux combinaisons ne peuvent pas avoir **le même couple** de touches | Sinon laquelle partirait ? |
| Pendant qu'une combinaison est partie, les autres touches sont **ignorées jusqu'au relâchement** | Rouler les doigts sur le pad en relâchant ne doit pas déclencher une seconde combinaison par accident. |

Les cinq dernières sont vérifiées **avant** tout enregistrement, comme
les macros : une configuration fautive est refusée avec un message clair,
elle n'est jamais écrite.

**Le compteur d'usage** compte **chaque touche** de la combinaison. C'est
volontaire : ce compteur mesure l'usage des **touches** — pour dessiner
le boîtier, et pour repérer une touche qui ne sert à rien — pas celui des
macros.

---

## 11.5 Les modifier toi-même

Dans la page de configuration (WiFi ou compagnon PC), sous le tableau de
chaque profil :

```
Combinaisons — deux touches appuyées ensemble
┌────────┬────────────┬──────────────────────────────┬───┐
│ 3+4    │ VUE PREC.  │ [texte + Entrée] MPVIEWPREV  │ x │
│ 5+6    │ VUE SUIV.  │ [texte + Entrée] MPVIEWNEXT  │ x │
└────────┴────────────┴──────────────────────────────┴───┘
                                              [+ combinaison]
```

* **Touches** : les numéros gravés sur le pad. Écris `3+4`, ou `3 4`, ou
  même `3 et 4` — la page ne garde que les chiffres, les trie et enlève
  les doublons.
* **Libellé** : ce que l'écran affichera, 16 caractères au plus.
* **Action** : exactement le même éditeur que pour les gestes, avec les
  mêmes types et les mêmes suites d'étapes (commande, pause, validation).

Dans `profils.json`, cela donne :

```json
"combos": [
  {"touches": [3, 4], "label": "VUE PREC.",
   "actions": [{"type": "text_enter", "valeur": "MPVIEWPREV"}]}
]
```

Les numéros du fichier sont **ceux du pad** : `[3, 4]`, c'est B3 et B4.

> **Un fichier écrit avant les combinaisons** n'a pas de bloc `combos` :
> il récupère alors celles d'usine, plutôt que de les perdre en silence à
> la première mise à jour. Une liste `combos` **présente mais vide** veut
> dire « je n'en veux aucune », et elle est respectée.

Pour les changer dans le code plutôt que dans la page, c'est la table
`COMBOS` de `device/profiles.py` :

```python
COMBOS = {
    "CIVIL3D": [
        COMBO((3, 4), "VUE PREC.", [("text_enter", "MPVIEWPREV")]),
    ],
}
```

---

## 11.6 Les réglages

Dans `device/config.py` :

| Réglage | Défaut | À quoi ça sert |
|---|---|---|
| `GESTE_COMBO_MS` | `50` | la fenêtre pendant laquelle deux appuis comptent comme simultanés |
| `COMBO_FLASH_MS` | `1200` | durée de l'affichage `B3+B4 / VUE PREC.` |

`GESTE_COMBO_MS` est le seul chiffre qui demande un peu de doigté :

* **trop court** (< 30 ms) : tes deux doigts n'arrivent jamais assez
  ensemble, la combinaison ne part pas et tu obtiens les deux macros
  séparées ;
* **trop long** (> 100 ms) : un appui **maintenu** sur une touche membre
  attend d'autant plus avant d'être transmis. Un appui **court** ne
  ralentit pas pour autant — il part au relâchement, comme toujours.

50 ms est un compromis prudent. Si les combinaisons t'échappent souvent,
monte à 70 avant d'aller plus loin.

---

## 11.7 Trois ou quatre touches ensemble

La mécanique les accepte **déjà** : `Combos` déclenche une combinaison
seulement quand aucune plus grande ne peut encore se former, et
`COMBO((3, 4, 5), ...)` est une écriture valable.

Ce n'est pas activé dans les valeurs d'usine, pour une raison simple :
**trois touches à la fois sur six, c'est déjà de la contorsion**. Si tu
en veux, ajoute-les dans la page ou dans `COMBOS` — rien d'autre n'est à
changer.

---

## 11.8 Ce qui n'a pas été vérifié

* **Rien de tout cela n'a été testé sur ton ESP32 par moi** : je n'y ai
  pas accès. Les 216 tests tournent sur PC, avec le temps, les GPIO et le
  transport USB simulés. Ce qu'ils prouvent, c'est la logique — pas le
  ressenti sous le doigt.
* **`GESTE_COMBO_MS = 50` est un pari**, pas une mesure. C'est le premier
  chiffre à ajuster après quelques minutes d'usage réel.
* Les quatre commandes AutoLISP sont écrites et relues, mais **elles
  n'ont pas tourné dans un vrai Civil 3D**. Leurs limites connues sont
  listées dans [`civil3d/README.md`](../civil3d/README.md).
