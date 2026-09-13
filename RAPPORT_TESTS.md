# Rapport de vérification — 6 septembre 2026

**Résultat : 316 tests PC réussis ; 23 fichiers Python compilés avec succès.**

> **Mise à jour après relecture.** Le projet a été relu, seize corrections y ont
> été apportées (voir `docs/06-corrections.md`) et **14 tests supplémentaires**
> ont été écrits, au moins un par correction.
>
> Ces nouveaux tests ont été exécutés contre la version d'origine du firmware :
> **12 des 14 échouent**, ce qui établit que chaque défaut était réel. Les deux
> restants passaient déjà et servent de garde-fou anti-régression.

## Exécuté réellement dans cet environnement

- Compilation syntaxique des **22 fichiers** du firmware avec CPython (`python3 -m py_compile device/*.py device/lib/usb/device/*.py`).
- Compilation des 16 sources de la V0 avec `mpy-cross` : MicroPython v1.29.0, compilation de l'outil datée 2026-08-29, format .mpy v6.3. Distribution PC utilisée : mpy-cross 1.29.0.post2. Les .mpy de vérification ne sont pas distribués : transférer les .py lisibles.
- 316 tests unitaires et d'intégration simulée (voir sortie ci-dessous) :
  274 pour le firmware, 42 pour le compagnon Windows.
- Lecture des API dans les fichiers officiels réellement inclus.
- Vérification des empreintes des quatre fichiers USB et du driver SH1106 ; driver SH1106 identique au commit figé.
- Schéma SVG rendu en PNG et inspecté visuellement.

## Ce que couvrent les tests PC

**Base V0.** Navigation dans les deux sens ; anti-rebond, rebonds et maintien ; démarrage avec touche tenue ; retour circulaire des ticks ; 26 lettres FR, underscore, macros et ENTER ; Caps Lock ; refus atomique d'un texte non pris en charge ; pressions/relâchements de Ctrl+Shift+Esc ; ESC au milieu d'Alt+Tab/texte ; endpoint occupé sans perte immédiate ; file bornée ; déconnexion sans reprise de macro ; faute et timeout avec annulation/libération ; respiration, flash et passage des ticks ; SAFE MODE sans initialisation HID et retour REPL ; absence/panne OLED ; une page transmise par tick ; boucle main simulée avec macro Civil3D, NEXT et ESC ; rapports de huit octets produits par la classe officielle KeyboardInterface.

**La page de configuration** (`PageDeConfigurationIntacte`, 20 tests). La page servie par `device/portal.py` et celle servie par `pc/macropad_auto.py` sont comparees a leur source unique `tools/page_config.html` ; le JavaScript est verifie syntaxiquement par `node --check` ; enfin il est **execute hors navigateur** avec un DOM minimal (`tests/page_smoke.js`), une fois avec les valeurs d'usine — on compte alors les cartes de profil, les listes deroulantes et les lignes de logiciels produites — une fois avec une configuration vide, pour verifier que la page explique pourquoi elle n'a rien a montrer, et une fois en TAPANT dans les champs pour verifier que chaque saisie arrive bien sur la touche voulue - et nulle part ailleurs - dans ce qui part vers le macropad. La capture de raccourci et la restauration d'une sauvegarde sont exercees de la meme facon : on fabrique de faux evenements clavier et on verifie les noms produits - dont AltGr, qui se presente comme Ctrl+Alt sous Windows et ne doit pas ressortir en CTRL+ALT -, puis on passe CHAQUE nom du tableau de la page dans layouts.key_code du firmware. Une page qui ecrirait DELETE la ou le firmware attend SUPPR fabriquerait des macros refusees a l'enregistrement sans que rien n'explique pourquoi ; ce test l'interdit. La restauration est verifiee sur une sauvegarde valable, sur un fichier illisible et sur un JSON etranger.

LE FILET CONTRE LA PAGE MORTE y est verifie lui aussi : une erreur JavaScript doit s'AFFICHER, avec son message et sa ligne, au lieu d'arreter tout le script en laissant une page muette - c'est la signature commune des corrections 11 et 13, et le retirer fait echouer la moitie de cette classe. La REMISE A ZERO DES COMPTEURS est exercee sur ses trois chemins : le bouton vise bien /api/compteurs, la route du portail efface les compteurs et refuse proprement quand il n'y en a pas, et la commande serie !ZERO efface les compteurs ET LEUR FICHIER - sans cette suppression, enregistrer() refuserait d'ecrire une table vide et les anciens chiffres reviendraient au prochain demarrage. L'ENREGISTREUR DE SEQUENCE y est exerce de bout en bout : on rejoue au clavier ce qu'un utilisateur taperait vraiment - une commande, Entree, une attente de 900 ms, puis Ctrl+S et F5 - avec une horloge simulee, et on verifie les trois regles qui portent tout : les caracteres ordinaires s'accumulent en UNE etape, Entree apres du texte donne "texte + Entree", et une attente reelle devient une pause. Le test qui compte est le suivant : ce que l'enregistreur fabrique repasse par store.actions_depuis_json puis compile_actions, et la configuration complete par store.verifier - une sequence enregistree qui serait refusee a l'enregistrement transformerait un raccourci en piege. Echap arrete la prise sans s'enregistrer lui-meme. Supprimer l'accumulation du texte ou la mesure des pauses fait echouer deux tests.

L'ENREGISTREMENT A LA SOURIS est verifie sous deux angles, parce qu'un DOM minimal ne suffit pas. Angle 1, en executant la page : le nombre d'appels a window.scrollTo pendant une prise doit rester a ZERO - c'est le correctif de la corvee signalee a l'usage, la page sautait en bas a chaque frappe - et la barre du bas doit s'allumer, nommer la touche en cours, compter les etapes, puis s'eteindre a l'arret. Angle 2, en lisant le HTML et le CSS servis : la barre doit etre en position fixe, collee en bas, et porter un bouton cable sur recStop. Sans ce second test, rien n'interdirait de la remettre dans le flux de la page, ou elle redeviendrait inatteignable sans defiler. Quatre mutations ont ete verifiees : retirer la garde sansDefiler, empecher la barre de s'allumer, la decoller du bas, renommer recStop - chacune fait echouer un test.

LE NOM COMPLET des touches et des combinaisons (`NomCompletDesTouches`, 8 tests) fait l'aller-retour complet : saisi dans la page, il part dans le JSON, revient par store.charger - dont le tuple est passe de neuf a dix elements - et ressort dans le recapitulatif du compagnon PC. Les tests verifient qu'un nom trop long est tronque a NOM_MAX - le fichier vit sur la flash de la carte -, qu'un nom absent laisse le libelle court faire office de nom sans rien casser, et que le recapitulatif produit bien une ligne d'en-tete par touche portant ce nom.

UN DEFAUT A ETE TROUVE ET CORRIGE PAR CES TESTS, avant toute mise en service. Le repli "aucun nom dans le fichier -> on remet ceux d'usine" est indispensable pour relire un profils.json ecrit AVANT les noms complets : sans lui, une mise a jour du firmware les ferait disparaitre. Mais applique tel quel, il rendait l'effacement IMPOSSIBLE : vider toutes les cases, enregistrer, et les noms d'usine revenaient au rechargement suivant. depuis_json distingue desormais "le fichier ne parle pas des noms" de "le fichier dit qu'ils sont vides", exactement comme il le fait deja pour les combinaisons et pour la seconde couleur. Deux tests tiennent les deux moities de la regle, et cinq mutations ont ete verifiees : remettre l'ancien repli, retirer la troncature, cesser d'envoyer le nom a la page, supprimer les noms d'usine, et retirer le tri de la cle d'une combinaison - chacune fait echouer un test. Ce dernier tri compte : la page accepte "4 3" comme "3 4", et sans tri le nom partait sous une cle que plus personne ne relit.

Ces tests sont nes du bug de la correction 11 : un antislash mal interprete cassait tout le script, et la page restait vide sans le moindre message.

**Les suites d'etapes et les pauses** (`SuitesDEtapesEtPauses`, 8 tests). La compilation d'une pause en marqueur, le refus d'une duree aberrante AVANT la premiere frappe, et surtout le deroulement : la suite d'une macro attend bien, rien n'est envoye pendant ce temps, le garde-fou ne se declenche pas sur une pause de trois secondes - une attente voulue est un progres, pas un blocage - et ESC interrompt une macro en pleine pause. Puis l'aller-retour par la page web, le refus d'une pause au-dela du plafond, et la relecture d'un ancien profils.json qui ne rangeait qu'une action par geste.

**La touche modificatrice** (`ToucheModificatrice`, 14 tests). La machine a etats (appui maintenu, appui bref puis maintenu, second appui hors delai, touche a un seul maintien) ; le modificateur reste present dans TOUS les rapports envoyes, y compris pendant qu'une macro se deroule par-dessus ; le relachement le libere ; et surtout les quatre filets contre un modificateur coince cote PC : ESC, changement de profil, deconnexion USB, macro intapable refusee sans rien envoyer.

**Les LED RGB** (`LedsRgb` et `CouleursDesProfils`, 37 tests). Le plafond de luminosite, qui est une securite electrique et non un reglage esthetique : le test calcule le courant que tireraient six LED et refuse qu'il approche des 500 mA du port USB. Puis la couleur par profil, l'ordre des octets configurable, la surbrillance de la touche utilisee et son retour, le rouge en cas de panne HID, l'extinction apres inactivite et le reveil, la cadence d'envoi bornee, l'absence totale d'acces materiel quand RGB_ENABLED vaut False, une LED absente ou arrachee en cours de route qui desactive l'affichage sans jamais remonter d'exception, et les deux variantes du montage a une seule LED RGB (anode ou cathode commune).

La respiration est verifiee comme une fonction pure - douce aux deux extremites, jamais sous son plancher, periodique - puis sur le rendu : la couleur varie bien dans le temps, la TEINTE ne bouge pas (c'est la luminosite qui respire), la touche surlignee ne respire pas, et un tour de boucle anormalement long ne fait pas sauter la couleur a l'autre bout du cycle. Les couleurs elles-memes voyagent avec la configuration : conversion dans les deux sens, couleur illisible qui retombe sur celle d'usine sans faire perdre les macros, aller-retour par la page web, et ancien profils.json sans couleur qui reprend les valeurs d'usine.

Deux outils de depannage s'y ajoutent, nes d'un ruban qui ne repondait a rien : `diag.rgb_pin()` balaie les broches plausibles pour retrouver celle ou le fil est soude - le test verifie qu'il n'essaie QUE des broches libres, car piloter en sortie le SDA de l'ecran ou l'horloge de la flash transformerait un diagnostic en panne - et `diag.rgb_saute(n)` pilote le ruban comme s'il avait n LED de plus, pour contourner une premiere puce grillee : le test verifie que les LED ignorees restent noires a CHAQUE envoi et que l'allumage est bien decale. Le diagnostic de cablage `diag.rgb()`, qu'on lance dans le REPL avant meme d'activer les LED, est teste lui aussi : il allume bien chaque LED seule et dans l'ordre - c'est ce qui permet de COMPTER celles qui repondent -, il place l'octet rouge la ou la puce l'attend quand il annonce ROUGE (sinon il induirait en erreur celui qui regle justement RGB_ORDRE), il eteint tout en partant meme interrompu par Ctrl-C, et il se contente d'un message si le firmware n'embarque pas neopixel.

L'ALTERNANCE DE DEUX COULEURS a aussi les siens : le melange doit etre PUR AUX SOMMETS - premiere couleur au sommet d'une respiration, seconde au sommet de la suivante - et bouger le moins possible a ces sommets, faute de quoi on n'aurait qu'un degrade continu sans jamais voir vraiment l'une ni l'autre. Le rendu est verifie aussi, pas seulement la formule : le pad passe bien par les deux couleurs, un profil a une seule couleur garde une TEINTE constante, et une panne HID efface l'alternance. Cote configuration, couleur2 voyage dans profils.json avec la meme regle que les combinaisons - chaine vide = aucune alternance et c'est respecte, cle absente = valeur d'usine - et une couleur illisible ne fait perdre aucune macro. La RESERVE D'APPUI a les siens, nes d'un defaut constate a l'usage : au sommet de la respiration on ne voyait plus quelle touche venait de servir. La cause n'etait pas la luminosite mais le plafond de courant, applique CANAL PAR CANAL : un bleu a 255 y touchait deja, et l'appui ne pouvait que delaver les autres canaux. Les tests exigent desormais que CHAQUE canal allume monte a l'appui, que le gain depasse +60 %, que l'appui atteigne exactement la couleur pleine du profil, qu'un bleu pur reagisse lui aussi, et que la respiration reste sous son plafond - remonter celui-ci a 1.0 fait echouer deux tests, et supprimer la reserve du mode sans respiration en fait echouer six. La reaction a l'appui a ses propres tests, nes d'une latence constatee sur le materiel : la LED s'intensifie des le premier tour de boucle et seulement la sienne, deux appuis coup sur coup montent plus haut qu'un seul, la retombee passe par plus de cinq paliers sans jamais remonter et finit exactement sur la couleur du profil, l'empilement est plafonne, et - le test qui compte - vingt appuis empiles sur du blanc ne franchissent pas le plafond de courant. Un dernier verifie que l'impulsion s'AJOUTE a la respiration : le gain est le meme en haut et en bas du cycle.

Enfin, deux tests font tourner main.run() en entier avec RGB_ENABLED a True et un faux ruban horodate. Le second reproduit la latence d'origine : il appuie sur la touche 1, celle qui a un double appui et dont la macro ne part donc qu'apres GESTE_DOUBLE_MS, et exige que la LED ait deja reagi dans les 60 premieres millisecondes. Il echoue sur la version precedente : rien ne sert de savoir que rgb.py fonctionne seul si l'activer fait tomber la boucle principale. Il verifie que le ruban est rafraichi tout au long de la boucle, qu'il change de couleur au changement de profil, et qu'il est ETEINT a l'arret.

**Le controle general** (`ControleGeneral`, 12 tests). Trois d'entre eux gardent le filet de demarrage : un firmware qui plante doit AFFICHER la cause - sur l'ecran et dans le REPL - au lieu de laisser un pad muet ; un ecran absent ne doit pas masquer l'erreur d'origine ; et un Ctrl-C n'est pas une panne. Nes de la
correction 14, ou une seule constante manquante dans un config.py conserve
faisait planter main.py au demarrage - donc pas de clavier, pas de LED et
pas de liaison PC, trois symptomes pour une cause. Deux tests ferment cette
porte : l'un fait tourner main.run() avec les reglages neufs RETIRES de
config et exige que le macropad demarre quand meme ; l'autre compare chaque
valeur de repli a celle du depot, parce qu'un repli qui divergerait
donnerait un pad au comportement different selon l'age du fichier. Les sept
autres exercent diag.controle() : reglage absent, interrupteur a False,
SAFE MODE, broche reservee, fichier absent distingue d'un fichier present
qui ne s'importe pas, et le cas sain.

S'y ajoute le clavier que Windows n'a jamais ouvert - les touches repondent, leur nom s'affiche, et rien n'est tape : le controle le nomme, l'ecran passe a USB? et le REPL explique UNE SEULE FOIS que la cause est presque toujours le mauvais port USB-C. Un test fait tourner main.run() avec une interface qui ne s'ouvre pas et verifie les trois. Deux tests de plus y veillent : `diag.controle()` signale DEUX ROLES SUR UNE MEME BROCHE - l'erreur qu'on fait en corrigeant un numero a la main, ou la broche repond mais a deux maitres - et le brochage livre est verifie sain, variante RGB active comprise.

**Le brochage, verifie AVANT le fer a souder** (`BrochesAvantDeSouder`,
8 tests). Une soudure ne se defait pas d'un clic : ces tests verifient
qu'aucune broche citee dans config.py n'est reservee par la flash SPI
(GPIO26-32), par la PSRAM octale d'un N16R8 (GPIO33-37) ou par l'USB
(GPIO19-20), qu'aucune n'est utilisee deux fois pour deux roles, et que
les numeros qui n'existent pas sur un S3 (GPIO22-25) sont bien rejetes.

Le test qui compte est le dernier : on declare volontairement une touche
sur GPIO30 - l'horloge de la flash - et on verifie que `diag.broches()`
la SIGNALE sans jamais construire le `Pin`, avec un faux Pin qui echoue si
on l'appelle. Creer un Pin sur la flash suffit a faire tomber la carte :
l'outil de diagnostic ne doit pas etre ce qui la fait tomber.

**LA PANNE IMAGINAIRE DU GARDE-FOU** (`BugRechargementPendantUneMacro`,
5 tests). Correction 15, constatee a l'usage : ecran ERR et plus une seule
touche, apres un enregistrement depuis la page web. Le garde-fou HID
comptait comme un blocage USB le temps passe HORS de la boucle - relire
profils.json, ecrire les compteurs sur la flash. Trois de ces tests font
tourner la VRAIE boucle de main.py avec un rechargement lent en plein vol,
jusqu'a cinq secondes. Les deux autres encadrent la correction dans les
deux sens : une absence de la boucle ne doit PAS declencher la panne, un
vrai blocage USB - ou tick() est appele sans arret - doit TOUJOURS la
declencher. Le cinquieme attrape la panne silencieuse qui accompagnait la
premiere : un modificateur tenu pendant un rechargement restait enfonce
cote Windows, et il echoue avec (-1,) != () - le code du Ctrl coince.
Trois mutations verifiees.

**CE QUE LA PAGE PEUT REGLER** (`LaPagePeutToutRegler`, 3 tests). Nes
d'une question posee telle quelle : « je peux le faire depuis la page
HTTP ? ». La reponse devait etre verifiable, pas affirmee. On fabrique
donc la configuration exactement comme la PAGE l'enverrait - ses types,
ses valeurs textuelles - et on verifie que la carte l'accepte et la relit
a l'identique : echanger les deux modificateurs de B1 se fait sans
toucher au code. Deux garde-fous l'accompagnent : MAJ et SHIFT doivent
compiler vers la MEME frappe, sinon un reglage fait a la page enverrait
autre chose que prevu ; et une valeur inventee est refusee AVANT d'etre
ecrite, la configuration precedente restant intacte.

**LE MAINTIEN DU BOUTON ESC** (`EscMaintenu`, 5 tests, dans la vraie
boucle de main.py). Le point delicat : ESC a une priorite absolue et part
sur le FRONT D'APPUI, pas au relachement. Distinguer un appui court d'un
long en attendant le relachement lui aurait pris cette priorite - c'est
exactement ce qu'il ne faut pas. On garde donc Echap instantane et on
AJOUTE Ctrl+Z si le doigt reste. Les tests exigent qu'un appui bref
n'envoie QUE Echap, qu'un maintien ajoute l'annulation, qu'elle ne part
QU'UNE FOIS meme sur trois secondes, que le compteur se reamorce au
relachement (deux maintiens = deux annulations), et que le seuil reste
plus long que GESTE_LONG_MS - dans Civil 3D, un Ctrl+Z involontaire defait
un vrai travail. Trois mutations verifiees.

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
meme couple, une macro intapable, un `maintien`, qui resterait enfonce
cote Windows faute d'une touche unique a surveiller, et - le seul
controle du projet qui parle du monde PHYSIQUE - deux touches placees
sous le meme doigt, qu'aucune main ne peut appuyer ensemble. La page web est
exercee hors navigateur : elle affiche les six combinaisons de Civil 3D,
comprend une saisie mal ecrite (`5 et 6` devient `[5, 6]`), n'ecrit pas
dans la mauvaise ligne, et **les renvoie entieres a l'enregistrement** -
une page qui les ignorerait effacerait en silence tout ce que la carte
avait.

**Ajouts V1.** Les six touches et leurs libellés ; la machine à états des trois gestes (appui court immédiat quand aucun double appui n'est défini, appui court retardé quand il y en a un, double appui, deux appuis trop espacés, appui long déclenché au seuil sans deuxième envoi au relâchement, touches indépendantes) ; l'aller-retour complet de la configuration par page web sans perte ; le refus d'une macro intapable et d'un libellé trop long ; le repli sur les valeurs d'usine pour un fichier corrompu ou incohérent ; **la relecture d'un `profils.json` de version 1**, dont la macro devient l'appui court ; le protocole série ligne par ligne, y compris une ligne coupée en deux envois, la lecture bornée par tour de boucle et une configuration trop volumineuse ; l'absence de séquence à deux actions dans les valeurs d'usine (que la page web tronquerait) ; **l'écran, qui ne doit jamais écrire hors des 128×64 pixels** — quatre profils, splash, surlignage de chaque touche, nom de fichier de 48 caractères en défilement, page WiFi.

**Compagnon Windows** (`tests/test_pc.py`, 42 tests). D'abord LE RECAPITULATIF DES COMMANDES, ne d'un constat mesurable : l'ecran OLED fait 16 caracteres sur 4 lignes visibles, le profil CIVIL3D compte 19 entrees, il manque un facteur cinq. La mise en forme est PURE - ni fenetre, ni port serie - et c'est elle qui est testee : une suite de trois etapes se lit d'un trait, le nom d'une touche ne se repete pas d'une ligne a l'autre, un geste vide ne prend pas de ligne, les combinaisons et le bouton ESC y figurent, un profil inconnu ne garde que ce qui est global, et l'ancienne forme a une seule action par geste se lit encore.

Trois tests de plus gardent LA propriete de surete de ce panneau, et elle n'est pas evidente : c'est une fenetre DU MEME PROGRAMME. Si elle passait au premier plan, la detection croirait a un changement de logiciel et basculerait le profil - regarder ses propres raccourcis les changerait. lire() reconnait donc nos fenetres a leur PID et rend (None, None), que la boucle distingue de la chaine vide : la premiere ne touche a rien, la seconde bascule sur le profil de repli. Retirer cette garde fait echouer deux tests. Un dernier verifie que sans tkinter, le compagnon continue exactement comme avant. Puis la correction 13 : D'abord la correction quand la page dit « macropad non connecte », elle doit dire POURQUOI. Les trois causes - aucun port Espressif, port deja pris par Thonny, pyserial absent - donnent trois messages distincts, le debranchement en cours de route est nomme lui aussi, et la raison survit au silence de la console : celle-ci ne se repete pas, mais la page la redemande a chaque rafraichissement. Puis le nettoyage du titre de fenêtre dans ses trois formes (tiret, crochets, chemin complet) ; troncature à ce que l'écran retient ; table de secours à deux ou trois champs, abrégé déduit et coupé à sept caractères, casse, commentaires, relecture à chaud, ligne incomplète ; priorité de la table lue sur la carte, repli sur le fichier quand la carte se tait ou n'annonce aucun logiciel, conservation de la dernière table connue ; le raccourci de démarrage automatique (chemin `shell:startup`, échappement PowerShell des apostrophes sans toucher aux antislash des chemins, script complet, refus propre hors Windows) ; le journal, y compris sans console utilisable.

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

--- BrochesAvantDeSouder
test_aucune_broche_n_est_utilisee_deux_fois ... ok
test_diag_broches_refuse_quand_une_broche_est_interdite ... ok
test_diag_ne_touche_JAMAIS_une_broche_reservee ... ok
test_la_console_serie_est_deconseillee_pas_interdite ... ok
test_les_broches_declarees_sont_toutes_utilisables ... ok
test_les_broches_libres_excluent_ce_qui_sert_deja ... ok
test_les_numeros_qui_n_existent_pas ... ok
test_usb_et_flash_sont_reservees ... ok

--- BugChangementDeProfil
test_cancel_apres_repos_ne_declenche_pas_de_panne ... ok
test_le_vrai_blocage_declenche_toujours_la_panne ... ok
test_reconnexion_usb_efface_la_panne ... ok

--- BugRechargementPendantUneMacro
test_le_rechargement_lent_ne_coupe_plus_le_clavier ... ok
test_le_rechargement_relache_le_modificateur_tenu ... ok
test_un_rechargement_instantane_ne_changeait_deja_rien ... ok
test_un_vrai_blocage_usb_reste_detecte ... ok
test_une_absence_de_la_boucle_ne_declenche_pas_de_panne ... ok

--- CombinaisonsDansLaBoucleReelle
test_deux_touches_ensemble_tapent_la_commande_de_la_combinaison ... ok
test_esc_annule_une_combinaison_en_cours_de_formation ... ok
test_un_appui_long_sur_une_touche_membre_part_a_l_heure ... ok
test_une_touche_membre_seule_garde_sa_macro ... ok

--- CombinaisonsDansLaConfiguration
test_aller_retour_par_le_fichier ... ok
test_aucune_combinaison_ne_touche_la_modificatrice ... ok
test_deux_combinaisons_sur_les_memes_touches ... ok
test_deux_touches_du_meme_doigt_sont_refusees ... ok
test_la_meme_touche_deux_fois ... ok
test_le_libelle_est_tronque_pas_refuse ... ok
test_le_message_nomme_les_touches_et_le_doigt ... ok
test_les_combinaisons_d_usine_sont_chargees ... ok
test_les_combinaisons_d_usine_sont_toutes_jouables ... ok
test_les_numeros_du_fichier_sont_ceux_du_pad ... ok
test_les_valeurs_d_usine_sont_saines ... ok
test_sans_table_de_doigts_rien_n_est_verifie ... ok
test_un_fichier_combos_illisible_retombe_sur_l_usine ... ok
test_un_fichier_sans_combos_recupere_celles_d_usine ... ok
test_un_maintien_est_impossible ... ok
test_un_profil_inconnu ... ok
test_une_liste_vide_est_respectee ... ok
test_une_macro_intapable_est_refusee ... ok
test_une_seule_touche_n_est_pas_une_combinaison ... ok
test_une_touche_qui_n_existe_pas ... ok
test_verifier_refuse_l_enregistrement ... ok

--- CombinaisonsSimultanees
test_apres_esc_le_relachement_ne_reveille_rien ... ok
test_deux_appuis_trop_espaces_restent_deux_appuis ... ok
test_deux_touches_ensemble_declenchent_la_combinaison ... ok
test_esc_abandonne_une_combinaison_en_attente ... ok
test_l_appui_long_d_une_touche_membre_part_a_l_heure ... ok
test_l_horodatage_d_origine_est_preserve ... ok
test_l_ordre_des_doigts_n_a_pas_d_importance ... ok
test_le_trio_ne_venant_pas_la_paire_part_a_la_fin_de_la_fenetre ... ok
test_les_relachements_de_la_combinaison_sont_avales ... ok
test_nom_pour_l_ecran ... ok
test_rouler_les_doigts_ne_declenche_pas_une_seconde_fois ... ok
test_une_combinaison_d_une_seule_touche_est_ignoree ... ok
test_une_paire_attend_si_un_trio_peut_encore_se_former ... ok
test_une_paire_sans_trio_declenche_sans_attendre ... ok
test_une_tape_rapide_sur_une_membre_ne_perd_rien ... ok
test_une_touche_hors_combinaison_passe_sans_delai ... ok

--- ControleGeneral
test_controle_accepte_un_clavier_ouvert ... ok
test_controle_distingue_un_fichier_absent_d_un_fichier_casse ... ok
test_controle_est_vert_sur_une_configuration_saine ... ok
test_controle_signale_deux_roles_sur_une_meme_broche ... ok
test_controle_signale_le_safe_mode ... ok
test_controle_signale_les_interrupteurs_a_False ... ok
test_controle_signale_un_clavier_jamais_ouvert ... ok
test_controle_signale_un_reglage_manquant ... ok
test_controle_signale_une_broche_reservee ... ok
test_l_ecran_affiche_USB_quand_le_clavier_n_est_pas_ouvert ... ok
test_le_repli_vaut_la_valeur_du_depot ... ok
test_pas_de_doublon_dans_la_configuration_livree ... ok
test_reglage_prefere_toujours_config ... ok
test_un_config_ancien_ne_doit_plus_empecher_le_demarrage ... ok
test_un_ctrl_c_n_est_pas_une_panne ... ok
test_un_ecran_absent_n_aggrave_pas_la_panne ... ok
test_une_panne_de_demarrage_est_affichee_pas_avalee ... ok

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

--- EscMaintenu
test_deux_appuis_maintenus_annulent_deux_fois ... ok
test_l_annulation_ne_part_qu_une_fois ... ok
test_le_seuil_est_plus_long_que_celui_des_touches ... ok
test_un_appui_bref_n_envoie_qu_echap ... ok
test_un_maintien_ajoute_l_annulation ... ok

--- GestesCourtLongDouble
test_appui_court_instantane_sans_double ... ok
test_appui_court_retarde_si_double_possible ... ok
test_appui_long_part_des_le_seuil ... ok
test_configurer_depuis_les_macros ... ok
test_deux_appuis_trop_espaces_font_deux_courts ... ok
test_double_appui ... ok
test_maintien_sans_macro_longue_reste_un_court ... ok
test_touches_independantes ... ok

--- LaPagePeutToutRegler
test_echanger_les_deux_modificateurs_depuis_la_page ... ok
test_le_nom_MAJ_est_bien_compris_par_le_clavier ... ok
test_un_maintien_invente_est_refuse_avant_d_etre_ecrit ... ok

--- LedsRgb
test_aucun_acces_materiel_quand_c_est_desactive ... ok
test_chaque_profil_a_sa_couleur ... ok
test_deux_appuis_montent_deux_fois_plus_haut ... ok
test_diag_rgb_eteint_tout_meme_si_on_l_interrompt ... ok
test_diag_rgb_parcourt_toutes_les_led ... ok
test_diag_rgb_pin_n_essaie_que_des_broches_libres ... ok
test_diag_rgb_respecte_l_ordre_des_octets ... ok
test_diag_rgb_sans_neopixel_ne_plante_pas ... ok
test_diag_rgb_saute_decale_bien_le_ruban ... ok
test_extinction_apres_la_veille_puis_reveil ... ok
test_l_empilement_est_plafonne ... ok
test_l_horloge_qui_saute_ne_fait_pas_sauter_la_couleur ... ok
test_l_impulsion_s_ajoute_a_la_respiration ... ok
test_la_boucle_principale_tourne_avec_les_led_actives ... ok
test_la_couleur_respire_vraiment ... ok
test_la_courbe_de_respiration ... ok
test_la_led_suit_le_doigt_et_pas_la_macro ... ok
test_la_luminosite_plafonne_vraiment_le_courant ... ok
test_la_reserve_de_l_appui_ne_depasse_pas_le_plafond_de_courant ... ok
test_la_respiration_reste_entre_son_plancher_et_son_plafond ... ok
test_la_retombee_est_progressive_et_revient_au_calme ... ok
test_le_demarrage_annonce_l_etat_des_led ... ok
test_le_demarrage_dit_pourquoi_rien_ne_s_allume ... ok
test_le_melange_bouge_le_moins_au_sommet ... ok
test_le_melange_est_pur_aux_sommets ... ok
test_le_pad_passe_vraiment_par_les_deux_couleurs ... ok
test_materiel_absent_ne_plante_pas ... ok
test_melanger_interpole_et_accepte_l_absence ... ok
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
test_sans_seconde_couleur_rien_ne_change ... ok
test_tout_s_eteint_a_l_arret ... ok
test_un_appui_amene_la_touche_a_sa_couleur_pleine ... ok
test_un_appui_intensifie_sa_touche_tout_de_suite ... ok
test_un_appui_se_voit_au_sommet_de_la_respiration ... ok
test_une_couleur_pure_reagit_aussi ... ok
test_une_panne_hid_efface_l_alternance ... ok

--- LiaisonSerieAvecLePC
test_changement_de_profil_demande_par_le_pc ... ok
test_commande_inconnue_ignoree ... ok
test_configuration_trop_volumineuse_refusee ... ok
test_json_casse_refuse ... ok
test_le_pc_ecrit_la_configuration ... ok
test_le_pc_lit_la_configuration ... ok
test_le_pc_remet_les_compteurs_a_zero ... ok
test_lecture_bornee_par_tour_de_boucle ... ok
test_ligne_coupee_en_deux_envois ... ok
test_macro_intapable_refusee_par_le_lien ... ok
test_nom_du_document ... ok
test_rechargement_demande ... ok
test_version ... ok
test_zero_sans_compteurs_repond_sans_planter ... ok

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

--- NomCompletDesTouches
test_aller_retour_par_le_fichier ... ok
test_effacer_TOUS_les_noms_les_efface_vraiment ... ok
test_la_page_recoit_le_nom_de_chaque_touche_et_combinaison ... ok
test_les_noms_d_usine_sont_charges ... ok
test_un_fichier_ecrit_avant_les_noms_retrouve_ceux_d_usine ... ok
test_un_nom_absent_ne_casse_rien ... ok
test_un_nom_trop_long_est_tronque ... ok
test_une_combinaison_saisie_a_l_envers_garde_son_nom ... ok

--- PageDeConfigurationIntacte
test_compagnon_pc_sert_la_meme_page ... ok
test_echap_arrete_l_enregistrement_sans_s_enregistrer ... ok
test_l_enregistrement_ne_fait_pas_sauter_la_page ... ok
test_l_enregistreur_ne_produit_que_des_macros_valables ... ok
test_l_enregistreur_transforme_les_frappes_en_etapes ... ok
test_la_barre_d_enregistrement_est_collee_en_bas_avec_son_stop ... ok
test_la_capture_de_raccourci_donne_des_noms_valides ... ok
test_la_couleur_des_led_se_choisit_par_profil ... ok
test_la_page_previent_quand_elle_n_a_rien_recu ... ok
test_la_page_se_construit_avec_de_vraies_donnees ... ok
test_la_restauration_d_une_sauvegarde ... ok
test_le_bouton_des_compteurs_vise_la_bonne_route ... ok
test_le_javascript_de_la_page_est_valide ... ok
test_les_combinaisons_s_editent_et_repartent_entieres ... ok
test_portail_wifi_sert_la_page_source ... ok
test_tous_les_noms_du_tableau_de_capture_sont_connus ... ok
test_une_barre_collee_en_bas_porte_le_bouton_stop ... ok
test_une_erreur_javascript_s_affiche_au_lieu_de_tout_tuer ... ok
test_une_lecture_impossible_explique_quoi_verifier ... ok
test_une_saisie_va_bien_sur_la_touche_ou_on_la_tape ... ok

--- PageWebDeConfiguration
test_api_renvoie_les_profils_usine ... ok
test_chemin_inconnu ... ok
test_enregistrement_refuse_un_json_casse ... ok
test_enregistrement_refuse_une_macro_intapable ... ok
test_enregistrement_valide ... ok
test_page_html_servie ... ok
test_remise_a_zero_des_compteurs ... ok
test_remise_a_zero_sans_compteurs_est_refusee_proprement ... ok
test_retour_usine ... ok

--- SecondeCouleurDansLaConfiguration
test_aller_retour_par_le_fichier ... ok
test_la_page_lit_et_ecrit_couleur2 ... ok
test_les_secondes_couleurs_d_usine_sont_chargees ... ok
test_un_fichier_sans_couleur2_reprend_celle_d_usine ... ok
test_un_profil_sans_seconde_couleur_donne_None ... ok
test_une_chaine_vide_coupe_l_alternance_pour_de_bon ... ok
test_une_seconde_couleur_illisible_ne_fait_rien_perdre ... ok

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

--- LePanneauNeDoitPasFausserLaDetection
test_None_et_chaine_vide_ne_veulent_pas_dire_la_meme_chose ... ok
test_notre_propre_fenetre_est_reconnue ... ok
test_une_vraie_fenetre_est_lue_normalement ... ok

--- NomDeDocument
test_chemin_complet_reduit_au_nom_de_fichier ... ok
test_coupe_a_ce_que_l_ecran_retient ... ok
test_titres_entre_crochets ... ok
test_titres_windows_classiques ... ok

--- PourquoiLeMacropadEstInjoignable
test_aucun_port_espressif_le_dit ... ok
test_la_raison_survit_au_silence_de_la_console ... ok
test_port_occupe_le_dit_avec_le_nom_du_port ... ok
test_pyserial_absent_le_dit ... ok
test_un_debranchement_en_cours_de_route_est_nomme ... ok

--- RecapitulatifDesCommandes
test_chaque_touche_a_son_en_tete_puis_ses_gestes ... ok
test_l_ancienne_forme_a_une_seule_action_se_lit_encore ... ok
test_le_nom_de_la_touche_ne_se_repete_pas ... ok
test_le_panneau_absent_ne_casse_rien ... ok
test_les_combinaisons_et_ESC_y_sont_aussi ... ok
test_un_geste_vide_ne_prend_pas_de_ligne ... ok
test_un_profil_inconnu_ne_garde_que_ce_qui_est_global ... ok
test_une_configuration_absente_ne_plante_pas ... ok
test_une_suite_d_etapes_se_lit_d_un_trait ... ok

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
Ran 316 tests

OK
```
