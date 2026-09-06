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
│  • nom du document   │ ─────────────────► │ T:Projet.dwg │
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

Au premier lancement, le script crée **`macropad_apps.txt`** à côté de lui :

```
acad.exe = CIVIL3D
acadlt.exe = CIVIL3D
blender.exe = BLENDER
winword.exe = WORD

# Profil utilisé pour tout le reste :
* = WINDOWS
```

Une ligne par logiciel. Le fichier est **relu à chaud** : ajoute
`qgis-bin.exe = QGIS`, enregistre, c'est actif dans la seconde — pas besoin
de relancer quoi que ce soit.

Pour connaître le nom exact d'un exécutable : Gestionnaire des tâches →
onglet **Détails**, colonne **Nom**.

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

Le script envoie aussi le titre de la fenêtre, nettoyé. Les titres Windows
ressemblent à `Projet_A12.dwg - Autodesk Civil 3D 2024` : on garde le
premier morceau, presque toujours le nom du fichier.

```
┌────────────────────────┐
│▓CIVIL 3D▓▓▓▓▓▓▓▓▓AUTO▓▓│
│ ▐1▌ MATCH   ▐2▌ HATCH  │
│ ▐3▌ ANNUL   ▐4▌ ISOLE  │
│ ▐5▌ ZOOM    ▐6▌ ENREG  │
│────────────────────────│
│ Projet_A12.dwg         │
└────────────────────────┘
```

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
| `T:Projet.dwg` | nom du document à afficher |
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
| Le profil ne change pas | vérifie le nom de l'exécutable dans `macropad_apps.txt` (Gestionnaire des tâches → Détails) |
| L'écran affiche `LOCK` | tu as verrouillé le profil : touche les deux TTP223 ensemble |
| La page ne s'ouvre pas | le script n'est pas lancé, ou le port 8765 est déjà pris |
| `le macropad n'a pas repondu` | `LINK_ENABLED = False` dans `config.py`, ou `main.py` ne tourne pas |
