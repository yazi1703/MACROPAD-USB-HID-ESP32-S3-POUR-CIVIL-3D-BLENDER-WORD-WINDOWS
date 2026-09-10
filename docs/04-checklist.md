# 4. Checklist finale

À cocher **sur ton matériel**. Rien ici ne peut être validé depuis un PC.
Suis l'ordre : chaque bloc suppose le précédent validé.

## Avant la première mise sous tension — multimètre, USB débranché

```
[ ] entre 3V3 et GND : pas de court-circuit
[ ] entre 5V et GND  : pas de court-circuit
[ ] entre 5V et 3V3  : pas de court-circuit
[ ] GPIO4/5/6/7 vers GND : continuité SEULEMENT quand on appuie sur B1..B4
[ ] GPIO12/13 vers GND : continuité SEULEMENT quand on appuie sur B5 et B6
[ ] GPIO14 vers GND : continuité SEULEMENT quand on appuie sur ESC
[ ] rien n'est branché sur GPIO19 ni GPIO20
[ ] OLED alimenté en 3V3, PAS en 5V
[ ] les deux TTP223 alimentés en 3V3, PAS en 5V
[ ] pattes E/B/C du BC547 identifiées (datasheet ou multimètre)
[ ] anode de la LED identifiée, orientée vers la résistance de 330 Ω
[ ] résistance de 330 Ω bien présente en série avec la LED
[ ] résistance de 2,2 kΩ montée CÔTÉ MACROPAD, en sortie de GPIO15
[ ] résistance de 10 kΩ entre base et GND
[ ] résistance de 1 kΩ en série sur GPIO14
[ ] connecteur du câble ESC détrompé, impossible à décaler
[ ] quartz 32 kHz sur GPIO15 : absent (ou LED_PIN déplacé)
```

## Firmware et environnement

```
[ ] ESP32-S3 détecté par Windows
[ ] les deux ports USB-C identifiés (natif = HID, UART = flash et Thonny)
[ ] MicroPython installé (SPIRAM_OCT ou variante standard : les deux conviennent)
[ ] version >= 1.27.0  (INDISPENSABLE : bug des rapports HID vides sur PSRAM)
[ ] diag.run() affiche machine.USBDevice disponible : True
[ ] REPL fonctionnel dans Thonny
[ ] dossier /lib/usb/device/ présent avec ses quatre fichiers
[ ] fichiers du dossier device/ copiés à la RACINE de la carte
[ ] HID_ENABLED est resté à False jusqu'au test 7
```

## Écran

```
[ ] OLED détecté au scan I2C (0x3C ou 0x3D)
[ ] texte lisible et non décalé
[ ] le nom du profil apparaît en gros au changement, puis la liste revient
```

## Entrées

```
[ ] B1 fonctionnel      [ ] B2 fonctionnel
[ ] B3 fonctionnel      [ ] B4 fonctionnel
[ ] B5 fonctionnel      [ ] B6 fonctionnel
[ ] GPIO12 et GPIO13 libres sur ta carte (pas pris par la nappe caméra)
[ ] un appui franc = exactement 1 événement
[ ] maintien de 5 s = aucune répétition
[ ] TTP PREVIOUS fonctionnel, en mode momentané (pas bascule)
[ ] TTP NEXT fonctionnel, en mode momentané
[ ] doigt maintenu sur un TTP = 1 seul changement de profil
[ ] navigation circulaire OK dans les deux sens
[ ] ESC mécanique détecté
[ ] aucun ESC fantôme en bougeant le câble
```

## LED

```
[ ] LED éteinte pendant le RESET de la carte (rôle du 10 kΩ)
[ ] paliers 5 % / 20 % / 100 % bien distincts
[ ] LED froide au toucher, y compris à 100 %
[ ] résistance de 330 Ω froide au toucher
[ ] respiration fluide, sans à-coup ni scintillement
[ ] flash ESC visible, avec retour progressif à la respiration
```

## Clavier USB

```
[ ] périphérique USB HID reconnu (Gestionnaire de périphériques > Claviers)
[ ] le port COM du REPL reste accessible en même temps
[ ] HID_TEST = LETTER : une seule lettre « a » par appui
[ ] maintenir B1 n'écrit pas une deuxième lettre
[ ] HID_TEST = ESC : Échap fonctionne
[ ] HID_TEST = UNDO : Ctrl+Z fonctionne
[ ] Win+E ouvre l'Explorateur
[ ] Alt+Tab change de fenêtre ET relâche bien Alt
[ ] Ctrl+Maj+Échap ouvre le Gestionnaire des tâches
[ ] aucune touche modificatrice ne reste bloquée après une macro
```

## Disposition clavier

```
[ ] disposition Windows vérifiée (FRA ou ENG dans la barre des tâches)
[ ] KEYBOARD_LAYOUT aligné sur Windows
[ ] diag.keymap("_MATCHPROP") donne bien touche 37 sans Maj
[ ] _MATCHPROP écrit correctement, Verr. Maj ÉTEINT
[ ] _MATCHPROP écrit correctement, Verr. Maj ALLUMÉ   <- la correction n° 1
[ ] _HATCH écrit correctement
[ ] _ISOLATEOBJECTS écrit correctement
[ ] ENTER part bien après chaque commande
```

## Profils en situation réelle

```
[ ] profil Civil3D : les 6 commandes passent dans Civil 3D
[ ] profil Blender : G / R / S / Tab / E / Ctrl+Z
[ ] profil Word : les 6 raccourcis
[ ] raccourcis Word adaptés si ton Word est en FRANÇAIS (Ctrl+G, pas Ctrl+B)
[ ] profil Windows : les 6 raccourcis
[ ] ESC fonctionne dans TOUS les profils
[ ] ESC interrompt bien une commande en cours d'écriture
```

## Les trois gestes (V1)

```
[ ] appui court : la macro part AU RELÂCHEMENT, sans attente perceptible
    (sur une touche SANS macro « double appui »)
[ ] appui long : la macro part AU BOUT DE 400 ms, doigt encore appuyé
[ ] relâcher après un appui long n'envoie PAS la macro courte en plus
[ ] double appui : deux appuis rapides envoient bien la macro « double »
[ ] deux appuis lents envoient bien DEUX macros courtes
[ ] une touche sans macro longue ni double reste instantanée
[ ] GESTE_LONG_MS / GESTE_DOUBLE_MS ajustés à ton doigt si besoin
```

## Les combinaisons — deux touches ensemble (V1)

```
[ ] B4+B5 lance _PEDIT, et NI _PLINE NI _ISOLATEOBJECTS
[ ] B3+B6 ouvre les hachures
[ ] l'écran annonce la combinaison en gros, puis revient tout seul
[ ] B3 seule tape toujours F3 : le collecteur ne mange aucun appui
[ ] B3 maintenue lance toujours _ZOOM E au bout de 400 ms, SANS retard
[ ] ESC pendant que deux doigts descendent n'envoie QUE Échap
[ ] GESTE_COMBO_MS monté à 70 si les combinaisons t'échappent
```

## Les commandes AutoLISP de Civil 3D (V1)

```
[ ] macropad_tools.lsp chargé (APPLOAD -> Suite de démarrage)
[ ] le dossier est dans les chemins approuvés (TRUSTEDPATHS)
[ ] MPVIEWNEXT / MPVIEWPREV parcourent les vues enregistrées
[ ] MPLAYEROFF éteint bien le calque de l'objet désigné
[ ] MPLAYERRESTORE le rallume
[ ] les 4 commandes répondent encore après un redémarrage de Civil 3D
```

## La touche modificatrice — Civil 3D B2 (V1)

```
[ ] appui maintenu : Ctrl+clic ajoute bien à la sélection dans Civil 3D
[ ] appui bref puis maintenu : Maj+clic retire bien de la sélection
[ ] le modificateur descend SANS délai perceptible
[ ] au relâchement, plus rien n'est enfoncé (teste une frappe normale après)
[ ] ESC pendant un maintien : tout est relâché
[ ] changement de profil pendant un maintien : tout est relâché
[ ] câble débranché pendant un maintien : rien ne reste coincé au rebranchement
```

## LED RGB (V1)

```
[ ] docs/10-led-rgb.md lu EN ENTIER avant de brancher
[ ] type identifié : WS2812 (3 fils, DIN) ou RGB ordinaire (4 pattes)
[ ] SIX LED coupées du ruban — le rouleau entier tirerait 18 A, jamais sur la carte
[ ] coupé au MILIEU des pastilles, pas au ras d'une LED
[ ] sens respecté : on entre par DIN, dans le sens des flèches
[ ] soudures faites en moins de 5 s par pastille, fer à 300-320 °C
[ ] alimentées en 5 V (VBUS), PAS en 3,3 V
[ ] GND commun avec la carte
[ ] résistance 220 à 470 Ω en série sur le fil de données, côté LED
[ ] sa valeur VÉRIFIÉE au multimètre avant soudure (déjà vu : une « 150 » à 1 MΩ)
[ ] condensateur 470 µF entre 5 V et GND, au plus près du ruban
[ ] bande marquée du condensateur côté GND (à l'envers, il explose)
[ ] multimètre AVANT branchement : pas de court-circuit +5V / GND
[ ] branché dans l'ordre : GND, puis +5V, puis DIN en dernier
[ ] RGB_LUMINOSITE laissé à 40 (ou consommation mesurée si tu l'augmentes)
[ ] essai 0 : la LED déjà soudée sur la carte (GPIO48) répond au REPL
[ ] essai 1 : une LED câblée s'allume
[ ] essai 2 : diag.rgb() — les six s'allument une par une, et tu les as comptées
[ ] essai 3 : RGB_ENABLED = True, chaque profil a sa couleur
[ ] la touche pressée passe au blanc puis revient
[ ] les couleurs sont justes (sinon : RGB_ORDRE)
[ ] aucun scintillement (sinon : diode 1N4148 sur le VCC du ruban)
[ ] LA CARTE NE REDÉMARRE PAS quand toutes les LED sont allumées
[ ] le port COM ne disparaît pas en tapant, LED allumées
[ ] extinction après 5 minutes, réveil au premier appui
```

## L'écran tableau (V1)

```
[ ] les colonnes CRT / LNG / DBL sont lisibles
[ ] les libellés ne débordent pas
[ ] le tableau défile tout seul toutes les 2,5 s (6 touches, 4 lignes)
[ ] un appui fait SAUTER l'écran sur la bonne ligne et la surligne
[ ] la surbrillance s'efface après ~1,3 s et le défilement reprend
[ ] le surlignage marche aussi sur un geste SANS macro (ligne avec « - »)
[ ] contraste minimal après 3 min sans appui (SCREEN_DIM_MS)
[ ] écran éteint après 15 min sans appui (SCREEN_OFF_MS)
[ ] le premier appui réveille l'écran ET exécute sa macro
```

## Comportement global

```
[ ] SAFE MODE fonctionne (B1 maintenu pendant le RESET)
[ ] en SAFE MODE, aucune frappe possible même en appuyant partout
[ ] aucun bouton ne se répète involontairement
[ ] l'écran et la LED ne provoquent aucun raté d'entrée
[ ] débranchement / rebranchement : aucune macro ne repart toute seule
[ ] Ctrl-C dans Thonny : le port COM reste disponible  <- la correction n° 4
[ ] une macro juste après un changement de profil part bien <- correction n° 3
[ ] fonctionnement stable après plusieurs heures
```

## À surveiller dans la durée

```
[ ] l'OLED ne se fige pas après plusieurs heures
    (sinon : 100 nF entre VCC et GND du module)
[ ] pas de faux touchers sur les TTP223
    (sinon : 100 nF sur leur alimentation, éloigner les câbles)
[ ] pas de scintillement de la LED sur câble long
    (sinon : 10 à 47 µF entre 5 V et GND dans le boîtier ESC, polarité !)
```

## Mode configuration WiFi (V1)

```
[ ] AP_PASSWORD changé dans config.py (au moins 8 caractères)
[ ] B2 maintenu au RESET : l'écran affiche MODE CONFIG
[ ] le réseau WiFi MACROPAD apparaît
[ ] http://192.168.4.1 s'ouvre dans le navigateur
[ ] les 6 touches × 3 gestes de chaque profil s'affichent dans la page
[ ] une modification s'enregistre et survit au RESET
[ ] une macro volontairement fausse (CTRL+BIDON) est REFUSÉE avec un message
[ ] le bouton « Valeurs d'usine » ramène bien aux valeurs de profiles.py
[ ] en mode config, aucune touche n'est envoyée (le clavier n'existe pas)
[ ] profils.json sauvegardé sur le PC une fois la configuration au point
```

## Compagnon PC et détection automatique (V1)

```
[ ] py -m pip install pyserial : installé
[ ] py macropad_auto.py --simuler : la console suit bien les fenêtres
[ ] le script trouve le port natif tout seul (VID 0x303A)
[ ] Thonny est resté sur le port UART, pas sur le port natif
[ ] passer sur Civil 3D bascule le profil, l'écran affiche AUTO
[ ] le nom du fichier ouvert s'affiche en bas de l'écran
[ ] il DÉFILE quand il est trop long, et l'abrégé reste fixe à gauche
[ ] les deux TTP223 ensemble : LOCK s'affiche, le PC ne change plus rien
[ ] http://127.0.0.1:8765 s'ouvre, les modifications sont IMMÉDIATES
[ ] ajouter un logiciel dans la page : la détection le prend en compte
[ ] le compteur d'usage monte quand on tape (et survit à un RESET)
```

## Démarrage automatique du compagnon (V1)

```
[ ] demarrage_windows.bat, choix 1 : « Installe : ...Macropad.lnk »
[ ] le raccourci est bien visible dans Win+R -> shell:startup
[ ] après un redémarrage de Windows, le profil suit le logiciel sans rien lancer
[ ] pc/macropad_auto.log se remplit à chaque session
[ ] macropad débranché : le script attend au lieu de s'arrêter
[ ] macropad rebranché : reconnexion, profil et nom de fichier renvoyés
[ ] choix 2 : le raccourci disparaît et le compagnon ne démarre plus seul
```
