;;; =====================================================================
;;; macropad_tools.lsp - Commandes Civil 3D pour le macropad ESP32-S3
;;; =====================================================================
;;;
;;; Quatre commandes, appelees par le macropad qui tape simplement leur
;;; nom suivi d'Entree :
;;;
;;;   MPVIEWNEXT      vue nommee suivante      (cycle circulaire)
;;;   MPVIEWPREV      vue nommee precedente
;;;   MPLAYEROFF      cache le calque d'un objet designe
;;;   MPLAYERRESTORE  reaffiche le dernier calque cache
;;;
;;; PAS de prefixe _ pour les appeler : le souligne sert a demander la
;;; version INTERNATIONALE d'une commande AutoCAD native. Une commande
;;; LISP n'a pas de traduction, donc rien a desambiguiser.
;;;
;;; Chargement : voir README.md (APPLOAD -> Suite de demarrage).
;;;
;;; =====================================================================
;;; POURQUOI SI PEU D'APPELS A (command ...)
;;; =====================================================================
;;; Les commandes AutoCAD portent des noms differents selon la langue de
;;; l'installation, et certaines posent des questions de confirmation qui
;;; cassent une sequence automatique. On passe donc par les TABLES du
;;; dessin (VIEW, LAYER) chaque fois que c'est possible : c'est
;;; independant de la langue, et rien ne peut interrompre l'operation.
;;;
;;; Seule exception : la restauration d'une vue, qui n'a pas d'equivalent
;;; propre en acces direct. On y utilise "_-VIEW" avec l'option "_R",
;;; toutes deux prefixees pour rester en anglais.
;;; =====================================================================


;;; ---------------------------------------------------------------------
;;; Outils internes (prefixe mp- pour ne rien ecraser)
;;; ---------------------------------------------------------------------

;; Modulo toujours positif : indispensable pour un cycle circulaire.
(defun mp-modulo (valeur diviseur / reste)
  (setq reste (rem valeur diviseur))
  (if (< reste 0) (+ reste diviseur) reste)
)

;; Position d'un nom dans une liste, -1 s'il n'y est pas.
(defun mp-position (nom liste / index trouve)
  (setq index 0 trouve -1)
  (foreach element liste
    (if (and nom (= (strcase element) (strcase nom)))
      (setq trouve index)
    )
    (setq index (1+ index))
  )
  trouve
)

;; Liste triee des vues nommees utiles du dessin.
;;
;; On lit la table VIEW directement. Deux familles sont ecartees :
;;   - les noms commencant par * : vues anonymes internes a AutoCAD ;
;;   - les noms commencant par A$C : vues fabriquees automatiquement.
;; Si tu vois passer d'autres vues parasites, ajoute leur prefixe ici.
(defun mp-vues ( / entree nom liste)
  (setq liste '())
  (setq entree (tblnext "VIEW" T))
  (while entree
    (setq nom (cdr (assoc 2 entree)))
    (if (and nom
             (/= nom "")
             (/= (substr nom 1 1) "*")
             (/= (strcase (substr nom 1 3)) "A$C")
        )
      (setq liste (cons nom liste))
    )
    (setq entree (tblnext "VIEW"))
  )
  ;; Tri alphabetique : le cycle est ainsi previsible et ne depend pas de
  ;; l'ordre de creation des vues.
  (if liste (vl-sort liste '<) nil)
)

;; Restaure une vue par son nom et memorise ou on en est.
(defun mp-restaure (nom / echo)
  (setq echo (getvar "CMDECHO"))
  (setvar "CMDECHO" 0)
  ;; "_-VIEW" : version ligne de commande, en anglais.
  ;; "_R"     : option Restore, en anglais elle aussi - les OPTIONS
  ;;            doivent etre prefixees comme les commandes.
  (command "_-VIEW" "_R" nom)
  (setvar "CMDECHO" echo)
  ;; On retient le NOM et non un numero : si tu ajoutes, renommes ou
  ;; supprimes une vue, le cycle repart quand meme du bon endroit.
  (setq *mp-vue-courante* nom)
  (princ (strcat "\nVue : " nom))
  (princ)
)

;; Avance de "pas" vues dans le cycle (+1 suivante, -1 precedente).
(defun mp-cycle (pas / liste nombre position)
  (setq liste (mp-vues))
  (if (null liste)
    (progn
      (princ "\nAucune vue nommee dans ce dessin.")
      (princ)
    )
    (progn
      (setq nombre (length liste))
      (setq position (mp-position *mp-vue-courante* liste))
      (if (< position 0)
        ;; Vue courante inconnue (premier appel, ou vue supprimee) :
        ;; on se place juste avant le debut pour que +1 donne la
        ;; premiere vue, et juste apres pour que -1 donne la derniere.
        (setq position (if (> pas 0) -1 0))
      )
      (mp-restaure (nth (mp-modulo (+ position pas) nombre) liste))
    )
  )
)


;;; ---------------------------------------------------------------------
;;; Les commandes
;;; ---------------------------------------------------------------------

(defun c:MPVIEWNEXT ()
  (mp-cycle 1)
)

(defun c:MPVIEWPREV ()
  (mp-cycle -1)
)


;; Cache le calque de l'objet designe, et empile son nom.
;;
;; On modifie la table LAYER directement (code 62 negatif = calque
;; eteint) plutot que d'appeler la commande CALQUE / LAYER. Deux raisons :
;;   - aucun nom de commande localise ;
;;   - aucune question de confirmation, y compris sur le calque courant.
(defun c:MPLAYEROFF ( / choix calque enregistrement donnees couleur)
  (setq choix (entsel "\nDesigne un objet dont le calque doit disparaitre : "))
  (if (null choix)
    (progn
      ;; Echap, ou clic dans le vide : on ne touche a rien.
      (princ "\nAnnule, aucun calque cache.")
      (princ)
    )
    (progn
      (setq calque (cdr (assoc 8 (entget (car choix)))))
      (setq enregistrement (tblobjname "LAYER" calque))
      (setq donnees (entget enregistrement))
      (setq couleur (cdr (assoc 62 donnees)))
      (if (< couleur 0)
        ;; Deja eteint : on ne l'empile PAS, sinon MPLAYERRESTORE
        ;; "rallumerait" un calque que nous n'avons jamais eteint.
        (princ (strcat "\nLe calque " calque " est deja eteint."))
        (progn
          (entmod (subst (cons 62 (- (abs couleur)))
                         (assoc 62 donnees)
                         donnees))
          (setq *mp-calques-caches* (cons calque *mp-calques-caches*))
          (princ (strcat "\nCalque cache : " calque))
          (if (= (strcase calque) (strcase (getvar "CLAYER")))
            (princ "  << ATTENTION : c'est ton calque COURANT >>")
          )
          ;; Si ton affichage ne se met pas a jour tout seul, enleve le
          ;; point-virgule de la ligne suivante. Elle est desactivee par
          ;; defaut : un REGEN coute cher sur un gros dessin.
          ;; (command "_.REGEN")
        )
      )
      (princ)
    )
  )
)


;; Reaffiche le dernier calque cache par MPLAYEROFF.
;;
;; C'est une PILE : trois calques caches se reaffichent dans l'ordre
;; inverse, du plus recent au plus ancien.
(defun c:MPLAYERRESTORE ( / calque enregistrement donnees couleur)
  (if (null *mp-calques-caches*)
    (progn
      (princ "\nAucun calque cache par MPLAYEROFF.")
      (princ)
    )
    (progn
      (setq calque (car *mp-calques-caches*))
      (setq *mp-calques-caches* (cdr *mp-calques-caches*))
      (setq enregistrement (tblobjname "LAYER" calque))
      (if (null enregistrement)
        ;; Calque renomme ou purge entre-temps : on le signale et on
        ;; passe au suivant a la prochaine invocation.
        (princ (strcat "\nLe calque " calque " n'existe plus."))
        (progn
          (setq donnees (entget enregistrement))
          (setq couleur (cdr (assoc 62 donnees)))
          (entmod (subst (cons 62 (abs couleur))
                         (assoc 62 donnees)
                         donnees))
          (princ (strcat "\nCalque reaffiche : " calque))
        )
      )
      (princ)
    )
  )
)


;;; ---------------------------------------------------------------------
(princ "\nmacropad_tools.lsp charge : MPVIEWNEXT, MPVIEWPREV, MPLAYEROFF, MPLAYERRESTORE")
(princ)
