# 7. Le mode configuration : WiFi et page web

Depuis la V1, tu n'as plus besoin de Thonny pour changer tes macros. Le
macropad sait allumer son propre réseau WiFi et servir une page web.

Il y a **deux chemins vers la même page**, et tu choisis selon la
situation :

| | Par WiFi (ce chapitre) | Par USB ([chapitre 8](08-detection-auto.md)) |
|---|---|---|
| Il faut | rien à installer | Python + `pyserial` sur le PC |
| Démarrage | maintenir B2 + RESET | rien, le macropad tourne normalement |
| Adresse | `http://192.168.4.1` | `http://127.0.0.1:8765` |
| Application | après un RESET | **immédiate** |
| Pratique pour | un téléphone, un PC verrouillé | l'usage courant |

---

## 7.1 En trois minutes

1. **Maintiens B2** et appuie sur **RESET**. Relâche après 2 secondes.
2. L'écran affiche :

```
┌────────────────────────┐
│▓MODE CONFIG▓▓▓▓▓▓WIFI▓▓│
│ Reseau :               │
│ MACROPAD               │
│ Cle :                  │
│ macropad2026           │
│────────────────────────│
│ 192.168.4.1            │
└────────────────────────┘
```

3. Sur ton PC ou ton téléphone, connecte-toi au réseau WiFi **MACROPAD**
   avec la clé affichée.
4. Ouvre **http://192.168.4.1** dans un navigateur.
5. Modifie ce que tu veux, clique sur **Enregistrer**.
6. Fais un **RESET normal** : le macropad redémarre avec tes macros.

---

## 7.2 Pourquoi ce n'est pas du WiFi permanent

C'est un choix de sécurité, pas une limitation technique.

Ce boîtier **tape dans ton ordinateur**. Si sa radio était allumée en
permanence, quelqu'un à portée pourrait y déposer des commandes qui
s'exécuteraient ensuite chez toi, sans que tu voies rien. Une clé USB
malveillante, mais à distance.

Trois barrières :

1. **La radio ne s'allume que si tu maintiens un bouton au démarrage.**
   Il faut un accès physique au boîtier.
2. **Dans ce mode, `boot.py` ne crée aucun clavier USB.** Le macropad est
   *physiquement* incapable de taper. Même une configuration malveillante
   ne pourrait rien faire tant que tu n'as pas redémarré.
3. **Le réseau est protégé par une clé WPA2**, affichée sur l'écran : il
   faut voir l'appareil pour la lire.

> **À faire :** change `AP_PASSWORD` dans `config.py`. La valeur livrée est
> un exemple, et elle est publique puisqu'elle est dans ce dépôt.

Effet de bord appréciable : le WiFi et l'USB HID ne cohabitent jamais dans
les 224 Ko de RAM de la carte.

---

## 7.3 Ce que la page sait faire

| | |
|---|---|
| Renommer un profil | ✅ nom interne et titre affiché |
| Ajouter / supprimer un profil | ✅ |
| Changer les macros des 6 touches | ✅ libellé, type, valeur |
| **Trois gestes par touche** | ✅ appui court, appui long, double appui |
| **Couleur des LED du profil** | ✅ carré de couleur à côté du titre |
| **Table des logiciels détectés** | ✅ programme, profil, abrégé écran |
| **Compteur d'usage** | ✅ affiché en bout de ligne, avec sa barre |
| **Capturer un raccourci au clavier** | ✅ bouton ⌨ : tu appuies, la page écrit le nom |
| Télécharger une sauvegarde | ✅ fichier JSON |
| **Restaurer une sauvegarde** | ✅ elle est chargée dans le formulaire, tu vérifies, tu enregistres |
| Revenir aux valeurs d'usine | ✅ bouton dédié |
| **Enchaîner plusieurs étapes** | ✅ bouton « + étape », avec des pauses |

### Les trois gestes

Chaque touche occupe trois lignes dans la page, une par geste :

| Geste | Comment | Par défaut |
|---|---|---|
| **court** | appuie et relâche | c'est la macro principale |
| **long** | garde appuyé ≥ 400 ms | vide |
| **double** | deux appuis en moins de 200 ms | vide |

Les deux durées se règlent dans `config.py` (`GESTE_LONG_MS`,
`GESTE_DOUBLE_MS`). Une touche qui n'a **pas** de macro « double » part
dès le relâchement : tu ne paies l'attente que là où tu t'en sers.
Voir le [chapitre 9](09-ecran-et-gestes.md) pour le détail.

### L'enregistreur de séquence

À côté de **`+ etape`**, un bouton **`⏺ Enregistrer`**. Tu cliques, tu
tapes ta séquence **au clavier**, et la page en fait des étapes. Bien plus
rapide que de choisir un type et une valeur pour chaque frappe — et
surtout, ça capture les **pauses réelles**, celles qu'on ne pense jamais à
mesurer soi-même.

Trois règles, et elles couvrent presque tout :

| Ce que tu tapes | Ce que ça produit |
|---|---|
| des caractères ordinaires | **une seule** étape `texte` — `_PLINE` fait une étape, pas six |
| Entrée juste après du texte | l'étape devient **`texte + Entrée`**, l'idiome des commandes AutoCAD |
| Ctrl+S, F5, Suppr… | une étape `combinaison` ou `touche` à part |
| une attente de plus de 0,4 s | une étape **`pause`**, arrondie à 50 ms près |

**Échap** termine l'enregistrement (il n'est pas enregistré lui-même), et
le bouton repasse sur **`■ Stop`** pendant la prise. L'enregistrement
**remplace** les étapes du geste : tu vois le résultat se construire au
fur et à mesure, et **rien n'est envoyé au macropad** tant que tu n'as pas
cliqué sur *Enregistrer*.

> **Limite du navigateur :** quelques raccourcis sont réservés par Windows
> ou par le navigateur et ne peuvent pas être interceptés — `Ctrl+W`,
> `F11`, la touche Windows seule. Ajoute-les à la main avec le bouton ⌨.

Le même bouton existe sur les **combinaisons** : elles rangent leurs
étapes de la même façon.

### Les combinaisons

Sous le tableau de chaque profil, un second tableau plus court :
**deux touches appuyées en même temps**, leur libellé, et leur macro —
avec exactement le même éditeur d'étapes.

| Colonne | Ce qu'on y met |
|---|---|
| **Touches** | les numéros gravés sur le pad : `3+4`, ou `3 4`, ou même `3 et 4` |
| **Libellé** | ce que l'écran affichera, 16 caractères au plus |
| **Action** | même chose que pour un geste, suites d'étapes comprises |

Deux règles y sont vérifiées à l'enregistrement : il faut **au moins deux
touches**, et un `maintien` y est **refusé** — il n'aurait aucune touche
unique à surveiller pour se relâcher, et Ctrl resterait enfoncé.
Le [chapitre 11](11-combinaisons.md) détaille le reste.

### Les cinq types de macro

| Type | Valeur à saisir | Effet |
|---|---|---|
| touche | `TAB`, `F5`, `G` | une seule touche |
| combinaison | `CTRL+Z`, `CTRL+SHIFT+ESC` | plusieurs touches ensemble |
| **maintenir** | `CTRL`, `SHIFT`, `CTRL+ALT` | **garde la touche enfoncée** tant que ton doigt reste dessus |
| **pause** | `500` | attend ce nombre de millisecondes avant l'étape suivante |
| texte | `_HATCH` | écrit la chaîne |
| texte + Entrée | `_MATCHPROP` | écrit la chaîne puis valide |
| inactive | — | ce geste ne fait rien |

**« maintenir » transforme la touche en vraie touche modificatrice.** Mets
`CTRL` sur l'appui court et `MAJ` sur le double appui : tu obtiens
*appui maintenu = Ctrl*, *appui bref puis maintenu = Maj*, et tu peux
cliquer à la souris pendant ce temps. C'est le seul type qui ne « tape »
rien. Détail dans [`docs/09`](09-ecran-et-gestes.md).

**Le libellé fait 6 caractères au maximum** : c'est ce que laisse la
largeur de l'écran une fois les trois colonnes de gestes posées.

### Ne plus deviner les noms de touches

`SUPPR` ou `DELETE` ? `PAGEDOWN` ou `PGDN` ? Tu n'as plus à savoir : à côté
de chaque champ de valeur, pour les types *touche*, *combinaison* et
*maintenir*, un petit bouton **⌨**. Tu cliques dessus, tu **appuies sur la
combinaison** sur ton vrai clavier, et la page écrit `CTRL+SHIFT+P` toute
seule.

Deux détails qui comptent :

* la page lit la touche **physique**, pas le caractère produit. Le
  résultat ne dépend donc pas de la disposition de ton clavier —
  exactement comme le firmware, qui raisonne lui aussi en touches
  physiques ;
* **AltGr** se présente comme Ctrl+Alt sous Windows. La page le reconnaît
  et écrit `ALTGR`, pas `CTRL+ALT`.

Un modificateur seul fonctionne aussi : appuie juste sur Ctrl et tu
obtiens `CTRL` — c'est ce qu'il faut pour le type *maintenir*.

### Sauvegarder, et surtout restaurer

**« Télécharger la sauvegarde »** te donne un fichier JSON avec tout :
profils, macros, gestes, couleurs, logiciels détectés.

**« Restaurer une sauvegarde »** le recharge. Il est mis dans le
formulaire **sans être appliqué** : tu vois ce que tu restaures, et rien
ne part vers le macropad tant que tu n'as pas cliqué sur **Enregistrer**.
Un fichier illisible ou qui n'est pas une sauvegarde du macropad est
refusé avec un message, sans rien casser.

> Garde une sauvegarde dès que ta configuration te convient. C'est ta
> seule copie en dehors de la carte.

### Enchaîner plusieurs étapes sur un seul appui

Un geste n'est pas limité à une frappe. Le bouton **« + étape »** ajoute
une ligne, et les étapes partent dans l'ordre :

```
B6 · appui court   [texte + Entrée ▾]  [_PURGE]      [×]
                   [pause          ▾]  [500]         [×]
                   [combinaison    ▾]  [CTRL+S]      [×]
                   + étape
```

La **pause** est là pour les logiciels qui ont besoin de respirer : une
commande ouvre une boîte de dialogue, et le `Ctrl+S` envoyé trop tôt
partirait dans le vide.

> **Une pause ne fige rien.** Pendant qu'elle s'écoule, le macropad
> continue de lire tes touches, d'animer les LED et de rafraîchir
> l'écran — et **ESC interrompt la macro en pleine pause**. C'est la
> règle de tout le firmware : rien n'attend jamais.

Le maximum est de **5 secondes** par pause (`PAUSE_MAX_MS`) : au-delà,
l'enregistrement est refusé. Une macro qui attendrait trente secondes
donnerait l'impression que le macropad est bloqué, alors qu'il tourne
parfaitement.

### Les logiciels détectés

La section du bas est la table que lit le compagnon PC :

| Programme (.exe) | Profil | Abrégé écran |
|---|---|---|
| `acad.exe` | CIVIL3D | `C3D` |
| `blender.exe` | BLENDER | `Blender` |
| *tout le reste* | WINDOWS | `Win` |

L'abrégé, **7 caractères au maximum**, est le texte fixe en bas à gauche
de l'écran pendant que le nom du fichier défile. Détails au
[chapitre 8](08-detection-auto.md).

### Le compteur d'usage

À droite de chaque touche, le nombre d'appuis depuis la mise en service,
avec une petite barre pour comparer d'un coup d'œil. C'est ce qui te dira,
au moment de dessiner le boîtier, quelles touches méritent la meilleure
place — et lesquelles ne servent jamais.

Le compteur est rangé dans `stats.json`, écrit **tous les 25 appuis** pour
ménager la mémoire flash (elle supporte un nombre fini d'écritures).

---

## 7.4 Rien ne peut être enregistré au hasard

Avant l'écriture, **chaque macro est réellement traduite en codes clavier**
avec ta disposition (`KEYBOARD_LAYOUT`). Si un nom de touche est inconnu ou
si un caractère est impossible à taper en AZERTY, l'enregistrement est
refusé et la page t'affiche pourquoi :

```
Refuse :
WORD B1 (KO) : Touche inconnue dans la macro : 'TOUCHE_BIDON'
```

Il est donc impossible d'enregistrer une configuration qui planterait au
démarrage suivant.

Et si le fichier était malgré tout corrompu — coupure de courant, carte
retirée en pleine écriture — le firmware le détecte au démarrage, le
signale dans le REPL et **repart sur les profils d'usine**. Une carte ne
peut pas devenir inutilisable à cause de ce fichier.

L'écriture se fait d'ailleurs dans un fichier temporaire, renommé ensuite :
une coupure ne peut pas laisser un `profils.json` à moitié écrit.

---

## 7.5 Où sont rangées tes macros

Dans **`profils.json`**, à la racine de la carte. C'est du texte, tu peux
l'ouvrir dans Thonny pour voir ce qu'il contient :

```json
{
  "version": 2,
  "ordre": ["BLENDER", "CIVIL3D", "WORD", "WINDOWS"],
  "profils": {
    "CIVIL3D": {
      "titre": "CIVIL 3D",
      "touches": [
        {"label": "MATCH",
         "court":  {"type": "text_enter", "valeur": "_MATCHPROP"},
         "long":   {"type": "none", "valeur": ""},
         "double": {"type": "text_enter", "valeur": "_PROPERTIES"}},
        ...
      ]
    }
  },
  "apps": {
    "repli": {"profil": "WINDOWS", "abrege": "Win"},
    "liste": [{"exe": "acad.exe", "profil": "CIVIL3D", "abrege": "C3D"}]
  }
}
```

> **Version 2** : un fichier de version 1 (une seule macro par touche) est
> relu sans problème — l'ancienne macro devient l'appui court. Le compteur
> d'usage, lui, vit à part dans `stats.json` : effacer tes profils ne remet
> pas les compteurs à zéro, et inversement.

**Supprimer ce fichier revient aux profils d'usine** de `profiles.py`.
C'est aussi ce que fait le bouton « Profils d'usine » de la page web.

Pense à en garder une copie sur ton PC quand ta configuration te convient :
c'est ta sauvegarde.

---

## 7.6 Si ça ne marche pas

| Symptôme | Cause probable |
|---|---|
| Aucun réseau `MACROPAD` visible | `AP_PASSWORD` fait moins de 8 caractères — le WiFi refuse alors de démarrer |
| Le réseau apparaît mais la page ne s'ouvre pas | vérifie l'adresse : `http://192.168.4.1`, pas `https` |
| Windows dit « pas d'accès Internet » | normal : ce réseau ne sert qu'à configurer le macropad, il n'est relié à rien |
| L'écran n'affiche pas MODE CONFIG | B2 n'était pas maintenu assez tôt — maintiens-le **avant** d'appuyer sur RESET |
| Les modifications ne s'appliquent pas | il faut un **RESET** après l'enregistrement |

Le REPL du port UART reste disponible pendant tout le mode configuration :
il affiche l'adresse, les connexions et le détail de chaque enregistrement.
