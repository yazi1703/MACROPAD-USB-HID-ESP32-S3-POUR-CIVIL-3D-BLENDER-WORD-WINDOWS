# 12. L'agenda du jour sur l'écran OLED

L'écran n'a plus à afficher les commandes : le compagnon PC les montre en
entier dans sa fenêtre ([chapitre 8](08-detection-auto.md)). Il peut donc
servir à ce qu'on ne voit **pas** ailleurs quand Civil 3D occupe tout
l'écran — **la journée qui vient**.

C'est une transposition de la vue « jour » de Teams sur 128 × 64 pixels :
les heures à gauche, les rendez-vous en blocs à droite, la ligne pointillée
de l'instant présent qui traverse tout, et en bas **la prochaine tâche**
avec son compte à rebours.

---

## 12.1 Ce que ça donne

À 14h10, avec la journée d'exemple livrée dans `pc/agenda-exemple.json` :

```
    +----------------+
  0 |################|
    |################|
    |DIM 13####14:10#|   le jour, et l'heure donnée par le PC
    |################|
    |################|
    |################|
    |################|
    |################|
  8 |################|
    |################|
    |################|
    |                |
    |13.             |   une heure = une ligne de 8 pixels
    |  .             |
    |  .             |
    |  .             |
 16 |  .             |
    |  .             |
    |  .             |
    |  .             |
    |14.#############|   le bloc du rendez-vous
    |#..Point de Bri.|   <- la ligne "maintenant", à 14h10 pile
    |  ..           .|
    |  .#############|
 24 |  .             |
    |  .             |
    |  .             |
    |  .             |
    |15.             |
    |  .             |
    |  .             |
    |  .             |
 32 |  .             |
    |  .             |
    |  .             |
    |  .             |
    |16.#############|
    |  .ELDV - Etude.|
    |  ..           .|
    |  ..           .|
 40 |  ..           .|
    |  ..           .|
    |  ..           .|
    |  ..           .|
    |17..           .|
    |  ..           .|
    |  ..           .|
    |  .#############|
 48 |  .             |
    |  .             |
    |  .             |
    |  .             |
    |                |
    |################|
    |                |
    |                |
 56 |>14:30Point de B|   14h10 : le briefing est EN COURS, il finit à 14h30
    +----------------+
```

Un bloc est dessiné **comme Teams les dessine** : un contour clair avec une
**barre pleine sur son bord gauche**. Sur un écran monochrome, c'est la
traduction fidèle du petit trait de couleur, et ça laisse l'intérieur libre
pour l'intitulé et pour la ligne « maintenant ».

### La ligne du bas

Elle dit trois choses différentes selon le moment :

| Situation | Ce qui s'affiche |
|---|---|
| une réunion est **en cours** | `>21:00` + son intitulé — quand elle finit |
| la suivante est **proche** (< 1 h) | `19min` + son intitulé |
| la suivante est **plus loin** | `19:30` + son intitulé |
| **plus rien** aujourd'hui | `Plus rien aujourd'hui` |
| le PC **n'a jamais parlé** | `En attente du PC - lance-le avec --agenda` |
| le PC **s'est tu** | `Le PC ne repond plus` |

> **Ces deux derniers ne sont pas la même panne**, et le message le dit.
> « Ne répond plus » sous-entend qu'il répondait avant : l'afficher alors
> que le compagnon n'a jamais parlé envoie chercher un problème de liaison
> qui n'existe pas — quand le vrai défaut est bien plus simple, le
> compagnon lancé **sans `--agenda`**.
>
> Côté PC, le compagnon écrit une fois `Heure envoyee au macropad` dès que
> la première heure part : si tu ne vois pas cette ligne, rien n'est
> envoyé, et c'est là qu'il faut chercher.

L'intitulé **défile** s'il est trop long, comme le nom de document.

---

## 12.2 La limite à connaître avant de s'énerver

**L'écran fait 16 caractères de large. Un bloc en accepte 12.**

`BUGEY II / Point d'équipe Atlas` devient `BUGEY II / P`. Ce n'est pas un
réglage à trouver, c'est la dalle.

Le partage est donc celui-ci, et il est assumé :

- **la timeline donne la FORME de ta journée** — quand tu es pris, quand ça
  commence, combien de temps il te reste ;
- **la ligne du bas donne le NOM**, en entier, en le faisant défiler.

Si tu veux des intitulés lisibles d'un coup d'œil, la vraie réponse est de
**renommer tes réunions récurrentes** côté calendrier (`Atlas` plutôt que
`BUGEY II / Point d'équipe Atlas`). Dis-le-moi si tu préfères un tableau de
surnoms côté configuration : c'est faisable, c'est juste plus de travail.

---

## 12.3 La carte n'a pas d'horloge, et ça se voit

L'ESP32-S3 **n'a aucune pile de sauvegarde**. Au branchement, il ne sait ni
l'heure ni la date. C'est le compagnon PC qui les lui envoie, **toutes les
minutes**.

Entre deux messages, la carte extrapole avec son horloge interne — fiable à
la seconde près sur quelques minutes. Mais si le compagnon **se tait** (PC
en veille, câble débranché, programme fermé), cette extrapolation dériverait
sans que rien ne le signale.

> **La règle, et elle est absolue :** au-delà de 5 minutes sans nouvelle,
> l'écran affiche **`--:--`** et **efface la ligne « maintenant »**.
>
> Une heure fausse est pire que pas d'heure : elle te ferait rater une
> réunion en te croyant à l'heure. Deux tests tiennent cette règle dans les
> deux sens.

**L'écran ne s'éteint jamais dans cette vue.** L'économiseur coupe la dalle
après un quart d'heure sans appui — appliqué ici, il rendrait la vue
inutile, puisque c'est justement quand on ne tape pas qu'on veut la voir.
Elle reste donc **atténuée** (contraste minimal, ce qui use bien moins les
pixels) mais allumée. Le tableau des macros, lui, garde l'extinction : un
test le vérifie, pour qu'on ne l'ait pas désactivée pour tout le monde en
passant.

---

## 12.4 D'où vient le planning

C'est **la seule partie que tu dois monter toi-même**, et c'est la seule que
je n'ai pas pu tester : je n'ai ni Windows, ni Teams, ni ton réseau
d'entreprise.

Le compagnon **ne se connecte à aucun calendrier**. Il lit un **fichier**
que quelqu'un d'autre remplit. Aucun identifiant ne traverse ce code, et
rien ne sort de ton PC.

### Tu as le « nouvel Outlook » : trois chemins, très inégaux

| Chemin | Ce que ça demande | Mon avis |
|---|---|---|
| **Power Automate → OneDrive** | rien de plus que ton compte M365 | ⭐ le chemin recommandé |
| **Microsoft Graph** | une inscription d'application Azure AD, souvent soumise à l'accord d'un administrateur | à tenter, sans y compter |
| **Calendrier publié en .ics** | que ton organisation autorise la publication | ⚠️ ça expose tes intitulés sur une URL. Avec des noms de projets comme les tiens, je l'éviterais |

> **Pourquoi pas simplement lire Outlook ?** L'Outlook classique exposait
> une automatisation locale (COM) qui rendait ça trivial. **Le nouvel
> Outlook ne l'expose plus.** C'est pour ça qu'on passe par un fichier.

> **Pourquoi pas un simple export .ics de ton calendrier ?** Parce qu'un
> `.ics` brut contient les **règles de répétition**, pas les occurrences.
> Ton « BUGEY II / Point d'équipe Atlas » hebdomadaire y figure une fois,
> avec une règle à interpréter — jours fériés, exceptions et décalages
> compris. Un analyseur approximatif te montrerait des réunions aux
> mauvais jours, en silence. Power Automate et Graph, eux, savent
> **dérouler** les répétitions : c'est leur travail, pas le mien.

### Power Automate, pas à pas

**Ce que c'est.** Un outil de Microsoft, inclus dans ton abonnement Office,
qui fait tourner des petites automatisations dans le cloud. Pas
d'installation, pas de droits d'administrateur : tu ouvres
[make.powerautomate.com](https://make.powerautomate.com), tu te connectes
avec ton compte professionnel.

Ton flux tiendra en **trois blocs** :

```
  ┌──────────────────────────────────────────────┐
  │ 1. Toutes les 15 minutes                     │  le déclencheur
  └──────────────────────────────────────────────┘
                      ↓
  ┌──────────────────────────────────────────────┐
  │ 2. Lire mon calendrier (vue de calendrier)    │  Office 365 Outlook
  └──────────────────────────────────────────────┘
                      ↓
  ┌──────────────────────────────────────────────┐
  │ 3. Écrire le résultat dans agenda.json         │  OneDrive
  └──────────────────────────────────────────────┘
```

---

#### Étape 0 — préparer le fichier de destination (à faire en premier)

Dans **OneDrive**, crée un fichier texte nommé **`agenda.json`** contenant
juste `{}`. N'importe quel dossier fait l'affaire ; retiens lequel.

> **Pourquoi d'abord ?** Parce qu'on va utiliser l'action **« Mettre à jour
> le fichier »**, qui a besoin d'un fichier existant à désigner. L'action
> « Créer un fichier », elle, ne remplace rien : elle ajouterait
> `agenda-1.json`, `agenda-2.json`… à chaque exécution. Avec un flux qui
> tourne toutes les 15 minutes, tu aurais quatre-vingt-seize fichiers
> inutiles par jour et le compagnon lirait toujours le premier, figé.
>
> C'est le genre de détail qui coûte une soirée.

---

#### Étape 1 — le déclencheur

**Créer** → **Flux de cloud planifié**. Donne-lui un nom (`Agenda macropad`),
répétition **toutes les 15 minutes**.

---

#### Étape 2 — lire le calendrier

**Nouvelle étape** → cherche **Office 365 Outlook** → prends l'action dont le
nom contient **« vue du calendrier »** (*Get calendar view of events* en
anglais), la version la plus élevée proposée (V3 ou plus).

> ### ⚠️ Prends bien « vue du calendrier », pas « obtenir les événements »
>
> Les deux existent et se ressemblent. **Seule la « vue du calendrier »
> déroule les réunions récurrentes.** L'autre te rendrait ton « BUGEY II /
> Point d'équipe Atlas » hebdomadaire **une seule fois**, à sa date de
> création — c'est-à-dire jamais aujourd'hui.

Trois champs à remplir :

| Champ | Quoi mettre |
|---|---|
| **Calendrier** | choisis-le dans la liste (`Calendrier` / `Calendar`) |
| **Heure de début** | l'expression ci-dessous |
| **Heure de fin** | l'expression ci-dessous |

Pour les deux heures, ne tape pas une date : clique sur l'onglet
**Expression** (ou *fx*) et colle exactement :

```
addDays(startOfDay(utcNow()), -1)
```

```
addDays(startOfDay(utcNow()), 2)
```

> **Pourquoi une fenêtre de trois jours, et pas la journée ?** Parce que
> `utcNow()` donne l'heure **UTC**, décalée de 1 ou 2 h par rapport à toi :
> viser « aujourd'hui » pile ferait manquer tes réunions du petit matin,
> selon la saison. On prend donc large — **c'est le compagnon qui filtre sur
> TA date locale**, et il te dit ce qu'il a écarté. Une fenêtre généreuse ne
> coûte rien ; une fenêtre trop juste coûte une réunion.

---

#### Étape 3 — écrire le fichier

**Nouvelle étape** → **OneDrive Entreprise** → **Mettre à jour le fichier**.

| Champ | Quoi mettre |
|---|---|
| **Fichier** | l'icône dossier, puis choisis le `agenda.json` de l'étape 0 |
| **Contenu du fichier** | la sortie **`body`** de l'étape 2 |

Pour le contenu : dans le panneau de contenu dynamique, prends l'entrée
**`body`** de l'action précédente. Si tu ne la trouves pas, va dans
**Expression** et colle (en remplaçant par le vrai nom de ton action, avec
des `_` à la place des espaces) :

```
body('Obtenir_la_vue_du_calendrier_des_événements_(V3)')
```

**Enregistre**, puis **Tester** → *Manuellement*.

---

#### Étape 4 — vérifier AVANT de toucher au macropad

OneDrive synchronise le fichier sur ton PC en quelques secondes. Puis :

```bash
python3 tools/verifier_agenda.py "C:\Users\toi\OneDrive\agenda.json"
```

C'est **là** que tu sauras si ça marche, pas sur l'écran du macropad. L'outil
te dit combien d'entrées ont été comprises, lesquelles ont été écartées **et
pourquoi**, et il affiche les heures brutes à côté des heures converties.

**Compare ces heures à ce que tu vois dans Teams.** Un décalage constant de
1 ou 2 heures, c'est le fuseau — dis-le-moi avec la première entrée du
fichier, j'adapte.

Quand c'est bon, pointe le compagnon dessus :

```bat
python macropad_auto.py --agenda "C:\Users\toi\OneDrive\agenda.json"
```

---

#### Si un libellé ne correspond pas à ce que tu vois

Les noms d'actions changent selon la version de Power Automate et la langue
de ton compte. **Je te donne la forme du flux, pas une suite de clics que je
ne peux pas vérifier d'ici.** Si tu bloques sur une étape, envoie-moi ce que
tu vois — la liste des actions proposées, ou le message d'erreur — et on
finit ensemble.

Et si ton organisation bloque Power Automate, dis-le-moi aussi : le
compagnon lit un simple fichier JSON, donc **n'importe quoi** capable d'en
écrire un fera l'affaire.

### Le format du fichier

```json
{
  "evenements": [
    {"debut": "2026-09-13T16:00:00Z",
     "fin":   "2026-09-13T17:30:00Z",
     "titre": "ELDV - Etude et modélisation 3D"}
  ]
}
```

Trois tolérances, pour que ça marche sans rien transformer :

| Ce qui est accepté | Pourquoi |
|---|---|
| `"16:00"` tout court | pratique pour un fichier d'essai écrit à la main |
| les clés anglaises `subject` / `start` / `end`, y compris **imbriquées** (`{"dateTime": ...}`) | un export brut de Graph ou de Power Automate fonctionne tel quel |
| une liste nue, sans l'objet autour | idem |

> ### ⚠️ Le piège du fuseau horaire
>
> Un calendrier d'entreprise donne très souvent ses heures **en UTC**. Les
> prendre telles quelles décalerait **tout** l'agenda d'une ou deux heures
> selon la saison — et **rien ne le signalerait**. Tu arriverais en retard
> en croyant être en avance.
>
> Il y a **deux écritures**, et la seconde m'avait échappé :
>
> ```json
> "start": {"dateTime": "2026-09-13T09:00:00Z"}                        ← le Z
> "start": {"dateTime": "2026-09-13T09:00:00.0000000", "timeZone": "UTC"}
> ```
>
> **La seconde est celle que Microsoft Graph produit par défaut.**
> L'horodatage n'a ni `Z` ni décalage : la seule mention du fuseau est le
> champ voisin. Les deux sont maintenant converties, et sept tests les
> tiennent — dont un sur un vidage brut de flux.
>
> Ce défaut a été trouvé par `tools/verifier_agenda.py` (ci-dessous), sur
> un fichier d'exemple, avant qu'il ne coûte une réunion.
>
> **Un fuseau qu'on ne sait pas traduire** (les noms Windows du genre
> `Romance Standard Time`) n'est **jamais deviné** — un fuseau inventé
> serait exactement la panne silencieuse qu'on cherche à éviter. L'heure est
> prise telle quelle, et l'outil de vérification le signale en gros.
> Demande à ton flux de sortir les heures **en UTC** : c'est le réglage par
> défaut de Graph, et le seul qu'on traduise à coup sûr.

**Les accents sont convertis avant l'envoi** (`modélisation` → `modelisation`)
: la police de l'écran est de l'ASCII pur, un caractère accentué y sortirait
en charabia. Un emoji dans un intitulé devient `?` — ça arrive, et ça ne
doit ni planter ni dessiner n'importe quoi.

---

## 12.5 Essayer tout de suite, sans rien brancher

Deux choses sont utilisables avant même d'avoir monté la source.

**Le vérificateur de fichier.** C'est l'outil à lancer **dès que ton flux
produit quelque chose**, avant même de brancher la carte :

```bash
python3 tools/verifier_agenda.py mon_agenda.json
```

Il lit le fichier **avec le même code que le compagnon** et dit, entrée par
entrée : gardée, ou écartée **et pourquoi**. Une réunion qui manque à
l'écran cesse d'être un mystère.

```
6 entree(s) lue(s), 2 gardee(s), 4 ecartee(s).

GARDEES
  11:00 - 12:00   BUGEY II / Point d'equipe Atlas
  16:00 - 17:30   ELDV - Etude et modelisation 3D

ECARTEES
  Reunion de demain  [2026-09-14T09:00:00Z]     pas aujourd'hui (2026-09-14)
    [2026-09-13T11:00:00Z]                      aucun titre (ni 'titre' ni 'subject')
  Sans date  [?]                                date de debut illisible ou absente
  'une chaine perdue'                           ce n'est pas un objet JSON

==================================================================
VERIFIE CES HEURES CONTRE CE QUE TU VOIS DANS TEAMS.
Un decalage CONSTANT de 1 ou 2 heures sur tout l'agenda est
un probleme de fuseau, pas un probleme de macropad :
   fichier 2026-09-13T09:00:00.0000000  ->  affiche 11:00
==================================================================
```

Cette dernière vérification est la raison d'être de l'outil : **compare ces
heures à Teams**. Un décalage constant, c'est le fuseau ; rien d'autre ne
te le dirait.

**L'aperçu dans le terminal.** Ce n'est pas une maquette dessinée à la
main : c'est le **vrai code** de `device/display.py` qui tourne, avec un
faux écran qui note chaque trait, puis les redessine.

```bash
python3 tools/apercu_agenda.py              # à l'heure qu'il est
python3 tools/apercu_agenda.py 14:10        # à une heure choisie
python3 tools/apercu_agenda.py 14:10 mon_agenda.json
```

Un bloc mal placé, un intitulé qui déborde, la ligne « maintenant » à la
mauvaise hauteur : ça se voit là, en une seconde, au lieu de se découvrir
après avoir tout soudé.

**Le fichier d'exemple.** `pc/agenda-exemple.json` contient une journée
complète. Remplace les heures par celles de ton après-midi et lance le
compagnon avec `--agenda` : tu verras la vue bouger sans avoir configuré
quoi que ce soit.

---

## 12.6 L'activer

Dans `device/config.py`, sur la carte :

```python
AGENDA_ENABLED = True       # livré à False
```

Livré à **False**, comme les LED RGB : rien de nouveau ne s'allume tout
seul, et l'écran garde le tableau des macros tant que tu n'as pas dit le
contraire. Sans compagnon PC, cette vue n'aurait de toute façon rien à
montrer.

Les autres réglages, tous dans `config.py` :

| Réglage | Défaut | À quoi ça sert |
|---|---|---|
| `AGENDA_FENETRE_H` | 5 | heures visibles dans la timeline |
| `AGENDA_AVANT_H` | 1 | heures de passé montrées, pour se repérer |
| `AGENDA_MAX` | 16 | événements gardés en mémoire |
| `AGENDA_TITRE_MAX` | 40 | au-delà, l'intitulé est coupé |
| `AGENDA_HEURE_PERIMEE_MS` | 300000 | 5 min sans nouvelle → `--:--` |

`AGENDA_FENETRE_H` ne peut pas déborder sur la ligne du bas : la hauteur
disponible est calculée à partir de la géométrie de l'écran, et c'est elle
qui décide, pas le réglage.

---

## 12.7 Le protocole, si tu veux bricoler

Trois lignes de plus sur la liaison série, dans le même esprit que les
existantes :

```
H:19:47|DIM 13                  l'heure et le libellé du jour
!AGBEGIN                        début de la liste
A:16:00|17:30|ELDV - Etude et modelisation 3D
A:19:30|21:00|tache 1
!AGEND                          fin : la liste remplace l'ancienne
```

> **La liste n'est adoptée qu'à `!AGEND`.** Une transmission coupée en deux
> — un câble qui bouge — laisse donc l'agenda **précédent** affiché, jamais
> un agenda à moitié effacé. Sans cette règle, on croirait sa journée libre.
> Un test le vérifie, et l'adopter plus tôt le fait échouer.

Une ligne `A:` illisible est ignorée **sans annuler les autres** : une
réunion perdue vaut mieux qu'un agenda refusé en entier.

Si `AGENDA_ENABLED` vaut `False`, ces trois lignes sont ignorées proprement.
Un compagnon plus récent que le firmware de la carte ne casse rien.

---

## 12.8 Ce qui n'a PAS été vérifié

Je n'ai ni ESP32, ni Windows, ni Teams, ni ton réseau. Donc :

| Vérifié en simulation | Pas vérifié |
|---|---|
| toute la logique de `agenda.py` (heure périmée, chevauchements, minuit) | l'affichage réel sur ta dalle SH1106 |
| le dessin, à chaque quart d'heure des 24 heures, sans un pixel hors des 128 × 64 | la lisibilité réelle à un mètre |
| la conversion UTC → heure locale, et la translittération des accents | ton flux Power Automate |
| l'aller-retour complet PC → protocole → firmware | le comportement quand ton PC se met en veille |
| le fichier absent, mal formé, ou en cours d'écriture | l'usure réelle des pixels sur des mois |

**Les 48 nouveaux tests sont verts, et sept mutations ont été vérifiées** —
chacune casse un test : supprimer le garde-fou de l'heure périmée, adopter
la liste avant la fin de la transmission, rendre n'importe laquelle de deux
réunions simultanées, éteindre l'écran en vue agenda, prendre l'UTC tel
quel, laisser passer les accents, et afficher hier et demain.

Une mutation avait d'ailleurs **survécu** au premier essai — mon test des
réunions simultanées ne discriminait rien. Il a été refait. C'est
exactement pour ça qu'on mute les tests au lieu de les croire sur parole.
