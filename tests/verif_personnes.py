# -*- coding: utf-8 -*-
"""Sur le site, chacun a ses saisies : la copie locale est rangee sous le
prenom choisi a l'entree. Passer de Simon a Romain sur le meme appareil
change de saisies, revenir les retrouve, recharger la page aussi. Le dernier
depot est note par prenom. Avec le serveur, le projet reste commun."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=58)
with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- comme sur le site : pas de serveur (?seul=1)
    banc.ouvrir('/?seul=1')
    essais.verifier('sans serveur, la page travaille seule', banc.js('RESEAU.possible'), False)
    essais.verifier('et demande quand meme le prenom a l entree', banc.js("!$('voile-nom').hidden"), True)
    banc.nommer()                                    # Simon
    essais.verifier('Simon est entre', [banc.js('UI.nom'), banc.js("$('voile-nom').hidden")], ['Simon', True])
    banc.js("ajouterPrise(DB.plans[0].id, false, { clip:'A001C001', par:'Simon' }); flush()")
    essais.verifier('sa copie locale est rangee sous son prenom', [banc.js("!!localStorage.getItem('fstdw.v1:simon')"), banc.js("localStorage.getItem('fstdw.v1')")], [True, None])
    banc.js("noterDepose('2026-10-05T18:40:00+02:00')")

    # -- Romain prend l'appareil : ses saisies a lui, vides
    banc.js("choisirNom(0)"); time.sleep(0.4)
    essais.verifier('Romain arrive sur le decoupage seul, sans les prises de Simon', [banc.js('UI.nom'), banc.js('DB.prises.length'), banc.js('DB.plans.length')], ['Romain', 0, 56])
    essais.verifier('le dernier depot est celui de personne', banc.js('derniereDepose()'), '')
    essais.verifier('la liste des prises est rendue a vide', banc.js("document.querySelectorAll('.prise').length"), 0)
    banc.js("ajouterPrise(DB.plans[1].id, false, { clip:'B001C001', par:'Romain' }); ajouterPrise(DB.plans[1].id, false, { clip:'B001C002', par:'Romain' }); flush()")
    essais.verifier('Romain saisit deux prises, rangees sous son prenom', [banc.js('DB.prises.length'), banc.js("!!localStorage.getItem('fstdw.v1:romain')")], [2, True])

    # -- retour a Simon, depuis la fiche Journee cette fois
    banc.js("openProd()"); time.sleep(0.3)
    banc.js("[...document.querySelectorAll('#sbody .choix .btn')].find(b => b.textContent === 'Simon').click()"); time.sleep(0.4)
    essais.verifier('Simon retrouve sa prise, et son dernier depot', [banc.js('UI.nom'), banc.js('DB.prises.map(t => t.clip)'), banc.js('derniereDepose()')], ['Simon', ['A001C001'], '2026-10-05T18:40:00+02:00'])
    essais.verifier('la fiche Journee s est refermee', banc.js('openType'), None)

    # -- recharger garde la personne et ses saisies
    banc.ouvrir('/?seul=1')
    essais.verifier('au rechargement, toujours Simon et sa prise', [banc.js('UI.nom'), banc.js('DB.prises.map(t => t.clip)'), banc.js("$('voile-nom').hidden")], ['Simon', ['A001C001'], True])
    banc.js("choisirNom(0)"); time.sleep(0.4)
    essais.verifier('et Romain a toujours ses deux', banc.js('DB.prises.map(t => t.clip)'), ['B001C001', 'B001C002'])
    essais.exceptions(banc)

    # -- avec le serveur du plateau, le projet est commun : changer de prenom ne change rien
    banc.ouvrir('/', vider=True)
    essais.verifier('avec le serveur, le projet est commun', banc.js('PROJET_COMMUN'), True)
    banc.js("ajouterPrise(DB.plans[2].id, false, { clip:'C001C001' }); flush()"); time.sleep(0.4)
    n = banc.js('DB.prises.length')
    banc.js("choisirNom(2)"); time.sleep(0.4)
    essais.verifier('Tom voit les memes prises que tout le monde', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['Tom', n])
    essais.exceptions(banc, quoi='aucune exception en console, la non plus')
essais.bilan()
