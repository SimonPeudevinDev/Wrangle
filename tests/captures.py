#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Captures d'ecran de la page, en format telephone et en grand ecran, pour
controler l'interface a l'oeil. Monte son propre serveur temporaire : le
projet reel n'est jamais touche.

  py tests\\captures.py [dossier_de_sortie]
"""
import base64
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc                                             # noqa: E402

PORT, PORT_CDP = 8797, 9334
SORTIE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), 'wrangle-captures')


def main():
    os.makedirs(SORTIE, exist_ok=True)
    with Banc(PORT, PORT_CDP, taille=(390, 844)) as banc:
        def capture(nom):
            r = banc.cdp.appel('Page.captureScreenshot', format='png')
            chemin = os.path.join(SORTIE, nom + '.png')
            with open(chemin, 'wb') as f:
                f.write(base64.b64decode(r['data']))
            print('capture', chemin)

        banc.vue(390, 844, echelle=2)
        banc.ouvrir('/?client=cap&nom=Marie', repos=2.5)

        # quelques prises pour que la liste ait de la matiere
        banc.js("""(() => { const p = DB.plans[7]; dernierPlan = p.id;
          const a = ajouterPrise(p.id); patch('prise', a.id, {clip:'A001C001', cam:'CAM-A', carte:'A001', statut:'NG', notes:'Faux raccord regard', diaph:'T2.8', fps:'25'});
          const b = ajouterPrise(p.id); patch('prise', b.id, {clip:'A001C002', statut:'OK', retenue:true, heure:'14:35', duree:'12s', focusStart:'2.40 m', focusStop:'3.10 m'});
          const q = DB.plans[8]; const c = ajouterPrise(q.id); patch('prise', c.id, {clip:'A001C003', heure:'14:41'});
          renderAll(); window.scrollTo(0, 0); })()""")
        time.sleep(0.6)

        banc.js("setJour('CG'); window.scrollTo(0, document.querySelector('.plan.done').offsetTop - 150)")
        time.sleep(0.4)
        capture('01-liste-mobile')

        banc.js('openPrise(prisesDe(DB.plans[7].id)[1].id)')
        time.sleep(0.4)
        capture('02-fiche-prise-mobile')

        banc.js("document.getElementById('sbody').scrollTop = 620")
        time.sleep(0.3)
        capture('03-fiche-prise-suite-mobile')

        banc.js('closeSheet(); moteur()')
        time.sleep(1.3)
        capture('04-moteur-mobile')

        banc.js('couper(); basculerTheme()')
        time.sleep(0.4)
        capture('05-liste-clair-mobile')

        banc.js("basculerTheme(); closeSheet(); document.querySelector('nav button[data-v=report]').click()")
        time.sleep(0.5)
        capture('06-rapport-mobile')

        banc.js("document.querySelector('nav button[data-v=shoot]').click(); openProd()")
        time.sleep(0.5)
        capture('07-journee-mobile')

        banc.js("closeSheet(); document.querySelector('nav button[data-v=prep]').click()")
        time.sleep(0.6)
        capture('08-preparation-mobile')

        banc.js("document.querySelector('nav button[data-v=shoot]').click(); openPlan(DB.plans[7].id);"
                " toggleElement('vert'); toggleElement('hdri');"
                " document.getElementById('sbody').scrollTop = 700")
        time.sleep(0.4)
        capture('09-fiche-plan-mobile')

        banc.js('closeSheet(); choisirPlan(true)')
        time.sleep(0.4)
        capture('10-choix-plan-mobile')

        banc.js('closeSheet()')
        banc.vue(1280, 800, mobile=False, echelle=2)
        time.sleep(0.5)
        banc.js("setJour('CG'); openPrise(prisesDe(DB.plans[7].id)[1].id)")
        time.sleep(0.5)
        capture('11-grand-ecran')
    return 0


if __name__ == '__main__':
    sys.exit(main())
