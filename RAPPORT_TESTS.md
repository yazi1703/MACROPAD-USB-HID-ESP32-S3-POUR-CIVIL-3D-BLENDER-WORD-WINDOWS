# Rapport de vérification — 6 septembre 2026

**Résultat : 38 tests PC réussis ; 16 fichiers Python compilés avec succès.**

> **Mise à jour après relecture.** Le projet a été relu, neuf corrections y ont
> été apportées (voir `docs/06-corrections.md`) et **14 tests supplémentaires**
> ont été écrits, au moins un par correction.
>
> Ces nouveaux tests ont été exécutés contre la version d'origine du firmware :
> **12 des 14 échouent**, ce qui établit que chaque défaut était réel. Les deux
> restants passaient déjà et servent de garde-fou anti-régression.

## Exécuté réellement dans cet environnement

- Compilation syntaxique des 16 fichiers du firmware avec CPython.
- Compilation des mêmes 16 sources avec `mpy-cross` : MicroPython v1.29.0, compilation de l'outil datée 2026-08-29, format .mpy v6.3. Distribution PC utilisée : mpy-cross 1.29.0.post2. Les .mpy de vérification ne sont pas distribués : transférer les .py lisibles.
- 24 tests unitaires et d'intégration simulée (voir sortie ci-dessous).
- Lecture des API dans les fichiers officiels réellement inclus.
- Vérification des empreintes des quatre fichiers USB et du driver SH1106 ; driver SH1106 identique au commit figé.
- Schéma SVG rendu en PNG et inspecté visuellement.

## Ce que couvrent les tests PC

Navigation dans les deux sens ; anti-rebond, rebonds et maintien ; démarrage avec touche tenue ; retour circulaire des ticks ; 26 lettres FR, underscore, macros et ENTER ; Caps Lock ; refus atomique d'un texte non pris en charge ; pressions/relâchements de Ctrl+Shift+Esc ; ESC au milieu d'Alt+Tab/texte ; endpoint occupé sans perte immédiate ; file bornée ; déconnexion sans reprise de macro ; faute et timeout avec annulation/libération ; respiration, flash et passage des ticks ; SAFE MODE sans initialisation HID et retour REPL ; absence/panne OLED ; une page transmise par tick ; boucle main simulée avec macro Civil3D, NEXT et ESC ; rapports de huit octets produits par la classe officielle KeyboardInterface.

Les GPIO, l'horloge, le PWM et le transport USB sont simulés. Le test d'absence d'OLED exerce le chemin d'initialisation indisponible ; le test de déconnexion OLED injecte une OSError lors d'une écriture. Le test des octets HID appelle le sérialiseur officiel mais remplace la transmission USB.

## Vérification documentaire / statique seulement

Support machine.USBDevice sur le port ESP32 du tag 1.29.0 ; sélection SPIRAM_OCT ; broches du S3 et cohérence du pinout photo ; calcul de courant LED/base ; méthodes PWM/I2C et conservation CDC ; reprise des licences.

## Non exécuté — à faire sur le matériel

Aucun ESP32-S3 ni PC Windows cible n'était accessible. Pas de flash de carte, pas d'énumération HID, pas de mesure de latence ou de consommation, pas de validation du SH1106 réel ni des TTP, pas d'essai Thonny USB physique, pas de test applicatif Civil3D/Blender/Word. La compilation complète ESP-IDF du firmware n'a pas été effectuée ; le binaire recommandé est celui du site officiel. Concernant l'issue HID #18098 : les notes de version officielles de MicroPython **v1.27.0** annoncent explicitement « *a fix for blank USB HID reports on boards with PSRAM* », ce qui correspond exactement au symptôme signalé et exactement à une carte N16R8. La version 1.29.0 retenue est postérieure à ce correctif. Cela reste une preuve documentaire, pas une preuve matérielle : commencer malgré tout par le test LETTER.

## Reproduire les tests sur PC

Depuis le dossier du projet :

```bash
python -m unittest discover -s tests -v
```

Ces tests ne nécessitent pas de carte et ne tapent aucune touche sur le PC. Ils utilisent unittest fourni avec Python. Les logs « ERREUR CRITIQUE », « file pleine » et « OLED désactivé » ci-dessous proviennent des pannes injectées intentionnellement.

## Sortie des tests

```text
test_azerty_all_letters ... ok
test_bounce_hold_release ... ok
test_breath_and_flash ... ok
test_busy_does_not_lose_event ... ok
test_capslock_digits_fr ... ok
test_capslock_mapping ... ok
test_capslock_underscore_fr ... ok
test_capslock_us_only_affects_letters ... ok
test_close_after_macro_leaves_nothing_pressed ... ok
test_close_keeps_usb_when_nothing_pressed ... ok
test_combo_accepts_digits_and_symbols ... ok
test_commands_typable_with_capslock_on ... ok
test_disconnect_discards_queue ... ok
test_esc_fast_edge_held_at_boot ... ok
test_esc_fast_edge_is_immediate ... ok
test_escape_preempts_modifier_and_text ... ok
test_extended_characters ... ok
test_fault_releases_without_resume ... ok
test_input_order_is_deterministic ... ok
test_invalid_text_atomic ... ok
test_led_wrap ... ok
test_macros_valid_and_enter ... ok
test_main_cooperative_integration ... ok
test_oled_absent_nonfatal ... ok
test_oled_transfer_failure_disables_only_display ... ok
test_oled_transmits_one_page_per_tick ... ok
test_press_release_every_combo ... ok
test_profiles_all_directions ... ok
test_queue_limit ... ok
test_safe_mode_main_returns_to_repl ... ok
test_safe_mode_never_initializes_hid ... ok
test_shortcut_uses_physical_key_not_character ... ok
test_start_held ... ok
test_submit_accepted_right_after_cancel ... ok
test_submit_accepted_right_after_escape ... ok
test_ticks_wrap ... ok
test_timeout_cancels_pending ... ok
test_vendor_report_bytes ... ok

----------------------------------------------------------------------
Ran 38 tests

OK
```
