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

## 10.3 Câblage WS2812

```
   VBUS (5 V) ──┬──────────────► VCC / 5V du ruban
                │
             470 µF            (chimique : ATTENTION A LA POLARITE)
                │
   GND ─────────┴──────────────► GND du ruban
                                  (le GND doit être COMMUN, sans quoi
                                   le signal n'a aucune référence)

   GPIO16 ──── 330 à 470 Ω ────► DIN du ruban
              (au plus près de la première LED)
```

**Les quatre points qui comptent :**

1. **Le 5 V vient de VBUS, jamais du 3,3 V.** Le régulateur 3,3 V de la
   carte n'a pas la marge, et les WS2812 sont prévues pour 5 V.

2. **La résistance de 330 à 470 Ω sur le fil de données** amortit les
   réflexions du signal et protège le GPIO. Elle se place **côté LED**,
   pas côté carte.

3. **Le condensateur de 470 à 1000 µF entre 5 V et GND**, au plus près
   des LED. Elles commutent en quelques nanosecondes et tirent des
   pointes de courant ; sans ce réservoir local, les pointes se voient
   sur toute l'alimentation. Tu en as → mets-en un. **La patte marquée
   d'une bande est le moins : à l'envers, un chimique gonfle et explose.**

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

**Ne branche jamais le fil de données sur des LED alimentées alors que la
carte est éteinte** : le courant entrerait par la diode de protection du
GPIO. Alimente les deux ensemble.

### Quelle broche ?

| Broche | Verdict |
|---|---|
| **16, 17, 18, 21** | ✅ libres, sans fonction spéciale — **GPIO16 est la valeur livrée** |
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
                    R ── 220 Ω ──► GPIO16
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

**Essai 2 — les six.**

```python
np = NeoPixel(Pin(16), 6)
for i in range(6):
    np[i] = (0, 10, 0); np.write()     # une par une, en rouge faible
```

**Essai 3 — le firmware.** Dans `config.py`, sur la carte :

```python
RGB_ENABLED = True
RGB_TYPE = "WS2812"
RGB_PIN = 16
RGB_COUNT = 6
```

RESET. Chaque profil doit prendre sa couleur, et la touche que tu presses
passer au blanc un instant.

---

## 10.6 Ce que ça fait, une fois branché

| | |
|---|---|
| **Une couleur par profil** | tu sais où tu es sans lire l'écran : Civil 3D en bleu, Blender en orange, Word en bleu foncé, Windows en vert |
| **La touche utilisée passe au blanc** | le même retour visuel que la surbrillance de l'écran, pendant `HIGHLIGHT_MS` |
| **Panne HID : tout passe au rouge** | tu le vois du coin de l'œil, sans lire le bandeau |
| **Extinction après 5 minutes** | `RGB_VEILLE_MS` — pour les yeux, pour les LED, et surtout pour le courant. Le premier appui rallume |

Les couleurs se changent dans `RGB_COULEURS`, dans `config.py`.

Et comme partout dans ce projet : **rien n'attend**. Les LED sont
rafraîchies au plus une fois toutes les 25 ms (`RGB_MS`), et seulement
quand quelque chose a changé. Une LED absente, mal câblée ou arrachée en
cours de route désactive l'affichage RGB et **n'empêche jamais le
macropad de taper**.

---

## 10.7 Si ça ne marche pas

| Symptôme | Cause probable |
|---|---|
| Rien ne s'allume | GND pas commun ; ou ruban branché par DO au lieu de DIN |
| `No module named 'neopixel'` | firmware MicroPython incomplet — reprends le binaire officiel |
| Les rouges sortent verts | ordre des octets : mets `RGB_ORDRE = "RGB"` (ou `"BGR"`) dans `config.py` |
| Les couleurs sautent au hasard | niveau de données trop juste : ajoute la diode 1N4148 sur le VCC du ruban (§10.3) |
| Ça scintille en même temps que la LED du bouton ESC | condensateur manquant sur le 5 V des LED |
| **La carte redémarre quand tout s'allume** | courant : `RGB_LUMINOSITE` trop haut, ou pas de condensateur. Redescends à 40 |
| Le port COM disparaît en tapant | même cause : le 5 V s'effondre. Baisse la luminosité avant toute autre piste |
| Seule la première LED s'allume | données coupées après la première : soudure du DO, ou LED morte |
