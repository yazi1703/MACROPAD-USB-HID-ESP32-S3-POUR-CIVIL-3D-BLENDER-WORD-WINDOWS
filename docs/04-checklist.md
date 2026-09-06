# 4. Checklist finale

À cocher **sur ton matériel**. Rien ici ne peut être validé depuis un PC.
Suis l'ordre : chaque bloc suppose le précédent validé.

## Avant la première mise sous tension — multimètre, USB débranché

```
[ ] entre 3V3 et GND : pas de court-circuit
[ ] entre 5V et GND  : pas de court-circuit
[ ] entre 5V et 3V3  : pas de court-circuit
[ ] GPIO4/5/6/7 vers GND : continuité SEULEMENT quand on appuie sur B1..B4
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
[ ] profil Civil3D : les 4 commandes passent dans Civil 3D
[ ] profil Blender : G / R / S / Tab
[ ] profil Word : les 4 raccourcis
[ ] raccourcis Word adaptés si ton Word est en FRANÇAIS (Ctrl+G, pas Ctrl+B)
[ ] profil Windows : les 4 raccourcis
[ ] ESC fonctionne dans TOUS les profils
[ ] ESC interrompt bien une commande en cours d'écriture
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
