# 10. Les LED RGB sous les touches

> **À lire en entier avant de brancher.** Il y a ici une histoire de
> courant qui ne détruit rien, mais qui fait **redémarrer la carte en
> pleine frappe** — la panne la plus déroutante du projet.

---

## 10.1 D'abord : lesquelles as-tu ?

Il existe deux familles, et elles n'ont rien à voir. **Compte les pattes.**

| Ce que tu as | Famille | `RGB_TYPE` |
|---|---|---|
| Un ruban, un anneau, ou des pastilles reliées par 3 fils, avec des flèches et les repères **DIN / DO** | **WS2812** (adressable, « NeoPixel », SK6812…) | `"WS2812"` |
| Une LED seule à **4 pattes**, dont une plus longue | RGB ordinaire (anode ou cathode commune) | `"PWM"` |

La différence tient en une phrase : **une WS2812 contient une puce**, on
lui parle par un seul fil de données et chaque LED de la chaîne a sa
propre couleur. Une LED RGB ordinaire n'est que trois LED dans un même
boîtier : il faut **trois broches par LED**, donc dix-huit pour six
touches. Impossible ici.

> **Pour éclairer six touches, il te faut des WS2812.** Si tu n'as que des
> LED RGB ordinaires, le firmware sait quand même s'en servir : une seule
> couleur pour tout le macropad, celle du profil actif. C'est déjà utile,
> et ça se câble en dix minutes.

---

## 10.1 bis Le ruban ne répond à rien — la panne la plus fréquente

**Le symptôme typique :** la **première LED reste allumée** dès la mise
sous tension, d'une couleur fixe, et **aucune** ne réagit au code. Les
boucles de test défilent dans la console, le ruban ne bouge pas.

Ce n'est presque jamais le code. Dans une chaîne WS2812, **chaque LED
régénère le signal pour la suivante** : si la première ne décode rien,
tout le ruban est mort derrière elle. Les causes, par ordre de fréquence :

| Cause | Comment la reconnaître | Le test |
|---|---|---|
| **Le fil n'est pas sur la broche qu'on croit** | rien ne bouge, quelle que soit la couleur envoyée | `diag.rgb_pin()` balaie les broches plausibles |
| **Le fil entre par DOUT au lieu de DIN** | idem. Regarde les **flèches** imprimées sur le ruban | inverse les deux extrémités du ruban |
| **La première puce est grillée** | elle reste allumée, fixe, et bloque tout le reste | `diag.rgb_saute(1)` |
| **GND non commun** | comportement erratique, ou rien | relie le GND du ruban à celui de la carte |
| **Niveau logique 3,3 V sur un ruban en 5 V** | marche par intermittence, ou pas du tout | alimente le ruban en **3,3 V** pour vérifier, ou ajoute un level-shifter |

> ### ⚠️ Ce qui tue la première LED
>
> **Alimenter un ruban WS2812 dont le GND n'est PAS relié** force le
> courant de retour à passer par le **fil de données**. Ce fil n'est pas
> fait pour ça : la première puce le prend en pleine figure, et le GPIO de
> l'ESP32 en amont morfle aussi.
>
> Si tu as branché le +5 V avant le GND, ne cherche pas plus loin :
> teste `diag.rgb_saute(1)`. Si le ruban se réveille à partir de la
> deuxième LED, tu as ta réponse.
>
> **L'ordre de branchement est toujours le même : GND d'abord, données
> ensuite, +5 V en dernier.** Au débranchement, l'inverse.

### Le niveau logique, le piège discret

La fiche technique du WS2812B demande un « 1 » logique à **0,7 × VDD**.
Alimenté en 5 V, cela fait **3,5 V**. Or un GPIO d'ESP32 sort **3,3 V** au
maximum : on est **en dessous du seuil**.

En pratique ça marche sur beaucoup de rubans — mais pas sur tous, et
jamais de façon garantie. Si le tien est capricieux, deux solutions
simples avant d'acheter un level-shifter :

* **alimente le ruban en 3,3 V** au lieu de 5 V : le seuil descend à
  2,31 V et le GPIO le franchit largement. Les LED sont moins lumineuses,
  ce qui n'est pas gênant ici — on travaille déjà à 40/255 ;
* **sacrifie la première LED** : câble-la en 5 V comme les autres mais
  utilise-la uniquement comme **répéteur de niveau**, et fais commencer
  ton éclairage à la deuxième (`diag.rgb_saute(1)`).

---

## 10.1 ter La réserve d'appui — pourquoi la respiration ne monte pas à fond

Au repos, la couleur monte au plus à **`RGB_RESPIRATION_MAX` (0,55)**.
Tout ce qui reste au-dessus est **réservé à l'appui**.

Ce n'est pas de la coquetterie. Le plafond de courant s'applique **canal
par canal** : une couleur dont un canal vaut déjà 255 — le bleu de
CIVIL3D, par exemple — **touchait le plafond au sommet de la
respiration**. L'appui ne pouvait plus l'éclaircir ; il ne faisait que
monter les *autres* canaux, c'est-à-dire **délaver la couleur** au lieu de
l'éclairer.

| | Avant | Après |
|---|---|---|
| repos, sommet du cycle | `(0, 25, 40)` | `(0, 13, 21)` |
| appui | `(0, 40, 40)` | `(0, 25, 40)` |
| gain de lumière | **+23 %**, teinte délavée | **+91 %**, teinte inchangée |

Sur un **bleu pur** `(0, 0, 255)` — que le sélecteur de couleur de la page
web rend très facile à choisir — l'appui ne faisait **rien du tout**.

Les trois réglages vont ensemble :

```python
RGB_RESPIRATION_MIN = 0.25   # creux de la respiration
RGB_RESPIRATION_MAX = 0.55   # sommet AU REPOS ; le reste est la réserve
RGB_IMPULSION       = 0.45   # 0,55 + 0,45 = 1,00 : la couleur PLEINE
```

Un appui amène donc la touche **exactement à la couleur nominale du
profil**, où qu'on en soit dans le cycle. Prévisible, et sans changement
de teinte.

> **Si tu veux un pad plus lumineux au repos**, monte `RGB_RESPIRATION_MAX`
> — mais tu reprends d'autant la réserve de l'appui, et à `1.0` tu
> retrouves le défaut d'origine. Monte plutôt `RGB_LUMINOSITE`, en
> surveillant le courant (section 10.2).

La réserve existe **aussi quand `RGB_RESPIRATION = False`** : une couleur
figée se pose à `RGB_RESPIRATION_MAX`, pas à 1,0. Sans quoi couper la
respiration ramènerait exactement le même problème.

---

## 10.2 Le vrai danger : le courant

Une WS2812 en **blanc à fond** tire **60 mA**. Six touches :

```
6 × 60 mA = 360 mA   pour les LED seules
+ ~100 mA            la carte, l'écran, la LED du bouton ESC
--------------------
≈ 460 mA             pour 500 mA que fournit un port USB ordinaire
```

On est au bord. Et quand le 5 V s'effondre, l'ESP32-S3 redémarre : ton
clavier disparaît de Windows au milieu d'une commande.

**La parade est dans le code, pas dans ta discipline.** `rgb.py` plafonne
chaque canal à `RGB_LUMINOSITE` (40 sur 255 à la livraison) **avant**
l'envoi. Personne ne peut demander du blanc plein et faire redémarrer la
carte :

```
6 LED × 60 mA × (40/255) ≈ 56 mA
```

Un test le vérifie (`test_la_luminosite_plafonne_vraiment_le_courant`).
Si tu montes `RGB_LUMINOSITE`, mesure la consommation — un multimètre en
série sur le 5 V, en blanc sur toutes les touches.

---

## 10.2 bis Ton ruban : WS2812B 5050, 5 m, 60 LED/m

C'est exactement ce qu'il faut — mais **il y a 300 LED sur ce rouleau**, et
c'est la seule chose à ne pas oublier :

```
300 LED × 60 mA = 18 AMPÈRES en blanc plein
```

Dix-huit ampères. Un port USB en fournit un demi. **Ne branche jamais le
rouleau entier sur la carte** : au mieux la carte redémarre aussitôt, au
pire tu chauffes les pistes du ruban. Ce rouleau est prévu pour une
alimentation dédiée de plusieurs ampères, pas pour un macropad.

**Tu vas en couper six.** Six LED, à la luminosité livrée, tirent environ
56 mA : c'est le bon ordre de grandeur pour l'USB.

### Où couper

Entre chaque LED, le ruban porte une **ligne de coupe** : deux paires de
pastilles cuivrées et souvent un petit ciseau imprimé.

```
   ┌───────┬───────┬───────┬───────┐
   │  LED  ┃  LED  ┃  LED  ┃  LED  │      ┃ = ligne de coupe
   └───────┴───────┴───────┴───────┘          (coupe au MILIEU des
        ──────────►  sens des flèches          pastilles)
```

**Coupe au milieu des pastilles**, pas au ras d'une LED : les deux
morceaux gardent ainsi de quoi souder. Et **respecte le sens des
flèches** — on entre toujours par **DIN**, jamais par DO. Une chaîne
branchée à l'envers ne s'allume pas du tout, sans autre symptôme.

### Le petit décalage à connaître

À 60 LED/m, il y a une LED **tous les 16,7 mm**. Des switches mécaniques
sont espacés de **19,05 mm**. Sur six touches, l'écart s'accumule :

```
6 LED en ruban continu : 5 × 16,7 = 83,5 mm
6 touches               : 5 × 19,05 = 95,3 mm
                          ──────────────────
                          près de 12 mm d'écart
```

Deux façons de faire, et le choix t'appartient :

* **ruban continu, tel quel** — environ 2 mm de décalage par touche. Sous
  un diffuseur, ça ne se voit pas ; c'est de loin le plus simple ;
* **une LED par touche, séparées** — tu coupes les six LED une par une et
  tu les relies par trois fils courts (5V, DIN→DO, GND), à l'espacement
  exact de tes touches. Plus long, mais chaque LED est pile sous sa
  touche. C'est ce que font les claviers du commerce.

### Souder du 5050 sans le tuer

* **étame d'abord les pastilles**, ruban posé à plat, puis pose le fil
  déjà étamé dessus : le contact dure une seconde au lieu de cinq ;
* **5 secondes maximum** par pastille. La puce est dans le boîtier de la
  LED, à deux millimètres : c'est elle qui meurt en premier, et ça ne se
  voit qu'à l'allumage ;
* fer à **300-320 °C**, pas plus. Un fer trop froid oblige à insister,
  c'est pire ;
* **retire le film adhésif au dos avant de souder** l'endroit concerné :
  il fond et colle au fer.

### Le reste du rouleau

Garde-le. Mais retiens qu'il ne se branche **jamais** sur la carte :
il lui faut une alimentation 5 V de plusieurs ampères. C'est un autre
projet.

---

## 10.3 Câblage WS2812

> **Schéma complet : [`SCHEMA_LED_RGB.svg`](../SCHEMA_LED_RGB.svg)** — à
> ouvrir dans un navigateur, il est fait pour être lu pendant que tu
> soudes.

**Trois fils, trois composants.**

| Depuis | À travers | Vers |
|---|---|---|
| **VBUS (5 V)** | *(rien, ou la 1N4148 si scintillements)* | **+5V** du ruban |
| **GPIO17** | **une résistance de 220 à 470 Ω** | **DIN** du ruban |
| **GND** | — | **GND** du ruban |

Plus le **condensateur 470 µF entre +5V et GND**, soudé au plus près du
ruban.

```
   VBUS (5 V) ──┬──────────────► +5V du ruban
                │
             470 µF            (chimique : ATTENTION A LA POLARITE)
                │
   GND ─────────┴──────────────► GND du ruban
                                  (le GND doit être COMMUN, sans quoi
                                   le signal n'a aucune référence)

   GPIO17 ──── 220 à 470 Ω ────► DIN du ruban
              (au plus près de la première LED)
```

### Le montage, dans l'ordre

Fais-le dans cet ordre : chaque étape se vérifie avant la suivante.

1. **Coupe six LED** du rouleau, au milieu des pastilles, flèches
   repérées. Note de quel côté est **DIN**.
2. **Étame les trois pastilles d'entrée** (+5V, DIN, GND) : fer à
   300-320 °C, 5 secondes maximum par pastille.
3. **Soude trois fils** d'une quinzaine de centimètres, un par pastille.
   Repère-les tout de suite — rouge pour le 5 V, une autre couleur pour
   DIN, noir pour GND. Une erreur ici ne se voit plus une fois en place.
4. **Soude la résistance** sur le fil de DIN, **du côté du ruban**, pas
   du côté de la carte. N'importe quelle valeur entre **220 et 470 Ω**
   convient — 300, 320, 330, 390, 470 : prends celle que tu as. Elle ne
   règle aucun courant, elle amortit le signal ; c'est sa **longueur de
   patte**, pas sa valeur, qui compte. Une seule résistance vaut mieux
   que deux en série.
5. **Soude le condensateur 470 µF** entre les fils +5V et GND, lui aussi
   au plus près du ruban. **Sa bande marquée va sur le GND.**
6. **Multimètre, ruban NON branché** — vérifie qu'il n'y a **pas de
   court-circuit** entre le fil +5V et le fil GND. En position
   continuité, tu dois entendre un bip très bref (le condensateur qui se
   charge) puis plus rien. Un bip continu = court-circuit, cherche avant
   d'aller plus loin.
7. **Branche GND en premier**, puis +5V, puis DIN en dernier. C'est
   l'ordre qui protège le GPIO : jamais de données sur un ruban qui n'a
   pas déjà sa masse commune.
8. **Lance `diag.rgb()`** (§10.5) avant de toucher à `config.py`.

**Les quatre points qui comptent :**

1. **Le 5 V vient de VBUS, jamais du 3,3 V.** Le régulateur 3,3 V de la
   carte n'a pas la marge, et les WS2812 sont prévues pour 5 V.

2. **La résistance de 220 à 470 Ω sur le fil de données** amortit les
   réflexions du signal et protège le GPIO. Elle se place **côté LED**,
   pas côté carte, et le plus court possible.

   La valeur n'est pas critique du tout : contrairement à la résistance
   d'une LED ordinaire, elle ne fixe aucun courant. Tout ce qui est entre
   220 et 470 Ω fait le travail. **Une seule résistance vaut mieux que
   deux en série** : deux soudures de plus, une patte plus longue, sur un
   signal qui commute en quelques nanosecondes.

3. **Le condensateur de 470 µF entre 5 V et GND**, au plus près des
   LED. Elles commutent en quelques nanosecondes et tirent des pointes de
   courant ; sans ce réservoir local, les pointes se voient sur toute
   l'alimentation. **La patte marquée d'une bande est le moins : à
   l'envers, un chimique gonfle et explose.**

   *Quelle valeur ?* 470 µF est la valeur de référence. **100 µF suffit
   largement pour six LED** — le 1000 µF qu'on lit partout vise des
   rubans de cinquante ou cent LED, où les pointes sont dix fois plus
   grosses. Et si tu veux monter, des condensateurs **en parallèle
   s'additionnent** : trois 100 µF côte à côte font 300 µF.

4. **Le niveau logique.** Ton GPIO sort du 3,3 V ; une WS2812 alimentée
   en 5 V attend au moins 3,5 V pour un « 1 ». **On est juste en
   dessous.** Souvent ça marche, parfois les couleurs sautent au hasard.
   Le remède éprouvé, si tu observes des scintillements :

```
   VBUS (5 V) ──►|── VCC du ruban      diode 1N4148, bande vers le ruban
                1N4148
```

   La diode fait chuter environ 0,7 V : le ruban est alimenté en ~4,3 V,
   son seuil descend à 3,0 V, et ton 3,3 V passe largement. C'est le
   truc le plus simple et le plus fiable, et tu as les diodes.

   > **La limite de la 1N4148 :** c'est une diode de signal, bonne pour
   > environ **200 mA**. Six LED plafonnées par le firmware en tirent
   > ~56 mA, on est très à l'aise. Mais si un jour tu montes
   > `RGB_LUMINOSITE`, **c'est cette diode qui devient le maillon
   > faible** avant même l'USB : passe alors à une 1N4007 (1 A) ou une
   > Schottky 1N5819, qui a l'avantage de ne faire chuter que 0,3 V.

   **Ne la monte pas d'entrée.** Commence sans : sur du WS2812**B**, le
   3,3 V passe le plus souvent. Tu ne l'ajoutes que si `diag.rgb()` te
   montre des couleurs qui sautent.

**Ne branche jamais le fil de données sur des LED alimentées alors que la
carte est éteinte** : le courant entrerait par la diode de protection du
GPIO. Alimente les deux ensemble.

### Quelle broche ?

| Broche | Verdict |
|---|---|
| **17, 18, 21** | ✅ libres, sans aucune fonction spéciale — **GPIO17 est la valeur livrée** |
| **16** | ⚠️ utilisable, mais c'est `XTAL_32K_N` : à éviter si ta carte monte un quartz 32,768 kHz |
| 48 (ou 38) | ⚠️ souvent la LED RGB **déjà soudée** sur la carte — parfait pour un premier essai sans rien câbler |
| 0, 3, 45, 46 | ❌ broches de strapping |
| 19, 20 | ❌ USB — on n'y touche jamais |
| 26 à 37 | ❌ flash et PSRAM |
| 43, 44 | ❌ UART0, c'est ton REPL |

---

## 10.4 Câblage d'une LED RGB ordinaire (4 pattes)

**Trouve d'abord si elle est à anode ou à cathode commune**, au
multimètre en position test de diode :

* pointe **rouge** sur la patte longue, pointe noire sur une autre → si
  la LED s'allume faiblement, c'est une **anode commune** ;
* pointe **noire** sur la patte longue → si elle s'allume, c'est une
  **cathode commune**.

Puis renseigne `RGB_ANODE_COMMUNE` dans `config.py`.

```
  anode commune :   patte commune ──► 3,3 V
                    R ── 220 Ω ──► GPIO17
                    V ── 220 Ω ──► GPIO17
                    B ── 220 Ω ──► GPIO18

  cathode commune : patte commune ──► GND
                    (mêmes résistances, mêmes broches)
```

**Une résistance par couleur, jamais une seule sur la patte commune** :
les trois puces n'ont pas la même tension de seuil, et la couleur
changerait avec le nombre de canaux allumés. Ici chaque canal tire ~6 mA,
très loin des 40 mA que supporte un GPIO.

---

## 10.5 Les essais, dans l'ordre

**Essai 0 — sans rien câbler.** Beaucoup de cartes ESP32-S3 ont déjà une
WS2812 soudée, en général sur GPIO48. Au REPL :

```python
from machine import Pin
from neopixel import NeoPixel
np = NeoPixel(Pin(48), 1)
np[0] = (10, 0, 0); np.write()      # faible : 10 sur 255 suffit à voir
```

Si elle s'allume, tu sais que `neopixel` fonctionne sur ta carte.

> **Elle s'allume en VERT alors que tu as demandé du rouge ?** C'est
> normal, et c'est instructif : les WS2812 attendent les octets dans
> l'ordre **VERT, ROUGE, BLEU**. Le firmware s'en occupe (`RGB_ORDRE`),
> mais ce test brut, lui, écrit les octets tels quels.

**Essai 1 — une seule LED câblée.** Même code avec ta broche et ta LED.
Si rien ne s'allume : vérifie le GND commun, puis le sens du ruban (les
flèches vont **du DIN vers la suite**, on entre toujours par DIN).

**Essai 2 — les six, avec le test intégré.** Le firmware a un
diagnostic dédié, à lancer dans le REPL de Thonny :

```python
import diag
diag.rgb()
```

> **Tape ces deux lignes sans les `>>>`.** Le `>>>` est l'invite du REPL,
> Thonny l'affiche tout seul — le coller avec la commande donne
> `SyntaxError: invalid syntax`. C'est pour ça que les commandes de ce
> guide sont écrites sans invite.

Il fait trois choses, dans cet ordre :

1. **un chenillard** — les LED s'allument une par une, et il annonce
   chaque numéro. **Compte-les.** Si tu en as soudé six et qu'il s'en
   allume quatre, la donnée ne passe plus après la quatrième : reprends
   cette soudure ;
2. **rouge, puis vert, puis bleu** sur toutes. S'il annonce ROUGE et que
   tu vois du vert, note l'ordre réel et corrige `RGB_ORDRE` ;
3. **une montée en luminosité.** C'est ici que le courant se voit : si la
   carte redémarre pendant cette phase, c'est le condensateur qui manque
   ou l'alimentation qui ne suit pas.

Il éteint tout en partant, même si tu l'interromps par Ctrl-C, et il
n'initialise jamais le clavier USB : impossible qu'il tape quoi que ce
soit dans Thonny pendant que tu as les mains dans le montage.

**Essai 3 — le firmware.** Dans `config.py`, sur la carte :

```python
RGB_ENABLED = True
RGB_TYPE = "WS2812"
RGB_PIN = 17
RGB_COUNT = 6
```

RESET. Chaque profil doit prendre sa couleur, respirer doucement, et la
touche que tu presses passer au blanc un instant.

> **`RGB_ORDRE = "GRB"` est le bon réglage pour du WS2812B** : c'est
> l'ordre que ces puces attendent. Ne le change que si `diag.rgb()` te
> montre autre chose.

---

## 10.6 Ce que ça fait, une fois branché

| | |
|---|---|
| **Le pad prend la couleur du logiciel actif** | tu cliques dans Civil 3D, le pad devient bleu ; dans Blender, orange. C'est le compagnon PC qui dit quel logiciel est au premier plan, et la couleur suit toute seule |
| **La couleur respire** | elle monte et redescend en douceur sur 4 secondes, comme la LED du bouton ESC. Vivant, mais jamais clignotant |
| **La touche sur laquelle tu appuies s'intensifie** | **dès le front d'appui**, sans attendre de savoir quelle macro partira. Deux appuis coup sur coup montent deux fois plus haut, puis tout redescend en douceur |
| **Panne HID : tout passe au rouge** | tu le vois du coin de l'œil, sans lire le bandeau |
| **Extinction après 5 minutes** | `RGB_VEILLE_MS` — pour les yeux, pour les LED, et surtout pour le courant. Le premier appui rallume |

### Choisir les couleurs

**Depuis la page de configuration**, un carré de couleur à côté du titre de
chaque profil. Tu cliques, tu choisis, tu enregistres : c'est appliqué
tout de suite et rangé dans `profils.json` avec le reste. **C'est aussi
comme ça qu'un logiciel que tu ajoutes toi-même reçoit sa couleur.**

Les couleurs d'usine, elles, sont dans `RGB_COULEURS` (`config.py`) — ce
sont celles qu'on retrouve après un retour aux valeurs d'usine.

### Régler la réaction à l'appui

```python
RGB_IMPULSION = 1.0        # ce qu'un appui ajoute (1.0 = double la clarté)
RGB_IMPULSION_MAX = 3.0    # au-delà, ça ne monte plus
RGB_RETOMBEE_MS = 700      # durée du retour au calme, PAR unité
RGB_MS = 16                # ~60 rafraîchissements par seconde
```

Trois choix expliquent ce que tu ressens sous le doigt :

* **la LED réagit au front d'appui**, pas au départ de la macro. C'est
  important : une touche qui a un double appui attend `GESTE_DOUBLE_MS`
  (200 ms) avant de savoir quelle macro envoyer. Allumer la LED à ce
  moment-là donnait un quart de seconde de retard, parfaitement
  perceptible ;
* **l'impulsion s'ajoute** à ce qui reste de la précédente. Deux appuis
  rapides montent deux fois plus haut, dix appuis ne montent pas dix fois
  plus haut (`RGB_IMPULSION_MAX`) ;
* **elle s'ajoute aussi à la respiration** au lieu de la multiplier : un
  appui se voit autant en haut qu'en bas du cycle.

La retombée dure `RGB_RETOMBEE_MS` **par unité** : un appui redescend en
0,7 s, deux appuis en 1,4 s. Le plafond de courant, lui, reste celui de
`RGB_LUMINOSITE` quoi qu'il arrive — un test le vérifie en empilant vingt
appuis sur du blanc.

### Régler la respiration

```python
RGB_RESPIRATION = True       # False = couleur fixe
RGB_RESPIRATION_MS = 4000    # durée d'un cycle complet
RGB_RESPIRATION_MIN = 0.35   # luminosité au creux (jamais éteint)
```

C'est **la même courbe que la LED du bouton ESC** : `(1 - cos) / 2`,
élevée à la puissance 1,6. Elle s'attarde dans les valeurs basses et ne
fait que passer par le maximum — c'est ce qui donne une respiration
plutôt qu'un clignotement. Le plancher évite que le pad s'éteigne
complètement en bas de cycle.

Bonus qui ne se voit pas : **la respiration baisse le courant moyen**.
Une couleur qui passe son temps entre 35 % et 100 % consomme moins qu'une
couleur fixe à 100 %.

Et comme partout dans ce projet : **rien n'attend**. Les LED sont
rafraîchies au plus une fois toutes les 25 ms (`RGB_MS`), et seulement
quand quelque chose a changé. Une LED absente, mal câblée ou arrachée en
cours de route désactive l'affichage RGB et **n'empêche jamais le
macropad de taper**.

---

## 10.7 Si ça ne marche pas

**Regarde d'abord le REPL au démarrage.** Le firmware annonce ce qu'il
fait des LED, en une ligne :

```
RGB : 6 LED sur GPIO17, ordre GRB, luminosite 40/255
```

ou bien :

```
RGB : desactive (RGB_ENABLED = False dans config.py)
```

Cette seconde ligne est la cause n° 1 d'un ruban qui reste noir, et elle
n'a rien à voir avec ton câblage : **retéléverser le dossier `device/`
écrase le `config.py` de la carte** et remet `RGB_ENABLED` — comme
`HID_ENABLED` — à `False`. Vérification en deux secondes dans le REPL :

```
import config
print(config.RGB_ENABLED, config.RGB_ORDRE, config.HID_ENABLED)
```

| Symptôme | Cause probable |
|---|---|
| `RGB : desactive` au démarrage | `RGB_ENABLED = False` : `config.py` a été écrasé par un téléversement |
| Rien ne s'allume, et rien dans le REPL | `main.py` ne tourne pas : regarde s'il y a une erreur au démarrage |
| Rien ne s'allume | GND pas commun ; ou ruban branché par DO au lieu de DIN |
| `No module named 'neopixel'` | firmware MicroPython incomplet — reprends le binaire officiel |
| Les rouges sortent verts | ordre des octets : mets `RGB_ORDRE = "RGB"` (ou `"BGR"`) dans `config.py` |
| Les couleurs sautent au hasard | niveau de données trop juste : ajoute la diode 1N4148 sur le VCC du ruban (§10.3) |
| Ça scintille en même temps que la LED du bouton ESC | condensateur manquant sur le 5 V des LED |
| **La carte redémarre quand tout s'allume** | courant : `RGB_LUMINOSITE` trop haut, ou pas de condensateur. Redescends à 40 |
| Le port COM disparaît en tapant | même cause : le 5 V s'effondre. Baisse la luminosité avant toute autre piste |
| Seule la première LED s'allume | données coupées après la première : soudure du DO, ou LED morte |
