# -*- coding: utf-8 -*-
"""Le plan vise : un anneau sur chaque carte choisit le plan que le Moteur et
+ Prise vont tourner. Ce choix passe avant tout : ouvrir ou ajouter une prise
ailleurs ne le deplace pas. Sans choix, le Moteur suit le dernier plan touche.
L'appareil se souvient du choix d'un chargement a l'autre."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

VISES = "[...document.querySelectorAll('#l-shoot .viser.on')].map(b => b.dataset.vise)"

essais = Essais(largeur=58)
with Banc(8785, 9385, taille=(1200, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    ids = banc.js('DB.plans.slice(0, 4).map(p => p.id)')
    nums = banc.js('DB.plans.slice(0, 4).map(p => p.plan)')
    essais.verifier('un anneau par carte', banc.js("document.querySelectorAll('#l-shoot .viser').length"),
                    banc.js("document.querySelectorAll('#l-shoot .plan').length"))
    essais.verifier('au depart, aucun plan vise', banc.js(VISES), [])
    essais.verifier('le Moteur ne nomme alors aucun plan', 'plan' in banc.js("$('fab').textContent"), False)

    # -- sans choix, le Moteur suit le dernier plan touche
    banc.js("ajouterPrise(%s)" % json.dumps(ids[0])); time.sleep(0.4)
    essais.verifier('une prise ajoutee : le Moteur suit ce plan', banc.js(VISES), [ids[0]])

    # -- l'anneau choisit, et ce choix passe avant tout
    banc.js("document.querySelector('#l-shoot .viser[data-vise=%s]').click()" % json.dumps(ids[2])); time.sleep(0.3)
    essais.verifier('toucher l anneau vise le plan', banc.js('UI.vise'), ids[2])
    essais.verifier('sa carte le montre, et elle seule', banc.js(VISES), [ids[2]])
    essais.verifier('le Moteur le nomme', 'plan ' + nums[2] in banc.js("$('fab').textContent"), True)
    essais.verifier('+ Prise compte pour lui', banc.js("$('fab2').textContent"), '+ Prise 1')
    essais.verifier('la fiche du plan ne s ouvre pas pour autant', banc.js('openType'), None)

    banc.js("ajouterPrise(%s)" % json.dumps(ids[0])); time.sleep(0.4)
    essais.verifier('une prise ajoutee ailleurs ne deplace pas le plan vise', banc.js(VISES), [ids[2]])
    banc.js("openPrise(prisesDe(%s)[0].id)" % json.dumps(ids[0])); time.sleep(0.4)
    essais.verifier('ouvrir une prise ailleurs non plus', banc.js(VISES), [ids[2]])
    essais.verifier('le Moteur nomme toujours le plan vise', 'plan ' + nums[2] in banc.js("$('fab').textContent"), True)
    banc.js("closeSheet(); nouvellePrise()"); time.sleep(0.4)
    essais.verifier('+ Prise ajoute la prise au plan vise', banc.js('prisesDe(%s).length' % json.dumps(ids[2])), 1)

    # -- toucher a nouveau l'anneau rend la main au suivi automatique
    banc.js("document.querySelector('#l-shoot .viser[data-vise=%s]').click()" % json.dumps(ids[2])); time.sleep(0.3)
    essais.verifier('retoucher l anneau lache le choix', banc.js('UI.vise'), None)
    essais.verifier('le Moteur revient au dernier plan touche', banc.js(VISES), [ids[2]])

    # -- l'appareil se souvient du choix
    banc.js("document.querySelector('#l-shoot .viser[data-vise=%s]').click()" % json.dumps(ids[1])); time.sleep(0.3)
    banc.ouvrir(repos=1.5)
    essais.verifier('apres rechargement, le plan vise est retrouve', banc.js('UI.vise'), ids[1])
    essais.verifier('et sa carte le montre', banc.js(VISES), [ids[1]])
    essais.exceptions(banc)
essais.bilan()
