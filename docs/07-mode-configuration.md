# 7. Le mode configuration : WiFi et page web

Depuis la V1, tu n'as plus besoin de Thonny pour changer tes macros. Le
macropad sait allumer son propre réseau WiFi et servir une page web.

---

## 7.1 En trois minutes

1. **Maintiens B2** et appuie sur **RESET**. Relâche après 2 secondes.
2. L'écran affiche :

```
┌────────────────────────┐
│▓MODE CONFIG▓▓▓▓▓▓WIFI▓▓│
│ Reseau :               │
│ MACROPAD               │
│ Cle :                  │
│ macropad2026           │
│────────────────────────│
│ 192.168.4.1            │
└────────────────────────┘
```

3. Sur ton PC ou ton téléphone, connecte-toi au réseau WiFi **MACROPAD**
   avec la clé affichée.
4. Ouvre **http://192.168.4.1** dans un navigateur.
5. Modifie ce que tu veux, clique sur **Enregistrer**.
6. Fais un **RESET normal** : le macropad redémarre avec tes macros.

---

## 7.2 Pourquoi ce n'est pas du WiFi permanent

C'est un choix de sécurité, pas une limitation technique.

Ce boîtier **tape dans ton ordinateur**. Si sa radio était allumée en
permanence, quelqu'un à portée pourrait y déposer des commandes qui
s'exécuteraient ensuite chez toi, sans que tu voies rien. Une clé USB
malveillante, mais à distance.

Trois barrières :

1. **La radio ne s'allume que si tu maintiens un bouton au démarrage.**
   Il faut un accès physique au boîtier.
2. **Dans ce mode, `boot.py` ne crée aucun clavier USB.** Le macropad est
   *physiquement* incapable de taper. Même une configuration malveillante
   ne pourrait rien faire tant que tu n'as pas redémarré.
3. **Le réseau est protégé par une clé WPA2**, affichée sur l'écran : il
   faut voir l'appareil pour la lire.

> **À faire :** change `AP_PASSWORD` dans `config.py`. La valeur livrée est
> un exemple, et elle est publique puisqu'elle est dans ce dépôt.

Effet de bord appréciable : le WiFi et l'USB HID ne cohabitent jamais dans
les 224 Ko de RAM de la carte.

---

## 7.3 Ce que la page sait faire

| | |
|---|---|
| Renommer un profil | ✅ nom interne et titre affiché |
| Ajouter / supprimer un profil | ✅ |
| Changer les 6 macros d'un profil | ✅ libellé, type, valeur |
| Revenir aux profils d'usine | ✅ bouton dédié |
| Séquences à plusieurs actions | ❌ réservées à `profiles.py` |

Les quatre types de macro disponibles :

| Type | Valeur à saisir | Effet |
|---|---|---|
| touche | `TAB`, `F5`, `G` | une seule touche |
| combinaison | `CTRL+Z`, `CTRL+SHIFT+ESC` | plusieurs touches ensemble |
| texte | `_HATCH` | écrit la chaîne |
| texte + Entrée | `_MATCHPROP` | écrit la chaîne puis valide |
| inactive | — | la touche ne fait rien |

**Le libellé fait 6 caractères au maximum** : c'est ce que laisse la
demi-largeur de l'écran avec six touches.

---

## 7.4 Rien ne peut être enregistré au hasard

Avant l'écriture, **chaque macro est réellement traduite en codes clavier**
avec ta disposition (`KEYBOARD_LAYOUT`). Si un nom de touche est inconnu ou
si un caractère est impossible à taper en AZERTY, l'enregistrement est
refusé et la page t'affiche pourquoi :

```
Refuse :
WORD B1 (KO) : Touche inconnue dans la macro : 'TOUCHE_BIDON'
```

Il est donc impossible d'enregistrer une configuration qui planterait au
démarrage suivant.

Et si le fichier était malgré tout corrompu — coupure de courant, carte
retirée en pleine écriture — le firmware le détecte au démarrage, le
signale dans le REPL et **repart sur les profils d'usine**. Une carte ne
peut pas devenir inutilisable à cause de ce fichier.

L'écriture se fait d'ailleurs dans un fichier temporaire, renommé ensuite :
une coupure ne peut pas laisser un `profils.json` à moitié écrit.

---

## 7.5 Où sont rangées tes macros

Dans **`profils.json`**, à la racine de la carte. C'est du texte, tu peux
l'ouvrir dans Thonny pour voir ce qu'il contient :

```json
{
  "version": 1,
  "ordre": ["BLENDER", "CIVIL3D", "WORD", "WINDOWS"],
  "profils": {
    "CIVIL3D": {
      "titre": "CIVIL 3D",
      "touches": [
        {"label": "MATCH", "type": "text_enter", "valeur": "_MATCHPROP"},
        ...
      ]
    }
  }
}
```

**Supprimer ce fichier revient aux profils d'usine** de `profiles.py`.
C'est aussi ce que fait le bouton « Profils d'usine » de la page web.

Pense à en garder une copie sur ton PC quand ta configuration te convient :
c'est ta sauvegarde.

---

## 7.6 Si ça ne marche pas

| Symptôme | Cause probable |
|---|---|
| Aucun réseau `MACROPAD` visible | `AP_PASSWORD` fait moins de 8 caractères — le WiFi refuse alors de démarrer |
| Le réseau apparaît mais la page ne s'ouvre pas | vérifie l'adresse : `http://192.168.4.1`, pas `https` |
| Windows dit « pas d'accès Internet » | normal : ce réseau ne sert qu'à configurer le macropad, il n'est relié à rien |
| L'écran n'affiche pas MODE CONFIG | B2 n'était pas maintenu assez tôt — maintiens-le **avant** d'appuyer sur RESET |
| Les modifications ne s'appliquent pas | il faut un **RESET** après l'enregistrement |

Le REPL du port UART reste disponible pendant tout le mode configuration :
il affiche l'adresse, les connexions et le détail de chaque enregistrement.
