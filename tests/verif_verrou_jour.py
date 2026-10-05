# -*- coding: utf-8 -*-
"""Une journee verrouillee (Journee -> Jours de tournage) ne se modifie plus,
pour toute l'equipe : ni ses shots, ni leurs prises, ni sa preparation, ni sa
date et son decor. Les autres journees restent libres ; la rouvrir rend la main."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

TOUCHE = "$('dlg').dispatchEvent(new KeyboardEvent('keydown', { key: %s, bubbles: true }))"

essais = Essais(largeur=60)
with Banc(8797, 9397, taille=(1100, 900)) as banc:
    banc.ouvrir()
    banc.js("changerDePersonne('Simon')"); time.sleep(0.5)
    j = banc.js('joursConnus().filter(x => x && x !== "CG")[0]')
    autre = banc.js('joursConnus().filter(x => x && x !== "CG")[1]')
    pid = banc.js('plansDuJour(%s)[0].id' % json.dumps(j))
    pid2 = banc.js('plansDuJour(%s)[0].id' % json.dumps(autre))
    tid = banc.js("ajouterPrise(%s, false, { clip:'A001C001' }).id" % json.dumps(pid))
    J, P, T = json.dumps(j), json.dumps(pid), json.dumps(tid)
    nb = lambda: banc.js('DB.plans.length')

    # -- verrouiller : depuis Journee, avec confirmation
    banc.js('openProd()'); time.sleep(0.3)
    banc.js("document.querySelector('.verrou-jour').click()"); time.sleep(0.3)
    essais.verifier('verrouiller demande confirmation', [banc.js("!$('dlg').hidden"), banc.js('jourFige(%s)' % J)], [True, False])
    banc.js(TOUCHE % "'Enter'"); time.sleep(0.4)
    essais.verifier('confirme : la journee est verrouillee', banc.js('DB.prod["verrou_" + %s]' % J), True)
    essais.verifier('le bouton de Journee le dit', banc.js("document.querySelector('.verrou-jour').textContent.trim()"), 'Verrouillé · rouvrir')
    essais.verifier('sa date et son decor en lecture', banc.js("document.querySelector('.jt fieldset').disabled"), True)
    banc.js('closeSheet()'); time.sleep(0.2)

    # -- rien ne passe
    avant = banc.js('JSON.stringify([plan(%s), prise(%s)])' % (P, T))
    banc.js("patch('plan', %s, { desc: 'change' })" % P)
    banc.js("marquer(%s, 'OK'); basculerEtoile(%s)" % (T, T))
    banc.js("patch('prise', %s, { clip: 'Z999' })" % T)
    essais.verifier('ni le shot ni sa prise ne bougent', banc.js('JSON.stringify([plan(%s), prise(%s)])' % (P, T)) == avant, True)
    essais.verifier('la page dit pourquoi', banc.js("$('toast-msg').textContent").endswith('verrouillé : rouvrez-le dans Journée pour le modifier'), True)
    essais.verifier('pas de nouvelle prise', banc.js('ajouterPrise(%s)' % P), None)
    essais.verifier('pas de shot ajoute a ce jour', [banc.js('creerPlan(%s, false)' % J), nb()], [None, nb()])
    banc.js('supprimerJourPrep(%s)' % J); time.sleep(0.2)
    essais.verifier('le jour ne se supprime pas', [banc.js("$('dlg').hidden"), banc.js('plansDuJour(%s).length > 0' % J)], [True, True])
    essais.verifier('le shot ne se supprime pas', banc.js('supprimerPlanConfirme(plan(%s)).then(v => window.__s = v), 1' % P) and
                    (time.sleep(0.2) or banc.js('window.__s')), False)
    banc.js("patch('prod', 'prod', { ['date_' + %s]: '2030-01-01' })" % J)
    essais.verifier('sa date ne change pas', banc.js('DB.prod["date_" + %s] === "2030-01-01"' % J), False)
    banc.js("patch('plan', %s, { jour: %s })" % (json.dumps(pid2), J))
    essais.verifier('un shot d un autre jour n y entre pas', banc.js('plan(%s).jour' % json.dumps(pid2)), autre)
    essais.verifier('le Moteur ne vise pas un shot du jour', [banc.js('viser(%s), UI.vise' % P)], [None])

    # -- les autres jours restent libres
    banc.js("patch('plan', %s, { desc: 'libre' })" % json.dumps(pid2))
    essais.verifier('un autre jour se modifie toujours', banc.js('plan(%s).desc' % json.dumps(pid2)), 'libre')

    # -- ce qui se voit
    banc.js("document.querySelector('nav button[data-v=\"shoot\"]').click()"); time.sleep(0.3)
    essais.verifier('la rangee des jours porte le cadenas',
                    banc.js("[...document.querySelectorAll('#c-jour .chip')].filter(c => c.querySelector('svg.jfige')).map(c => c.textContent.trim())"),
                    [banc.js('nomJour(%s)' % J)])
    banc.js('openPlan(%s)' % P); time.sleep(0.3)
    essais.verifier('la fiche du shot ouvre sur le bandeau du jour',
                    banc.js("document.querySelector('#sbody .verrou-shot span').textContent"), banc.js('nomJour(%s)' % J) + ' verrouillé : rien ne s’y modifie.')
    banc.js('closeSheet()'); time.sleep(0.2)
    banc.js("document.querySelector('nav button[data-v=\"prep\"]').click()"); time.sleep(0.4)
    essais.verifier('la preparation du jour est en lecture, sans « + Plan »',
                    banc.js("(f => !!f && f.disabled && !!f.querySelector('.prow'))(document.querySelector('#l-prep fieldset.fige'))"), True)
    essais.verifier('les autres jours se preparent toujours', banc.js("document.querySelectorAll('#l-prep .addplan').length >= 1"), True)

    # -- rouvrir : sans confirmation, tout repasse
    banc.js('verrouillerJour(%s)' % J); time.sleep(0.3)
    essais.verifier('rouvrir ne demande rien', [banc.js("$('dlg').hidden"), banc.js('jourFige(%s)' % J)], [True, False])
    banc.js("patch('prise', %s, { clip: 'A001C002' })" % T)
    essais.verifier('rouvert, la prise se modifie', banc.js('prise(%s).clip' % T), 'A001C002')
    essais.verifier('et la preparation se tape', banc.js("document.querySelector('#l-prep fieldset.fige')"), None)
    essais.exceptions(banc)
essais.bilan()
