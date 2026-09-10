# 9. L'écran tableau et les trois gestes

Avec six touches et trois gestes par touche, le macropad connaît **dix-huit
commandes par profil**. Personne ne retient ça de tête. L'écran est donc
devenu un tableau : il montre en permanence ce que fait chaque touche.

---

## 9.1 Ce que tu vois

```
┌────────────────┐
│▓CIVIL 3D▓▓▓AUTO│  ← bandeau inversé : profil actif + état
│ CRT   LNG DBL  │  ← en-tête : court / long / double
│1MATCH -   PROP │
│2HATCH -   ANGL │  ← quatre lignes visibles à la fois
│3ANNUL REDO -   │
│4ISOLE -   -    │
│────────────────│
│C3D A12_Phase2.d│  ← abrégé du logiciel + nom du fichier
└────────────────┘
```

| Zone | Contenu |
|---|---|
| **Bandeau** | le titre du profil, et à droite `AUTO`, `HID`, `LOCK`, `ERR`, `OFF` ou `...` |
| **En-tête** | `CRT` = appui court, `LNG` = appui long, `DBL` = double appui |
| **Colonne 1** | le **libellé** de la touche (ce que tu as écrit dans la page de configuration) |
| **Colonnes 2 et 3** | un résumé de la macro, ou `-` si le geste est libre |
| **Ligne du bas** | le logiciel abrégé + le nom du fichier (voir [chapitre 8](08-detection-auto.md)) |

Les largeurs sont imposées par les 128 pixels de la dalle et la police
8×8 : **6 caractères pour le libellé** (autant que la page de
configuration en accepte, donc rien n'est perdu) et **4 pour chacun des
deux résumés**. Le résumé prend :

* le nom de la touche pour une macro « touche » (`F5` → `F5`) ;
* la **dernière** touche d'une combinaison (`CTRL+SHIFT+Z` → `Z`) ;
* le modificateur d'un maintien (`CTRL` → `CTRL`, `MAJ` → `MAJ`) ;
* le texte sans son underscore de tête (`_MATCHPROP` → `MATC`).

> **Pourquoi la colonne `CRT` montre le libellé et pas la macro ?** Parce
> que le libellé, c'est toi qui l'as écrit, et il désigne précisément
> l'appui court : `MATCH` se lit mieux que `MATC` (le résumé qu'on tirerait
> de `_MATCHPROP`). Les deux autres colonnes n'ont pas de libellé à elles,
> on y résume donc la macro.

---

## 9.2 Les trois gestes

| Geste | Comment | Réglage |
|---|---|---|
| **court** | appuie et relâche normalement | — |
| **long** | garde appuyé **≥ 400 ms** | `GESTE_LONG_MS` |
| **double** | deux appuis en **moins de 260 ms** | `GESTE_DOUBLE_MS` |

L'appui long **part tout seul dès le seuil atteint**, sans attendre que tu
relâches : tu sens la commande arriver sous le doigt, et l'écran surligne
la ligne au même instant. Relâcher ensuite ne déclenche rien de plus.

### Le point important : aucune latence là où tu n'en veux pas

Un macropad qui attend 260 ms à chaque appui « pour voir si un deuxième
arrive » serait insupportable. Ici, **c'est décidé touche par touche** :

* la touche n'a **pas** de macro « double » → l'appui court part **au
  relâchement**, immédiatement, comme avant ;
* la touche **a** une macro « double » → et seulement dans ce cas, le
  firmware attend 260 ms avant de conclure « c'était un court ».

Autrement dit, tu ne paies l'attente que sur les touches où tu as demandé
le double appui. Laisse la colonne `DBL` vide sur tes touches les plus
utilisées et elles restent parfaitement sèches.

> Le tableau des gestes est reconstruit à chaque changement de profil :
> une même touche peut donc être instantanée dans WORD et à double appui
> dans CIVIL3D.

### Où c'est écrit dans le code

`device/gestures.py`. C'est une petite **machine à états** : chaque touche
est dans l'un de quatre états — au repos, enfoncée, en attente d'un
éventuel second appui, ou « long déjà envoyé ». Rien n'y bloque : la
fonction `service(now)` est appelée à chaque tour de boucle et se contente
de comparer des dates.

---

## 9.2 bis Une touche qui fait Ctrl et Maj

C'est un quatrième comportement, à part des trois gestes : une touche qui
**ne tape rien**, mais qui enfonce un modificateur et le **garde enfoncé**
tant que ton doigt reste dessus — exactement comme la touche Ctrl d'un
vrai clavier.

| Ce que tu fais | Ce que le PC reçoit |
|---|---|
| tu appuies et tu **maintiens** | **Ctrl** enfoncé, relâché quand tu lâches |
| tu appuies **brièvement**, puis tu **maintiens** | **Maj** enfoncé, relâché quand tu lâches |

C'est B2 dans le profil CIVIL 3D. L'usage visé : ta main gauche tient le
modificateur pendant que ta main droite reste à la souris —
**Ctrl+clic** pour ajouter à la sélection, **Maj+clic** pour en retirer.

### Comment on la configure

Dans la page de configuration, type **« maintenir (Ctrl, Maj...) »** :

| Geste | Type | Valeur |
|---|---|---|
| appui court | maintenir | `CTRL` |
| double appui | maintenir | `MAJ` |

Tu peux évidemment mettre autre chose : `ALTGR`, `CTRL+ALT`, ou même une
touche ordinaire à maintenir.

### Deux choix assumés

**Le modificateur descend dès l'appui, sans le moindre délai.** Attendre
260 ms pour voir si un second appui arrive rendrait la touche
inutilisable : un modificateur qui traîne, c'est un clic raté.

**Conséquence : le premier appui bref de la séquence « bref puis
maintenu » envoie un Ctrl seul, très court.** Un Ctrl seul n'a aucun effet
dans Windows, Civil 3D, Blender ou Word. Mais **évite `ALT` sur le premier
appui** : un Alt seul ouvre la barre de menus.

### Ce qui ne peut pas arriver

Un modificateur resté coincé côté PC est la pire panne possible — tout
devient un raccourci. Trois filets, chacun couvert par un test :

| Événement | Effet |
|---|---|
| tu relâches la touche | le modificateur remonte |
| **ESC** | tout est relâché, y compris un maintien |
| changement de profil | idem |
| câble débranché | le maintien est oublié |
| `Ctrl-C` dans Thonny | `close()` relâche avant de rendre la main |

---

## 9.3 Le tableau défile tout seul

Six touches, quatre lignes visibles : le tableau **glisse d'un cran toutes
les 2,5 secondes** (`TABLE_SCROLL_MS`), puis revient au début. Tu finis par
tout voir sans rien toucher.

Quand un profil tient sur quatre lignes ou moins, il n'y a évidemment rien
à faire défiler : l'écran reste fixe.

---

## 9.4 Le saut instantané sur la touche utilisée

C'est le comportement le plus utile au quotidien : **dès que tu appuies,
l'écran saute sur la ligne de cette touche et la met en surbrillance**
(fond blanc, texte noir) pendant 1,3 seconde (`HIGHLIGHT_MS`).

Trois choses arrivent en même temps :

1. si la touche n'était pas dans les quatre lignes visibles, la fenêtre se
   déplace juste ce qu'il faut pour l'amener à l'écran ;
2. la ligne s'inverse : tu vois immédiatement **ce que tu viens de
   déclencher**, et du même coup les deux autres gestes disponibles ;
3. le défilement automatique est mis en pause pendant le surlignage, sinon
   la ligne partirait sous tes yeux.

Le surlignage a lieu **même si le geste n'a aucune macro** : c'est ainsi
que tu découvres qu'une touche est libre, au lieu de croire à une panne.

---

## 9.5 Le nom du fichier qui défile

La ligne du bas reçoit `abrégé|nom du fichier` du compagnon PC. L'abrégé
(`C3D`, `Wrd`, `Blender`…) reste **fixe à gauche**, le nom du fichier
**défile** dans la place restante :

* 70 ms par pixel (`DOC_SCROLL_MS`) — c'est lent, donc lisible ;
* 1,6 s de pause à chaque bout (`DOC_SCROLL_PAUSE_MS`), le temps de lire le
  début puis la fin ;
* aller-retour, pas de retour brutal au début.

Si le nom tient entièrement, il ne bouge pas.

---

## 9.6 L'anti-marquage d'écran

Un OLED **s'use là où il éclaire**. Une image fixe pendant des mois laisse
une trace permanente — le bandeau du profil serait le premier à marquer.

Deux étapes, remises à zéro dès que tu touches une touche :

| Après | Ce qui se passe | Réglage |
|---|---|---|
| **3 minutes** sans appui | contraste au minimum, l'écran reste lisible dans une pièce sombre | `SCREEN_DIM_MS` |
| **15 minutes** sans appui | écran **éteint** par la commande sommeil du SH1106 | `SCREEN_OFF_MS` |

Le réveil est immédiat au premier appui : c'est la même touche qui réveille
l'écran **et** exécute sa macro, tu ne perds jamais un appui à rallumer.

Écran éteint, le firmware **n'envoie plus rien du tout en I2C** : la boucle
tourne encore plus au large, et le bus se tait.

---

## 9.7 Le compteur d'usage

Chaque appui est compté par profil et par touche (`device/stats.py`). Tu
lis les totaux dans la page de configuration, avec une barre pour comparer.

Deux précautions :

* **écriture tous les 25 appuis seulement** (`STATS_SAVE_EVERY`) : la
  mémoire flash supporte un nombre fini d'écritures, il serait absurde de
  l'user pour un compteur ;
* écriture **atomique** (fichier temporaire puis renommage) : une coupure
  de courant ne peut pas laisser un `stats.json` à moitié écrit.

Le total est aussi enregistré proprement à l'arrêt du programme.

À quoi ça sert vraiment : quand tu dessineras le boîtier, ces chiffres te
diront quelles touches méritent la meilleure place sous les doigts — et
lesquelles ne servent jamais.

---

## 9.8 Tous les réglages, au même endroit

Dans `config.py` :

```python
GESTE_LONG_MS = 400          # seuil de l'appui long
GESTE_DOUBLE_MS = 260        # fenêtre du double appui
TABLE_SCROLL_MS = 2500       # défilement du tableau
HIGHLIGHT_MS = 1300          # durée du surlignage
DOC_SCROLL_MS = 70           # ms par pixel du nom de fichier
DOC_SCROLL_PAUSE_MS = 1600   # pause en bout de course
SCREEN_DIM_MS = 180000       # 3 min  -> contraste minimal
SCREEN_OFF_MS = 900000       # 15 min -> écran éteint
```

Quelques repères si tu veux ajuster :

| Tu trouves que… | Change |
|---|---|
| l'appui long part trop vite | `GESTE_LONG_MS` à 500 ou 600 |
| le double appui est dur à réussir | `GESTE_DOUBLE_MS` à 350 |
| le tableau défile trop vite | `TABLE_SCROLL_MS` à 4000 |
| la surbrillance s'efface trop tôt | `HIGHLIGHT_MS` à 2000 |
| l'écran s'éteint trop tôt | `SCREEN_OFF_MS` à `1800000` (30 min) |

Mettre `SCREEN_DIM_MS` et `SCREEN_OFF_MS` très grands désactive
l'économiseur — au prix du marquage, à toi de voir.

---

## 9.9 Pourquoi tout cela ne ralentit jamais les touches

C'est la règle qui tient tout le firmware : **rien n'attend**.

L'écran fait 1024 octets. Les envoyer d'un coup en I2C prend environ 25 ms,
pendant lesquelles aucune touche ne serait lue — un appui rapide pourrait
passer à la trappe. Le firmware envoie donc **une bande de 128 octets par
tour de boucle**, soit 3 ms, huit tours pour une image complète. À 2 ms par
tour, l'image se rafraîchit en ~40 ms : invisible à l'œil, et les touches
restent lues en permanence.

Mieux : le défilement du nom de fichier ne redessine **que la dernière
bande** (`_rafraichir_bas`), celle qui change. Huit fois moins de trafic
sur le bus pour la même animation.

Toutes les animations sont pilotées par comparaison de dates dans
`display.tick(now)`. Aucun `sleep`, nulle part.

---

## 9.10 Si ça ne marche pas

| Symptôme | Cause probable |
|---|---|
| L'appui court tarde un peu | cette touche a une macro « double » : c'est l'attente prévue. Vide la colonne `DBL` si tu préfères l'instantané |
| Le double appui n'est jamais reconnu | tu appuies trop lentement : augmente `GESTE_DOUBLE_MS` |
| L'appui long part alors que je voulais un court | tu restes appuyé plus de 400 ms : augmente `GESTE_LONG_MS` |
| Le tableau ne défile pas | le profil tient sur quatre lignes : normal |
| L'écran est très pâle | économiseur : plus de 3 minutes sans appui. Appuie sur une touche |
| L'écran est noir | plus de 15 minutes sans appui. Un appui le rallume |
| La colonne du milieu affiche `-` partout | aucune macro longue définie dans ce profil |
| Un résumé de macro est tronqué | 4 caractères par colonne de geste, c'est la largeur de l'écran. Le libellé, lui, en a 6 |
