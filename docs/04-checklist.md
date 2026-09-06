# 4. Checklist finale

A imprimer ou a garder ouverte pendant le montage. Suivez l'ordre : chaque
bloc suppose le precedent valide.

## Firmware et environnement

```
[ ] ESP32-S3 detecte par Windows
[ ] les deux ports USB-C identifies (natif = HID, UART = flash et Thonny)
[ ] bon port USB identifie pour le flash
[ ] MicroPython installe, variante ESP32_GENERIC_S3-SPIRAM_OCT
[ ] version MicroPython >= 1.27.0  (INDISPENSABLE : bug HID sur cartes a PSRAM)
[ ] "Octal-SPIRAM" confirme par diag.info()
[ ] REPL fonctionnel dans Thonny
[ ] bibliotheque usb-device-keyboard installee dans /lib/usb/device
[ ] fichiers du firmware televerses a la racine de la carte
[ ] GPIO verifies (aucune broche de strapping, de flash, de PSRAM ni d'USB)
```

## Ecran

```
[ ] OLED detecte au scan I2C (0x3C ou 0x3D)
[ ] SH1106 affiche correctement, sans decalage horizontal
[ ] la vue a quatre cases est lisible
[ ] le nom du profil apparait en gros caracteres au changement
```

## Entrees

```
[ ] B1 fonctionnel
[ ] B2 fonctionnel
[ ] B3 fonctionnel
[ ] B4 fonctionnel
[ ] un appui franc = exactement 1 evenement
[ ] TTP PREVIOUS fonctionnel
[ ] TTP NEXT fonctionnel
[ ] doigt maintenu sur un TTP = 1 seul changement de profil
[ ] navigation circulaire des profils OK dans les deux sens
[ ] ESC mecanique detecte
```

## LED du bouton ESC

```
[ ] brochage E/B/C du BC547 verifie (datasheet ou multimetre) AVANT soudure
[ ] BC547 correctement cable (emetteur a la masse, collecteur vers la LED)
[ ] resistance 330 Ohm en serie avec la LED presente
[ ] resistance 2,2 kOhm sur la base presente
[ ] resistance 10 kOhm base-masse presente
[ ] LED eteinte pendant le reset de la carte (grace au 10 kOhm)
[ ] LED fonctionne sans chauffer anormalement, y compris a 100 %
[ ] resistance 330 Ohm froide au toucher
[ ] PWM fonctionne (paliers 5 / 20 / 50 / 100 % distincts)
[ ] respiration LED fonctionne, sans a-coup ni scintillement
[ ] flash ESC fonctionne, avec retour progressif a la respiration
```

## USB HID

```
[ ] peripherique USB HID reconnu par Windows (rubrique Claviers)
[ ] une lettre de test arrive dans le Bloc-notes
[ ] Escape fonctionne
[ ] Ctrl+Z fonctionne
[ ] Win+E fonctionne
[ ] Alt+Tab fonctionne et libere bien la fenetre
[ ] Ctrl+Shift+Echap ouvre le Gestionnaire des taches
[ ] aucune touche modificatrice HID ne reste bloquee apres une macro
```

## Disposition clavier

```
[ ] disposition Windows verifiee (FRA ou ENG dans la barre des taches)
[ ] KEYBOARD_LAYOUT de config.py aligne sur Windows
[ ] clavier FR AZERTY verifie : diag.test_keymap("_MATCHPROP") donne 0x25 / 0x00
[ ] _MATCHPROP ecrit correctement dans le Bloc-notes
[ ] _HATCH ecrit correctement
[ ] _ISOLATEOBJECTS ecrit correctement
```

## Profils en situation reelle

```
[ ] profil Civil3D fonctionnel (les 4 commandes passent dans Civil 3D)
[ ] profil Blender fonctionnel (G / R / S / Tab)
[ ] profil Word fonctionnel
[ ] profil Windows fonctionnel
[ ] raccourcis Word adaptes si votre Word est en francais (Ctrl+G au lieu de Ctrl+B)
```

## Comportement global

```
[ ] SAFE MODE fonctionne (B1 maintenu au demarrage)
[ ] en SAFE MODE, aucune touche n'est envoyee, meme en appuyant partout
[ ] aucun bouton ne se repete involontairement
[ ] OLED et LED ne ralentissent pas les entrees
[ ] ESC reste instantane meme pendant l'ecriture d'une commande longue
[ ] ESC interrompt bien la frappe en cours
[ ] main.py renomme et demarrage automatique valide
[ ] fonctionnement general stable apres plusieurs heures
```

## Points a surveiller sur la duree

```
[ ] l'OLED ne se fige pas apres plusieurs heures
    (si oui : ajouter un condensateur 100 nF sur son alimentation)
[ ] pas de declenchement capacitif parasite des TTP223
    (si oui : 100 nF sur leur alimentation, eloigner les cables)
[ ] pas de detection ESC parasite quand la LED clignote
    (si oui : pull-up externe 4,7 kOhm sur GPIO14)
```
