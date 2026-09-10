# Rapport de vérification — 6 septembre 2026

**Résultat : 216 tests PC réussis ; 23 fichiers Python compilés avec succès.**

> **Mise à jour après relecture.** Le projet a été relu, neuf corrections y ont
> été apportées (voir `docs/06-corrections.md`) et **14 tests supplémentaires**
> ont été écrits, au moins un par correction.
>
> Ces nouveaux tests ont été exécutés contre la version d'origine du firmware :
> **12 des 14 échouent**, ce qui établit que chaque défaut était réel. Les deux
> restants passaient déjà et servent de garde-fou anti-régression.

## Exécuté réellement dans cet environnement

- Compilation syntaxique des **22 fichiers** du firmware avec CPython (`python3 -m py_compile device/*.py device/lib/usb/device/*.py`).
- Compilation des 16 sources de la V0 avec `mpy-cross` : MicroPython v1.29.0, compilation de l'outil datée 2026-08-29, format .mpy v6.3. Distribution PC utilisée : mpy-cross 1.29.0.post2. Les .mpy de vérification ne sont pas distribués : transférer les .py lisibles.
- 216 tests unitaires et d'intégration simulée (voir sortie ci-dessous) :
  191 pour le firmware, 25 pour le compagnon Windows.
- Lecture des API dans les fichiers officiels réellement inclus.
- Vérification des empreintes des quatre fichiers USB et du driver SH1106 ; driver SH1106 identique au commit figé.
- Schéma SVG rendu en PNG et inspecté visuellement.

## Ce que couvrent les tests PC

**Base V0.** Navigation dans les deux sens ; anti-rebond, rebonds et maintien ; démarrage avec touche tenue ; retour circulaire des ticks ; 26 lettres FR, underscore, macros et ENTER ; Caps Lock ; refus atomique d'un texte non pris en charge ; pressions/relâchements de Ctrl+Shift+Esc ; ESC au milieu d'Alt+Tab/texte ; endpoint occupé sans perte immédiate ; file bornée ; déconnexion sans reprise de macro ; faute et timeout avec annulation/libération ; respiration, flash et passage des ticks ; SAFE MODE sans initialisation HID et retour REPL ; absence/panne OLED ; une page transmise par tick ; boucle main simulée avec macro Civil3D, NEXT et ESC ; rapports de huit octets produits par la classe officielle KeyboardInterface.

**La page de configuration** (`PageDeConfigurationIntacte`, 10 tests). La page servie par `device/portal.py` et celle servie par `pc/macropad_auto.py` sont comparees a leur source unique `tools/page_config.html` ; le JavaScript est verifie syntaxiquement par `node --check` ; enfin il est **execute hors navigateur** avec un DOM minimal (`tests/page_smoke.js`), une fois avec les valeurs d'usine — on compte alors les cartes de profil, les listes deroulantes et les lignes de logiciels produites — une fois avec une configuration vide, pour verifier que la page explique pourquoi elle n'a rien a montrer, et une fois en TAPANT dans les champs pour verifier que chaque saisie arrive bien sur la touche voulue - et nulle part ailleurs - dans ce qui part vers le macropad. La capture de raccourci et la restauration d'une sauvegarde sont exercees de la meme facon : on fabrique de faux evenements clavier et on verifie les noms produits - dont AltGr, qui se presente comme Ctrl+Alt sous Windows et ne doit pas ressortir en CTRL+ALT -, puis on passe CHAQUE nom du tableau de la page dans layouts.key_code du firmware. Une page qui ecrirait DELETE la ou le firmware attend SUPPR fabriquerait des macros refusees a l'enregistrement sans que rien n'explique pourquoi ; ce test l'interdit. La restauration est verifiee sur une sauvegarde valable, sur un fichier illisible et sur un JSON etranger.

Ces tests sont nes du bug de la correction 11 : un antislash mal interprete cassait tout le script, et la page restait vide sans le moindre message.

**Les suites d'etapes et les pauses** (`SuitesDEtapesEtPauses`, 8 tests). La compilation d'une pause en marqueur, le refus d'une duree aberrante AVANT la premiere frappe, et surtout le deroulement : la suite d'une macro attend bien, rien n'est envoye pendant ce temps, le garde-fou ne se declenche pas sur une pause de trois secondes - une attente voulue est un progres, pas un blocage - et ESC interrompt une macro en pleine pause. Puis l'aller-retour par la page web, le refus d'une pause au-dela du plafond, et la relecture d'un ancien profils.json qui ne rangeait qu'une action par geste.

**La touche modificatrice** (`ToucheModificatrice`, 14 tests). La machine a etats (appui maintenu, appui bref puis maintenu, second appui hors delai, touche a un seul maintien) ; le modificateur reste present dans TOUS les rapports envoyes, y compris pendant qu'une macro se deroule par-dessus ; le relachement le libere ; et surtout les quatre filets contre un modificateur coince cote PC : ESC, changement de profil, deconnexion USB, macro intapable refusee sans rien envoyer.

**Les LED RGB** (`LedsRgb` et `CouleursDesProfils`, 37 tests). Le plafond de luminosite, qui est une securite electrique et non un reglage esthetique : le test calcule le courant que tireraient six LED et refuse qu'il approche des 500 mA du port USB. Puis la couleur par profil, l'ordre des octets configurable, la surbrillance de la touche utilisee et son retour, le rouge en cas de panne HID, l'extinction apres inactivite et le reveil, la cadence d'envoi bornee, l'absence totale d'acces materiel quand RGB_ENABLED vaut False, une LED absente ou arrachee en cours de route qui desactive l'affichage sans jamais remonter d'exception, et les deux variantes du montage a une seule LED RGB (anode ou cathode commune).

La respiration est verifiee comme une fonction pure - douce aux deux extremites, jamais sous son plancher, periodique - puis sur le rendu : la couleur varie bien dans le temps, la TEINTE ne bouge pas (c'est la luminosite qui respire), la touche surlignee ne respire pas, et un tour de boucle anormalement long ne fait pas sauter la couleur a l'autre bout du cycle. Les couleurs elles-memes voyagent avec la configuration : conversion dans les deux sens, couleur illisible qui retombe sur celle d'usine sans faire perdre les macros, aller-retour par la page web, et ancien profils.json sans couleur qui reprend les valeurs d'usine.

Le diagnostic de cablage `diag.rgb()`, qu'on lance dans le REPL avant meme d'activer les LED, est teste lui aussi : il allume bien chaque LED seule et dans l'ordre - c'est ce qui permet de COMPTER celles qui repondent -, il place l'octet rouge la ou la puce l'attend quand il annonce ROUGE (sinon il induirait en erreur celui qui regle justement RGB_ORDRE), il eteint tout en partant meme interrompu par Ctrl-C, et il se contente d'un message si le firmware n'embarque pas neopixel.

La reaction a l'appui a ses propres tests, nes d'une latence constatee sur le materiel : la LED s'intensifie des le premier tour de boucle et seulement la sienne, deux appuis coup sur coup montent plus haut qu'un seul, la retombee passe par plus de cinq paliers sans jamais remonter et finit exactement sur la couleur du profil, l'empilement est plafonne, et - le test qui compte - vingt appuis empiles sur du blanc ne franchissent pas le plafond de courant. Un dernier verifie que l'impulsion s'AJOUTE a la respiration : le gain est le meme en haut et en bas du cycle.

Enfin, deux tests font tourner main.run() en entier avec RGB_ENABLED a True et un faux ruban horodate. Le second reproduit la latence d'origine : il appuie sur la touche 1, celle qui a un double appui et dont la macro ne part donc qu'apres GESTE_DOUBLE_MS, et exige que la LED ait deja reagi dans les 60 premieres millisecondes. Il echoue sur la version precedente : rien ne sert de savoir que rgb.py fonctionne seul si l'activer fait tomber la boucle principale. Il verifie que le ruban est rafraichi tout au long de la boucle, qu'il change de couleur au changement de profil, et qu'il est ETEINT a l'arret.

**Les combinaisons de touches** (`CombinaisonsSimultanees`,
`CombinaisonsDansLaBoucleReelle` et `CombinaisonsDansLaConfiguration`,
37 tests). Le collecteur d'abord, seul : une touche qui n'entre dans
aucune combinaison ne traverse meme pas le module ; un appui court sur une
touche membre part au relachement, sans un seul tour d'attente ; un appui
maintenu est transmis a la fin de la fenetre AVEC SON HORODATAGE
D'ORIGINE, ce qui est toute la conception ; la fenetre se ferme, les
appuis retenus sont rendus intacts, ESC et le changement de profil
abandonnent sans rien declencher, et rouler les doigts en relachant ne
fabrique pas une seconde combinaison.

Puis la meme chose dans la VRAIE boucle de `main.py`, avec de vrais
rebonds de contact et de vrais paquets clavier : B3+B4 tape bien
`MPVIEWPREV` et surtout pas les macros des deux touches, B3 seule tape
toujours F3, et l'appui long sur une touche membre part a
`GESTE_LONG_MS` **pile** - ce dernier test echoue si l'on remplace
l'horodatage d'origine par l'heure courante, ce qui est exactement le
defaut qu'il surveille. ESC pendant la formation d'une combinaison
n'envoie qu'Echap, rien d'autre, alors que la touche reste enfoncee 300 ms.

Cote configuration enfin : les combinaisons voyagent dans `profils.json`
avec les numeros du pad (`[3, 4]`, c'est B3 et B4) ; un fichier ecrit
AVANT les combinaisons recupere celles d'usine plutot que de les perdre en
silence, tandis qu'une liste presente mais vide est respectee ; et six
formes fautives sont refusees avec un message nomme - une seule touche, une
touche qui n'existe pas, la meme touche deux fois, deux combinaisons sur le
meme couple, une macro intapable, et un `maintien`, qui resterait enfonce
cote Windows faute d'une touche unique a surveiller. La page web est
exercee hors navigateur : elle affiche les six combinaisons de Civil 3D,
comprend une saisie mal ecrite (`5 et 6` devient `[5, 6]`), n'ecrit pas
dans la mauvaise ligne, et **les renvoie entieres a l'enregistrement** -
une page qui les ignorerait effacerait en silence tout ce que la carte
avait.

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

--- CouleursDesProfils
test_conversion_dans_les_deux_sens ... ok
test_la_page_web_recoit_les_couleurs ... ok
test_les_couleurs_usine_viennent_de_config ... ok
test_un_ancien_fichier_sans_couleur_prend_celles_d_usine ... ok
test_une_couleur_choisie_survit_a_l_enregistrement ... ok
test_une_couleur_illisible_ne_bloque_pas_l_enregistrement ... ok

--- GestesCourtLongDouble
test_appui_court_instantane_sans_double ... ok
test_appui_court_retarde_si_double_possible ... ok
test_appui_long_part_des_le_seuil ... ok
test_configurer_depuis_les_macros ... ok
test_deux_appuis_trop_espaces_font_deux_courts ... ok
test_double_appui ... ok
test_maintien_sans_macro_longue_reste_un_court ... ok
test_touches_independantes ... ok

--- LedsRgb
test_aucun_acces_materiel_quand_c_est_desactive ... ok
test_chaque_profil_a_sa_couleur ... ok
test_deux_appuis_montent_deux_fois_plus_haut ... ok
test_diag_rgb_eteint_tout_meme_si_on_l_interrompt ... ok
test_diag_rgb_parcourt_toutes_les_led ... ok
test_diag_rgb_respecte_l_ordre_des_octets ... ok
test_diag_rgb_sans_neopixel_ne_plante_pas ... ok
test_extinction_apres_la_veille_puis_reveil ... ok
test_l_empilement_est_plafonne ... ok
test_l_horloge_qui_saute_ne_fait_pas_sauter_la_couleur ... ok
test_l_impulsion_s_ajoute_a_la_respiration ... ok
test_la_boucle_principale_tourne_avec_les_led_actives ... ok
test_la_couleur_respire_vraiment ... ok
test_la_courbe_de_respiration ... ok
test_la_led_suit_le_doigt_et_pas_la_macro ... ok
test_la_luminosite_plafonne_vraiment_le_courant ... ok
test_la_retombee_est_progressive_et_revient_au_calme ... ok
test_le_demarrage_annonce_l_etat_des_led ... ok
test_le_demarrage_dit_pourquoi_rien_ne_s_allume ... ok
test_materiel_absent_ne_plante_pas ... ok
test_meme_a_fond_le_plafond_de_courant_tient ... ok
test_montage_pwm_anode_commune ... ok
test_montage_pwm_cathode_commune ... ok
test_ordre_des_couleurs_configurable ... ok
test_panne_en_cours_de_route_desactive_sans_remonter ... ok
test_panne_hid_passe_au_rouge_et_revient ... ok
test_pas_plus_d_un_envoi_par_periode ... ok
test_profil_inconnu_prend_la_couleur_par_defaut ... ok
test_respiration_eteinte_laisse_la_couleur_fixe ... ok
test_rien_a_envoyer_rien_n_est_envoye ... ok
test_tout_s_eteint_a_l_arret ... ok
test_un_appui_intensifie_sa_touche_tout_de_suite ... ok

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
test_la_capture_de_raccourci_donne_des_noms_valides ... ok
test_la_couleur_des_led_se_choisit_par_profil ... ok
test_la_page_previent_quand_elle_n_a_rien_recu ... ok
test_la_page_se_construit_avec_de_vraies_donnees ... ok
test_la_restauration_d_une_sauvegarde ... ok
test_le_javascript_de_la_page_est_valide ... ok
test_portail_wifi_sert_la_page_source ... ok
test_tous_les_noms_du_tableau_de_capture_sont_connus ... ok
test_une_saisie_va_bien_sur_la_touche_ou_on_la_tape ... ok

--- PageWebDeConfiguration
test_api_renvoie_les_profils_usine ... ok
test_chemin_inconnu ... ok
test_enregistrement_refuse_un_json_casse ... ok
test_enregistrement_refuse_une_macro_intapable ... ok
test_enregistrement_valide ... ok
test_page_html_servie ... ok
test_retour_usine ... ok

--- SuitesDEtapesEtPauses
test_esc_interrompt_une_macro_en_pleine_pause ... ok
test_l_ancienne_forme_a_une_seule_action_se_relit ... ok
test_la_pause_retarde_la_suite_sans_bloquer ... ok
test_la_pause_se_compile_en_marqueur ... ok
test_une_longue_pause_ne_declenche_pas_le_garde_fou ... ok
test_une_pause_aberrante_est_refusee_avant_la_premiere_frappe ... ok
test_une_pause_trop_longue_est_refusee_a_l_enregistrement ... ok
test_une_suite_survit_a_l_enregistrement ... ok

--- ToucheModificatrice
test_aller_retour_par_la_page_web ... ok
test_appui_maintenu_donne_le_premier_modificateur ... ok
test_bref_puis_maintenu_donne_le_second ... ok
test_changement_de_profil_libere_le_modificateur ... ok
test_deconnexion_usb_oublie_le_maintien ... ok
test_esc_libere_un_modificateur_bloque ... ok
test_le_modificateur_reste_enfonce ... ok
test_les_autres_touches_ne_changent_pas ... ok
test_les_valeurs_usine_de_civil3d ... ok
test_maintien_intapable_refuse_sans_rien_envoyer ... ok
test_relachement_libere_le_modificateur ... ok
test_second_appui_trop_tard_redonne_le_premier ... ok
test_touche_a_un_seul_maintien ... ok
test_une_macro_pendant_le_maintien_garde_le_modificateur ... ok

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
test_les_suites_d_actions_traversent_la_page_web ... ok

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
Ran 216 tests

OK
```
