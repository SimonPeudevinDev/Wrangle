# -*- coding: utf-8 -*-
"""Pick-up se coche en plus du resultat : une prise peut etre OK (ou NG) et
Pick-up a la fois. Il ne remplace rien, se decoche seul, et se lit dans la
liste, le journal DIT, la fiche VFX et les exports."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=56)
with Banc(8796, 9396, taille=(1100, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    pid = banc.js('DB.plans[0].id')
    tid = banc.js("ajouterPrise(%s, false, { clip:'A001C001', carte:'A001', par:'Alice', heure:'09:12' }).id" % json.dumps(pid))
    t = lambda k: banc.js('prise(%s).%s' % (json.dumps(tid), k))

    banc.js("marquer(%s, 'OK')" % json.dumps(tid))
    banc.js("marquer(%s, 'Pick-up')" % json.dumps(tid))
    essais.verifier('OK puis Pick-up : les deux restent', [t('statut'), t('pickup')], ['OK', True])
    banc.js("marquer(%s, 'NG')" % json.dumps(tid))
    essais.verifier('NG remplace OK, Pick-up reste', [t('statut'), t('pickup')], ['NG', True])
    banc.js("marquer(%s, 'Pick-up')" % json.dumps(tid))
    essais.verifier('Pick-up se decoche seul', [t('statut'), t('pickup')], ['NG', False])
    banc.js("marquer(%s, 'OK'); marquer(%s, 'Pick-up')" % (json.dumps(tid), json.dumps(tid)))

    # -- la fiche : deux boutons allumes
    banc.js('openPrise(%s)' % json.dumps(tid)); time.sleep(0.4)
    allumes = lambda: banc.js("[...document.querySelectorAll('#seg-statut button.on')].map(b => b.dataset.st)")
    essais.verifier('la fiche allume OK et Pick-up', allumes(), ['OK', 'Pick-up'])
    banc.js("document.querySelector('#seg-statut button[data-st=\"Pick-up\"]').click()"); time.sleep(0.3)
    essais.verifier('cliquer Pick-up dans la fiche ne touche pas a OK', [allumes(), t('statut'), t('pickup')], [['OK'], 'OK', False])
    banc.js("document.querySelector('#seg-statut button[data-st=\"Pick-up\"]').click()"); time.sleep(0.3)
    banc.js('closeSheet && closeSheet()'); time.sleep(0.3)

    # -- la liste : la carte reste verte et dit Pick-up
    banc.js('renderList()'); time.sleep(0.3)
    carte = banc.js("(e => e && [e.classList.contains('ok'), [...e.querySelectorAll('.tstat')].map(x => x.textContent)])"
                    "(document.querySelector('.prise[data-id=%s]'))" % json.dumps(tid))
    essais.verifier('la carte de la prise : verte, et Pick-up', carte, [True, ['Pick-up']])

    # -- le journal DIT et la fiche VFX
    banc.js("patch('prise', %s, { retenue: true })" % json.dumps(tid))
    banc.js('chargerLogo()'); time.sleep(0.8)
    pdf = banc.js("Array.from(pdfDIT('*'), b => String.fromCharCode(b)).join('')")
    essais.verifier('le journal DIT dit OK, puis Pick-up', ['(OK)' in pdf, '( \xb7 Pick-up)' in pdf], [True, True])
    essais.verifier('la fiche VFX le note', 'Pick-up' in banc.js("modeleVFX('*')[0].prises[0].note"), True)
    essais.verifier('l export CSV aussi', 'OK · Pick-up' in banc.js("libStatut(prise(%s))" % json.dumps(tid)), True)

    # -- l'ancien format : Pick-up etait un statut
    essais.verifier('un ancien « Pick-up » devient la marque', banc.js(
        "(db => [db.prises[0].statut, db.prises[0].pickup])(normaliser(Object.assign(structuredClone(DB), "
        "{ prises: [Object.assign(structuredClone(DB.prises[0]), { statut: 'Pick-up', pickup: false })] })))"), ['', True])
    essais.exceptions(banc)
essais.bilan()
