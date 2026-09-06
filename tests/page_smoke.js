// ---------------------------------------------------------------------
// page_smoke.js - Fait tourner le JavaScript de la page de configuration
// hors navigateur, avec un DOM minimal, et verifie qu'elle se construit.
//
// Un controle de syntaxe (node --check) ne dit pas si la page FONCTIONNE.
// Ici on lui donne une vraie configuration, on la laisse se dessiner, et
// on compte ce qu'elle a produit. Une erreur pendant le rendu - un champ
// absent, une propriete mal orthographiee - fait echouer ce test.
//
//     node page_smoke.js <script.js> <configuration.json>
// ---------------------------------------------------------------------
const fs = require('fs');

const script = fs.readFileSync(process.argv[2], 'utf8');
const donnees = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

// --- un DOM juste assez complet -------------------------------------
function Element(tag) {
  this.tag = tag;
  this.children = [];
  this.attrs = {};
  this.style = {};
  this.className = '';
  this.textContent = '';
  this.value = '';
}
Element.prototype.appendChild = function (n) {
  this.children.push(n);
  return n;
};
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
function confirm() { return false; }
const URL = { createObjectURL: function () { return 'blob:x'; } };
function Blob() {}

function fetch(url, options) {
  if (options && options.method === 'POST') {
    return Promise.resolve({ json: function () {
      return Promise.resolve({ ok: true, raison: '' }); } });
  }
  return Promise.resolve({ json: function () {
    return Promise.resolve(donnees); } });
}

// --- on execute la page ---------------------------------------------
new Function('document', 'window', 'fetch', 'URL', 'Blob', 'confirm',
             'location', script)(
  document, window, fetch, URL, Blob, confirm, location);

// --- puis on regarde ce qu'elle a fabrique ---------------------------
function compter(noeud, tag) {
  let total = noeud.tag === tag ? 1 : 0;
  noeud.children.forEach(function (enfant) { total += compter(enfant, tag); });
  return total;
}
function texte(noeud) {
  let sortie = noeud.textContent || '';
  noeud.children.forEach(function (enfant) { sortie += texte(enfant); });
  return sortie;
}

setTimeout(function () {
  const profs = registre.profs;
  const nbProfils = (donnees.ordre || []).length;
  const resultat = {
    cartes: profs.children.length,
    lignes: compter(profs, 'tr'),
    champs: compter(profs, 'input') + compter(registre.apps, 'input'),
    listes: compter(profs, 'select'),
    src: registre.src.textContent,
    cnt: registre.cnt.textContent,
    apps: compter(registre.apps, 'tr'),
    texte_vide: texte(profs).indexOf('Aucun profil') >= 0
  };
  console.log(JSON.stringify(resultat));

  const attendu = nbProfils * (donnees.touches || 6) * 3;
  if (nbProfils > 0) {
    if (resultat.cartes !== nbProfils) {
      throw new Error('cartes de profil : ' + resultat.cartes +
                      ' au lieu de ' + nbProfils);
    }
    // Une ligne d'en-tete par profil, puis une ligne par geste.
    if (resultat.lignes !== attendu + nbProfils) {
      throw new Error('lignes du tableau : ' + resultat.lignes +
                      ' au lieu de ' + (attendu + nbProfils));
    }
    if (resultat.listes !== attendu) {
      throw new Error('listes deroulantes : ' + resultat.listes +
                      ' au lieu de ' + attendu);
    }
    if (!resultat.src) { throw new Error("l'origine n'est pas affichee"); }
  } else if (!resultat.texte_vide) {
    throw new Error('aucun profil, et aucun message pour le dire');
  }
}, 0);
