# 2. Cablage : verification du brochage, schemas et electronique

## 2.1 Verdict sur le brochage propose

**Aucune broche n'est a changer.** Votre proposition est valide sur une
ESP32-S3 N16R8. Voici la verification, broche par broche.

Contraintes de l'ESP32-S3 (source : documentation GPIO d'ESP-IDF, fichier
`docs/en/api-reference/peripherals/gpio/esp32s3.inc`) :

* *"GPIO26–GPIO32 are typically reserved for SPI flash and PSRAM"* ;
* *"When using Octal flash, Octal PSRAM, or both, GPIO33–GPIO37 connect to
  SPIIO4–SPIIO7 and SPIDQS"* — c'est le cas de la puce **R8** de votre carte :
  **GPIO33 a GPIO37 sont inutilisables chez vous** ;
* *"GPIO19 and GPIO20 are used by USB-JTAG by default"* : ce sont les lignes
  D- et D+ de l'USB natif ;
* broches de strapping (echantillonnees au reset) : **GPIO0, GPIO3, GPIO45,
  GPIO46** ;
* GPIO43 / GPIO44 = UART0, c'est le REPL de secours sur le port USB-serie.

| GPIO | Fonction retenue | Strapping ? | Flash/PSRAM ? | USB ? | Verdict |
|---|---|---|---|---|---|
| 4 | B1 (+ SAFE MODE) | non | non | non | **OK** |
| 5 | B2 | non | non | non | **OK** |
| 6 | B3 | non | non | non | **OK** |
| 7 | B4 | non | non | non | **OK** |
| 8 | OLED SDA | non | non | non | **OK** — c'est le SDA par defaut de MicroPython |
| 9 | OLED SCL | non | non | non | **OK** — c'est le SCL par defaut de MicroPython |
| 10 | TTP223 PROFIL PRECEDENT | non | non | non | **OK** |
| 11 | TTP223 PROFIL SUIVANT | non | non | non | **OK** |
| 14 | Switch ESC | non | non | non | **OK** |
| 15 | PWM LED ESC | non | non | non | **OK** (*) |
| 19 / 20 | USB D- / D+ | — | — | **oui** | **NE RIEN BRANCHER** |

(*) GPIO15 porte la fonction IO MUX `U0RTS`, mais MicroPython n'utilise aucun
controle de flux materiel sur l'UART0 : la broche est totalement libre en GPIO.

Precautions supplementaires pour ce type de carte :

* GPIO4 a GPIO7 sont des entrees ADC1 : aucune consequence en usage numerique ;
* n'utilisez pas GPIO0 (bouton BOOT) ni GPIO45 / GPIO46 pour de futures
  extensions : un niveau parasite au reset peut empecher le demarrage ;
* si vous ajoutez des touches plus tard, les broches libres et sures les plus
  evidentes sont **GPIO1, 2, 12, 13, 16, 17, 18, 21, 38, 39, 40, 41, 42, 47,
  48** (verifiez sur la serigraphie de votre carte : certaines exemplaires
  utilisent GPIO38 ou GPIO48 pour une LED RGB WS2812).

## 2.2 Les deux ports USB-C de la carte

Les cartes ESP32-S3 N16R8 de type DevKitC-1 possedent **deux ports USB-C** :

| Port | Relie a | Sert a |
|---|---|---|
| **USB natif / OTG** | directement au S3, GPIO19/GPIO20 | **le clavier HID**, et le REPL CDC |
| **USB-UART / COM** | a la puce pont USB-serie (CH343, CP2102 ou equivalent) puis a GPIO43/44 | flasher le firmware, REPL de secours |

Comment les distinguer sans documentation : debranchez tout, mettez la carte
sous tension par un seul port a la fois et regardez le Gestionnaire de
peripheriques Windows. Le port UART fait apparaitre un peripherique nomme
`USB-SERIAL CH343`, `Silicon Labs CP210x` ou similaire **meme sans firmware
MicroPython**. Le port natif, lui, n'apparait que lorsque MicroPython tourne
(sous la forme `Peripherique serie USB (COMx)`).

> **Conseil de developpement, tres utile ici :** branchez **les deux** ports en
> meme temps. Thonny se connecte au port UART (le REPL y est actif, voir
> `MICROPY_HW_ENABLE_UART_REPL` dans la recherche) pendant que le port natif
> fait le clavier. Vous evitez ainsi le desagrement de voir le port COM du
> REPL disparaitre a chaque `usb.device.get().init()`. Les deux ports partagent
> la meme masse via le PC, ce cablage est prevu par la carte.

## 2.3 Tableau de cablage final

| Signal | ESP32-S3 | Vers | Remarque |
|---|---|---|---|
| OLED VCC | 3V3 | OLED VCC | **3,3 V**, pas 5 V |
| OLED GND | GND | OLED GND | |
| OLED SDA | GPIO8 | OLED SDA | I2C, 400 kHz |
| OLED SCL | GPIO9 | OLED SCL | I2C, 400 kHz |
| B1 | GPIO4 | switch -> GND | pull-up interne, actif BAS |
| B2 | GPIO5 | switch -> GND | idem |
| B3 | GPIO6 | switch -> GND | idem |
| B4 | GPIO7 | switch -> GND | idem |
| TTP PRECEDENT VCC | 3V3 | TTP223 VCC | **3,3 V imperatif** |
| TTP PRECEDENT GND | GND | TTP223 GND | |
| TTP PRECEDENT OUT | GPIO10 | TTP223 OUT | actif HAUT |
| TTP SUIVANT VCC | 3V3 | TTP223 VCC | **3,3 V imperatif** |
| TTP SUIVANT GND | GND | TTP223 GND | |
| TTP SUIVANT OUT | GPIO11 | TTP223 OUT | actif HAUT |
| ESC signal | GPIO14 | switch ESC -> GND | pull-up interne, actif BAS |
| ESC LED | GPIO15 | 2,2 kOhm -> base BC547 | PWM 1 kHz |
| ESC +5 V | 5V (VBUS) | 330 Ohm -> LED | alimentation de la LED |
| ESC masse | GND | GND commun | **obligatoire** |

**Les TTP223 doivent etre alimentes en 3,3 V** : leur sortie suit leur tension
d'alimentation. En 5 V, la sortie monterait a 5 V sur un GPIO qui ne tolere pas
plus de 3,3 V et vous abimeriez le S3.

## 2.4 Schema ASCII complet

```
                    ESP32-S3 N16R8
                 +-------------------+
   USB-C natif ->| GPIO19 D-  GPIO20 |<- D+      (RESERVE USB, ne rien brancher)
                 |                   |
                 | 3V3           GND |
                 |  |             |  |
                 |  |             |  |
   OLED SH1106   |  |             |  |
   +---------+   |  |             |  |
   | VCC     |---+--+             |  |
   | GND     |----------------------+ |
   | SDA     |---| GPIO8            | |
   | SCL     |---| GPIO9            | |
   +---------+   |                  | |
                 |                  | |
   B1 o----------| GPIO4            | |
      |          |                  | |
   B2 o----------| GPIO5            | |
      |          |                  | |
   B3 o----------| GPIO6            | |
      |          |                  | |
   B4 o----------| GPIO7            | |
      |          |                  | |
      +----------+------------------+ |   (toutes les touches vers GND)
                 |                    |
   TTP223 PREV   |                    |
   +---------+   |                    |
   | VCC 3V3 |---+                    |
   | GND     |------------------------+
   | OUT     |---| GPIO10             |
   +---------+   |                    |
   TTP223 NEXT   |                    |
   +---------+   |                    |
   | VCC 3V3 |---+                    |
   | GND     |------------------------+
   | OUT     |---| GPIO11             |
   +---------+   |                    |
                 |  5V   GPIO14  GPIO15
                 +---|------|-------|-+
                     |      |       |
                     |      |       |          cable 4 conducteurs
   ==================|======|=======|====================================
                     |      |       |
                     |      |       |        BOITIER DU GROS BOUTON ESC
                     |      |       |
                    +5V     |       +---[ 2,2 kOhm ]---+---- B (base)
                     |      |                          |
                 [330 Ohm]  |                       [10 kOhm]
                     |      |                          |
                   LED 1 W  |                          |
                  (anode)   |                          |
                     |      |                          |
                     |      |     BC547 (NPN)          |
                     +------|------ C (collecteur)     |
                            |         |                |
                            |       E (emetteur)       |
                            |         |                |
                            |         |                |
    switch ESC  o-----------+         |                |
                |                     |                |
                +---------------------+----------------+---- GND commun
```

Vue simplifiee du seul etage LED :

```
   +5 V (VBUS USB)
        |
      [330 R]          <- limite le courant a ~8 mA (LED rouge)
        |
       LED 1 W
        |
        C
   B --|<  BC547 (NPN)
        E
        |
       GND

   GPIO15 ---[2k2]--- B
                       |
                     [10k]
                       |
                      GND
```

## 2.5 Verification electrique du montage BC547 + LED

Le montage est **correct**. Voici pourquoi, chiffres a l'appui.

### Courant dans la LED

La LED est en collecteur commun bas ("low-side switch"), ce qui est la bonne
topologie avec un NPN.

Avec une LED **rouge** (Vf ~ 2,1 V) et un BC547 sature (Vce_sat ~ 0,2 V) :

```
I = (5 V - 2,1 V - 0,2 V) / 330 Ohm = 2,7 / 330 = 8,2 mA
```

* Puissance dissipee dans la LED : 8,2 mA x 2,1 V = **17 mW**, sur une LED
  prevue pour 1 W. Elle ne chauffera pas, meme legerement. C'est exactement
  l'usage "veilleuse" que vous vouliez.
* Puissance dans la resistance : (8,2 mA)^2 x 330 = **22 mW** -> une resistance
  1/4 W convient largement.
* Duree de vie : a 3 % du courant nominal, elle est pratiquement illimitee.

Avec une LED **blanche, bleue ou verte** (Vf ~ 3,2 V) :

```
I = (5 - 3,2 - 0,2) / 330 = 4,8 mA
```
Cela reste visible mais nettement plus faible. Si le rendu vous parait trop
sombre, descendez a **220 Ohm** (~7,3 mA) ou **150 Ohm** (~10,7 mA) : on reste
tres loin du 1 W et de tout echauffement.

### Commande de la base

```
Ib = (3,3 V - 0,7 V) / 2200 Ohm = 1,18 mA
```
dont environ 0,07 mA part dans la resistance de 10 kOhm (0,7 V / 10 k), soit
**Ib utile ~ 1,11 mA**.

Pour saturer franchement un transistor, on vise un gain force d'environ 10 :

```
Ib necessaire = 8,2 mA / 10 = 0,82 mA     <     1,11 mA disponible
```

Le transistor est donc bien sature, avec de la marge. Le GPIO ne fournit que
1,18 mA, tres loin de sa limite (40 mA sur ESP32-S3).

La resistance de **10 kOhm entre base et masse est utile** : elle garantit que
le transistor reste bloque quand le GPIO est en haute impedance, c'est-a-dire
pendant le reset et le boot de l'ESP32. Sans elle, la LED pourrait s'allumer
brievement au demarrage. Gardez-la.

### Limites a respecter (BC547)

| Parametre | Limite BC547 | Notre usage | Marge |
|---|---|---|---|
| Ic max | 100 mA | 8,2 mA | x12 |
| Vce max | 45 V | 5 V | x9 |
| Puissance | 500 mW | 8,2 mA x 0,2 V = 1,6 mW | x300 |

Aucun radiateur, aucune precaution thermique.

### Brochage du BC547 : A VERIFIER AVANT DE SOUDER

**Je ne vous donnerai pas l'ordre des pattes de memoire.** Le brochage d'un
boitier TO-92 varie selon le fabricant et la reference, et une inversion
collecteur/emetteur produit un montage qui a l'air de fonctionner tout en
degradant le transistor.

Faites l'une de ces trois verifications :

1. **Lisez le marquage** sur la face plate du boitier (par exemple `BC547B`,
   `BC547C`, suivi d'un code fabricant) et cherchez la fiche technique
   correspondante ;
2. **testez au multimetre** en position "test de diode" : sur un NPN, la base
   est la seule patte qui conduit vers les deux autres quand la pointe rouge
   (+) est dessus ;
3. **dites-moi la reference exacte et le marquage complet** et je vous indique
   le brochage sur cette base.

Le brochage le plus courant pour un BC547 en TO-92, face plate vers vous et
pattes vers le bas, est C-B-E de gauche a droite — **mais ne cablez pas sur
cette phrase seule, verifiez d'abord.**

### Le cable a 4 conducteurs

Vos 4 conducteurs (+5 V, GND, GPIO14, GPIO15) suffisent, le montage est bon.

Un point d'attention : la ligne ESC (GPIO14) est en haute impedance (le pull-up
interne de l'ESP32 vaut environ 45 kOhm) et elle chemine a cote d'un signal PWM
a 1 kHz. Sur un cable long, une diaphonie est theoriquement possible.

**Solution recommandee, sans condensateur** (vous n'en avez pas de 100 nF) :
ajoutez une **resistance de 4,7 kOhm entre GPIO14 et +3,3 V**, cote macropad.
Ce pull-up externe rend la ligne environ dix fois plus "raide" que le pull-up
interne et supprime le probleme. L'anti-rebond logiciel de 15 ms fait le reste.

Si vous avez un condensateur de 1 nF a 100 nF sous la main, un exemplaire entre
GPIO14 et GND, cote carte, apporte le meme benefice.

## 2.6 Liste exacte des resistances necessaires

| Quantite | Valeur | Role | Obligatoire ? |
|---|---|---|---|
| 1 | **330 Ohm** (1/4 W) | limitation du courant de la LED ESC | **oui** |
| 1 | **2,2 kOhm** | resistance de base du BC547 | **oui** |
| 1 | **10 kOhm** | maintien de la base a la masse (blocage au boot) | fortement conseillee |
| 1 | 4,7 kOhm | pull-up externe de la ligne ESC (anti-diaphonie du cable) | conseillee si cable > 50 cm |

Variantes possibles pour le 330 Ohm : 220 Ohm ou 150 Ohm si votre LED est
blanche / bleue et vous parait trop sombre.

**Aucune autre resistance n'est necessaire** : les quatre touches, le bouton
ESC et les deux TTP223 utilisent les pull-up/pull-down internes de l'ESP32-S3
(configures par le firmware dans `inputs.py`).

## 2.7 Alimentation et consommation

Tout est alimente par l'USB du PC (500 mA disponibles au minimum).

| Element | Consommation typique |
|---|---|
| ESP32-S3, Wi-Fi et BLE inactifs | 40 a 60 mA |
| OLED SH1106 1,3", en 3,3 V | < 11 mA (annonce constructeur) |
| 2 x TTP223 | ~ 2 x 3 mA au repos |
| LED ESC via BC547 | 8 mA en crete, **~ 1,5 mA en moyenne** (PWM 4-25 %) |
| **Total** | **environ 75 a 90 mA** |

C'est tres confortable pour un port USB. La LED, en particulier, consomme en
moyenne moins qu'une diode temoin classique grace au PWM.

### A propos des condensateurs de 100 nF

**Le prototype fonctionne sans.** Vous n'avez pas besoin d'en acheter pour
commencer :

* la carte ESP32-S3 possede deja ses propres condensateurs de decouplage ;
* les modules OLED et TTP223 du commerce en integrent generalement un ;
* les courants en jeu sont faibles et il n'y a aucune commutation rapide de
  puissance.

Pour la **version definitive**, si vous en achetez, placez-en :

1. **un 100 nF entre VCC et GND du module OLED**, au plus pres de ses broches :
   c'est le peripherique le plus sensible aux micro-coupures d'alimentation
   (un OLED qui se fige apres plusieurs heures vient souvent de la) ;
2. **un 100 nF sur chaque TTP223**, entre VCC et GND, pour stabiliser le seuil
   de detection capacitive et eviter les declenchements parasites ;
3. eventuellement **un 10 uF electrolytique sur le +5 V** dans le boitier du
   bouton ESC, si vous constatez un scintillement de la LED lors des appuis.

Aucun de ces trois n'est necessaire au fonctionnement, ce sont des ameliorations
de fiabilite a long terme.
