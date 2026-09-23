# -*- coding: utf-8 -*-
"""Le journal DIT : il s'ouvre sur les prises retenues pour le montage, puis
liste tous les plans, leurs prises, celle qui est retenue, et qui a saisi quoi
a quelle heure."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=56)
with Banc(8792, 9392, taille=(1100, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    ids = banc.js('DB.plans.slice(0, 3).map(p => p.id)')
    banc.js("""
      ajouterPrise(%s, false, { clip:'A001C001', carte:'A001', statut:'NG', notes:'faux départ', par:'Alice', heure:'09:12' });
      ajouterPrise(%s, false, { clip:'A001C002', carte:'A001', statut:'OK', retenue:true, tcIn:'10:22:31:04',
                                tcOut:'10:23:02:12', duree:'31s', par:'Bob', heure:'09:15' });
      ajouterPrise(%s, false, { clip:'A001C003', carte:'A001', statut:'OK', par:'Alice', heure:'09:40' });
    """ % (json.dumps(ids[0]), json.dumps(ids[0]), json.dumps(ids[1])))

    html = banc.js("htmlDIT('*')")
    essais.verifier('un bloc par plan, tous les plans', html.count('<article class="dplan">'), banc.js('DB.plans.length'))
    essais.verifier('la sequence est nommee', 'Séquence 06' in html, True)
    essais.verifier('le journal s ouvre sur la prise retenue et son clip',
                    0 < html.find('A001C002') < html.find('Tous les plans'), True)
    essais.verifier('la prise non retenue n est pas dans le montage',
                    html.find('A001C001') > html.find('Tous les plans'), True)
    essais.verifier('qui a saisi, et quand', 'Bob · 09:15' in html and 'Alice · 09:12' in html, True)
    essais.verifier('la prise retenue est marquee sur son plan',
                    'retenue' in html.split('A001C002')[2][:200], True)
    essais.verifier('l en-tete compte', '<b>1</b>prises à monter' in html and '<b>3</b>prises au total' in html, True)
    essais.verifier('et nomme la carte', '<b>1</b>carte · A001' in html, True)
    essais.verifier('un plan sans prise le dit', html.count('Aucune prise'), banc.js('DB.plans.length') - 2)

    j = banc.js('DB.plans[0].jour')
    html_j = banc.js('htmlDIT(%s)' % json.dumps(j))
    essais.verifier('le journal d un jour ne liste que ses plans',
                    html_j.count('<article class="dplan">'), banc.js('plansDuJour(%s).length' % json.dumps(j)))

    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.4)
    essais.verifier('le bouton Journal DIT est dans le rapport',
                    banc.js("""!!document.querySelector('#report button[onclick="imprimerDIT()"]')"""), True)
    essais.exceptions(banc)
essais.bilan()
