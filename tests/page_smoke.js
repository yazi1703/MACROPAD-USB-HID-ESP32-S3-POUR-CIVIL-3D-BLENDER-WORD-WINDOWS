// ---------------------------------------------------------------------
// page_smoke.js - Fait tourner le JavaScript de la page de configuration
// hors navigateur, avec un DOM minimal, et verifie qu'elle FONCTIONNE.
//
// Deux bugs reels ont motive ce fichier :
//
//   1. un antislash mal interprete cassait tout le script : la page
//      s'affichait vide, sans le moindre message ;
//   2. une variable « var » declaree dans une boucle etait partagee par
//      les six touches : tout ce qu'on tapait dans un profil finissait
//      dans la derniere touche.
//
// Aucun des deux n'etait visible sans ouvrir un navigateur. Maintenant si.
//
//     node page_smoke.js <script.js> <configuration.json>
//
// Ecrit sur la sortie standard un JSON decrivant ce que la page a produit
// et ou ont atterri les saisies. C'est tests/test_logic.py qui juge.
// ---------------------------------------------------------------------
const fs = require('fs');

const script = fs.readFileSync(process.argv[2], 'utf8');
const donnees = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

// --- un DOM juste assez complet --------------------------------------
function Element(tag) {
  this.tag = tag;
  this.children = [];
  this.attrs = {};
  this.style = {};
  this.className = '';
  this.textContent = '';
  this.value = '';
}
Element.prototype.appendChild = function (n) { this.children.push(n); return n; };
Element.prototype.setAttribute = function (k, v) { this.attrs[k] = v; };
Object.defineProperty(Element.prototype, 'firstChild', {
  get: function () { return this.children[0]; }
});
Object.defineProperty(Element.prototype, 'innerHTML', {
  get: function () { return ''; },
  set: function () { this.children = []; }
});

const registre = {};
['profs', 'apps', 'msg', 'src', 'cnt'].forEach(function (id) {
  registre[id] = new Element('div');
});

const document = {
  createElement: function (tag) { return new Element(tag); },
  createTextNode: function (t) { const n = new Element('#text');
                                 n.textContent = t; return n; },
  getElementById: function (id) { return registre[id] || null; },
  body: { scrollHeight: 0 }
};
const window = { scrollTo: function () {} };
const location = { reload: function () {} };
function confirm() { return true; }
const URL = { createObjectURL: function () { return 'blob:x'; } };
function Blob() {}

let envoye = null;               // ce que la page a POSTE au macropad
function fetch(url, options) {
  if (options && options.method === 'POST') {
    if (options.body) { envoye = JSON.parse(options.body); }
    return Promise.resolve({ json: function () {
      return Promise.resolve({ ok: true, raison: '' }); } });
  }
  return Promise.resolve({ json: function () {
    return Promise.resolve(donnees); } });
}

// On execute la page, en se donnant au passage un acces a ses fonctions :
// le petit ajout ci-dessous est dans la meme portee que le script.
new Function('document', 'window', 'fetch', 'URL', 'Blob', 'confirm',
             'location',
             script + '\n;globalThis.__page={D:function(){return D;},' +
                      'save:save,nomTouche:nomTouche,' +
                      'charger_sauvegarde:charger_sauvegarde};')(
  document, window, fetch, URL, Blob, confirm, location);

// --- outils d'inspection ---------------------------------------------
function compter(noeud, tag) {
  let total = noeud.tag === tag ? 1 : 0;
  noeud.children.forEach(function (e) { total += compter(e, tag); });
  return total;
}
function texte(noeud) {
  let sortie = noeud.textContent || '';
  noeud.children.forEach(function (e) { sortie += texte(e); });
  return sortie;
}
function champs(noeud, sortie) {
  sortie = sortie || [];
  // Le selecteur de couleur est mis a part : il n'a pas de position fixe
  // dans la liste, et le compter decalerait tous les indices.
  if (noeud.tag === 'input' && noeud.attrs.type !== 'color') {
    sortie.push(noeud);
  }
  noeud.children.forEach(function (e) { champs(e, sortie); });
  return sortie;
}
function couleurs(noeud, sortie) {
  sortie = sortie || [];
  if (noeud.tag === 'input' && noeud.attrs.type === 'color') {
    sortie.push(noeud);
  }
  noeud.children.forEach(function (e) { couleurs(e, sortie); });
  return sortie;
}
function boutons(noeud, libelle, sortie) {
  sortie = sortie || [];
  if (noeud.tag === 'button' && texte(noeud).indexOf(libelle) >= 0) {
    sortie.push(noeud);
  }
  noeud.children.forEach(function (e) { boutons(e, libelle, sortie); });
  return sortie;
}
// Retrouver un champ par son infobulle plutot que par sa position : les
// combinaisons sont en nombre variable, compter les champs qui les
// precedent rendrait ce fichier faux au premier ajout.
function parTitre(noeud, fragment, sortie) {
  sortie = sortie || [];
  if (noeud.tag === 'input' && (noeud.title || '').indexOf(fragment) >= 0) {
    sortie.push(noeud);
  }
  noeud.children.forEach(function (e) { parTitre(e, fragment, sortie); });
  return sortie;
}
function listes(noeud, sortie) {
  sortie = sortie || [];
  if (noeud.tag === 'select') { sortie.push(noeud); }
  noeud.children.forEach(function (e) { listes(e, sortie); });
  return sortie;
}
function saisir(champ, valeur) {
  champ.value = valeur;
  if (champ.oninput) { champ.oninput(); }
  else if (champ.onchange) { champ.onchange(); }
}

setTimeout(function () {
  const profs = registre.profs;
  const nbProfils = (donnees.ordre || []).length;
  const nbTouches = donnees.touches || 6;

  const vu = {
    cartes: profs.children.length,
    lignes: compter(profs, 'tr'),
    listes: compter(profs, 'select'),
    src: registre.src.textContent,
    cnt: registre.cnt.textContent,
    apps: compter(registre.apps, 'tr'),
    texte_vide: texte(profs).indexOf('Aucun profil') >= 0
  };

  if (nbProfils > 0) {
    // ---- on tape dans les champs de la PREMIERE touche ---------------
    // Par carte : nom interne, titre, puis par touche un libelle suivi
    // des trois valeurs de gestes.
    const c = champs(profs.children[0]);
    saisir(c[2], 'ZZZ');            // libelle de la touche 1
    saisir(c[3], 'TESTVAL');        // valeur de son appui court

    // ---- on change aussi la couleur des LED du profil ---------------
    const cc = couleurs(profs.children[0]);
    if (cc.length) { saisir(cc[0], '#123456'); }

    // ---- et dans le deuxieme logiciel de la table -------------------
    const ca = champs(registre.apps);
    if (ca.length >= 6) { saisir(ca[5], 'AbRg'); }   // abrege du 2e

    // ---- les combinaisons, sur la carte qui en a ---------------------
    // Meme piege que pour les touches : chaque champ doit ecrire dans SA
    // combinaison. On modifie donc la PREMIERE et on regarde la DERNIERE.
    let carteCombos = null;
    profs.children.forEach(function (carte) {
      if (!carteCombos && parTitre(carte, 'appuyees ensemble').length > 1) {
        carteCombos = carte;
      }
    });
    vu.carte_combos = profs.children.indexOf(carteCombos);
    if (carteCombos) {
      const duo = parTitre(carteCombos, 'appuyees ensemble');
      const lib = parTitre(carteCombos, 'libelle affiche');
      vu.combos_affiches = duo.length;
      vu.combo_touches_lues = duo[0].value;
      vu.combo_dernier_libelle_avant = lib[lib.length - 1].value;
      saisir(duo[0], '5 et 6');        // volontairement mal ecrit
      saisir(lib[0], 'ESSAI');
    }

    // ---- on enchaine une etape : commande, pause, validation --------
    // Chaque clic redessine la page : il faut recollecter les elements
    // apres chaque action, comme le ferait un vrai navigateur.
    const plus = boutons(profs.children[0], '+ etape');
    vu.boutons_etape = plus.length;
    if (plus.length) {
      plus[0].onclick();                       // B1, appui court
      const sel2 = listes(registre.profs.children[0])[1];
      sel2.value = 'pause';
      if (sel2.onchange) { sel2.onchange(); }
      const champs2 = champs(registre.profs.children[0]);
      saisir(champs2[4], '500');               // duree de la pause
    }

    // ---- puis on enregistre, et on regarde ce qui part --------------
    globalThis.__page.save();

    setTimeout(function () {
      const D = globalThis.__page.D();
      const p = envoye ? envoye.profils[envoye.ordre[0]] : null;
      vu.envoye = !!envoye;
      vu.touche1_label = p ? p.touches[0].label : null;
      // Un geste est maintenant une SUITE d'etapes.
      const suite = p ? p.touches[0].court : null;
      vu.touche1_etapes = suite ? suite.length : 0;
      vu.touche1_valeur = suite && suite[0] ? suite[0].valeur : null;
      vu.touche1_etape2 = suite && suite[1] ? suite[1] : null;
      vu.derniere_touche_label = p ? p.touches[nbTouches - 1].label : null;
      vu.app2_abrege = (envoye && envoye.apps.liste[1])
        ? envoye.apps.liste[1].abrege : null;
      vu.app1_abrege = (envoye && envoye.apps.liste[0])
        ? envoye.apps.liste[0].abrege : null;
      const pc = (envoye && carteCombos)
        ? envoye.profils[envoye.ordre[vu.carte_combos]] : null;
      vu.combos_envoyes = pc && pc.combos ? pc.combos.length : 0;
      vu.combo1 = pc && pc.combos ? pc.combos[0] : null;
      vu.combo_dernier_libelle = (pc && pc.combos)
        ? pc.combos[pc.combos.length - 1].label : null;
      // Un profil SANS combinaison ne doit pas s'en voir inventer une.
      const p0 = envoye ? envoye.profils[envoye.ordre[0]] : null;
      vu.combos_profil_sans = (p0 && p0.combos) ? p0.combos.length : -1;
      vu.couleurs = cc.length;
      vu.couleur1 = p ? p.couleur : null;
      const second = (envoye && envoye.ordre[1])
        ? envoye.profils[envoye.ordre[1]] : null;
      vu.couleur2 = second ? second.couleur : null;
      vu.message = registre.msg.textContent;

      // ---- capture d'un raccourci au clavier -------------------------
      const nom = globalThis.__page.nomTouche;
      vu.capture = {
        ctrl_maj_p: nom({ code: 'KeyP', ctrlKey: true, shiftKey: true }),
        f5: nom({ code: 'F5' }),
        f12: nom({ code: 'F12' }),
        ctrl_seul: nom({ code: 'ControlLeft' }),
        maj_seul: nom({ code: 'ShiftRight' }),
        suppr: nom({ code: 'Delete' }),
        fleche: nom({ code: 'ArrowUp' }),
        altgr: nom({ code: 'AltRight' }),
        win_e: nom({ code: 'KeyE', metaKey: true }),
        ctrl_1: nom({ code: 'Digit1', ctrlKey: true }),
        echap: nom({ code: 'Escape' }),
        inconnu: nom({ code: 'Lang1' })
      };

      // ---- restauration d'une sauvegarde -----------------------------
      // En dernier : elle remplace tout le contenu du formulaire.
      vu.restaure_bonne = globalThis.__page.charger_sauvegarde(
        JSON.stringify(donnees));
      vu.message_restaure = registre.msg.textContent;
      vu.restaure_cassee = globalThis.__page.charger_sauvegarde('{pas du json');
      vu.restaure_etrangere = globalThis.__page.charger_sauvegarde(
        '{"autre": 1}');
      vu.message_refus = registre.msg.textContent;
      vu.cartes_apres_restauration = registre.profs.children.length;

      console.log(JSON.stringify(vu));
    }, 0);
  } else {
    console.log(JSON.stringify(vu));
  }
}, 0);
