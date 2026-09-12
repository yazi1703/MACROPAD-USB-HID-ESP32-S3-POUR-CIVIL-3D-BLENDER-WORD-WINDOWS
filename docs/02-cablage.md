# 2. Cablage : verification du brochage et schemas

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
| 12 | B5 | non | non | non | **OK** (*) |
| 13 | B6 | non | non | non | **OK** (*) |
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

(*) GPIO12 et GPIO13 sont les deux broches ajoutees pour passer de quatre a
six touches. Elles n'ont ni strapping, ni flash, ni PSRAM, ni USB. **Verifie
tout de meme sur ta carte** qu'elles ne sont pas prises par le connecteur
camera : sur ce type de clone, la nappe camera occupe plusieurs GPIO. Replis
surs en cas de conflit : GPIO1, GPIO2, GPIO21, GPIO47, GPIO48. Il suffit alors
de changer un numero dans `BUTTON_PINS` (config.py), rien d'autre.

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
| B1 | GPIO4 | switch -> GND | pull-up interne, actif BAS — **pouce** |
| B2 | GPIO5 | switch -> GND | idem — **index** |
| B3 | GPIO6 | switch -> GND | idem — **index**, 2e touche |
| B4 | GPIO7 | switch -> GND | idem — **majeur** |
| B5 | GPIO12 | switch -> GND | idem — **annulaire** |
| B6 | GPIO13 | switch -> GND | idem — **auriculaire** |
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

### Quel doigt sur quelle broche — a ne pas melanger

Le pad est sous la main **GAUCHE** : le pouce est a DROITE du groupe,
l'auriculaire a GAUCHE. Vu d'au-dessus, du bord gauche vers le bord droit :

```
   gauche  <───────────── main GAUCHE ─────────────>  droite
     B6          B5          B4        B3   B2       B1
   GPIO13      GPIO12      GPIO7    GPIO6 GPIO5    GPIO4
  auriculaire  annulaire   majeur      index       pouce
```

Ce n'est pas qu'une question d'ordre a l'ecran. Les **combinaisons** sont
choisies sur cette geometrie : « deux doigts voisins » pour les vues,
« on saute un doigt » pour les calques. Inverser deux fils rend ces
raccourcis illogiques, et le firmware ne peut pas le deviner. Si tu soudes
autrement, corrige `BUTTON_PINS` **et** `DOIGTS` dans `config.py` — les
deux vont ensemble.

> **Avant de souder, une verification de trente secondes.** Dans le REPL :
>
>     import diag
>     diag.broches()
>
> Elle dit, pour chaque broche declaree, si elle est libre, deconseillee
> ou **reservee** par la flash, la PSRAM ou l'USB — une broche reservee
> n'est meme pas lue, car creer un `Pin` sur la flash suffit a faire
> tomber la carte. Puis elle affiche l'etat des entrees en continu : tu
> touches la broche avec un fil relie a GND, son niveau doit passer de 1 a
> 0. Elle liste aussi les broches encore disponibles, en cas de conflit.

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
   B1 o----------| GPIO4            | |   pouce
      |          |                  | |
   B2 o----------| GPIO5            | |   index
      |          |                  | |
   B3 o----------| GPIO6            | |   index (2e touche)
      |          |                  | |
   B4 o----------| GPIO7            | |   majeur
      |          |                  | |
   B5 o----------| GPIO12           | |   annulaire
      |          |                  | |
   B6 o----------| GPIO13           | |   auriculaire
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

## 2.5 Electronique : voir le document dedie

Tout ce qui concerne l'electronique proprement dite est regroupe dans
**[`05-electronique.md`](05-electronique.md)** :

* les trois regles d'or et le tableau des pannes destructrices ;
* les verifications au multimetre **avant** la premiere mise sous tension ;
* comment identifier les pattes E/B/C du BC547 et l'anode de la LED ;
* le calcul complet du montage (8,2 mA dans une LED prevue pour 1 W) ;
* la protection du cable deporte : **2,2 kOhm cote macropad** et **1 kOhm en
  serie sur GPIO14** ;
* ou placer condensateurs, diodes et diodes Zener, et ou surtout pas ;
* la verification du quartz 32 kHz eventuel sur GPIO15.

Liste des resistances a prevoir :

| Quantite | Valeur | Role |
|---|---|---|
| 1 | **330 Ohm** 1/4 W | limitation du courant de la LED ESC |
| 1 | **2,2 kOhm** | resistance de base du BC547, **a monter cote macropad** |
| 1 | **10 kOhm** | maintien de la base a la masse pendant le boot |
| 1 | **1 kOhm** | protection en serie sur l'entree GPIO14 |

Variantes : 220 Ohm ou 150 Ohm au lieu de 330 Ohm si ta LED est blanche ou
bleue et te parait trop sombre.
