# -*- coding: utf-8 -*-
"""
injecter_page.py - Recopie tools/page_config.html dans les deux serveurs.

La meme page de configuration est servie a deux endroits :
  * device/portal.py    -> par le WiFi du macropad
  * pc/macropad_auto.py -> par le cable USB depuis le PC

Pour qu'elles ne divergent jamais, la source unique est
tools/page_config.html, et ce script l'injecte dans les deux fichiers.

    python3 tools/injecter_page.py

=====================================================================
POURQUOI UNE CHAINE BRUTE (prefixe r) ET PAS UNE CHAINE ORDINAIRE
=====================================================================
Dans une chaine Python ordinaire, l'antislash est un caractere
d'echappement : le \\n ecrit dans le JavaScript de la page deviendrait un
VRAI passage a la ligne au moment ou Python lit le fichier. Le texte
JavaScript

    say("Refuse :\\n" + r.raison)

se retrouverait coupe en deux lignes, la chaine ne serait plus fermee, et
le navigateur refuserait TOUT le script : la page s'affiche, mais elle
reste vide et aucun bouton ne repond. C'est exactement le bug qui est
arrive.

Le prefixe r (« raw », brut) supprime cette interpretation : ce qui est
ecrit dans la page arrive intact dans le navigateur. Ce script verifie en
plus, apres ecriture, que Python relit bien la page a l'identique.
"""

import ast
import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "tools", "page_config.html")
CIBLES = [os.path.join(RACINE, "device", "portal.py"),
          os.path.join(RACINE, "pc", "macropad_auto.py")]

DEBUTS = ('PAGE = r"""', 'PAGE = """')      # le second : ancienne forme
FIN = '"""'


def literal(page):
    """La page, sous forme de litteral Python brut."""
    return 'PAGE = r"""' + page + '\n"""'


def verifier(page):
    """Refuse une page que le litteral ne pourrait pas contenir."""
    if FIN in page:
        raise SystemExit("La page ne doit pas contenir de triple guillemet.")
    if page.endswith("\\"):
        # Une chaine brute ne peut pas finir par un antislash : il collerait
        # au guillemet fermant.
        raise SystemExit("La page ne doit pas finir par un antislash.")


def injecter(cible, page):
    with open(cible, encoding="utf-8") as fichier:
        source = fichier.read()

    for marqueur in DEBUTS:
        debut = source.find(marqueur)
        if debut != -1:
            break
    else:
        raise SystemExit("Marqueur PAGE introuvable dans " + cible)

    fin = source.index(FIN, debut + len(marqueur))
    neuf = source[:debut] + literal(page) + source[fin + len(FIN):]

    # Le controle qui manquait : Python relit-il la page a l'identique ?
    relu = ast.literal_eval(neuf[debut + len("PAGE = "):
                                 debut + len(literal(page))])
    if relu.rstrip("\n") != page:
        raise SystemExit("Le litteral ne redonne pas la page : injection "
                         "abandonnee pour " + cible)

    with open(cible, "w", encoding="utf-8") as fichier:
        fichier.write(neuf)
    print("page injectee dans", os.path.relpath(cible, RACINE))


def main():
    with open(SOURCE, encoding="utf-8") as fichier:
        page = fichier.read().rstrip("\n")
    verifier(page)
    for cible in CIBLES:
        injecter(cible, page)


if __name__ == "__main__":
    main()
