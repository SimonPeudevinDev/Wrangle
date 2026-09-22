# -*- coding: utf-8 -*-
"""Le filtre « Saisie par » : la rangee de prenoms du panneau des filtres.

Sur un plateau ou trois personnes saisissent depuis leur telephone, chacun doit
pouvoir ne voir que ce qu'il a saisi. Le filtre reduit la liste aux plans ou la
personne a une prise, et, dans ces plans, aux prises qui sont les siennes.

  py tests/verif_filtre_qui.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais()
with Banc(8777, 9362) as banc:
    banc.ouvrir(repos=1.0)
    banc.nommer()

    # trois personnes saisissent : Simon sur deux plans, Romain et Tom sur un meme
    # troisieme plan, pour que le filtre ait a trier a l'interieur d'un plan.
    banc.js("""
      DB.prises.length = 0;
      fJour = '*'; UI.jour = '*'; fEtat = ''; fCrit = {}; fQui = '';
      UI.nom = 'Simon';  ajouterPrise(DB.plans[0].id, false); ajouterPrise(DB.plans[1].id, false);
      UI.nom = 'Romain'; ajouterPrise(DB.plans[2].id, false);
      UI.nom = 'Tom';    ajouterPrise(DB.plans[2].id, false); ajouterPrise(DB.plans[3].id, false);
      flush(); renderShoot();
    """)
    time.sleep(0.6)

    boutons = banc.js("""
      [...document.querySelectorAll('#c-filtre .gens button')]
        .map(b => [b.firstChild.textContent, +b.querySelector('b').textContent])
    """)
    essais.verifier('les trois prenoms sont proposes, par ordre alphabetique',
                    boutons, [['Romain', 1], ['Simon', 2], ['Tom', 2]])

    total = banc.js("document.querySelectorAll('#l-shoot .plan').length")
    essais.verifier('sans filtre, toute la liste est la', total > 4, True)

    # -- Simon : deux plans, une prise dans chacun
    banc.js("setQui('Simon')"); time.sleep(0.4)
    essais.verifier('Simon : seuls ses deux plans restent',
                    banc.js("document.querySelectorAll('#l-shoot .plan').length"), 2)
    essais.verifier('Simon : seules ses prises sont montrees',
                    banc.js("document.querySelectorAll('#l-shoot .prise').length"), 2)
    essais.verifier('le bouton Filtres porte 1 filtre pose',
                    banc.js("document.querySelector('#btn-filtres b').textContent"), '1')

    # -- Tom partage un plan avec Romain : la prise de Romain doit disparaitre
    banc.js("setQui('Tom')"); time.sleep(0.4)
    essais.verifier('Tom : ses deux plans', banc.js("document.querySelectorAll('#l-shoot .plan').length"), 2)
    essais.verifier('Tom : la prise de Romain sur le plan partage est ecartee',
                    banc.js("document.querySelectorAll('#l-shoot .prise').length"), 2)
    essais.verifier('le plan partage ne montre plus qu une prise',
                    banc.js('document.querySelectorAll(`#l-shoot .plan[data-id="${DB.plans[2].id}"] .prise`).length'), 1)

    # -- recliquer sur le meme prenom relache le filtre
    banc.js("setQui('Tom')"); time.sleep(0.4)
    essais.verifier('recliquer Tom relache le filtre',
                    banc.js("[fQui, document.querySelectorAll('#l-shoot .plan').length]"), ['', total])

    # -- Effacer remet tout a zero
    banc.js("setQui('Romain')"); time.sleep(0.3)
    banc.js('razFiltres()'); time.sleep(0.4)
    essais.verifier('Effacer relache aussi le filtre par personne',
                    banc.js("[fQui, document.querySelectorAll('#l-shoot .plan').length]"), ['', total])

    # -- une seule personne : la rangee n'a rien a trier, on ne l'affiche pas
    banc.js("DB.prises.forEach(t => t.par = 'Simon'); renderShoot()"); time.sleep(0.4)
    essais.verifier('une seule personne : la rangee disparait',
                    banc.js("document.querySelectorAll('#c-filtre .gens button').length"), 0)

    essais.exceptions(banc)
essais.bilan()
