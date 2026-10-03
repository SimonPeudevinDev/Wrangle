# -*- coding: utf-8 -*-
"""La priorite d'un shot : une pastille a trois niveaux, en Tournage et en Preparation.

Sans priorite, une pastille vide « Prio » ; un clic ouvre le menu Principal,
Optionnel, Plan de réserve (et « Aucune ») ; les 4 et 5 d'avant comptent comme plan de réserve.

  py tests/verif_priorite.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais()
with Banc(8799, 9384) as banc:
    banc.ouvrir()
    banc.nommer()
    pid = banc.js("DB.plans[0].id")
    pastille = lambda sel='.plan': banc.js("""(b => b ? b.className + ' | ' + b.textContent : '')(document.querySelector('%s[data-id="%s"] .ptag.prio'))""" % (sel, pid))

    banc.js("patch('plan', DB.plans[0].id, { prio: '' }); renderList()")
    essais.verifier('Tournage : sans priorite, une pastille vide', pastille(), 'ptag vide prio | Prio')
    banc.js("document.querySelector('.plan[data-id=\"%s\"] .ptag.prio').click()" % pid); time.sleep(0.2)
    essais.verifier('le menu : trois niveaux', banc.js("[...document.querySelectorAll('.menu.puce button')].map(b => b.textContent)"),
                    ['Principal', 'Optionnel', 'Plan de réserve'])
    banc.js("document.querySelectorAll('.menu.puce button')[0].click()"); time.sleep(0.2)
    essais.verifier('Principal choisi : vert, sur la carte', [banc.js("DB.plans[0].prio"), pastille()], ['1', 'ptag prio p1 | Principal'])
    banc.js("document.querySelector('.plan[data-id=\"%s\"] .ptag.prio').click()" % pid); time.sleep(0.2)
    essais.verifier('rouvert : la sienne cochee, et Aucune', banc.js("[...document.querySelectorAll('.menu.puce button')].map(b => b.textContent + (b.classList.contains('on') ? '*' : ''))"),
                    ['Principal*', 'Optionnel', 'Plan de réserve', 'Aucune'])
    banc.js("document.querySelectorAll('.menu.puce button')[3].click()"); time.sleep(0.2)
    essais.verifier('Aucune : la pastille redevient vide', [banc.js("DB.plans[0].prio"), pastille()], ['', 'ptag vide prio | Prio'])

    banc.js("patch('plan', DB.plans[0].id, { prio: '5' }); renderList()")
    essais.verifier('un 5 d avant compte comme plan de reserve', pastille(), 'ptag prio p3 | Plan de réserve')

    # Preparation : la meme pastille dans la ligne du shot, plus de colonne a taper
    banc.js("allerVue('prep')"); time.sleep(0.6)
    essais.verifier('Preparation : la pastille dans la ligne du shot', pastille('.prow'), 'ptag prio p3 | Plan de réserve')
    essais.verifier('plus de case Prio a taper', banc.js("!!document.querySelector('#l-prep .w-prio')"), False)
    essais.exceptions(banc)
essais.bilan()
