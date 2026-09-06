# Rapport de vérification — 6 septembre 2026

**Résultat : 113 tests PC réussis ; 21 fichiers Python compilés avec succès.**

> **Mise à jour après relecture.** Le projet a été relu, neuf corrections y ont
> été apportées (voir `docs/06-corrections.md`) et **14 tests supplémentaires**
> ont été écrits, au moins un par correction.
>
> Ces nouveaux tests ont été exécutés contre la version d'origine du firmware :
> **12 des 14 échouent**, ce qui établit que chaque défaut était réel. Les deux
> restants passaient déjà et servent de garde-fou anti-régression.

## Exécuté réellement dans cet environnement

- Compilation syntaxique des **21 fichiers** du firmware avec CPython (`python3 -m py_compile device/*.py device/lib/usb/device/*.py`).
- Compilation des 16 sources de la V0 avec `mpy-cross` : MicroPython v1.29.0, compilation de l'outil datée 2026-08-29, format .mpy v6.3. Distribution PC utilisée : mpy-cross 1.29.0.post2. Les .mpy de vérification ne sont pas distribués : transférer les .py lisibles.
- 113 tests unitaires et d'intégration simulée (voir sortie ci-dessous) :
  88 pour le firmware, 25 pour le compagnon Windows.
- Lecture des API dans les fichiers officiels réellement inclus.
- Vérification des empreintes des quatre fichiers USB et du driver SH1106 ; driver SH1106 identique au commit figé.
- Schéma SVG rendu en PNG et inspecté visuellement.

## Ce que couvrent les tests PC

**Base V0.** Navigation dans les deux sens ; anti-rebond, rebonds et maintien ; démarrage avec touche tenue ; retour circulaire des ticks ; 26 lettres FR, underscore, macros et ENTER ; Caps Lock ; refus atomique d'un texte non pris en charge ; pressions/relâchements de Ctrl+Shift+Esc ; ESC au milieu d'Alt+Tab/texte ; endpoint occupé sans perte immédiate ; file bornée ; déconnexion sans reprise de macro ; faute et timeout avec annulation/libération ; respiration, flash et passage des ticks ; SAFE MODE sans initialisation HID et retour REPL ; absence/panne OLED ; une page transmise par tick ; boucle main simulée avec macro Civil3D, NEXT et ESC ; rapports de huit octets produits par la classe officielle KeyboardInterface.

**La page de configuration** (`PageDeConfigurationIntacte`, 5 tests). La page servie par `device/portal.py` et celle servie par `pc/macropad_auto.py` sont comparees a leur source unique `tools/page_config.html` ; le JavaScript est verifie syntaxiquement par `node --check` ; enfin il est **execute hors navigateur** avec un DOM minimal (`tests/page_smoke.js`), une fois avec les valeurs d'usine — on compte alors les cartes de profil, les listes deroulantes et les lignes de logiciels produites — et une fois avec une configuration vide, pour verifier que la page explique pourquoi elle n'a rien a montrer. Ces tests sont nes du bug de la correction 11 : un antislash mal interprete cassait tout le script, et la page restait vide sans le moindre message.

**Ajouts V1.** Les six touches et leurs libellés ; la machine à états des trois gestes (appui court immédiat quand aucun double appui n'est défini, appui court retardé quand il y en a un, double appui, deux appuis trop espacés, appui long déclenché au seuil sans deuxième envoi au relâchement, touches indépendantes) ; l'aller-retour complet de la configuration par page web sans perte ; le refus d'une macro intapable et d'un libellé trop long ; le repli sur les valeurs d'usine pour un fichier corrompu ou incohérent ; **la relecture d'un `profils.json` de version 1**, dont la macro devient l'appui court ; le protocole série ligne par ligne, y compris une ligne coupée en deux envois, la lecture bornée par tour de boucle et une configuration trop volumineuse ; l'absence de séquence à deux actions dans les valeurs d'usine (que la page web tronquerait) ; **l'écran, qui ne doit jamais écrire hors des 128×64 pixels** — quatre profils, splash, surlignage de chaque touche, nom de fichier de 48 caractères en défilement, page WiFi.

**Compagnon Windows** (`tests/test_pc.py`, 25 tests). Nettoyage du titre de fenêtre dans ses trois formes (tiret, crochets, chemin complet) ; troncature à ce que l'écran retient ; table de secours à deux ou trois champs, abrégé déduit et coupé à sept caractères, casse, commentaires, relecture à chaud, ligne incomplète ; priorité de la table lue sur la carte, repli sur le fichier quand la carte se tait ou n'annonce aucun logiciel, conservation de la dernière table connue ; le raccourci de démarrage automatique (chemin `shell:startup`, échappement PowerShell des apostrophes sans toucher aux antislash des chemins, script complet, refus propre hors Windows) ; le journal, y compris sans console utilisable.

Les GPIO, l'horloge, le PWM et le transport USB sont simulés. Le test d'absence d'OLED exerce le chemin d'initialisation indisponible ; le test de déconnexion OLED injecte une OSError lors d'une écriture. Le test des octets HID appelle le sérialiseur officiel mais remplace la transmission USB.

## Vérification documentaire / statique seulement

Support machine.USBDevice sur le port ESP32 du tag 1.29.0 ; sélection SPIRAM_OCT ; broches du S3 et cohérence du pinout photo ; calcul de courant LED/base ; méthodes PWM/I2C et conservation CDC ; reprise des licences.

## Validé sur le matériel réel (session de montage)

Les points suivants ne relèvent plus de la simulation : ils ont été
constatés sur la carte de l'utilisateur, un ESP32-S3 N16R8.

| Point | Résultat |
|---|---|
| Firmware | MicroPython **v1.28.0**, `_build='ESP32_GENERIC_S3'` (variante standard, PSRAM non activée, 224 Ko libres) |
| `machine.USBDevice` | présent : `True` |
| Chargement des modules | `config`, `layouts`, `inputs`, `display`, `sh1106`, `led`, `profiles`, `runtime`, `diag` s'importent et s'exécutent sans erreur sur la carte |
| Écran OLED | SH1106 détecté à **0x3C**, pilote initialisé sans exception, texte affiché correctement et non décalé |
| Anti-rebond | appuis francs sur ESC, B1, B2, B3 : **un seul événement APPUI suivi d'un seul relâchement**, aucun rebond, compteurs exacts |
| Étage LED | paliers PWM 5 / 25 / 50 / 100 % distincts, respiration fluide, aucun échauffement |
| Traduction clavier | `diag.keymap()` produit bien le `_` en touche 37 sans Maj |
| **Clavier USB HID** | ✅ **énumération sous Windows réussie, frappe réelle confirmée** : un appui sur B1 en profil CIVIL3D a produit `_MATCHPROP` + Entrée dans une fenêtre Windows |
| **Disposition FR AZERTY** | ✅ le `_` sort bien en `_` (ni `8`, ni `-`) : la table AZERTY et la gestion de la rangée des chiffres sont correctes |
| Macro `text_enter` | ✅ dix caractères envoyés par la file non bloquante, puis Entrée |

Le bug des « blank USB HID reports » ne se manifeste donc pas sur cette
configuration (v1.28.0, variante standard sans PSRAM). C'était le seul
point de la recherche qui restait à démontrer.

Un **bug réel** a par ailleurs été trouvé en service, pas en simulation :
après un changement de profil suivi d'une seconde d'inactivité, la
première macro déclenchait « transfert sans progression » et arrêtait le
clavier. Cause : `cancel()` ne remettait pas à jour l'horodatage de
progression, si bien que le chien de garde comparait la nouvelle macro à
une date ancienne. Corrigé, et couvert par trois tests
(`BugChangementDeProfil`) dont deux échouent sur le code d'origine.

Restent non validés à ce stade : les deux modules TTP223, les touches
mécaniques B4 à B6, la rotation des profils, les trois gestes sur le
matériel, le compagnon PC en conditions réelles, et les essais
applicatifs Civil 3D / Blender / Word.

## Non exécuté — à faire sur le matériel

Aucun ESP32-S3 ni PC Windows n'est accessible **depuis l'environnement où ce firmware est écrit** : tout ce qui figure dans la section précédente a été constaté par l'utilisateur sur sa propre carte, et rapporté ici tel quel. Restent donc à faire, sur le matériel : la mesure de latence et de consommation, la validation des TTP223, le compagnon PC branché sur le port natif, les trois gestes sous le doigt, et les tests applicatifs Civil3D / Blender / Word. La compilation complète ESP-IDF du firmware n'a pas été effectuée ; le binaire recommandé est celui du site officiel. Concernant l'issue HID #18098 : les notes de version officielles de MicroPython **v1.27.0** annoncent explicitement « *a fix for blank USB HID reports on boards with PSRAM* », ce qui correspond exactement au symptôme signalé et exactement à une carte N16R8. La version 1.29.0 retenue est postérieure à ce correctif. Cela reste une preuve documentaire, pas une preuve matérielle : commencer malgré tout par le test LETTER.

## Reproduire les tests sur PC

Depuis le dossier du projet :

```bash
python -m unittest discover -s tests -v
```

Ces tests ne nécessitent pas de carte et ne tapent aucune touche sur le PC. Ils utilisent unittest fourni avec Python. Les logs « ERREUR CRITIQUE », « file pleine » et « OLED désactivé » ci-dessous proviennent des pannes injectées intentionnellement.

## Sortie des tests

```text
--- AncienFichierDeConfiguration
test_version_1_relue_comme_appui_court ... ok
test_version_2_non_touchee_par_la_conversion ... ok

--- BugChangementDeProfil
test_cancel_apres_repos_ne_declenche_pas_de_panne ... ok
test_le_vrai_blocage_declenche_toujours_la_panne ... ok
test_reconnexion_usb_efface_la_panne ... ok

--- Corrections
test_capslock_digits_fr ... ok
test_capslock_underscore_fr ... ok
test_capslock_us_only_affects_letters ... ok
test_close_after_macro_leaves_nothing_pressed ... ok
test_close_keeps_usb_when_nothing_pressed ... ok
test_combo_accepts_digits_and_symbols ... ok
test_commands_typable_with_capslock_on ... ok
test_esc_fast_edge_held_at_boot ... ok
test_esc_fast_edge_is_immediate ... ok
test_extended_characters ... ok
test_input_order_is_deterministic ... ok
test_shortcut_uses_physical_key_not_character ... ok
test_submit_accepted_right_after_cancel ... ok
test_submit_accepted_right_after_escape ... ok

--- GestesCourtLongDouble
test_appui_court_instantane_sans_double ... ok
test_appui_court_retarde_si_double_possible ... ok
test_appui_long_part_des_le_seuil ... ok
test_configurer_depuis_les_macros ... ok
test_deux_appuis_trop_espaces_font_deux_courts ... ok
test_double_appui ... ok
test_maintien_sans_macro_longue_reste_un_court ... ok
test_touches_independantes ... ok

--- LiaisonSerieAvecLePC
test_changement_de_profil_demande_par_le_pc ... ok
test_commande_inconnue_ignoree ... ok
test_configuration_trop_volumineuse_refusee ... ok
test_json_casse_refuse ... ok
test_le_pc_ecrit_la_configuration ... ok
test_le_pc_lit_la_configuration ... ok
test_lecture_bornee_par_tour_de_boucle ... ok
test_ligne_coupee_en_deux_envois ... ok
test_macro_intapable_refusee_par_le_lien ... ok
test_nom_du_document ... ok
test_rechargement_demande ... ok
test_version ... ok

--- Logic
test_azerty_all_letters ... ok
test_bounce_hold_release ... ok
test_breath_and_flash ... ok
test_busy_does_not_lose_event ... ok
test_capslock_mapping ... ok
test_disconnect_discards_queue ... ok
test_escape_preempts_modifier_and_text ... ok
test_fault_releases_without_resume ... ok
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
test_start_held ... ok
test_ticks_wrap ... ok
test_timeout_cancels_pending ... ok
test_vendor_report_bytes ... ok

--- PageDeConfigurationIntacte
test_compagnon_pc_sert_la_meme_page ... ok
test_la_page_previent_quand_elle_n_a_rien_recu ... ok
test_la_page_se_construit_avec_de_vraies_donnees ... ok
test_le_javascript_de_la_page_est_valide ... ok
test_portail_wifi_sert_la_page_source ... ok

--- PageWebDeConfiguration
test_api_renvoie_les_profils_usine ... ok
test_chemin_inconnu ... ok
test_enregistrement_refuse_un_json_casse ... ok
test_enregistrement_refuse_une_macro_intapable ... ok
test_enregistrement_valide ... ok
test_page_html_servie ... ok
test_retour_usine ... ok

--- V1SixTouchesEtConfigWeb
test_affichage_six_touches_sans_debordement ... ok
test_aller_retour_json ... ok
test_conversion_combo ... ok
test_fichier_corrompu_repli_sur_usine ... ok
test_fichier_incoherent_repli_sur_usine ... ok
test_libelle_trop_long_refuse ... ok
test_libelles_tiennent_sur_l_ecran ... ok
test_macro_intapable_refusee ... ok
test_rotation_sur_six_touches ... ok
test_six_touches_partout ... ok
test_toutes_les_macros_usine_sont_tapables ... ok

--- ValeursUsineSansPiege
test_aller_retour_complet_sans_perte ... ok
test_aucune_sequence_dans_les_valeurs_usine ... ok

--- DemarrageAutomatiqueWindows
test_apostrophes_doublees_pas_les_antislash ... ok
test_dossier_de_demarrage ... ok
test_hors_windows_ne_touche_a_rien ... ok
test_sans_appdata_message_clair ... ok
test_script_powershell_complet ... ok

--- JournalDuCompagnon
test_ecrit_dans_les_deux_sorties ... ok
test_une_console_absente_ne_casse_rien ... ok

--- NomDeDocument
test_chemin_complet_reduit_au_nom_de_fichier ... ok
test_coupe_a_ce_que_l_ecran_retient ... ok
test_titres_entre_crochets ... ok
test_titres_windows_classiques ... ok

--- TableDeSecours
test_abrege_coupe_a_sept_caracteres ... ok
test_abrege_deduit_quand_le_champ_manque ... ok
test_commentaires_et_lignes_vides_ignores ... ok
test_fichier_cree_avec_les_valeurs_par_defaut ... ok
test_fichier_illisible_ne_plante_pas ... ok
test_insensible_a_la_casse ... ok
test_ligne_sans_profil_ignoree ... ok
test_relecture_a_chaud ... ok

--- TableLueSurLaCarte
test_carte_muette_apres_une_lecture_reussie_garde_la_table ... ok
test_carte_muette_garde_le_fichier ... ok
test_la_carte_remplace_le_fichier ... ok
test_lignes_incompletes_ignorees ... ok
test_table_vide_sur_la_carte_laisse_le_fichier_travailler ... ok
test_une_table_identique_ne_change_rien ... ok

----------------------------------------------------------------------
Ran 113 tests

OK
```
