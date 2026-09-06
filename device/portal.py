# -*- coding: utf-8 -*-
"""
portal.py - Le mode configuration : point d'accès WiFi + page web.

=====================================================================
COMMENT ÇA S'UTILISE
=====================================================================
1. Maintiens **B2** pendant que tu appuies sur RESET.
2. L'écran affiche le nom du réseau, la clé WiFi et l'adresse à ouvrir.
3. Sur ton PC ou ton téléphone, connecte-toi à ce réseau WiFi.
4. Ouvre **http://192.168.4.1** dans un navigateur.
5. Modifie tes profils et tes macros, puis « Enregistrer ».
6. RESET normal : le macropad redémarre avec tes nouvelles macros.

=====================================================================
POURQUOI C'EST UN MODE SÉPARÉ, ET PAS DU WIFI EN PERMANENCE
=====================================================================
Ce boîtier tape dans ton ordinateur. Si une radio était allumée en
permanence, quelqu'un à portée pourrait y déposer des commandes qui
s'exécuteraient ensuite chez toi. Ici :

* la radio ne s'allume que si TU maintiens un bouton au démarrage ;
* dans ce mode, le clavier USB n'est même pas créé : le macropad est
  physiquement incapable de taper quoi que ce soit ;
* le réseau est protégé par une clé WPA2 affichée sur l'écran, il faut
  donc voir l'appareil pour s'y connecter.

Change quand même `AP_PASSWORD` dans config.py.

=====================================================================
CE QUE LA PAGE SAIT FAIRE, ET CE QU'ELLE NE SAIT PAS
=====================================================================
Elle gère une action par touche : une touche seule, une combinaison, un
texte, ou un texte suivi d'Entrée. C'est ce qui couvre l'immense majorité
des besoins.

Les séquences à plusieurs actions (par exemple `_ZOOM` puis `E`) restent
réservées à profiles.py : les écrire dans un formulaire deviendrait vite
illisible. Si tu en as créé une à la main et que tu enregistres depuis la
page, elle sera remplacée par sa première action.
"""

import json
import socket
import time

import config as C
import store

# La page web. Volontairement compacte : elle tient dans la RAM de la carte.
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
<h1>Macropad &mdash; configuration</h1>
<p class="sub">Libelles : 6 caracteres max. Combinaison : <code>CTRL+MAJ+ESC</code>.
Apres enregistrement, faire un RESET.</p>
<div id="app"></div>
<div class="bar">
<button onclick="addProfil()" class="g">+ Profil</button>
<button onclick="save()">Enregistrer</button>
<button onclick="usine()" class="r">Profils d'usine</button>
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
  say(r.ok?"Enregistre. Fais un RESET pour appliquer.":"Refuse :\\n"+r.raison,r.ok)})
 .catch(function(e){say("Erreur reseau : "+e,0)})}
function usine(){if(!confirm("Revenir aux profils d'usine ?"))return;
 fetch("/api/usine",{method:"POST"}).then(function(){location.reload()})}
fetch("/api/profils").then(function(r){return r.json()}).then(function(d){
 D=d;N=d.touches||6;render()});
</script></body></html>"""


# =====================================================================
# Point d'accès WiFi
# =====================================================================
def demarrer_ap():
    """Allume le réseau WiFi du macropad. Retourne (ssid, cle, adresse)."""
    import network
    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    if len(C.AP_PASSWORD) < 8:
        print("[portal] ATTENTION : AP_PASSWORD fait moins de 8 caracteres,")
        print("[portal] le WiFi risque de refuser de demarrer.")

    reglages = {"essid": C.AP_SSID, "password": C.AP_PASSWORD,
                "channel": C.AP_CHANNEL}
    try:
        # WPA2 explicite. Le nom de la constante a varié selon les versions,
        # d'où le getattr avec une valeur de repli.
        reglages["authmode"] = getattr(network, "AUTH_WPA_WPA2_PSK", 4)
        ap.config(**reglages)
    except Exception:
        del reglages["authmode"]
        ap.config(**reglages)

    attente = 0
    while not ap.active() and attente < 5000:
        time.sleep_ms(100)
        attente += 100
    adresse = ap.ifconfig()[0]
    print("[portal] reseau '%s' actif, page sur http://%s" % (C.AP_SSID, adresse))
    return C.AP_SSID, C.AP_PASSWORD, adresse


def arreter_ap():
    try:
        import network
        network.WLAN(network.AP_IF).active(False)
    except Exception:
        pass


# =====================================================================
# Serveur web minimal
# =====================================================================
class Portail:

    def __init__(self, nb_touches):
        self.nb_touches = nb_touches
        self.serveur = None
        self.clients = 0

    def ouvrir(self):
        adresse = socket.getaddrinfo("0.0.0.0", C.AP_PORT)[0][-1]
        self.serveur = socket.socket()
        self.serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serveur.bind(adresse)
        self.serveur.listen(2)
        # Court délai d'attente : on rend la main régulièrement pour que la
        # LED continue de respirer même sans visiteur.
        self.serveur.settimeout(0.25)

    def fermer(self):
        if self.serveur:
            try:
                self.serveur.close()
            except Exception:
                pass
            self.serveur = None

    # ------------------------------------------------------------------
    def _etat_json(self):
        profils, ordre, titres, origine = store.charger(self.nb_touches)
        blocs = {}
        for nom, macros in profils.items():
            touches = []
            for label, actions in macros:
                kind, valeur = store.action_vers_json(actions)
                touches.append({"label": label, "type": kind, "valeur": valeur})
            blocs[nom] = {"titre": titres.get(nom, nom), "touches": touches}
        return {"ordre": ordre, "profils": blocs,
                "touches": self.nb_touches, "origine": origine}

    def _enregistrer(self, data):
        profils = {}
        titres = {}
        try:
            ordre = [str(n) for n in data["ordre"]]
            for nom, bloc in data["profils"].items():
                macros = []
                for touche in bloc["touches"][:self.nb_touches]:
                    actions = store.action_depuis_json(
                        touche.get("type", "none"), touche.get("valeur", ""))
                    macros.append((str(touche.get("label", ""))[:6], actions))
                while len(macros) < self.nb_touches:
                    macros.append(("", []))
                profils[str(nom)] = macros
                titres[str(nom)] = str(bloc.get("titre", nom))
        except Exception as exc:
            return False, "donnees illisibles : %s" % exc
        return store.enregistrer(profils, ordre, titres, self.nb_touches)

    # ------------------------------------------------------------------
    def _repondre(self, client, corps, type_mime="text/html", code="200 OK"):
        entete = ("HTTP/1.0 %s\r\nContent-Type: %s; charset=utf-8\r\n"
                  "Cache-Control: no-store\r\nConnection: close\r\n\r\n"
                  % (code, type_mime))
        client.write(entete.encode())
        if isinstance(corps, str):
            corps = corps.encode()
        # Envoi par morceaux : la page fait plusieurs kilo-octets et la pile
        # réseau de l'ESP32 n'avale pas tout d'un coup.
        for debut in range(0, len(corps), 512):
            client.write(corps[debut:debut + 512])

    def _traiter(self, client):
        ligne = client.readline()
        if not ligne:
            return
        try:
            methode, chemin, _ = ligne.decode().split(" ", 2)
        except ValueError:
            return

        taille = 0
        while True:
            entete = client.readline()
            if not entete or entete in (b"\r\n", b"\n"):
                break
            bas = entete.decode().lower()
            if bas.startswith("content-length:"):
                try:
                    taille = int(bas.split(":", 1)[1].strip())
                except ValueError:
                    taille = 0

        corps = client.read(taille) if taille else b""

        if chemin.startswith("/api/profils"):
            if methode == "POST":
                try:
                    data = json.loads(corps)
                except Exception as exc:
                    self._repondre(client,
                                   json.dumps({"ok": False,
                                               "raison": "JSON invalide : %s" % exc}),
                                   "application/json")
                    return
                ok, raison = self._enregistrer(data)
                print("[portal] enregistrement :", "OK" if ok else raison)
                self._repondre(client, json.dumps({"ok": ok, "raison": raison}),
                               "application/json")
            else:
                self._repondre(client, json.dumps(self._etat_json()),
                               "application/json")
        elif chemin.startswith("/api/usine") and methode == "POST":
            store.effacer()
            print("[portal] retour aux profils d'usine")
            self._repondre(client, json.dumps({"ok": True}), "application/json")
        elif chemin == "/" or chemin.startswith("/index"):
            self._repondre(client, PAGE)
        else:
            self._repondre(client, "introuvable", "text/plain", "404 Not Found")

    # ------------------------------------------------------------------
    def service(self):
        """Traite au plus un visiteur. Ne bloque jamais plus de 0,25 s."""
        if not self.serveur:
            return False
        try:
            client, _ = self.serveur.accept()
        except OSError:
            return False        # personne pour l'instant, c'est normal
        self.clients += 1
        try:
            client.settimeout(3)
            self._traiter(client)
        except Exception as exc:
            print("[portal] client abandonne :", exc)
        finally:
            try:
                client.close()
            except Exception:
                pass
        return True
