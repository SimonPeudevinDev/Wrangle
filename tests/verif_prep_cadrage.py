# -*- coding: utf-8 -*-
"""En preparation, un plan peut porter plusieurs cadrages : le menu du champ
coche et decoche, le champ s'ecrit « Large / Poitrine », et la valeur suit
dans le projet."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=56)
with Banc(8790, 9390, taille=(1200, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    pid = banc.js('DB.plans[3].id')                    # 6.8 : un plan sans cadrage
    banc.js("""document.querySelector('nav button[data-v="prep"]').click()"""); time.sleep(0.5)
    SEL = "document.querySelector('#l-prep .prow[data-id=%s] input[data-k=\"cadrage\"]')" % json.dumps(pid)
    essais.verifier('le plan choisi n a pas de cadrage', banc.js(SEL + '.value'), '')
    banc.js(SEL + ".closest('.pc').querySelector('.deroul').click()"); time.sleep(0.3)
    essais.verifier('le menu du cadrage s ouvre, a choix multiple', banc.js("!!document.querySelector('.menu.multi')"), True)
    banc.js("""[...document.querySelectorAll('.menu.multi button')].find(b => b.dataset.v === 'Large').click()"""); time.sleep(0.2)
    essais.verifier('le menu reste ouvert apres un choix', banc.js("!!document.querySelector('.menu.multi')"), True)
    banc.js("""[...document.querySelectorAll('.menu.multi button')].find(b => b.dataset.v === 'Poitrine').click()"""); time.sleep(0.2)
    essais.verifier('deux cadrages coches : le champ les ecrit', banc.js(SEL + '.value'), 'Large / Poitrine')
    essais.verifier('et le projet les garde', banc.js('plan(%s).cadrage' % json.dumps(pid)), 'Large / Poitrine')
    essais.verifier('les deux sont coches dans le menu',
                    banc.js("[...document.querySelectorAll('.menu.multi button.on')].map(b => b.dataset.v)"), ['Poitrine', 'Large'])
    banc.js("""[...document.querySelectorAll('.menu.multi button')].find(b => b.dataset.v === 'Large').click()"""); time.sleep(0.2)
    essais.verifier('decocher retire la valeur', banc.js(SEL + '.value'), 'Poitrine')
    banc.js('fermerMenu()'); time.sleep(0.2)
    # un champ a valeur unique garde son comportement : choisir ferme le menu
    banc.js(SEL + ".closest('.prow').querySelector('input[data-k=\"jour\"]').closest('.pc').querySelector('.deroul').click()"); time.sleep(0.3)
    essais.verifier('le menu du jour est a choix unique', banc.js("!!document.querySelector('.menu:not(.multi)')"), True)
    banc.js("""[...document.querySelectorAll('.menu button')].find(b => b.dataset.v === 'J2').click()"""); time.sleep(0.2)
    essais.verifier('choisir un jour ferme le menu', banc.js("!!document.querySelector('.menu')"), False)
    essais.verifier('et pose la valeur', banc.js('plan(%s).jour' % json.dumps(pid)), 'J2')
    essais.exceptions(banc)
essais.bilan()
