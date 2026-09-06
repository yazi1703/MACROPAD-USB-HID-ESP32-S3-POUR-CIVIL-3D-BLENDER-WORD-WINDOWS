# 5. Électronique expliquée — et surtout : ce qui risque de cramer

Document écrit pour quelqu'un qui débute. Chaque règle est suivie de son
**pourquoi**, parce qu'une règle qu'on comprend, on ne l'oublie pas.

---

## 5.1 Les trois règles d'or

### Règle 1 — Rien de plus de 3,3 V sur une broche GPIO

L'ESP32-S3 fonctionne en 3,3 V. Sa fiche technique donne une tension
maximale absolue de **3,6 V** sur une entrée. Au-delà, on ne détruit pas
forcément la puce d'un coup : on l'abîme lentement, et la panne arrive
plus tard, de façon incompréhensible.

C'est pour cette raison que **les TTP223 doivent être alimentés en 3,3 V et
jamais en 5 V**. Ces modules recopient leur tension d'alimentation sur leur
sortie OUT. Alimentés en 5 V, ils enverraient 5 V directement dans GPIO10
et GPIO11. C'est l'erreur la plus fréquente sur ce genre de montage, et
c'est une erreur définitive.

Même chose pour l'OLED : il accepte 3,3 V et 5 V côté alimentation, mais
ses broches SDA et SCL suivent la tension d'alimentation. **Alimenté en
5 V, il enverrait 5 V dans GPIO8 et GPIO9.** On l'alimente donc en 3,3 V.

### Règle 2 — Jamais de LED directement sur un GPIO

Un GPIO d'ESP32-S3 peut fournir environ **40 mA au maximum absolu**, et on
recommande de rester sous 20 mA. Une LED sans résistance se comporte
presque comme un court-circuit une fois sa tension de seuil atteinte :
elle tirerait plusieurs centaines de milliampères. Résultat : la broche
grille, parfois en emportant sa voisine.

D'où le transistor BC547 : il sert d'interrupteur commandé. Le GPIO ne
fournit qu'**1,2 mA** pour commander la base, et c'est le +5 V de l'USB qui
fournit le courant de la LED, à travers la résistance de 330 ohms.

### Règle 3 — On ne modifie jamais un câblage sous tension

Débranche l'USB avant de toucher un fil. Deux raisons :

1. Un contact fugitif entre le +5 V et un fil de signal met 5 V sur un
   GPIO pendant quelques millisecondes. C'est suffisant.
2. Un court-circuit entre 3V3 et GND fait travailler le régulateur de la
   carte en surcharge ; il chauffe très vite et peut lâcher.

---

## 5.2 Tableau des pannes destructrices

| Erreur | Ce qui se passe | Ce qui meurt | Comment l'éviter |
|---|---|---|---|
| TTP223 alimenté en 5 V | 5 V sur GPIO10/11 | la broche, puis la puce | fil VCC sur **3V3**, jamais sur 5V |
| OLED alimenté en 5 V | 5 V sur SDA/SCL | GPIO8 et GPIO9 | fil VCC sur **3V3** |
| LED branchée en direct sur GPIO15 | courant non limité | la broche GPIO | passer par le BC547 + 330 Ω |
| Résistance 330 Ω oubliée | la LED voit 5 V | LED **et** BC547 (max 100 mA) | vérifier avant la mise sous tension |
| BC547 avec E et C inversés | la jonction base-émetteur est en inverse (claquage vers 6 V) | le transistor, en silence | identifier E/B/C à la fiche technique **ou** au multimètre |
| Fil du +5 V qui touche le fil GPIO14 | 5 V sur une entrée | la broche | connecteur détrompé + résistance série 1 kΩ (voir 5.5) |
| Quelque chose branché sur GPIO19/20 | on parasite les données USB | l'USB, parfois la broche | ne rien y connecter, jamais |
| 3V3 relié à 5V | le régulateur est mis en conflit | le régulateur de la carte | vérifier au multimètre avant de brancher |
| Condensateur électrolytique à l'envers | il chauffe, gonfle, puis éclate | le condensateur, et ce qui est autour | respecter la bande blanche (le « − ») |
| Deux ports USB sur **deux ordinateurs différents** | les masses ne sont pas au même potentiel | la carte | les deux ports sur **le même PC**, ou un seul |
| Fer à souder sur une carte alimentée | fuites de courant par la panne | la puce | souder toujours hors tension |

---

## 5.3 Vérifications au multimètre AVANT la première mise sous tension

Câble USB **débranché**. Multimètre en position continuité (le symbole qui
fait « bip ») ou en ohms.

```
[ ] entre 3V3 et GND        -> PAS de bip  (une résistance de plusieurs
                               kilo-ohms est normale, un bip = court-circuit)
[ ] entre 5V  et GND        -> PAS de bip
[ ] entre 5V  et 3V3        -> PAS de bip
[ ] entre GPIO4 et GND      -> bip SEULEMENT quand tu appuies sur B1
[ ] idem GPIO5/6/7 et B2/B3/B4
[ ] entre GPIO14 et GND     -> bip SEULEMENT quand tu appuies sur ESC
[ ] entre GPIO19 ou GPIO20 et n'importe quoi -> rien, ces broches sont libres
```

Si un seul de ces points échoue, **ne branche pas**. Cherche d'abord.

### ⚠️ Remplacer un MOSFET par un BC547 : le brochage n'est PAS le même

Piège classique, rencontré sur ce montage. On ne peut **pas** échanger le
composant en laissant les fils dans les mêmes trous.

```
   IRFZ44N (face marquée vers toi)      BC547 (face plate vers toi)
        G  |  D  |  S                        C  |  B  |  E
      grille drain source                collecteur base émetteur
```

La **broche du milieu** est le **drain** sur le MOSFET, mais la **base** sur
le BC547. Ce ne sont pas du tout les mêmes fonctions : le drain transporte
le courant de la LED, la base reçoit la commande.

Si tu remplaces le composant sans rien recâbler, tu obtiens :

| Fil | Allait sur | Arrive maintenant sur | Correct ? |
|---|---|---|---|
| GPIO15 via la résistance | grille (gauche) | **collecteur** | ❌ |
| cathode de la LED | drain (milieu) | **base** | ❌ |
| GND | source (droite) | émetteur | ✅ |
| 10 kΩ vers GND | grille (gauche) | **collecteur** | ❌ |

Trois fils sur quatre sont faux. Le câblage correct pour le BC547 :

```
   cathode LED  -> COLLECTEUR  (broche de gauche)
   GPIO15 -[2,2 kΩ]-> BASE     (broche du MILIEU)
   10 kΩ           -> entre la BASE (milieu) et GND
   GND             -> ÉMETTEUR (broche de droite)
```

Note bien que **la 10 kΩ doit être déplacée elle aussi** : elle était entre
la grille et GND, elle doit maintenant être entre la **base** et GND.

### Le test de pontage change lui aussi

Pour court-circuiter un transistor et vérifier ce qu'il y a en amont :

* **MOSFET** : ponter **milieu ↔ droite** (drain ↔ source) ;
* **BC547** : ponter les **deux broches EXTÉRIEURES** (collecteur ↔ émetteur).
  Ponter le milieu sur une extérieure relierait la **base**, ce qui ne
  court-circuite rien du tout — et forcerait même le transistor à se
  bloquer.

Un pontage fait sur les mauvaises broches ne prouve rien : il ne faut pas
en conclure que l'amont est en panne.

### BC547 ou BC557 ? Ne pas les confondre

Ils se ressemblent — même boîtier TO-92, même taille, numéros voisins — mais
ce sont des **contraires**.

| | BC547 | BC557 |
|---|---|---|
| Type | **NPN** | **PNP** |
| Commute du côté | de la **masse** (low-side) | du **plus** (high-side) |
| Pour l'allumer | base **haute** (3,3 V) | base **basse** (0 V) |
| Notre montage | ✅ **c'est celui-ci** | ❌ ne convient pas |

**Pourquoi le BC557 ne peut pas marcher ici.** Un PNP se monte entre le
+5 V et la charge, et pour le **bloquer** il faut remonter sa base au
potentiel de son émetteur, donc à **5 V**. Or un GPIO d'ESP32 ne monte qu'à
3,3 V. La jonction reste alors polarisée en direct de `5 − 3,3 = 1,7 V`,
largement au-dessus des 0,7 V nécessaires : le transistor **ne se bloque
jamais**.

Concrètement, avec une résistance de base de 2,2 kΩ, il subsisterait
`(5 − 0,7 − 3,3) / 2200 = 0,45 mA` de courant de base même à l'état
« éteint ». La LED ne s'éteindrait jamais complètement et le réglage PWM
serait inutilisable.

Moyen mnémotechnique : **NPN = interrupteur en bas** (côté GND),
**PNP = interrupteur en haut** (côté +). Notre LED a sa cathode en bas,
donc c'est un NPN.

Le BC557 reste utile ailleurs — pour commuter le + d'une charge — mais il
demande alors d'être piloté lui-même par un NPN, ce qui n'a aucun intérêt
ici.

### Identifier les pattes du BC547

Le brochage d'un boîtier TO-92 **change selon le fabricant**. Ne te fie
jamais à « face plate vers toi, c'est C-B-E » : c'est vrai pour certains,
faux pour d'autres, et une inversion émetteur/collecteur abîme le
transistor de façon invisible.

Deux méthodes fiables :

**Méthode 1 — le marquage.** Lis le texte complet sur la face plate
(par exemple `BC547B` + un logo ou un code fabricant), et cherche la fiche
technique de ce fabricant précis. Envoie-moi le marquage exact, je te
confirme le brochage.

**Méthode 2 — le multimètre, position test de diode.** Sur un NPN comme le
BC547, la **base** est la seule patte qui, avec la pointe **rouge** posée
dessus, fait apparaître une tension d'environ 0,6 à 0,7 V vers **les deux
autres** pattes. Une fois la base identifiée, il reste à distinguer
émetteur et collecteur : la mesure base→émetteur donne une tension
légèrement **plus élevée** que base→collecteur (quelques dizaines de
millivolts d'écart). En cas de doute, un testeur de composants à quelques
euros donne directement E/B/C.

### Identifier l'anode de la LED

En position test de diode : la LED s'allume faiblement quand la pointe
**rouge** est sur l'**anode**. L'anode va vers la résistance de 330 Ω, donc
vers le +5 V. La cathode va vers le collecteur du transistor.

---

## 5.4 Le montage de la LED, expliqué pas à pas

```
   +5 V (venant de l'USB)
        |
      [330 Ω]        <-- c'est CETTE résistance qui protège tout le montage
        |
       LED 1 W       <-- anode en haut, cathode en bas
        |
        C  (collecteur)
        |
   B --|<   BC547, transistor NPN
        |
        E  (émetteur)
        |
       GND

   GPIO15 ---[2,2 kΩ]---+--- B
                        |
                     [10 kΩ]
                        |
                       GND
```

**Ce que fait chaque composant :**

- **330 Ω** : limite le courant. Sans elle, la LED verrait 5 V et tirerait
  un courant destructeur. Avec elle, et une LED rouge dont la tension de
  seuil est d'environ 2,1 V :
  `I = (5 − 2,1 − 0,2) / 330 = 8,2 mA`.
  La LED est prévue pour 1 W, elle dissipe ici **17 mW**. Elle ne chauffera
  pas, même à 100 % de PWM. C'est exactement l'effet veilleuse voulu.

- **BC547** : interrupteur commandé. Quand GPIO15 est à 3,3 V, il laisse
  passer le courant ; à 0 V, il le bloque. Il supporte 100 mA, on en
  utilise 8,2 : marge d'un facteur 12.

- **2,2 kΩ** : limite le courant qui entre dans la base.
  `Ib = (3,3 − 0,7) / 2200 = 1,18 mA`. Sans elle, la base se comporterait
  comme une diode directe et le GPIO se retrouverait quasiment en
  court-circuit.

- **10 kΩ entre base et masse** : maintient le transistor bloqué quand le
  GPIO n'est pas encore configuré, c'est-à-dire pendant le reset et le
  démarrage. Sans elle, la LED peut s'allumer brièvement au boot. Elle
  consomme 0,07 mA sur les 1,18, il reste 1,11 mA pour la base : largement
  assez (il en faut 0,82 pour saturer).

**Si ta LED est blanche, bleue ou verte**, sa tension de seuil est plus
haute (environ 3,2 V) et le courant tombe à 4,8 mA : elle paraîtra sombre.
Descends alors à **220 Ω** (7,3 mA) ou **150 Ω** (10,7 mA). On reste très
loin du watt et de tout échauffement.

---

## 5.4 bis — Variante avec un MOSFET IRFZ44N à la place du BC547

Si tu as monté un **IRFZ44N** plutôt qu'un BC547, la topologie est la même
(interrupteur côté masse), mais **trois différences importantes**.

```
   +5 V
    |
  [330 Ω]
    |
   LED
    |
    D  (drain = broche du MILIEU, et aussi la patte métallique)
    |
G --|  IRFZ44N          G = broche de GAUCHE
    |                   S = broche de DROITE
    S
    |
   GND

   GPIO15 ---[220 Ω]---+--- G
                       |
                    [10 kΩ]        <-- INDISPENSABLE avec un MOSFET
                       |
                      GND
```

### Différence 1 — la résistance de 10 kΩ n'est plus optionnelle

La grille d'un MOSFET est un **condensateur isolé** : elle ne consomme
aucun courant, mais elle **retient sa charge**. Pendant le RESET et le
démarrage de l'ESP32, GPIO15 est en haute impédance : la grille garde alors
la tension qu'elle avait, et la LED peut rester allumée ou clignoter au
hasard.

Avec un BC547 c'était un confort. Avec un MOSFET, **c'est obligatoire** :
10 kΩ entre la grille et GND.

#### Le piège classique : 10 kΩ sur la GRILLE, pas sur la SOURCE

Les deux résistances aboutissent à GND, ce qui prête à confusion. Mais
électriquement elles n'ont rien à voir.

```
   CORRECT                             FAUX
   -------                             ----
   GPIO15 --[220Ω]--+-- G              GPIO15 --[220Ω]-- G
                    |
                 [10 kΩ]
                    |
                   GND
                                       S --[10 kΩ]-- GND     <-- ERREUR
   S ------------- GND
   (fil direct, rien entre)
```

**Pourquoi la version fausse ne marche pas.** Si la 10 kΩ est *en série*
avec la source, tout le courant de la LED doit la traverser. Pour y faire
passer 8 mA, il faudrait `0,008 × 10000 = 80 V` à ses bornes. On n'en a
que 5.

Le montage se met alors à s'auto-étrangler : dès qu'un peu de courant
passe, la source monte en tension, donc `Vgs = Vgrille − Vsource` diminue,
donc le transistor se referme. Le point d'équilibre se situe autour de
`(3,3 − Vgs(th)) / 10000`, soit **quelques dizaines de microampères**.
La LED reste éteinte, ou luit à peine dans le noir.

C'est ce qu'on appelle une résistance de dégénérescence de source. Utile
dans un amplificateur, catastrophique dans un interrupteur.

**Aucun risque de casse** : on parle de microampères. C'est juste
inopérant.

**Vérification au multimètre, hors tension :**

* entre la broche **droite (source)** et GND → **continuité franche**,
  0 Ω. Si tu lis 10 kΩ, la résistance est au mauvais endroit.
* entre la broche **gauche (grille)** et GND → **10 kΩ**.

---

### Différence 2 — l'IRFZ44N n'est pas un modèle « logic level »

C'est le vrai point faible de ce choix. Sa fiche technique donne une
tension de seuil `Vgs(th)` comprise entre **2,0 V et 4,0 V**, et sa
résistance à l'état passant est spécifiée pour **Vgs = 10 V**.

Or l'ESP32 ne fournit que **3,3 V**. Selon l'exemplaire que tu as :

* seuil bas (2,0 V) → il conduit très correctement, tout va bien ;
* seuil haut (4,0 V) → à 3,3 V il est pratiquement **bloqué**, et la LED
  reste éteinte ou très sombre.

C'est une loterie, et deux transistors du même sachet peuvent se comporter
différemment. **Bonne nouvelle** : on ne demande que 8 mA. Même partiellement
ouvert, un IRFZ44N laisse en général passer largement plus que cela, donc
ça fonctionne le plus souvent. Et tant qu'il peut écouler 8 mA avec moins
de 2,7 V à ses bornes, c'est la résistance de 330 Ω qui fixe le courant :
la luminosité est alors exactement celle prévue.

**Aucun risque de destruction** dans les deux cas : à 8 mA, même s'il
travaille en régime linéaire, il dissipe moins de 20 mW pour un boîtier
prévu pour plusieurs dizaines de watts.

Donc : **teste, et regarde**. Si la LED s'allume franchement et que les
paliers 5 % / 20 % / 100 % du test 6 sont bien distincts, garde ce montage.
Si elle reste sombre ou éteinte, deux solutions :

1. revenir au **BC547** (330 Ω / 2,2 kΩ / 10 kΩ), qui lui n'a aucun seuil
   problématique à 3,3 V ;
2. utiliser un MOSFET **logic level** si tu en as un : IRLZ44N, IRL540,
   AO3400, 2N7000… Le `L` de IRLZ44N signifie justement « logic level ».

Pour ce montage à 8 mA, le BC547 reste le choix le plus sûr : l'IRFZ44N est
prévu pour 49 A, il est surdimensionné d'un facteur 6000.

#### Cas rencontré sur ce montage : l'IRFZ44N ne s'ouvre pas à 3,3 V

Le risque décrit ci-dessus **s'est effectivement produit**. Symptômes : LED
totalement éteinte quel que soit le rapport cyclique, alors que tout le
reste est bon.

**Les trois tests qui isolent le coupable en cinq minutes, sans rien
dessouder :**

1. **Pontage drain-source** (relier la broche du milieu à celle de droite) :
   si la LED s'allume, alors le +5 V, la résistance série et la LED sont
   bons. Le problème est donc le transistor ou sa commande.

2. **Continuité de la chaîne de grille**, sans multimètre :

   ```python
   from machine import Pin
   print(Pin(15, Pin.IN, Pin.PULL_UP).value())
   ```

   Le tirage interne (~45 kΩ) se bat contre la 10 kΩ externe. Un **0**
   prouve que GPIO15 → 220 Ω → grille → 10 kΩ → GND est continu. Un **1**
   signale une coupure.

3. **Preuve par le raisonnement sur la diode interne.** Un MOSFET N possède
   une diode intrinsèque de la source vers le drain. Si drain et source
   étaient inversés, cette diode serait passante et **la LED resterait
   allumée en permanence**, grille ou pas. Une LED totalement éteinte prouve
   donc que l'orientation drain/source est correcte.

Quand ces trois points sont vérifiés, il ne reste qu'une explication : la
grille reçoit bien 3,3 V, mais c'est insuffisant pour ouvrir ce transistor.

**Test décisif, trente secondes.** Débranche le fil qui va à GPIO15, puis
touche son extrémité (celle qui part vers la 220 Ω) sur la broche **5V** de
la carte. Aucun risque : une grille ne consomme pas de courant continu.

* la LED s'allume → **confirmé**, c'est bien un problème de seuil ;
* la LED reste éteinte → le transistor est mort, ou il ne s'agit pas d'un
  IRFZ44N.

**Correctif : passer au BC547** (voir § 5.4), ou à un MOSFET *logic level*
type IRLZ44N. Le BC547 est un transistor bipolaire : il n'a pas de seuil de
grille, 3,3 V suffisent toujours à le commander.

---

### Différence 3 — identifier les broches, sans se tromper

Sur un IRFZ44N en boîtier TO-220, **face marquée vers toi, pattes vers le
bas**, l'ordre est :

```
   G   D   S
   |   |   |
  gauche milieu droite
```

**Vérifie-le au multimètre plutôt que de me croire sur parole**, c'est
immédiat :

* **Le drain est relié à la patte métallique.** Mets le multimètre en
  continuité entre le dissipateur et chaque broche : celle qui « bipe » est
  le **drain**, et c'est normalement celle du milieu. C'est le test le plus
  rapide et le plus fiable.
* **La grille est isolée** : en position test de diode, elle ne conduit
  vers aucune autre broche, dans aucun sens.
* **La source** est la broche restante. Un MOSFET N possède une diode
  interne source → drain : pointe **rouge sur la source**, pointe noire sur
  le drain, tu lis environ 0,5 V. Dans l'autre sens, rien.

Attention aussi : comme le drain est relié au dissipateur, **la patte
métallique est au potentiel de la cathode de la LED**. Ne la visse pas sur
quelque chose de conducteur relié à la masse.

---

## 5.5 Le câble du bouton ESC : le point le plus risqué du montage

Ton câble porte quatre fils : **+5 V, GND, GPIO14, GPIO15**. Le danger est
qu'un +5 V vienne toucher un fil de signal, par exemple lors d'un
branchement à chaud, d'un connecteur mal enfiché, ou d'un fil qui se
dessoude dans le boîtier.

### Protection recommandée, avec les résistances que tu as déjà

**a) Déplace la résistance de 2,2 kΩ côté macropad.**

Ta version actuelle la place dans le boîtier du bouton. Mets-la plutôt
juste à la sortie de GPIO15, sur la carte. Le fonctionnement est
rigoureusement identique, mais le fil du câble se retrouve **derrière** la
résistance : si du 5 V le touche, le courant qui atteint le GPIO est limité
à `(5 − 3,3) / 2200 = 0,77 mA`, ce que les diodes de protection internes de
l'ESP32 absorbent sans difficulté. Cette simple permutation transforme un
accident destructeur en non-événement.

**b) Ajoute 1 kΩ en série sur GPIO14, côté macropad.**

```
GPIO14 ---[1 kΩ]--- fil du câble --- contact ESC --- GND
```

Même raisonnement : un 5 V accidentel sur le fil ne fait plus passer que
`(5 − 3,3) / 1000 = 1,7 mA`. En fonctionnement normal, la résistance ne
gêne pas : le contact tire la ligne à la masse et le niveau bas mesuré
vaut environ 0,07 V, très loin du seuil de basculement.

**c) Choisis un connecteur détrompé** (JST, Molex, DIN…) qu'il est
impossible de brancher à l'envers ou décalé d'un cran. Et branche ou
débranche toujours **hors tension**.

Avec (a) + (b), ton câble devient tolérant aux fautes. Ce sont deux
résistances, tu les as.

---

## 5.6 Où mettre des condensateurs

Un condensateur de découplage est un petit réservoir d'énergie placé au
plus près d'un composant. Quand celui-ci consomme un pic de courant, il
puise dans le réservoir au lieu de faire chuter la tension de toute la
carte.

| Valeur | Où | Pourquoi | Indispensable ? |
|---|---|---|---|
| **100 nF** | entre VCC et GND du module **OLED**, au plus près de ses broches | un OLED qui se fige après plusieurs heures vient très souvent de là | non pour le prototype, oui pour la version définitive |
| **100 nF** | entre VCC et GND de **chaque TTP223** | stabilise le seuil de détection capacitive et supprime les faux touchers | non, mais fortement conseillé |
| **10 nF à 100 nF** | entre **GPIO14 et GND**, côté macropad | filtre les parasites captés par le câble du bouton ESC | seulement si tu constates des ESC fantômes |
| **10 à 47 µF** électrolytique, ≥ 10 V | entre **+5 V et GND dans le boîtier ESC** | évite un léger scintillement de la LED sur un câble long | seulement si tu observes le scintillement |
| **aucun** | sur **D+ / D− (GPIO19/20)** | un condensateur y déforme les signaux USB et casse l'énumération | **à ne jamais faire** |

**Le condensateur électrolytique a une polarité.** Une bande claire sur le
flanc marque la patte **négative**, qui va vers GND. À l'envers, il chauffe,
gonfle et finit par éclater. Les condensateurs céramiques de 100 nF, eux,
n'ont pas de polarité et se montent dans n'importe quel sens.

Ordre de grandeur pratique : le 100 nF traite les parasites rapides, le
10 µF traite les creux de tension lents. **Ils ne se remplacent pas l'un
l'autre**, ils se complètent.

---

## 5.7 Où mettre des diodes, et où ne surtout pas en mettre

### Diode classique (1N4148, 1N4007)

- **Pas nécessaire dans ce montage.** On met une diode de roue libre en
  parallèle d'un relais ou d'un moteur, parce qu'une bobine renvoie une
  surtension quand on la coupe. Une LED n'est pas une bobine : il n'y a
  rien à renvoyer.

- **Utile si un jour tu alimentes le macropad autrement que par l'USB** :
  une diode en série sur le + de l'alimentation externe protège contre une
  inversion de polarité. Coût : environ 0,7 V de chute (0,3 V avec une
  Schottky).

- **À ne pas faire** : mettre une diode en série avec le contact du bouton
  ESC en croyant le protéger. Elle empêcherait la ligne de descendre
  franchement à 0 V et le bouton deviendrait capricieux.

- Si tu veux un écrêtage sur GPIO14 sans zener, la version classique est
  deux diodes de signal (1N4148) : une de GPIO14 vers 3V3 (cathode côté
  3V3) et une de GND vers GPIO14 (cathode côté GPIO14). Combinées à la
  résistance de 1 kΩ du § 5.5, elles renvoient toute surtension vers
  l'alimentation. C'est exactement ce que font déjà les diodes internes de
  l'ESP32 : ce montage n'est utile que si tu veux une marge supplémentaire.

### Diode Zener

Une zener se monte **à l'envers** d'une diode normale : la cathode (bande)
vers le **plus**. Elle laisse passer dès que la tension dépasse sa valeur
nominale, ce qui plafonne la tension.

- **Usage possible ici** : une zener 3,3 V entre GPIO14 et GND, cathode
  côté GPIO14, **obligatoirement associée à la résistance série de 1 kΩ**
  du § 5.5.

- **Le piège** : une zener de 3,3 V n'est pas franche. À 3,3 V pile, elle
  conduit déjà un peu (quelques dizaines de microampères). Or la résistance
  de tirage interne de l'ESP32 vaut environ 45 kΩ et ne fournit que 73 µA :
  la zener pourrait tirer la ligne vers le bas et faire croire à un appui
  permanent. **Si tu montes cette zener, ajoute impérativement un tirage
  externe de 4,7 kΩ entre GPIO14 et 3V3**, qui fournit alors 700 µA et
  reprend le dessus.

- **Erreur fatale** : brancher une zener directement entre 3V3 et GND sans
  résistance série. Elle devient un court-circuit dès le seuil dépassé,
  chauffe et grille en quelques secondes.

- **Mon avis** : pour cette V0, la résistance série de 1 kΩ suffit
  largement. Garde tes zeners pour un montage où tu auras vraiment une
  source de tension supérieure à 3,3 V à maîtriser.

---

## 5.8 Vérification particulière à ta carte : le quartz 32 kHz sur GPIO15

Sur l'ESP32-S3, GPIO15 et GPIO16 sont aussi les broches prévues pour un
quartz horloger de 32,768 kHz (`XTAL_32K_P` et `XTAL_32K_N`). La plupart
des cartes de développement ne montent pas ce quartz, mais **certaines
oui**.

Si ta carte en possède un, GPIO15 est chargée par le quartz et ses
condensateurs : le signal PWM sera déformé, et le quartz peut souffrir.

**Comment vérifier en trente secondes**, sans rien souder :

1. Regarde la carte à côté du module : cherche un petit boîtier métallique
   allongé, souvent marqué `32.768` ou `32K`.
2. Ou fais le test logiciel, avant de câbler la LED :

```python
>>> from machine import Pin, PWM
>>> p = PWM(Pin(15), freq=2000, duty_u16=32768)
```

Branche provisoirement une LED ordinaire avec une résistance de 1 kΩ entre
GPIO15 et GND : elle doit s'allumer à mi-luminosité. Si rien ne se passe ou
si la carte se comporte bizarrement, GPIO15 est occupée.

**Solution de repli si GPIO15 est prise :** utilise **GPIO21**, **GPIO47**
ou **GPIO48** (vérifie sur la sérigraphie de ta carte que la broche est
libre et qu'elle n'est pas prise par la LED RGB de la carte). Il suffit
alors de changer une seule ligne dans `config.py` :

```python
LED_PIN = 21
```

---

## 5.9 Ordre de branchement recommandé

Ne câble jamais tout d'un coup. Cet ordre correspond exactement aux tests
de `docs/03-tests-progressifs.md` :

```
1. carte seule                    -> test 1
2. + OLED                         -> test 2
3. + les 4 switches               -> test 3
4. + les 2 TTP223                 -> test 4
5. + le contact ESC (sans LED)    -> test 5
6. + l'étage LED / BC547          -> test 6
7. seulement ensuite : le clavier -> test 7
```

À chaque étape : **débranche l'USB, câble, revérifie au multimètre,
rebranche, teste.** Si une étape échoue, tu sais exactement quel fil est en
cause, parce que c'est le seul que tu viens d'ajouter.

---

## 5.10 Consommation, et ce qu'on ne peut pas affirmer

| Élément | Ordre de grandeur |
|---|---|
| OLED SH1106 en 3,3 V | < 11 mA (annonce du fabricant) |
| 2 × TTP223 | quelques mA, davantage si le module porte un voyant |
| LED ESC via le BC547 | 8 mA en crête, environ 1,5 mA en moyenne avec le PWM |
| **Sous-total des périphériques** | **environ 20 à 25 mA** |

**Ce chiffre ne comprend pas la carte ESP32-S3 elle-même** : processeur,
PSRAM, régulateur, pont USB-série et voyants s'y ajoutent, et cela dépend
du modèle. Un port USB fournit au minimum 500 mA : on est très loin d'un
problème. Mais je ne peux pas t'annoncer une consommation totale mesurée
sans l'avoir mesurée. Si tu as un petit testeur USB à afficheur, branche-le
et tu auras la vraie valeur en trois secondes.
