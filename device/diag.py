# -*- coding: utf-8 -*-
"""
diag.py - Diagnostic du matériel. N'ENVOIE JAMAIS AUCUNE TOUCHE.

=====================================================================
A QUOI CA SERT
=====================================================================
C'est l'outil à utiliser pour les étapes 1 à 6 des tests, quand tu montes
le matériel morceau par morceau. Il n'initialise même pas le clavier USB :
il est donc impossible qu'il tape quelque chose dans Thonny pendant que tu
travailles.

=====================================================================
COMMENT L'UTILISER DANS THONNY
=====================================================================
Dans la zone du bas (le REPL, celle où il y a ">>>"). Tape les commandes
SANS le ">>>" : c'est l'invite, Thonny l'affiche tout seul, et la coller
avec la commande donne "SyntaxError: invalid syntax".


    import diag
    diag.run()              # 20 secondes de surveillance des entrées
    diag.run(seconds=60)    # plus long
    diag.run(led_test=True) # ajoute le test de la LED

Test par test :

    diag.controle()             # « rien ne marche » : par ou commencer
    diag.broches()              # AVANT DE SOUDER : les broches sont-elles libres ?
    diag.keymap()               # vérifie l'AZERTY, sans matériel
    diag.keymap("_ISOLATEOBJECTS")
    diag.rgb()                  # câblage des LED RGB, une par une
    diag.rgb_pin()              # sur QUELLE broche le fil est-il soudé ?
    diag.rgb_saute(1)           # ignorer une première LED grillée

Pour arrêter avant la fin : Ctrl-C, ou le bouton STOP de Thonny.
"""

import sys
from time import ticks_ms, ticks_diff, sleep_ms
import config as C


# =====================================================================
# LE CONTROLE GENERAL : « rien ne marche, par ou je commence ? »
# =====================================================================
# Quand DEUX choses tombent en meme temps - les LED eteintes ET le
# compagnon PC qui ne voit rien - il n'y a presque jamais deux pannes.
# Il y en a une, en amont des deux. Cette fonction la trouve.

# Les fichiers que le firmware attend sur la carte.
MODULES_ATTENDUS = ("config", "profiles", "runtime", "inputs", "gestures",
                    "combos", "layouts", "store", "stats", "link",
                    "hid_keyboard", "display", "led", "rgb", "sh1106")

# Les reglages ajoutes au fil des versions. Un config.py conserve d'une
# version precedente ne les a pas : le firmware se rabat sur une valeur
# d'usine, mais autant le savoir.
REGLAGES_ATTENDUS = (
    ("config", "GESTE_COMBO_MS"),
    ("config", "COMBO_FLASH_MS"),
    ("config", "DOIGTS"),
    ("config", "RGB_RESPIRATION_MAX"),
    ("config", "RGB_COULEURS2"),
    ("profiles", "COMBO_LABEL_MAX"),
    ("profiles", "COMBOS"),
)

# Les quatre interrupteurs qui expliquent, a eux seuls, la plupart des
# « rien ne se passe ».
INTERRUPTEURS = (
    ("HID_ENABLED", True, "le macropad ne tapera AUCUNE touche"),
    ("RGB_ENABLED", True, "les LED RGB resteront eteintes"),
    ("LINK_ENABLED", True, "le compagnon PC ne verra jamais la carte"),
    ("OLED_ENABLED", True, "l'ecran restera noir"),
)


def controle():
    """Le premier reflexe quand plusieurs choses ne marchent plus.

    Verifie, dans l'ordre ou les causes s'enchainent :
      1. tous les fichiers du firmware sont-ils sur la carte ?
      2. config.py est-il aussi recent que le reste ?
      3. les quatre interrupteurs sont-ils sur la bonne position ?
      4. le brochage est-il coherent ?

    Ne touche a aucun materiel et n'envoie aucune touche.
    """
    import runtime
    print("=" * 46)
    print(" CONTROLE GENERAL DU MACROPAD")
    print("=" * 46)
    soucis = []

    # --- 1. Les fichiers -------------------------------------------
    print("1. Fichiers du firmware")
    absents, casses = [], []
    for nom in MODULES_ATTENDUS:
        try:
            __import__(nom)
        except Exception as exc:
            # Un fichier ABSENT et un fichier PRESENT QUI PLANTE ne se
            # reparent pas pareil : le premier se reteleverse, le second se
            # lit. Le message d'erreur nomme le module introuvable, et ce
            # n'est pas forcement celui qu'on importe.
            texte = str(exc).lower()
            if "no module named" in texte and nom.lower() in texte:
                absents.append(nom)
                print("   ABSENT   %s" % nom)
            else:
                casses.append((nom, exc))
                print("   PRESENT mais son import echoue : %s (%s)" % (nom, exc))
    if absents:
        soucis.append("%d fichier(s) absent(s) de la carte : %s"
                      % (len(absents), ", ".join(absents)))
        print("   -> reteleverse le CONTENU de device/ a la racine de la carte.")
    for nom, exc in casses:
        soucis.append("%s ne s'importe pas : %s" % (nom, exc))
    if not absents and not casses:
        print("   les %d fichiers sont la et s'importent." % len(MODULES_ATTENDUS))

    # --- 2. config.py est-il a jour ? ------------------------------
    print("2. Reglages")
    vieux = []
    for module, reglage in REGLAGES_ATTENDUS:
        try:
            if not hasattr(__import__(module), reglage):
                vieux.append("%s.%s" % (module, reglage))
        except Exception:
            pass
    if vieux:
        soucis.append("config.py ou profiles.py est plus ancien que le "
                      "firmware (%s)" % ", ".join(vieux))
        print("   ces reglages manquent, valeur d'usine utilisee :")
        for nom in vieux:
            print("     -", nom)
        print("   -> recopie les lignes manquantes depuis le depot.")
    else:
        print("   config.py et profiles.py sont a jour.")

    # --- 3. Les interrupteurs --------------------------------------
    print("3. Interrupteurs de config.py")
    for nom, attendu, consequence in INTERRUPTEURS:
        valeur = getattr(C, nom, None)
        if valeur is None:
            print("   %-13s ABSENT" % nom)
            continue
        if bool(valeur) != attendu:
            soucis.append("%s = %s : %s" % (nom, valeur, consequence))
            print("   %-13s %-5s <- %s" % (nom, valeur, consequence))
        else:
            print("   %-13s %s" % (nom, valeur))

    # --- 4. Le brochage --------------------------------------------
    print("4. Brochage")
    mauvaises = []
    for numero, premier, second in broches_en_double():
        mauvaises.append("GPIO%d sert a DEUX choses : %s et %s"
                         % (numero, premier, second))
    for numero, role in sorted(broches_deja_prises().items()):
        verdict, raison = verifier_broche(numero)
        if verdict in ("reservee", "inexistante"):
            mauvaises.append("GPIO%d (%s) : %s" % (numero, role, raison))
    if mauvaises:
        soucis.extend(mauvaises)
        for ligne in mauvaises:
            print("  ", ligne)
    else:
        print("   les %d broches declarees sont utilisables."
              % len(broches_deja_prises()))

    # --- 5. L'etat du demarrage ------------------------------------
    print("5. Demarrage")
    print("   SAFE MODE   :", runtime.safe_mode,
          "   (B1 maintenu au RESET : aucun clavier, aucune liaison)")
    print("   MODE CONFIG :", runtime.config_mode,
          "   (B2 maintenu au RESET : WiFi, aucune liaison serie)")
    if runtime.interface is None:
        print("   clavier USB : ABSENT (non cree au demarrage)")
    else:
        try:
            ouvert = runtime.interface.is_open()
        except Exception as exc:
            ouvert = None
            print("   clavier USB : cree, etat illisible (%s)" % exc)
        if ouvert is True:
            print("   clavier USB : cree et OUVERT par Windows")
        elif ouvert is False:
            print("   clavier USB : cree mais Windows NE L'A PAS OUVERT")
            soucis.append("Windows n'a pas ouvert le clavier USB : c'est "
                          "presque toujours le mauvais port USB-C (il faut "
                          "le port NATIF, pas le port UART/COM)")
    if runtime.hid_error:
        soucis.append("erreur HID au demarrage : %s" % runtime.hid_error)
        print("   erreur HID :", runtime.hid_error)
    if runtime.safe_mode or runtime.config_mode:
        soucis.append("la carte n'est pas en mode normal : ni clavier, "
                      "ni liaison avec le compagnon PC")

    print("=" * 46)
    if soucis:
        print(" %d POINT(S) A CORRIGER, dans cet ordre :" % len(soucis))
        for rang, souci in enumerate(soucis):
            print("   %d. %s" % (rang + 1, souci))
    else:
        print(" TOUT EST COHERENT.")
        print(" Si quelque chose ne marche toujours pas, c'est du cablage :")
        print("   diag.broches()  puis  diag.run()  puis  diag.rgb()")
    print("=" * 46)
    return not soucis


# =====================================================================
# CE QU'ON PEUT ET NE PEUT PAS UTILISER SUR UN ESP32-S3
# =====================================================================
# Ces numéros ne sont pas une opinion : ils viennent du brochage du
# module. Souder une touche sur l'un d'eux, c'est au mieux une touche qui
# ne répond jamais, au pire une carte qui ne redémarre plus.
BROCHES_INEXISTANTES = (22, 23, 24, 25)

BROCHES_RESERVEES = {
    19: "USB D- : sans elle le macropad ne peut pas etre un clavier",
    20: "USB D+ : sans elle le macropad ne peut pas etre un clavier",
    26: "flash SPI interne (SPICS1)",
    27: "flash SPI interne (SPIHD)",
    28: "flash SPI interne (SPIWP)",
    29: "flash SPI interne (SPICS0)",
    30: "flash SPI interne (SPICLK)",
    31: "flash SPI interne (SPIQ)",
    32: "flash SPI interne (SPID)",
    33: "PSRAM octale, c'est le cas d'un N16R8 (SPIIO4)",
    34: "PSRAM octale, c'est le cas d'un N16R8 (SPIIO5)",
    35: "PSRAM octale, c'est le cas d'un N16R8 (SPIIO6)",
    36: "PSRAM octale, c'est le cas d'un N16R8 (SPIIO7)",
    37: "PSRAM octale, c'est le cas d'un N16R8 (SPIDQS)",
}

BROCHES_DECONSEILLEES = {
    0:  "bouton BOOT : a 0 au demarrage, la carte attend un televersement",
    3:  "strapping au demarrage (choix de la source JTAG)",
    38: "LED RGB soudee sur la carte, sur beaucoup de DevKitC-1",
    39: "JTAG MTCK : utilisable, mais tu perds le debogage materiel",
    40: "JTAG MTDO : idem",
    41: "JTAG MTDI : idem",
    42: "JTAG MTMS : idem",
    43: "UART0 TX : c'est la console serie de Thonny",
    44: "UART0 RX : c'est la console serie de Thonny",
    45: "strapping : tension du bus SPI",
    46: "strapping, et en lecture seule apres le demarrage",
}


def verifier_broche(numero):
    """(verdict, raison) pour une broche. Ne touche AUCUN materiel.

    verdict vaut "libre", "deconseillee", "reservee" ou "inexistante".
    Fonction pure, sans acces au materiel : c'est elle que les tests PC
    verifient, et elle repond donc aussi depuis un PC.
    """
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return "inexistante", "ce n'est pas un numero de broche"
    if numero < 0 or numero > 48 or numero in BROCHES_INEXISTANTES:
        return "inexistante", "ce numero n'existe pas sur un ESP32-S3"
    if numero in BROCHES_RESERVEES:
        return "reservee", BROCHES_RESERVEES[numero]
    if numero in BROCHES_DECONSEILLEES:
        return "deconseillee", BROCHES_DECONSEILLEES[numero]
    return "libre", ""


def roles_declares():
    """[(numero, role), ...] pour tout ce que config.py declare, SANS dedoublonner.

    C'est la forme brute : deux entrees sur la meme broche y restent
    visibles. broches_deja_prises() la resume, broches_en_double() y
    cherche les collisions.
    """
    roles = []

    def poser(numero, role):
        if numero is None:
            return
        roles.append((int(numero), role))

    for rang, numero in enumerate(C.BUTTON_PINS):
        poser(numero, "touche B%d" % (rang + 1))
    poser(C.ESC_PIN, "bouton ESC")
    poser(getattr(C, "LED_PIN", None), "LED du bouton ESC")
    poser(getattr(C, "TTP_PREVIOUS_PIN", None), "TTP profil precedent")
    poser(getattr(C, "TTP_NEXT_PIN", None), "TTP profil suivant")
    poser(getattr(C, "OLED_SDA", None), "OLED SDA")
    poser(getattr(C, "OLED_SCL", None), "OLED SCL")
    if getattr(C, "RGB_TYPE", "") == "WS2812":
        poser(getattr(C, "RGB_PIN", None), "donnees des LED RGB")
    else:
        poser(getattr(C, "RGB_PIN_R", None), "LED RGB rouge")
        poser(getattr(C, "RGB_PIN_V", None), "LED RGB verte")
        poser(getattr(C, "RGB_PIN_B", None), "LED RGB bleue")
    return roles


def broches_deja_prises():
    """{numero: a quoi elle sert} pour tout ce que config.py declare deja."""
    prises = {}
    for numero, role in roles_declares():
        prises.setdefault(numero, role)
    return prises


def broches_en_double():
    """[(numero, role1, role2), ...] : deux fonctions sur la meme broche.

    Le genre d'erreur qu'on fait en corrigeant un numero a la main - et
    qui ne se voit nulle part : la broche repond, mais a deux maitres.
    """
    premier = {}
    doubles = []
    for numero, role in roles_declares():
        if numero in premier:
            doubles.append((numero, premier[numero], role))
        else:
            premier[numero] = role
    return doubles


def broches_libres():
    """La liste des broches encore disponibles, dans l'ordre."""
    prises = broches_deja_prises()
    return [numero for numero in range(49)
            if numero not in prises and verifier_broche(numero)[0] == "libre"]


def broches(secondes=60):
    """À FAIRE AVANT DE SOUDER. Chaque broche déclarée est-elle utilisable ?

    D'abord la théorie : le brochage de l'ESP32-S3 dit si la broche est
    libre, déconseillée ou réservée. Une broche réservée n'est même pas
    LUE — créer un Pin sur une broche de la flash suffit à faire tomber la
    carte.

    Ensuite la pratique : l'état de chaque entrée est affiché en continu.
    Relie la broche à GND avec un fil et son 1 doit passer à 0. Une broche
    qui reste à 0 sans que tu y touches est tenue basse par quelque chose
    sur la carte : elle ne pourra pas servir de touche.
    """
    from machine import Pin
    print("-" * 46)
    print("VERIFICATION DES BROCHES - a faire AVANT de souder")
    print("-" * 46)

    # (nom, numero, pull) : une touche relie sa broche a GND, donc pull-up.
    # Un module TTP223 d'usine POUSSE sa sortie a 3,3 V, donc pull-down.
    ttp_pull = Pin.PULL_DOWN if C.TTP_ACTIVE_HIGH else Pin.PULL_UP
    attendues = [("B%d" % (rang + 1), numero, Pin.PULL_UP)
                 for rang, numero in enumerate(C.BUTTON_PINS)]
    attendues.append(("ESC", C.ESC_PIN, Pin.PULL_UP))
    attendues.append(("PREV", C.TTP_PREVIOUS_PIN, ttp_pull))
    attendues.append(("NEXT", C.TTP_NEXT_PIN, ttp_pull))

    vues = {}
    lisibles = []
    refusees = 0
    for nom, numero, pull in attendues:
        verdict, raison = verifier_broche(numero)
        if numero in vues:
            print("  %-5s GPIO%-2d  DOUBLON : deja prise par %s"
                  % (nom, numero, vues[numero]))
            refusees += 1
            continue
        vues[numero] = nom
        if verdict == "reservee" or verdict == "inexistante":
            print("  %-5s GPIO%-2d  %s : %s" % (nom, numero, verdict.upper(), raison))
            print("        NE SOUDE PAS ICI. Corrige config.py d'abord.")
            refusees += 1
            continue
        if verdict == "deconseillee":
            print("  %-5s GPIO%-2d  a eviter : %s" % (nom, numero, raison))
        else:
            print("  %-5s GPIO%-2d  libre" % (nom, numero))
        lisibles.append((nom, Pin(numero, Pin.IN, pull)))

    print("")
    print("Broches encore disponibles :", broches_libres())
    if refusees:
        print("")
        print("%d broche(s) a corriger dans config.py AVANT de souder." % refusees)
    if not lisibles:
        return False

    print("")
    print("Au repos, tout doit afficher le meme niveau.")
    print("Touche une broche avec un fil relie a GND : son niveau change.")
    print("Ctrl-C pour arreter (%d s sinon)." % secondes)
    debut = ticks_ms()
    try:
        while ticks_diff(ticks_ms(), debut) < int(secondes * 1000):
            print("  " + "  ".join("%s=%d" % (nom, broche.value())
                                   for nom, broche in lisibles))
            sleep_ms(400)
    except KeyboardInterrupt:
        print("Arret demande.")
    print("-" * 46)
    return refusees == 0


def keymap(text="_MATCHPROP"):
    """Montre comment chaque caractère sera tapé. Aucun matériel requis.

    C'est le test à faire en premier si Civil 3D reçoit des lettres
    fausses : il affiche le numéro de touche envoyé pour chaque caractère.
    """
    from layouts import character_keys, TABLES
    print("-" * 46)
    print("DISPOSITION :", C.KEYBOARD_LAYOUT,
          "(%d caracteres connus)" % len(TABLES[C.KEYBOARD_LAYOUT]))
    print("Chaine testee :", text)
    print("  Verr. Maj ETEINT :")
    for char in text:
        print("    %-4r -> %s" % (char, character_keys(char, C.KEYBOARD_LAYOUT)))
    print("  Verr. Maj ALLUME (Windows FR inverse la rangee des chiffres) :")
    for char in text[:3]:
        print("    %-4r -> %s" % (char,
                                  character_keys(char, C.KEYBOARD_LAYOUT, True)))
    print("Rappel : en AZERTY le '_' doit sortir en touche 37 sans Maj.")
    return True


def rgb(nb=None, broche=None, luminosite=12):
    """Teste le cablage des LED RGB, une LED a la fois.

    A faire APRES avoir soude et AVANT de passer RGB_ENABLED a True. Ce
    test n'utilise pas rgb.py : il parle directement aux LED, pour que ce
    soit bien TON cablage qui soit teste, et pas la configuration.

        diag.rgb()          # utilise RGB_PIN et RGB_COUNT
        diag.rgb(6, 17)     # six LED sur GPIO17

    Ce que tu dois voir, dans l'ordre :

      1. les LED s'allument UNE PAR UNE, de la premiere a la derniere.
         Compte-les : si tu en as soude six et qu'il s'en allume quatre,
         la suite du ruban ne recoit pas les donnees ;
      2. puis ROUGE, VERT, BLEU sur toutes. Si les couleurs ne
         correspondent pas aux noms annonces, note l'ordre reel et
         corrige RGB_ORDRE dans config.py ;
      3. enfin une montee en luminosite. Si la carte redemarre pendant
         cette phase, c'est le courant : condensateur manquant, ou
         alimentation trop faible.

    La luminosite est volontairement basse (12 sur 255) : on teste un
    cablage, pas un eclairage. Ne la monte pas pour "mieux voir".
    """
    from machine import Pin
    try:
        from neopixel import NeoPixel
    except ImportError:
        print("neopixel absent de ce firmware MicroPython.")
        return

    if nb is None:
        nb = getattr(C, "RGB_COUNT", 6)
    if broche is None:
        broche = getattr(C, "RGB_PIN", 16)
    print("-" * 46)
    print("TEST RGB : %d LED sur GPIO%d" % (nb, broche))
    print("Luminosite de test :", luminosite, "sur 255")
    print("-" * 46)

    bande = NeoPixel(Pin(broche, Pin.OUT), nb)

    def tout(couleur):
        for index in range(nb):
            bande[index] = couleur
        bande.write()

    try:
        # 1. Une par une : on compte, et on verifie que la chaine passe.
        print("1. Chenillard : compte les LED qui s'allument")
        for index in range(nb):
            tout((0, 0, 0))
            bande[index] = (luminosite, luminosite, luminosite)
            bande.write()
            print("   LED %d" % (index + 1))
            sleep_ms(500)

        # 2. Les trois couleurs, pour verifier l'ordre des octets.
        print("2. Couleurs : annonce -> ce que tu dois voir")
        ordre = getattr(C, "RGB_ORDRE", "GRB")
        for nom, valeurs in (("ROUGE", {"R": luminosite}),
                             ("VERT", {"G": luminosite}),
                             ("BLEU", {"B": luminosite})):
            couleur = tuple(valeurs.get(lettre, 0) for lettre in ordre)
            print("   %s   (RGB_ORDRE = %s)" % (nom, ordre))
            tout(couleur)
            sleep_ms(1200)

        # 3. Montee en luminosite : c'est ici que le courant se voit.
        print("3. Montee en luminosite - la carte doit rester stable")
        for niveau in range(0, 41, 4):
            tout((niveau, niveau, niveau))
            sleep_ms(200)
        print("   (on redescend)")
        tout((0, 0, 0))
        print("-" * 46)
        print("Si tout est bon : RGB_ENABLED = True dans config.py.")
        print("Si les couleurs sont permutees : change RGB_ORDRE.")
    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        # On n'abandonne JAMAIS les LED allumees.
        try:
            tout((0, 0, 0))
        except Exception:
            pass


def rgb_pin(broches=None, nb=None, luminosite=12, secondes=3):
    """Sur QUELLE broche le fil de donnees est-il vraiment soude ?

    Le ruban ne repond a rien et tu ne sais plus sur quelle broche il est
    cable : cette fonction balaie les broches candidates une par une, en
    annoncant chacune et en allumant TOUT le ruban en blanc pendant
    quelques secondes.

    Tu regardes le RUBAN, pas l'ecran : la broche annoncee au moment ou il
    s'allume est la bonne. Note-la dans RGB_PIN.

        diag.rgb_pin()              # les broches plausibles
        diag.rgb_pin([16, 17])      # seulement celles-la

    Ne balaie QUE des broches libres : celles qui portent deja les
    touches, l'ecran ou le bouton ESC sont ecartees, et les broches
    reservees par la flash, la PSRAM ou l'USB ne sont jamais touchees.
    """
    from machine import Pin
    try:
        from neopixel import NeoPixel
    except ImportError:
        print("neopixel absent de ce firmware MicroPython.")
        return False

    if nb is None:
        nb = getattr(C, "RGB_COUNT", 6)
    if broches is None:
        # La broche configuree d'abord, puis ses voisines habituelles.
        candidates = [getattr(C, "RGB_PIN", 16), 16, 17, 18, 21, 47, 48]
        prises = broches_deja_prises()
        role_rgb = "donnees des LED RGB"
        broches = []
        for numero in candidates:
            if numero in broches:
                continue
            if verifier_broche(numero)[0] != "libre":
                continue
            if prises.get(numero, role_rgb) != role_rgb:
                continue          # cette broche sert deja a autre chose
            broches.append(numero)

    print("-" * 46)
    print("RECHERCHE DE LA BROCHE DES LED")
    print("-" * 46)
    print("REGARDE LE RUBAN, pas l'ecran.")
    print("Il s'allume en blanc quand on tombe sur la bonne broche.")
    print("%d broche(s) a essayer, %d s chacune." % (len(broches), secondes))
    print("-" * 46)
    try:
        for numero in broches:
            print("  -> GPIO%d" % numero)
            bande = NeoPixel(Pin(numero, Pin.OUT), nb)
            for index in range(nb):
                bande[index] = (luminosite, luminosite, luminosite)
            bande.write()
            sleep_ms(int(secondes * 1000))
            for index in range(nb):
                bande[index] = (0, 0, 0)
            bande.write()
            sleep_ms(300)
    except KeyboardInterrupt:
        print("Arret demande.")
    print("-" * 46)
    print("Le ruban s'est allume sur une broche ? Mets-la dans RGB_PIN.")
    print("Sur aucune ? Le probleme n'est alors pas la broche :")
    print("  - le fil de donnees entre-t-il bien par DIN (sens des fleches) ?")
    print("  - la premiere LED est-elle grillee ? essaie diag.rgb_saute(1)")
    print("  - le GND du ruban et celui de la carte sont-ils relies ?")
    print("-" * 46)
    return True


def rgb_saute(combien=1, nb=None, broche=None, luminosite=12):
    """Teste le ruban en IGNORANT ses premieres LED.

    Une WS2812 grillee ne transmet plus rien a ses voisines : tout le
    ruban parait mort alors qu'une seule puce l'est. On envoie donc du
    noir aux premieres, et de vraies couleurs ensuite.

        diag.rgb_saute(1)      # la premiere LED est morte

    Si le ruban se reveille a partir de la suivante, tu as ta reponse.

    ATTENTION A CE QUI L'A TUEE : alimenter un ruban WS2812 dont le GND
    n'est PAS relie force le courant de retour a passer par le fil de
    donnees. C'est le meilleur moyen de griller la premiere puce, et
    d'abimer le GPIO au passage.
    """
    from machine import Pin
    try:
        from neopixel import NeoPixel
    except ImportError:
        print("neopixel absent de ce firmware MicroPython.")
        return False

    if nb is None:
        nb = getattr(C, "RGB_COUNT", 6)
    if broche is None:
        broche = getattr(C, "RGB_PIN", 16)
    total = nb + combien
    print("-" * 46)
    print("TEST EN IGNORANT %d LED, sur GPIO%d" % (combien, broche))
    print("Le ruban est pilote comme s'il avait %d LED : les %d premieres"
          % (total, combien))
    print("recoivent du noir, les %d suivantes s'allument une par une." % nb)
    print("-" * 46)
    bande = NeoPixel(Pin(broche, Pin.OUT), total)
    try:
        for index in range(nb):
            for rang in range(total):
                bande[rang] = (0, 0, 0)
            bande[combien + index] = (luminosite, luminosite, luminosite)
            bande.write()
            print("   LED %d (la %d-eme du ruban)"
                  % (index + 1, combien + index + 1))
            sleep_ms(500)
    except KeyboardInterrupt:
        print("Arret demande.")
    finally:
        try:
            for rang in range(total):
                bande[rang] = (0, 0, 0)
            bande.write()
        except Exception:
            pass
    print("-" * 46)
    print("Elles repondent ? Les %d premieres puces sont mortes." % combien)
    print("Recable DIN sur la LED suivante, ou garde ce decalage.")
    print("-" * 46)
    return True


def run(seconds=20, led_test=False):
    """Diagnostic complet du matériel branché."""
    import machine
    import runtime
    from inputs import Inputs
    from display import Display

    # --- 1. Informations sur le firmware ---------------------------
    print("-" * 46)
    print("MicroPython :", sys.version)
    print("Implementation :", sys.implementation)
    print("Plateforme :", sys.platform)
    # Si cette ligne affiche False, le clavier USB est impossible :
    # ce n'est pas le bon firmware.
    print("machine.USBDevice disponible :", hasattr(machine, "USBDevice"))
    print("HID initialise au boot :", runtime.interface is not None)
    print("Envois HID : DESACTIVES en diagnostic")

    # --- 2. Ecran ---------------------------------------------------
    print("I2C bus", C.I2C_ID, "SDA", C.OLED_SDA, "SCL", C.OLED_SCL)
    print("OLED : attention, un ACK I2C prouve qu'un ecran repond,")
    print("       pas que son controleur est bien un SH1106.")
    display = Display()
    display.message("DIAGNOSTIC", "HID DISABLED")
    display.flush_startup()

    # --- 3. Etat instantané des entrées ----------------------------
    controls = Inputs()
    print("Etat initial des entrees :")
    for name, item in controls.sequence:
        print("  %-9s actif = %-5s  niveau electrique = %d"
              % (name, item.active(), item.pin.value()))
    print("Au repos, tout doit afficher 'actif = False'.")
    print("Si une entree est active sans que tu y touches, verifie son cablage.")

    # --- 4. LED (facultatif) ---------------------------------------
    led = None
    if led_test:
        from led import Led
        led = Led()
        print("LED : 0-3 s a 5 %, 3-6 s a 20 %, puis respiration.")
        print("      Appuie sur ESC pour declencher le flash.")
        print("      TOUCHE la LED et la resistance : elles doivent rester froides.")

    # --- 5. Surveillance des entrées -------------------------------
    print("Actionne maintenant chaque touche, une par une (%d s) :" % seconds)
    start = ticks_ms()
    compteur = {}
    try:
        while ticks_diff(ticks_ms(), start) < int(seconds * 1000):
            now = ticks_ms()
            for name, edge in controls.poll(now):
                if edge == 1:
                    compteur[name] = compteur.get(name, 0) + 1
                    print("  %-9s APPUI/TOUCHER  (total %d)"
                          % (name, compteur[name]))
                    if led and name == "ESC":
                        led.flash(now)
                else:
                    print("  %-9s relachement" % name)
            if led:
                age = ticks_diff(now, start)
                if age < 3000:
                    led.set_level(0.05)
                elif age < 6000:
                    led.set_level(0.20)
                else:
                    led.tick(now)
            sleep_ms(5)
    except KeyboardInterrupt:
        print("  interrompu")
    finally:
        if led:
            led.close()

    # --- 6. Bilan ---------------------------------------------------
    print("Bilan des appuis detectes :")
    for name, _ in controls.sequence:
        print("  %-9s : %d" % (name, compteur.get(name, 0)))
    print("Un appui franc doit compter EXACTEMENT 1.")
    print("S'il en compte 2 ou 3 : augmente DEBOUNCE_MS dans config.py.")
    print("Diagnostic termine, retour REPL")


if __name__ == "__main__":
    run()
