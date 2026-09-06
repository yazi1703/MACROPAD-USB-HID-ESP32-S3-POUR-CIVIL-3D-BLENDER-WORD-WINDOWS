# -*- coding: utf-8 -*-
"""
macropad_auto.py - Le compagnon Windows du macropad.

Ce programme tourne sur le PC, pas sur la carte. Il fait deux choses :

  1. DETECTION AUTOMATIQUE : il regarde toutes les 400 ms quelle
     application est au premier plan et dit au macropad quel profil
     activer. Tu passes sur Civil 3D, le macropad bascule tout seul.
     Il envoie aussi le nom du document, que l'ecran affiche.

  2. PAGE DE CONFIGURATION : il sert une page web sur
     http://127.0.0.1:8765 ou tu modifies tes macros a la souris. Les
     changements partent par le port serie et s'appliquent
     IMMEDIATEMENT, sans redemarrer le macropad.

=====================================================================
INSTALLATION
=====================================================================
    py -m pip install pyserial

Puis, dans une invite de commandes :

    py macropad_auto.py

Pour verifier que la detection marche sans avoir le macropad branche :

    py macropad_auto.py --simuler

=====================================================================
QUEL PORT SERIE ?
=====================================================================
La carte expose DEUX ports COM :
  * celui du pont USB-serie (CH343, CP210x...) -> reserve a Thonny
  * celui de l'USB natif de l'ESP32-S3         -> c'est celui-ci

Le script reconnait le second a son identifiant fabricant Espressif
(VID 0x303A) et le choisit tout seul. Tu peux forcer :

    py macropad_auto.py --port COM7

ATTENTION : un port serie ne s'ouvre qu'une fois. Si Thonny est connecte
au port NATIF, ce script ne pourra pas l'ouvrir. Garde Thonny sur le port
UART, c'est justement a ca qu'il sert.

=====================================================================
QUELS LOGICIELS ?
=====================================================================
La table est dans macropad_apps.txt, cree automatiquement a cote de ce
script au premier lancement. Une ligne par logiciel :

    acad.exe = CIVIL3D
    blender.exe = BLENDER
    winword.exe = WORD

Tout ce qui n'est pas dans la liste bascule sur le profil de repli
(WINDOWS par defaut). Le fichier est relu a chaud : pas besoin de
relancer le script apres l'avoir modifie.
"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DOSSIER = os.path.dirname(os.path.abspath(__file__))
FICHIER_APPS = os.path.join(DOSSIER, "macropad_apps.txt")
VID_ESPRESSIF = 0x303A
PORT_WEB = 8765

APPS_PAR_DEFAUT = """# Association logiciel -> profil du macropad.
# Une ligne par logiciel :  nom_du_programme.exe = NOM_DU_PROFIL
# Les lignes vides et celles commencant par # sont ignorees.
# Ce fichier est relu automatiquement, inutile de relancer le script.

acad.exe = CIVIL3D
acadlt.exe = CIVIL3D
blender.exe = BLENDER
winword.exe = WORD

# Quelques exemples a decommenter ou adapter :
# excel.exe = WORD
# qgis-bin.exe = QGIS
# notepad.exe = WINDOWS

# Profil utilise pour tout le reste :
* = WINDOWS
"""


# =====================================================================
# 1. Lire quelle application est au premier plan (API Windows)
# =====================================================================
class FenetreActive:
    """Interroge Windows sans dependance supplementaire, via ctypes."""

    def __init__(self):
        self.disponible = False
        if sys.platform != "win32":
            return
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.disponible = True

    def lire(self):
        """Retourne (nom_du_programme, titre_de_la_fenetre)."""
        if not self.disponible:
            return "", ""
        ctypes, wintypes = self.ctypes, self.wintypes
        fenetre = self.user32.GetForegroundWindow()
        if not fenetre:
            return "", ""

        # --- titre de la fenetre ---
        longueur = self.user32.GetWindowTextLengthW(fenetre)
        tampon = ctypes.create_unicode_buffer(longueur + 1)
        self.user32.GetWindowTextW(fenetre, tampon, longueur + 1)
        titre = tampon.value

        # --- nom de l'executable ---
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(fenetre, ctypes.byref(pid))
        # 0x1000 = PROCESS_QUERY_LIMITED_INFORMATION : le droit minimal,
        # il fonctionne sans etre administrateur.
        poignee = self.kernel32.OpenProcess(0x1000, False, pid.value)
        if not poignee:
            return "", titre
        try:
            chemin = ctypes.create_unicode_buffer(512)
            taille = wintypes.DWORD(512)
            self.kernel32.QueryFullProcessImageNameW(
                poignee, 0, chemin, ctypes.byref(taille))
            programme = os.path.basename(chemin.value)
        finally:
            self.kernel32.CloseHandle(poignee)
        return programme, titre


# =====================================================================
# 2. La table logiciel -> profil
# =====================================================================
class TableApplications:
    """Lit macropad_apps.txt et le relit tout seul quand il change."""

    def __init__(self, chemin):
        self.chemin = chemin
        self.regles = {}
        self.repli = "WINDOWS"
        self._date = 0
        if not os.path.exists(chemin):
            with open(chemin, "w", encoding="utf-8") as fichier:
                fichier.write(APPS_PAR_DEFAUT)
            print("Table des logiciels creee :", chemin)
        self.recharger()

    def recharger(self):
        try:
            date = os.path.getmtime(self.chemin)
        except OSError:
            return
        if date == self._date:
            return
        self._date = date
        regles, repli = {}, "WINDOWS"
        try:
            with open(self.chemin, encoding="utf-8") as fichier:
                for ligne in fichier:
                    ligne = ligne.strip()
                    if not ligne or ligne.startswith("#") or "=" not in ligne:
                        continue
                    cle, valeur = ligne.split("=", 1)
                    cle, valeur = cle.strip().lower(), valeur.strip().upper()
                    if cle == "*":
                        repli = valeur
                    else:
                        regles[cle] = valeur
        except OSError as exc:
            print("Table des logiciels illisible :", exc)
            return
        self.regles, self.repli = regles, repli
        print("Table des logiciels rechargee : %d regles, repli %s"
              % (len(regles), repli))

    def profil(self, programme):
        return self.regles.get((programme or "").lower(), self.repli)


def nom_document(titre, programme):
    """Extrait un nom de document lisible du titre de la fenetre.

    Les titres Windows ressemblent a "Projet_A12.dwg - Autodesk Civil 3D"
    ou "Rapport.docx - Word". On garde le premier morceau, qui est
    presque toujours le nom du fichier.
    """
    if not titre:
        return ""
    for separateur in (" - ", " — ", " | "):
        if separateur in titre:
            titre = titre.split(separateur)[0]
            break
    titre = titre.strip().lstrip("*").strip()      # * = document modifie
    return titre[:16]


# =====================================================================
# 3. Le dialogue avec le macropad
# =====================================================================
class Macropad:
    """Port serie vers la carte, protege par un verrou.

    Le fil de la detection et celui du serveur web s'en servent tous les
    deux : le verrou garantit qu'un echange de configuration n'est pas
    coupe en deux par un envoi de profil.
    """

    def __init__(self, port=None, simuler=False):
        self.simuler = simuler
        self.port = port
        self.serie = None
        self.verrou = threading.Lock()
        if not simuler:
            self.ouvrir()

    # ------------------------------------------------------------------
    @staticmethod
    def trouver_port():
        """Cherche le port USB natif de l'ESP32-S3 (fabricant Espressif)."""
        from serial.tools import list_ports
        candidats = []
        for infos in list_ports.comports():
            if infos.vid == VID_ESPRESSIF:
                candidats.append(infos.device)
        if candidats:
            return candidats[0]
        return None

    def ouvrir(self):
        import serial
        if self.port is None:
            self.port = self.trouver_port()
        if self.port is None:
            raise SystemExit(
                "Aucun port Espressif trouve.\n"
                "Branche le port USB NATIF du macropad, ou precise le port :\n"
                "    py macropad_auto.py --port COM7")
        self.serie = serial.Serial(self.port, 115200, timeout=0.3)
        print("Macropad connecte sur", self.port)

    # ------------------------------------------------------------------
    def _ecrire(self, ligne):
        if self.simuler:
            print("  -> %s" % ligne)
            return
        self.serie.write((ligne + "\n").encode())

    def envoyer(self, ligne):
        with self.verrou:
            self._ecrire(ligne)

    def _lire_reponse(self, fin, delai=3.0):
        """Lit jusqu'au marqueur de fin. Ignore les messages de debogage."""
        if self.simuler:
            return []
        lignes = []
        limite = time.time() + delai
        while time.time() < limite:
            brut = self.serie.readline()
            if not brut:
                continue
            ligne = brut.decode("utf-8", "replace").strip()
            if not ligne.startswith("#"):
                continue          # trace normale du firmware, pas pour nous
            if ligne == fin:
                return lignes
            lignes.append(ligne)
        raise TimeoutError("le macropad n'a pas repondu (%s)" % fin)

    # ------------------------------------------------------------------
    def lire_config(self):
        """Demande la configuration complete au macropad."""
        with self.verrou:
            if self.simuler:
                return {"ordre": [], "profils": {}, "touches": 6,
                        "origine": "simulation"}
            self.serie.reset_input_buffer()
            self._ecrire("?CFG")
            self._lire_reponse("#CFGBEGIN")
            morceaux = self._lire_reponse("#CFGEND")
        texte = "".join(m[3:] for m in morceaux if m.startswith("#C:"))
        return json.loads(texte)

    def ecrire_config(self, data):
        """Envoie une configuration. Retourne (True, "") ou (False, raison)."""
        texte = json.dumps(data)
        with self.verrou:
            if self.simuler:
                self._ecrire("!CFGBEGIN ... %d octets ... !CFGEND" % len(texte))
                return True, ""
            self.serie.reset_input_buffer()
            self._ecrire("!CFGBEGIN")
            for debut in range(0, len(texte), 160):
                self._ecrire("!C:" + texte[debut:debut + 160])
            self._ecrire("!CFGEND")
            limite = time.time() + 5.0
            while time.time() < limite:
                brut = self.serie.readline()
                if not brut:
                    continue
                ligne = brut.decode("utf-8", "replace").strip()
                if ligne.startswith("#OK:"):
                    return True, ""
                if ligne.startswith("#KO:"):
                    return False, ligne[4:]
        return False, "le macropad n'a pas confirme"


# =====================================================================
# 4. La page de configuration, servie sur http://127.0.0.1:8765
# =====================================================================
# Note : cette page est volontairement proche de celle de device/portal.py.
# Les deux existent parce qu'elles servent des cas differents : celle-ci
# passe par le cable USB, l'autre par le WiFi depuis un telephone.
PAGE = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Macropad</title><style>
*{box-sizing:border-box}body{margin:0;padding:16px;background:#14161a;color:#e6e8ec;
font:14px/1.5 system-ui,sans-serif}h1{font-size:18px;margin:0 0 4px}
p.sub{margin:0 0 20px;color:#9aa3af}
.prof{background:#1c1f26;border:1px solid #2a2f3a;border-radius:10px;padding:14px;margin-bottom:14px}
.head{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.head input{flex:1;min-width:120px}
input,select{background:#0f1115;color:#e6e8ec;border:1px solid #2a2f3a;
border-radius:6px;padding:7px 8px;font:13px/1.2 ui-monospace,monospace}
table{width:100%;border-collapse:collapse}td{padding:3px 4px 3px 0}
td.n{width:26px;color:#7c8698;text-align:right;font:12px ui-monospace,monospace}
.lab{width:88px}.val{width:100%}
button{background:#2f6feb;color:#fff;border:0;border-radius:6px;padding:9px 14px;
font:600 13px system-ui;cursor:pointer}button.g{background:#2a2f3a}
button.r{background:#7a2230}.bar{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
#msg{margin-top:14px;padding:10px 12px;border-radius:8px;display:none;white-space:pre-wrap}
.ok{background:#123524;border:1px solid #1f7a4d}.ko{background:#3a1620;border:1px solid #8a2b3f}
</style></head><body>
<h1>Macropad &mdash; configuration par USB</h1>
<p class="sub">Libelles : 6 caracteres max. Combinaison : <code>CTRL+MAJ+ESC</code>.
Les changements s'appliquent <b>immediatement</b>, sans redemarrer.</p>
<div id="app">Chargement...</div>
<div class="bar">
<button onclick="addProfil()" class="g">+ Profil</button>
<button onclick="save()">Enregistrer</button>
<button onclick="telecharger()" class="g">Telecharger la sauvegarde</button>
</div>
<div id="msg"></div>
<script>
let D={ordre:[],profils:{}},N=6;
const TYPES=[["key","touche"],["combo","combinaison"],["text","texte"],
["text_enter","texte + Entree"],["none","inactive"]];
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/"/g,"&quot;")}
function render(){
 let h="";
 D.ordre.forEach(function(nom){
  const p=D.profils[nom];if(!p)return;
  h+='<div class="prof"><div class="head"><input value="'+esc(nom)+
     '" onchange="ren(this,\\''+esc(nom)+'\\')" title="nom interne">'+
     '<input value="'+esc(p.titre)+'" oninput="D.profils[\\''+esc(nom)+
     '\\'].titre=this.value" title="titre a l\\'ecran">'+
     '<button class="r" onclick="del(\\''+esc(nom)+'\\')">Supprimer</button></div><table>';
  for(let i=0;i<N;i++){
   const t=p.touches[i]||{label:"",type:"none",valeur:""};
   let o="";TYPES.forEach(function(x){
    o+='<option value="'+x[0]+'"'+(t.type==x[0]?" selected":"")+'>'+x[1]+'</option>'});
   h+='<tr><td class="n">B'+(i+1)+'</td>'+
      '<td><input class="lab" maxlength="6" value="'+esc(t.label)+
      '" oninput="set(\\''+esc(nom)+'\\','+i+',\\'label\\',this.value)"></td>'+
      '<td><select onchange="set(\\''+esc(nom)+'\\','+i+',\\'type\\',this.value)">'+o+'</select></td>'+
      '<td><input class="val" value="'+esc(t.valeur)+
      '" oninput="set(\\''+esc(nom)+'\\','+i+',\\'valeur\\',this.value)"></td></tr>';
  }
  h+="</table></div>";
 });
 document.getElementById("app").innerHTML=h;
}
function set(n,i,k,v){const p=D.profils[n];
 while(p.touches.length<N)p.touches.push({label:"",type:"none",valeur:""});
 p.touches[i][k]=v}
function ren(el,anc){const nv=el.value.trim();if(!nv||D.profils[nv]){render();return}
 D.profils[nv]=D.profils[anc];delete D.profils[anc];
 D.ordre=D.ordre.map(function(x){return x==anc?nv:x});render()}
function del(n){if(D.ordre.length<2){return say("Il faut au moins un profil",0)}
 delete D.profils[n];D.ordre=D.ordre.filter(function(x){return x!=n});render()}
function addProfil(){let n="PROFIL",i=1;while(D.profils[n])n="PROFIL"+(++i);
 D.profils[n]={titre:n,touches:[]};
 for(let k=0;k<N;k++)D.profils[n].touches.push({label:"",type:"none",valeur:""});
 D.ordre.push(n);render()}
function say(t,ok){const m=document.getElementById("msg");
 m.textContent=t;m.className=ok?"ok":"ko";m.style.display="block"}
function save(){fetch("/api/profils",{method:"POST",body:JSON.stringify(D)})
 .then(function(r){return r.json()}).then(function(r){
  say(r.ok?"Applique immediatement sur le macropad.":"Refuse :\\n"+r.raison,r.ok)})
 .catch(function(e){say("Erreur : "+e,0)})}
function telecharger(){const a=document.createElement("a");
 a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,2)],{type:"application/json"}));
 a.download="macropad_profils.json";a.click()}
fetch("/api/profils").then(function(r){return r.json()}).then(function(d){
 if(d.erreur){return say("Lecture impossible : "+d.erreur,0)}
 D=d;N=d.touches||6;render()}).catch(function(e){say("Erreur : "+e,0)});
</script></body></html>"""


def creer_serveur(macropad):
    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *args):
            pass          # on ne veut pas polluer la console

        def _repondre(self, corps, mime="application/json", code=200):
            if isinstance(corps, str):
                corps = corps.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if self.path.startswith("/api/profils"):
                try:
                    self._repondre(json.dumps(macropad.lire_config()))
                except Exception as exc:
                    self._repondre(json.dumps({"erreur": str(exc)}))
            else:
                self._repondre(PAGE, "text/html")

        def do_POST(self):
            taille = int(self.headers.get("Content-Length", 0))
            corps = self.rfile.read(taille)
            try:
                data = json.loads(corps)
            except Exception as exc:
                self._repondre(json.dumps({"ok": False,
                                           "raison": "JSON invalide : %s" % exc}))
                return
            try:
                ok, raison = macropad.ecrire_config(data)
            except Exception as exc:
                ok, raison = False, str(exc)
            print("Configuration :", "appliquee" if ok else "refusee (%s)" % raison)
            self._repondre(json.dumps({"ok": ok, "raison": raison}))

    return ThreadingHTTPServer(("127.0.0.1", PORT_WEB), Handler)


# =====================================================================
# 5. Programme principal
# =====================================================================
def main():
    analyseur = argparse.ArgumentParser(description="Compagnon du macropad")
    analyseur.add_argument("--port", help="port COM du macropad (sinon auto)")
    analyseur.add_argument("--simuler", action="store_true",
                           help="afficher ce qui serait envoye, sans macropad")
    analyseur.add_argument("--periode", type=float, default=0.4,
                           help="intervalle de detection en secondes")
    options = analyseur.parse_args()

    fenetre = FenetreActive()
    if not fenetre.disponible:
        print("ATTENTION : detection de la fenetre active indisponible")
        print("(ce script est prevu pour Windows). La page de configuration")
        print("fonctionne quand meme.")

    table = TableApplications(FICHIER_APPS)
    macropad = Macropad(options.port, options.simuler)

    serveur = creer_serveur(macropad)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    print("Page de configuration : http://127.0.0.1:%d" % PORT_WEB)
    print("Ctrl-C pour arreter.")
    print("-" * 50)

    dernier_profil = None
    dernier_document = None
    try:
        while True:
            table.recharger()
            programme, titre = fenetre.lire()
            profil = table.profil(programme)
            document = nom_document(titre, programme)

            if profil != dernier_profil:
                dernier_profil = profil
                print("%-22s -> %s" % (programme or "(inconnu)", profil))
                macropad.envoyer("P:" + profil)
            if document != dernier_document:
                dernier_document = document
                macropad.envoyer("T:" + document)

            time.sleep(options.periode)
    except KeyboardInterrupt:
        print("\nArret.")
    finally:
        serveur.shutdown()


if __name__ == "__main__":
    main()
