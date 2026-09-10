# Les commandes Civil 3D du macropad

`macropad_tools.lsp` ajoute quatre commandes à Civil 3D. Le macropad se
contente d'écrire leur nom suivi d'Entrée — c'est AutoCAD qui fait le
reste.

| Commande | Ce qu'elle fait |
|---|---|
| `MPVIEWNEXT` | vue nommée **suivante**, en cycle |
| `MPVIEWPREV` | vue nommée **précédente**, en cycle |
| `MPLAYEROFF` | tu désignes un objet, son calque disparaît |
| `MPLAYERRESTORE` | réaffiche le **dernier** calque caché |

> **Pas de `_` devant ces noms.** Le souligne sert à demander la version
> *internationale* d'une commande AutoCAD native. Une commande LISP n'a
> pas de traduction : `MPVIEWNEXT` tout court, c'est ce que le macropad
> envoie.

---

## 1. Installation

**1. Range le fichier quelque part de stable.** Pas dans `Téléchargements`
— AutoCAD ira le chercher à chaque ouverture de dessin. Par exemple :

```
C:\Users\<toi>\Documents\Macropad\macropad_tools.lsp
```

**2. Autorise le dossier.** Depuis AutoCAD 2014, les LISP non signés
chargés depuis un dossier « non approuvé » déclenchent un avertissement à
chaque ouverture. Dans la ligne de commande :

```
TRUSTEDPATHS
```

Ajoute le chemin de ton dossier à la liste (séparés par des
point-virgules). **Ne mets pas `SECURELOAD` à 0** : ça désactiverait la
protection pour tous les fichiers, y compris ceux que tu n'as pas écrits.

**3. Charge-le à chaque démarrage.** Dans la ligne de commande :

```
APPLOAD
```

Dans la fenêtre, en bas à droite, la zone **« Suite de démarrage »**
(*Startup Suite*) — clique sur **Contenu…**, puis **Ajouter…**, et
choisis `macropad_tools.lsp`.

C'est le seul moyen fiable : le fichier sera rechargé à **chaque ouverture
de dessin**, y compris les dessins ouverts par double-clic.

**4. Vérifie.** Ferme et rouvre Civil 3D. Dans la ligne de commande, tu
dois voir au chargement :

```
macropad_tools.lsp charge : MPVIEWNEXT, MPVIEWPREV, MPLAYEROFF, MPLAYERRESTORE
```

Tape `MPVIEWNEXT` pour essayer.

---

## 2. Les vues nommées

Le cycle parcourt les vues nommées du dessin, **triées par ordre
alphabétique** — pas par ordre de création. C'est volontaire : tu sais
toujours dans quel ordre tu tournes, même après avoir ajouté une vue.

Sont écartées :

* les vues dont le nom commence par `*` — vues anonymes internes ;
* celles commençant par `A$C` — vues fabriquées automatiquement.

> **Si tu vois passer des vues parasites**, note leur préfixe et
> dis-le-moi : le filtre est une seule ligne dans `mp-vues`.

**Aucune vue nommée dans le dessin ?** La commande écrit
`Aucune vue nommee dans ce dessin.` et ne fait rien d'autre.

### Deux limites, dites franchement

**Les noms avec espaces.** `(command "_-VIEW" "_R" "Vue Nord Est")` envoie
la chaîne comme **une seule réponse**, elle devrait donc passer. Je n'ai
pas pu le vérifier sur une vraie installation : **teste-le tôt** avec une
vue dont le nom contient un espace, et dis-moi si ça coince.

**Si tu changes de vue à la molette**, AutoCAD ne garde nulle part
l'information « je suis dans la vue nommée X ». Le cycle reprend donc à
partir de la dernière vue **restaurée par la commande**, pas de ce que tu
regardes. C'est le mieux raisonnablement faisable.

---

## 3. Cacher et réafficher un calque

`MPLAYEROFF` te demande de **désigner un objet**, puis éteint son calque.

Le calque est éteint en modifiant **directement la table LAYER** du
dessin (code couleur négatif), et non en appelant la commande
`CALQUE` / `LAYER`. Deux avantages :

* aucun nom de commande localisé, donc rien à traduire ;
* **aucune question de confirmation** — notamment celle qui apparaît
  quand on éteint le calque courant et qui bloquerait la commande.

Les cas particuliers sont traités :

| Situation | Comportement |
|---|---|
| Échap, ou clic dans le vide | `Annule, aucun calque cache.` Rien n'est modifié |
| Calque déjà éteint | signalé, et **non empilé** — sinon la restauration rallumerait un calque que la commande n'a jamais éteint |
| Objet sur le calque `0` | aucun cas particulier, il s'éteint comme un autre |
| C'est ton **calque courant** | il s'éteint, avec un avertissement bien visible. Le refuser aurait été plus prudent, mais moins prévisible |

`MPLAYERRESTORE` réaffiche le dernier calque caché. **C'est une pile :**
calques A, B puis C cachés → les restaurations donnent C, puis B, puis A.

La pile vit le temps de la session AutoCAD. Un calque renommé ou purgé
entre-temps est signalé et sauté.

> **Si l'affichage ne se met pas à jour tout seul**, ouvre le `.lsp` et
> enlève le point-virgule devant la ligne `(command "_.REGEN")`, dans
> `MPLAYEROFF`. Elle est désactivée par défaut : un REGEN coûte cher sur
> un dessin chargé, et c'est justement sur ces dessins-là que tu vas t'en
> servir.

---

## 4. Ce que le macropad envoie

Une macro de type **texte + Entrée**, avec le nom nu :

```
MPVIEWNEXT
```

Ces commandes sont affectées à des **combinaisons de deux touches** —
voir `docs/11-combinaisons.md`.
