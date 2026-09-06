# 8. Détection automatique du logiciel, et configuration depuis le PC

Un petit programme tourne sur ton PC et parle au macropad par le **port
série**, celui qui existe déjà à côté du clavier HID sur le même câble.

Il fait deux choses :

1. il regarde quelle application est au premier plan et **change le profil
   tout seul** ;
2. il sert une **page de configuration** sur `http://127.0.0.1:8765`, où tu
   modifies tes macros — appliquées **immédiatement, sans redémarrer**.

```
        PC                                      Macropad
┌──────────────────────┐                    ┌──────────────┐
│ macropad_auto.py     │   port série USB   │              │
│  • fenêtre active    │ ─────────────────► │ P:CIVIL3D    │
│  • nom du document   │ ─────────────────► │ T:C3D|Pro... │
│  • page de config    │ ◄────────────────► │ ?CFG / !CFG  │
└──────────────────────┘                    └──────────────┘
```

---

## 8.1 Installation

```bat
py -m pip install pyserial
```

C'est la seule dépendance. Tout le reste utilise la bibliothèque standard
de Python : l'accès à l'API Windows passe par `ctypes`, sans `pywin32`.

Puis, dans le dossier `pc/` :

```bat
py macropad_auto.py
```

Ou double-clique sur **`macropad_auto.bat`**.

Pour vérifier que la détection fonctionne **sans avoir le macropad
branché** :

```bat
py macropad_auto.py --simuler
```

Change de fenêtre et regarde la console : elle affiche ce qu'elle enverrait.

---

## 8.2 Quel port série ?

La carte expose **deux** ports COM :

| Port | Pour |
|---|---|
| pont USB-série (CH343, CP210x…) | **Thonny** |
| USB natif de l'ESP32-S3 | **ce script** |

Le script reconnaît le second à son identifiant fabricant Espressif
(VID `0x303A`) et le choisit seul. Pour forcer :

```bat
py macropad_auto.py --port COM7
```

> ⚠️ **Un port série ne s'ouvre qu'une fois.** Si Thonny est connecté au
> port **natif**, le script ne pourra pas l'ouvrir. Garde Thonny sur le
> port UART — c'est exactement à ça qu'il sert.

---

## 8.3 Choisir quels logiciels déclenchent quel profil

**La table des logiciels vit dans le macropad**, pas sur le PC. Elle se
modifie dans la page de configuration, section « Logiciels détectés »,
bouton **« + Logiciel »** :

| Programme (.exe) | Profil | Abrégé écran |
|---|---|---|
| `acad.exe` | CIVIL3D | `C3D` |
| `acadlt.exe` | CIVIL3D | `C3D` |
| `blender.exe` | BLENDER | `Blender` |
| `winword.exe` | WORD | `Wrd` |
| *tout le reste* | WINDOWS | `Win` |

Trois raisons de la mettre là plutôt que dans un fichier du PC :

* elle **suit la carte** — branche le macropad sur un autre poste, la
  détection fonctionne pareil ;
* le **portail WiFi** peut la modifier lui aussi, depuis un téléphone ;
* l'**abrégé** sert à l'écran de la carte, c'est donc sa donnée à lui.

L'**abrégé** est le petit texte fixe en bas à gauche de l'écran, celui qui
reste lisible pendant que le nom du fichier défile à côté. **Sept
caractères au maximum** : c'est la place disponible. Laisse-le vide et le
nom du profil est repris, coupé à sept.

Pour connaître le nom exact d'un exécutable : Gestionnaire des tâches →
onglet **Détails**, colonne **Nom**.

### Le fichier de secours

Au premier lancement, le script crée quand même **`macropad_apps.txt`** à
côté de lui. Il ne sert que de **secours** : il n'est consulté que si la
carte ne répond pas, avec `--simuler`, ou tant que la table de la carte est
vide.

```
acad.exe = CIVIL3D = C3D
blender.exe = BLENDER = Blender
winword.exe = WORD = Wrd

# Profil utilisé pour tout le reste :
* = WINDOWS = Win
```

Le troisième champ est facultatif. Le fichier est **relu à chaud** : ajoute
`qgis-bin.exe = QGIS = Qgis`, enregistre, c'est actif dans la seconde.

> **Les deux sources ne se mélangent jamais.** Si la carte annonce au
> moins un logiciel, c'est elle qui décide et le fichier est ignoré ; sinon
> c'est le fichier. La console te dit laquelle sert au démarrage. Comme ça,
> quand une détection ne fait pas ce que tu attends, tu sais où regarder.

Le script redemande la table à la carte **toutes les 30 secondes** et
immédiatement après chaque enregistrement : une modification faite depuis
le portail WiFi est donc prise en compte sans rien relancer. Si la carte se
tait, il espace les tentatives et garde la dernière table connue.

---

## 8.4 Le verrouillage de profil

La détection automatique est une **suggestion**, pas une contrainte. Tu es
dans Civil 3D mais tu veux les macros Windows ? **Touche les deux TTP223 en
même temps.**

L'écran affiche `LOCK` en haut à droite, et le PC ne peut plus changer de
profil. Refais le geste pour déverrouiller.

Les indicateurs du bandeau, par ordre de priorité :

| Affiché | Signification |
|---|---|
| `LOCK` | tu as verrouillé le profil, l'auto est ignorée |
| `ERR` | panne HID, un RESET est nécessaire |
| `...` | Windows n'a pas encore ouvert le clavier |
| `AUTO` | le PC pilote les profils, tout va bien |
| `HID` | clavier prêt, mais aucun script PC connecté |
| `OFF` | `HID_ENABLED = False` |

---

## 8.5 Le nom du document sur l'écran

Le script envoie aussi le titre de la fenêtre, nettoyé, précédé de
l'abrégé du logiciel :

```
T:C3D|Projet_A12_Phase2_Voirie.dwg
  ▲   ▲
  │   └── nom du fichier : il DÉFILE doucement s'il est trop long
  └────── abrégé : il reste FIXE, toujours lisible
```

```
┌────────────────┐
│▓CIVIL 3D▓▓▓AUTO│  bandeau : profil + etat
│ CRT   LNG DBL  │  les trois gestes
│1MATCH -   PROP │
│2HATCH -   ANGL │
│3ANNUL REDO -   │
│4ISOLE -   -    │  4 lignes visibles sur 6
│────────────────│
│C3D A12_Phase2.d│  abrege fixe + nom qui defile
└────────────────┘
```

Le nettoyage du titre gère les trois formes courantes sous Windows :

| Titre de la fenêtre | Ce qui est envoyé |
|---|---|
| `Projet_A12.dwg - Autodesk Civil 3D 2024` | `Projet_A12.dwg` |
| `Blender* [C:\Travail\maquette.blend]` | `maquette.blend` |
| `*Sans titre 1 - Bloc-notes` | `Sans titre 1` |

C'est-à-dire : d'abord ce qui est entre crochets (Blender, AutoCAD
classique), sinon ce qui précède le tiret ; puis, s'il reste un chemin
complet, seulement le nom du fichier ; enfin l'astérisque du « document
modifié » est retiré. On coupe à 48 caractères — ce que l'écran retient
pour le défilement, inutile d'envoyer plus.

Quand aucun document n'est signalé, la ligne du bas reprend son rôle
habituel : le carrousel de position dans la liste des profils.

---

## 8.6 Configurer par USB plutôt que par WiFi

Ouvre **http://127.0.0.1:8765**. C'est la même page que le mode WiFi, avec
trois différences :

* pas besoin de redémarrer en mode configuration ;
* pas de WiFi à allumer ;
* **les changements s'appliquent instantanément** — enregistre, et l'écran
  du macropad se met à jour dans la seconde.

Un bouton **« Télécharger la sauvegarde »** récupère ta configuration en
fichier JSON. Garde-la : c'est ta seule copie hors de la carte.

> Le mode WiFi reste utile quand tu ne peux pas installer Python sur le PC,
> ou pour configurer depuis un téléphone.

---

## 8.7 Le protocole, si tu veux bricoler

Une commande par ligne, texte pur. Tu peux tout faire à la main depuis
n'importe quel terminal série.

**Du PC vers le macropad :**

| Commande | Effet |
|---|---|
| `P:CIVIL3D` | active ce profil (sauf si verrouillé) |
| `T:C3D\|Projet.dwg` | abrégé + nom du document (`T:` seul efface la ligne) |
| `?VER` | état du macropad |
| `?CFG` | demande la configuration complète |
| `!CFGBEGIN` / `!C:…` / `!CFGEND` | envoi d'une configuration, en morceaux |
| `!RELOAD` | relire `profils.json` sans redémarrer |

**Du macropad vers le PC**, toujours préfixé par `#` pour se distinguer des
messages de débogage : `#VER:`, `#CFGBEGIN`, `#C:`, `#CFGEND`, `#OK:`, `#KO:`.

Deux garde-fous côté carte :

* la lecture est **bornée à 256 caractères par tour de boucle**, pour qu'un
  envoi de 3 ko n'immobilise pas les touches ;
* **aucune configuration n'est enregistrée sans avoir été traduite en codes
  clavier au préalable.** Une macro intapable est refusée avec son motif,
  et rien n'est écrit.

Aucun caractère de contrôle n'est utilisé : **Ctrl-C continue d'interrompre
le firmware normalement**, tu ne perds pas cette porte de sortie.

---

## 8.8 Si ça ne marche pas

| Symptôme | Cause probable |
|---|---|
| `Aucun port Espressif trouve` | le port **natif** n'est pas branché, ou Thonny le tient |
| `could not open port` | Thonny est connecté au port natif — bascule-le sur le port UART |
| Le profil ne change pas | vérifie le nom de l'exécutable dans la table (Gestionnaire des tâches → Détails), et regarde quelle source la console annonce au démarrage |
| Un logiciel ajouté dans `macropad_apps.txt` est ignoré | la carte a une table non vide : c'est elle qui décide. Ajoute le logiciel dans la page de configuration |
| L'abrégé est tronqué | c'est normal au-delà de 7 caractères : c'est la place disponible sur l'écran |
| L'écran affiche `LOCK` | tu as verrouillé le profil : touche les deux TTP223 ensemble |
| La page ne s'ouvre pas | le script n'est pas lancé, ou le port 8765 est déjà pris |
| `le macropad n'a pas repondu` | `LINK_ENABLED = False` dans `config.py`, ou `main.py` ne tourne pas |
