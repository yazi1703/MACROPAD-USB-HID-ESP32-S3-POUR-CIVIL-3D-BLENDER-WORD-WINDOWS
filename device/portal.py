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
PAGE = r"""<!DOCTYPE html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Macropad</title><style>
*{box-sizing:border-box}
body{margin:0;padding:0 0 40px;background:#0e1014;color:#e8eaee;
font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:9;background:#151922;
border-bottom:1px solid #262c3a;padding:14px 18px;display:flex;
align-items:center;gap:14px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;letter-spacing:.4px}
header .tag{font:11px ui-monospace,monospace;color:#8b94a6;
border:1px solid #2b3242;border-radius:99px;padding:3px 9px}
main{max-width:940px;margin:0 auto;padding:18px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:1px;
color:#8b94a6;margin:26px 0 10px;font-weight:600}
.card{background:#151922;border:1px solid #262c3a;border-radius:12px;
padding:14px;margin-bottom:12px}
.ph{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.ph .grow{flex:1;min-width:110px}
input,select{background:#0b0d12;color:#e8eaee;border:1px solid #2b3242;
border-radius:7px;padding:7px 9px;font:13px/1.2 ui-monospace,monospace;
width:100%}
input[type=color]{width:42px;flex:0 0 42px;padding:2px;height:33px;
cursor:pointer}
.val{display:flex;gap:5px;align-items:center}
.pile{display:flex;flex-direction:column;gap:5px}
.pile select{flex:0 0 138px}
.pile .add{align-self:flex-start;padding:4px 9px;font-size:11px}
.cap{flex:0 0 30px;padding:6px 0;font-size:14px;line-height:1}
.cap.on{background:#3d7bfd;color:#fff}
input:focus,select:focus{outline:0;border-color:#3d7bfd}
table{width:100%;border-collapse:collapse}
td,th{padding:3px 5px 3px 0;vertical-align:middle}
th{font:11px system-ui;color:#6f7788;text-align:left;font-weight:600;
text-transform:uppercase;letter-spacing:.6px;padding-bottom:6px}
td.k{width:30px;color:#3d7bfd;font:700 13px ui-monospace,monospace}
td.g{width:58px;color:#6f7788;font:11px system-ui}
td.lab{width:110px}td.ty{width:132px}
tr.sep td{border-top:1px solid #1f2531;padding-top:8px}
.use{width:64px;text-align:right;font:11px ui-monospace,monospace;color:#6f7788}
.bar{height:3px;background:#3d7bfd;border-radius:2px;margin-top:3px}
button{background:#2b3242;color:#e8eaee;border:0;border-radius:8px;
padding:9px 14px;font:600 13px system-ui;cursor:pointer}
button:hover{filter:brightness(1.25)}
button.p{background:#3d7bfd;color:#fff}button.d{background:#6d2233}
button.s{padding:6px 10px;font-size:12px}
.bar2{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
#msg{margin-top:16px;padding:11px 13px;border-radius:9px;display:none;
white-space:pre-wrap;font:13px ui-monospace,monospace}
.ok{background:#0f2e20;border:1px solid #1d6f47;color:#8ee0b4}
.ko{background:#33131d;border:1px solid #7d2a3c;color:#f0a6b6}
.hint{color:#6f7788;font-size:12px;margin:0 0 14px}
.vide{text-align:center;padding:26px 14px}
.vide b{display:block;font-size:15px;margin-bottom:8px;color:#e8eaee}
.vide p{color:#8b94a6;margin:5px 0;font-size:13px}
</style></head><body>
<header>
<h1>Macropad</h1>
<span class=tag id=src>...</span>
<span class=tag id=cnt>...</span>
</header>
<main>
<p class=hint>Libelles : 6 caracteres maximum. Combinaison :
<b>CTRL+MAJ+ESC</b>. Chaque touche accepte trois gestes : appui court,
appui long et double appui.</p>
<p class=hint>Le carre de couleur a cote du titre donne la couleur des
LED RGB de ce profil. Comme le PC change de profil selon le logiciel au
premier plan, <b>le macropad prend la couleur du logiciel</b> ou tu
travailles, en respiration douce.</p>
<p class=hint>Un geste peut <b>enchainer plusieurs etapes</b> :
« + etape » ajoute une ligne. Utile quand un logiciel a besoin de
respirer entre deux frappes — tape la commande, mets une
<b>pause</b> de 500 ms, puis valide.</p>
<p class=hint><b>maintenir</b> transforme la touche en vraie touche
modificatrice : mets <b>CTRL</b> sur l'appui court et <b>MAJ</b> sur le
double appui, et tu obtiens <i>appui maintenu = Ctrl</i>,
<i>appui bref puis maintenu = Maj</i>. Le modificateur reste enfonce tant
que ton doigt reste sur la touche, ce qui permet de cliquer a la souris
pendant ce temps.</p>

<h2>Profils et macros</h2>
<div id=profs></div>
<div class=bar2><button class=s onclick=addProfil()>+ Profil</button></div>

<h2>Logiciels detectes</h2>
<p class=hint>Le compagnon PC lit cette table sur le macropad. Le nom
abrege reste affiche a gauche de l'ecran pendant que le nom du fichier
defile.</p>
<div class=card id=apps></div>

<div class=bar2>
<button class=p onclick=save()>Enregistrer</button>
<button onclick=dl()>Telecharger la sauvegarde</button>
<button onclick=restaurer()>Restaurer une sauvegarde</button>
<button class=d onclick=usine()>Valeurs d'usine</button>
</div>
<div id=msg></div>
</main>
<script>
var D={ordre:[],profils:{},apps:{repli:{profil:"WINDOWS",abrege:"Win"},liste:[]}};
var N=6,GESTES=["court","long","double"];
var LIB={court:"court",long:"long",double:"double"};
var TYPES=[["none","inactive"],["key","touche"],["combo","combinaison"],
["maintien","maintenir (Ctrl, Maj...)"],
["text","texte"],["text_enter","texte + Entree"],
["pause","pause (millisecondes)"]];

function el(tag,attrs,kids){var e=document.createElement(tag);
 for(var k in attrs||{}){if(k=="cls")e.className=attrs[k];
  else if(k.slice(0,2)=="on")e[k]=attrs[k];else e.setAttribute(k,attrs[k]);}
 (kids||[]).forEach(function(c){
  e.appendChild(typeof c=="string"?document.createTextNode(c):c);});
 return e;}
// fin=true : on previent quand tu QUITTES le champ, pas a chaque
// frappe. Indispensable pour le nom d'un profil, qui redessine la page.
// Le selecteur de couleur du navigateur : c'est lui qui pilote la
// couleur des LED RGB du profil. Il rend une valeur du genre "#00a0ff".
function col(val,cb){var i=el("input",{type:"color"});
 i.value=val||"#808080";i.title="couleur des LED de ce profil";
 i.oninput=function(){cb(i.value);};return i;}

function inp(val,max,cb,fin){var i=el("input");i.value=val||"";
 if(max)i.maxLength=max;
 if(fin)i.onchange=function(){cb(i.value);};
 else i.oninput=function(){cb(i.value);};
 return i;}
function sel(val,cb){var s=el("select");TYPES.forEach(function(t){
 var o=el("option",{value:t[0]},[t[1]]);if(t[0]==val)o.selected=true;
 s.appendChild(o);});s.onchange=function(){cb(s.value);render();};return s;}

// =====================================================================
// CAPTURE D'UN RACCOURCI
// =====================================================================
// Plutot que de deviner comment s'ecrit une touche (SUPPR ? DELETE ?
// PAGEDOWN ?), tu cliques sur le bouton et tu APPUIES sur la combinaison.
// On lit ev.code, c'est-a-dire la touche PHYSIQUE : le resultat ne depend
// donc pas de la disposition du clavier, exactement comme le firmware qui
// raisonne lui aussi en touches physiques.
var TOUCHES={Escape:"ESC",Tab:"TAB",Space:"SPACE",Enter:"ENTER",
NumpadEnter:"ENTER",Backspace:"BACKSPACE",Delete:"SUPPR",Insert:"INSERT",
Home:"HOME",End:"END",PageUp:"PAGEUP",PageDown:"PAGEDOWN",
ArrowUp:"UP",ArrowDown:"DOWN",ArrowLeft:"LEFT",ArrowRight:"RIGHT",
PrintScreen:"PRINTSCREEN",ContextMenu:"MENU",CapsLock:"CAPSLOCK"};
var MODIFS={ControlLeft:"CTRL",ControlRight:"CTRL",ShiftLeft:"SHIFT",
ShiftRight:"SHIFT",AltLeft:"ALT",AltRight:"ALTGR",MetaLeft:"WIN",
MetaRight:"WIN"};

function nomTouche(ev){
 var code=ev.code||"";
 // AltGr se presente comme Ctrl+Alt sous Windows : on le detecte a part.
 var altgr=(code=="AltRight")||
  (ev.getModifierState&&ev.getModifierState("AltGraph"));
 if(MODIFS[code])return altgr?"ALTGR":MODIFS[code];

 var base="";
 if(code.slice(0,3)=="Key")base=code.slice(3);
 else if(code.slice(0,5)=="Digit")base=code.slice(5);
 else if(code.slice(0,6)=="Numpad"&&TOUCHES[code])base=TOUCHES[code];
 else if(code.charAt(0)=="F"&&code.length<=3&&!isNaN(code.slice(1)))base=code;
 else if(TOUCHES[code])base=TOUCHES[code];
 if(!base)return "";

 var parties=[];
 if(altgr)parties.push("ALTGR");
 else{if(ev.ctrlKey)parties.push("CTRL");if(ev.altKey)parties.push("ALT");}
 if(ev.shiftKey)parties.push("SHIFT");
 if(ev.metaKey)parties.push("WIN");
 parties.push(base);
 return parties.join("+");}

function capture(champ,cb){
 var b=el("button",{cls:"s cap",
  title:"Cliquer, puis appuyer sur la combinaison voulue"},["\u2328"]);
 b.onclick=function(){
  b.className="s cap on";champ.value="";
  champ.onkeydown=function(ev){
   var nom=nomTouche(ev);
   if(!nom)return;
   if(ev.preventDefault)ev.preventDefault();
   champ.value=nom;cb(nom);
   champ.onkeydown=null;b.className="s cap";};
  if(champ.focus)champ.focus();};
 return b;}

function maxUse(){var m=1;for(var n in D.profils)
 (D.profils[n].touches||[]).forEach(function(t){if(t.usages>m)m=t.usages;});
 return m;}

function vide(){
 var c=el("div",{cls:"card vide"},[]);
 c.appendChild(el("b",{},["Aucun profil recu du macropad."]));
 if(D.origine=="simulation"){
  c.appendChild(el("p",{},["Le compagnon tourne en mode --simuler : il "+
   "n'est relie a aucune carte."]));
  c.appendChild(el("p",{},["Relance-le sans --simuler, macropad branche."]));
 }else{
  c.appendChild(el("p",{},["Verifie qu'il est branche sur son port USB "+
   "NATIF, et que Thonny n'occupe pas ce port."]));
  c.appendChild(el("p",{},["La console du compagnon dit ce qu'elle voit ; "+
   "avec --journal, tout est dans macropad_auto.log."]));
 }
 c.appendChild(el("p",{},["Tu peux aussi partir des valeurs d'usine avec le "+
  "bouton rouge, ou ajouter un profil ci-dessous."]));
 return c;}

// Une fonction a part, et ce n'est pas cosmetique : en JavaScript,
// « var » appartient a la FONCTION, pas au bloc. Ecrite dans la boucle,
// la variable k etait la MEME pour les six touches, si bien que tous les
// champs finissaient par ecrire dans la derniere. Ici chaque appel a sa
// propre variable k : chaque champ modifie bien sa touche.
// Un geste est une SUITE d'etapes : taper une commande, attendre que la
// boite de dialogue s'ouvre, valider. Une seule etape reste le cas
// courant, et c'est ce qu'on affiche par defaut.
function etapes(k,g){
 if(!k[g]||!k[g].length)k[g]=[{type:"none",valeur:""}];
 else if(!k[g].length&&k[g].type)k[g]=[k[g]];   // ancienne forme
 return k[g];}

function ligneEtape(k,g,i){
 var e=k[g][i];
 var l=el("div",{cls:"val"},[]);
 l.appendChild(sel(e.type,function(v){e.type=v;}));
 var champ=inp(e.valeur,60,function(v){e.valeur=v;});
 if(e.type=="pause")champ.title="duree en millisecondes, 500 par exemple";
 l.appendChild(champ);
 if(e.type=="key"||e.type=="combo"||e.type=="maintien")
  l.appendChild(capture(champ,function(v){e.valeur=v;}));
 if(k[g].length>1)
  l.appendChild(el("button",{cls:"d s cap",title:"retirer cette etape",
   onclick:function(){k[g].splice(i,1);render();}},["\u00d7"]));
 return l;}

function ligne(p,i,tb,mx){
 if(!p.touches[i])p.touches[i]={label:"",usages:0};
 var k=p.touches[i];
 GESTES.forEach(function(g,gi){
  var tr=el("tr",{cls:gi==0?"sep":""},[]);
  if(gi==0)tr.appendChild(el("td",{cls:"k",rowspan:3},["B"+(i+1)]));
  tr.appendChild(el("td",{cls:"g"},[LIB[g]]));
  if(gi==0){
   var cl=el("td",{cls:"lab",rowspan:3},[]);
   cl.appendChild(inp(k.label,6,function(v){k.label=v;}));
   tr.appendChild(cl);
  }
  var ca=el("td",{},[]);
  var pile=el("div",{cls:"pile"},[]);
  etapes(k,g).forEach(function(e,rang){
   pile.appendChild(ligneEtape(k,g,rang));});
  pile.appendChild(el("button",{cls:"s add",title:"enchainer une etape",
   onclick:function(){k[g].push({type:"none",valeur:""});render();}},
   ["+ etape"]));
  ca.appendChild(pile);
  tr.appendChild(ca);
  if(gi==0){
   var u=k.usages||0;
   var box=el("td",{cls:"use",rowspan:3},[String(u)]);
   var b=el("div",{cls:"bar"});b.style.width=Math.round(60*u/mx)+"px";
   box.appendChild(b);tr.appendChild(box);
  }
  tb.appendChild(tr);
 });
}

function render(){
 var zone=document.getElementById("profs");zone.innerHTML="";
 var mx=maxUse();
 if(!D.ordre.length){zone.appendChild(vide());renderApps();return;}
 D.ordre.forEach(function(nom){
  var p=D.profils[nom];if(!p)return;
  var head=el("div",{cls:"ph"},[]);
  head.appendChild(inp(nom,20,function(v){ren(nom,v);},true));
  head.firstChild.className="grow";head.firstChild.title="nom interne";
  var t=inp(p.titre,16,function(v){p.titre=v;});t.className="grow";
  t.title="titre affiche sur l'ecran";head.appendChild(t);
  head.appendChild(col(p.couleur,function(v){p.couleur=v;}));
  head.appendChild(el("button",{cls:"d s",onclick:function(){del(nom);}},
   ["Supprimer"]));
  var tb=el("table",{},[el("tr",{},[el("th",{},["#"]),el("th",{},["Geste"]),
   el("th",{},["Libelle"]),el("th",{},["Action"]),
   el("th",{},["Usage"])])]);
  for(var i=0;i<N;i++)ligne(p,i,tb,mx);
  zone.appendChild(el("div",{cls:"card"},[head,tb]));
 });
 renderApps();
}

function renderApps(){
 var z=document.getElementById("apps");z.innerHTML="";
 var tb=el("table",{},[el("tr",{},[el("th",{},["Programme (.exe)"]),
  el("th",{},["Profil"]),el("th",{},["Abrege ecran"]),el("th",{},[""])])]);
 D.apps.liste.forEach(function(a,i){
  var tr=el("tr",{},[]);
  var c1=el("td",{},[]);c1.appendChild(inp(a.exe,40,function(v){a.exe=v;}));
  var c2=el("td",{},[]);c2.appendChild(inp(a.profil,20,function(v){a.profil=v;}));
  var c3=el("td",{},[]);c3.appendChild(inp(a.abrege,7,function(v){a.abrege=v;}));
  var c4=el("td",{cls:"use"},[el("button",{cls:"d s",onclick:function(){
   D.apps.liste.splice(i,1);renderApps();}},["x"])]);
  tr.appendChild(c1);tr.appendChild(c2);tr.appendChild(c3);tr.appendChild(c4);
  tb.appendChild(tr);
 });
 var tr=el("tr",{cls:"sep"},[]);
 tr.appendChild(el("td",{},["tout le reste"]));
 var r1=el("td",{},[]);r1.appendChild(inp(D.apps.repli.profil,20,
  function(v){D.apps.repli.profil=v;}));
 var r2=el("td",{},[]);r2.appendChild(inp(D.apps.repli.abrege,7,
  function(v){D.apps.repli.abrege=v;}));
 tr.appendChild(r1);tr.appendChild(r2);tr.appendChild(el("td",{},[]));
 tb.appendChild(tr);
 z.appendChild(tb);
 z.appendChild(el("div",{cls:"bar2"},[el("button",{cls:"s",onclick:function(){
  D.apps.liste.push({exe:"",profil:D.ordre[0]||"",abrege:""});renderApps();}},
  ["+ Logiciel"])]));
}

function ren(anc,nv){nv=(nv||"").trim();if(!nv||D.profils[nv])return;
 D.profils[nv]=D.profils[anc];delete D.profils[anc];
 D.ordre=D.ordre.map(function(x){return x==anc?nv:x});render();}
function del(n){if(D.ordre.length<2)return say("Il faut au moins un profil",0);
 delete D.profils[n];D.ordre=D.ordre.filter(function(x){return x!=n});render();}
function addProfil(){var n="PROFIL",i=1;while(D.profils[n])n="PROFIL"+(++i);
 var t=[];for(var k=0;k<N;k++)t.push({label:"",usages:0});
 D.profils[n]={titre:n,couleur:"#808080",touches:t};
 D.ordre.push(n);render();}
function say(t,ok){var m=document.getElementById("msg");
 m.textContent=t;m.className=ok?"ok":"ko";m.style.display="block";
 window.scrollTo(0,document.body.scrollHeight);}
function dl(){var a=document.createElement("a");
 a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,2)],
  {type:"application/json"}));
 a.download="macropad_config.json";a.click();}
// =====================================================================
// RESTAURER UNE SAUVEGARDE
// =====================================================================
// Le bouton "Telecharger" existait depuis le debut, mais rien ne
// permettait de RECHARGER le fichier : la sauvegarde ne servait donc a
// rien. On charge le fichier dans le formulaire SANS l'appliquer, pour
// que tu voies ce que tu restaures avant de cliquer sur Enregistrer.
function charger_sauvegarde(texte){
 var d;
 try{d=JSON.parse(texte);}
 catch(e){say("Fichier illisible : "+e,0);return false;}
 if(!d||!d.ordre||!d.ordre.length||!d.profils){
  say("Ce fichier n'est pas une sauvegarde du macropad.",0);return false;}
 D=normaliser(d);N=d.touches||N;
 if(!D.apps)D.apps={repli:{profil:"WINDOWS",abrege:"Win"},liste:[]};
 render();
 say("Sauvegarde chargee : "+D.ordre.length+" profils. Verifie, puis "+
  "clique sur Enregistrer pour l'appliquer au macropad.",1);
 return true;}

function restaurer(){
 var i=el("input",{type:"file",accept:".json,application/json"});
 i.onchange=function(){
  var f=i.files&&i.files[0];if(!f)return;
  var lecteur=new FileReader();
  lecteur.onload=function(){charger_sauvegarde(lecteur.result);};
  lecteur.readAsText(f);};
 i.click();}

function usine(){if(!confirm("Revenir aux valeurs d'usine ?"))return;
 fetch("/api/usine",{method:"POST"}).then(function(){location.reload();});}
function save(){fetch("/api/profils",{method:"POST",
 body:JSON.stringify(D)}).then(function(r){return r.json();})
 .then(function(r){say(r.ok?"Enregistre et applique.":"Refuse :\n"+r.raison,
  r.ok);if(r.ok)charger();})
 .catch(function(e){say("Erreur : "+e,0);});}
// Une sauvegarde ou un fichier ecrit avant les suites d'etapes range un
// SEUL objet par geste. On le remet en liste des la lecture : le reste de
// la page n'a ainsi qu'une seule forme a connaitre.
function normaliser(d){
 for(var nom in (d.profils||{})){
  ((d.profils[nom]||{}).touches||[]).forEach(function(k){
   GESTES.forEach(function(g){
    if(k[g]&&!(k[g] instanceof Array))k[g]=[k[g]];});});}
 return d;}

function charger(){fetch("/api/profils").then(function(r){return r.json();})
 .then(function(d){
  if(d.erreur)return say("Lecture impossible : "+d.erreur,0);
  D=normaliser(d);N=d.touches||6;
  if(!D.apps)D.apps={repli:{profil:"WINDOWS",abrege:"Win"},liste:[]};
  document.getElementById("src").textContent="source : "+(d.origine||"?");
  var tot=0;for(var n in D.profils)(D.profils[n].touches||[]).forEach(
   function(t){tot+=t.usages||0;});
  document.getElementById("cnt").textContent=tot+" appuis comptes";
  render();}).catch(function(e){say("Erreur : "+e,0);});}
charger();
</script></body></html>
"""


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

    def __init__(self, nb_touches, stats=None):
        self.nb_touches = nb_touches
        self.stats = stats
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
        return store.vers_json(self.nb_touches, self.stats)

    def _enregistrer(self, data):
        return store.enregistrer_json(data, self.nb_touches)

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
