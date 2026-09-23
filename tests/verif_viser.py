# -*- coding: utf-8 -*-
"""Le plan vise : un anneau sur chaque carte choisit le plan que le Moteur et
+ Prise vont tourner. Il suit la derniere prise ajoutee, et l'appareil s'en
souvient d'un chargement a l'autre."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=56)
with Banc(8785, 9385, taille=(1200, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    ids = banc.js('DB.plans.slice(0, 4).map(p => p.id)')
    nums = banc.js('DB.plans.slice(0, 4).map(p => p.plan)')
    essais.verifier('un anneau par carte', banc.js("document.querySelectorAll('#l-shoot .viser').length"), banc.js("document.querySelectorAll('#l-shoot .plan').length"))
    essais.verifier('au depart, aucun plan vise', banc.js("document.querySelectorAll('#l-shoot .viser.on').length"), 0)
    essais.verifier('le Moteur ne nomme alors aucun plan', 'plan' in banc.js("$('fab').textContent"), False)

    banc.js("document.querySelector('#l-shoot .viser[data-vise=%s]').click()" % json.dumps(ids[2])); time.sleep(0.3)
    essais.verifier('toucher l anneau vise le plan', banc.js('dernierPlan'), ids[2])
    essais.verifier('sa carte le montre, et elle seule', banc.js("[...document.querySelectorAll('#l-shoot .viser.on')].map(b => b.dataset.vise)"), [ids[2]])
    essais.verifier('le Moteur le nomme', 'plan ' + nums[2] in banc.js("$('fab').textContent"), True)
    essais.verifier('+ Prise compte pour lui', banc.js("$('fab2').textContent"), '+ Prise 1')
    essais.verifier('la fiche du plan ne s ouvre pas pour autant', banc.js('openType'), None)

    banc.js("nouvellePrise()"); time.sleep(0.4)
    essais.verifier('+ Prise ajoute la prise au plan vise', banc.js('prisesDe(%s).length' % json.dumps(ids[2])), 1)

    banc.js("ajouterPrise(%s)" % json.dumps(ids[0])); time.sleep(0.4)
    essais.verifier('une prise ajoutee ailleurs deplace le plan vise', banc.js("[...document.querySelectorAll('#l-shoot .viser.on')].map(b => b.dataset.vise)"), [ids[0]])

    banc.js("document.querySelector('#l-shoot .viser[data-vise=%s]').click()" % json.dumps(ids[1])); time.sleep(0.3)
    banc.ouvrir(repos=1.5)
    essais.verifier('apres rechargement, le plan vise est retrouve', banc.js('dernierPlan'), ids[1])
    essais.verifier('et sa carte le montre', banc.js("[...document.querySelectorAll('#l-shoot .viser.on')].map(b => b.dataset.vise)"), [ids[1]])
    essais.exceptions(banc)
essais.bilan()
