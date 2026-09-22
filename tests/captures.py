#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Captures d'écran de la page (format téléphone et grand écran) pour contrôler
l'interface à l'œil. Démarre un serveur temporaire, comme lancer_scenario.py.

  py tests\\captures.py [dossier_de_sortie]
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lancer_scenario import CDP, NAVIGATEURS, ICI  # noqa: E402

PORT = 8798
PORT_CDP = 9334
SORTIE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), 'fstdw-captures')


def main():
    exe = next((n for n in NAVIGATEURS if os.path.exists(n)), None)
    if not exe:
        print('Aucun navigateur Chrome/Edge trouvé.'); return 2
    os.makedirs(SORTIE, exist_ok=True)
    data = tempfile.mkdtemp(prefix='fstdw-data-')
    serveur = subprocess.Popen([sys.executable, os.path.join(ICI, '..', 'serveur.py'), str(PORT), '--data', data],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = 'http://localhost:%d' % PORT
    for _ in range(50):
        try:
            urllib.request.urlopen(base + '/api/etat', timeout=2).read(); break
        except Exception:
            time.sleep(0.2)
    profil = tempfile.mkdtemp(prefix='fstdw-cap-')
    proc = subprocess.Popen([exe, '--headless=new', '--disable-gpu', '--no-first-run', '--disable-extensions',
                             '--hide-scrollbars', '--remote-debugging-port=%d' % PORT_CDP,
                             '--user-data-dir=' + profil, 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        cible = None
        for _ in range(100):
            try:
                pages = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT_CDP, timeout=2).read())
                cible = next((p for p in pages if p.get('type') == 'page'), None)
                if cible:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        cdp = CDP(cible['webSocketDebuggerUrl'])
        cdp.appel('Page.enable'); cdp.appel('Runtime.enable')

        def vue(largeur, hauteur, mobile):
            cdp.appel('Emulation.setDeviceMetricsOverride', width=largeur, height=hauteur,
                      deviceScaleFactor=2, mobile=mobile)

        def capture(nom):
            r = cdp.appel('Page.captureScreenshot', format='png')
            chemin = os.path.join(SORTIE, nom + '.png')
            with open(chemin, 'wb') as f:
                f.write(base64.b64decode(r['data']))
            print('capture', chemin)

        def js(code):
            return cdp.evaluer(code)

        vue(390, 844, True)
        cdp.appel('Page.navigate', url=base + '/?client=cap&nom=Marie')
        time.sleep(2.5)
        # quelques prises pour que la liste ait de la matiere
        js("""(() => { const p = DB.plans[7]; dernierPlan = p.id;
          const a = ajouterPrise(p.id); patch('prise', a.id, {clip:'A001C001', cam:'CAM-A', carte:'A001', statut:'NG', notes:'Faux raccord regard', diaph:'T2.8', fps:'25'});
          const b = ajouterPrise(p.id); patch('prise', b.id, {clip:'A001C002', statut:'OK', retenue:true, heure:'14:35', duree:'12s', focusStart:'2.40 m', focusStop:'3.10 m'});
          const q = DB.plans[8]; const c = ajouterPrise(q.id); patch('prise', c.id, {clip:'A001C003', heure:'14:41'});
          renderAll(); window.scrollTo(0, 0); })()""")
        time.sleep(0.6)
        js("setJour('CG'); window.scrollTo(0, document.querySelector('.plan.done').offsetTop - 150)")
        time.sleep(0.4)
        capture('01-liste-mobile')
        js("openPrise(prisesDe(DB.plans[7].id)[1].id)")
        time.sleep(0.4)
        capture('02-fiche-prise-mobile')
        js("document.getElementById('sbody').scrollTop = 620")
        time.sleep(0.3)
        capture('03-fiche-prise-suite-mobile')
        js("closeSheet(); moteur()")
        time.sleep(1.3)
        capture('04-moteur-mobile')
        js("couper(); basculerTheme()")
        time.sleep(0.4)
        capture('05-liste-clair-mobile')
        js("basculerTheme(); closeSheet(); document.querySelector('nav button[data-v=report]').click()")
        time.sleep(0.5)
        capture('06-rapport-mobile')
        js("document.querySelector('nav button[data-v=shoot]').click(); openProd()")
        time.sleep(0.5)
        capture('07-journee-mobile')
        js("closeSheet(); document.querySelector('nav button[data-v=cards]').click(); creerCartesOubliees(); openCard(); closeSheet()")
        time.sleep(0.5)
        capture('09-medias-mobile')
        js("openCard(DB.cards[0].id)")
        time.sleep(0.4)
        capture('10-fiche-carte-mobile')
        js("closeSheet(); document.querySelector('nav button[data-v=shoot]').click(); openPlan(DB.plans[7].id); toggleElement('vert'); toggleElement('hdri'); document.getElementById('sbody').scrollTop = 700")
        time.sleep(0.4)
        capture('11-fiche-plan-mobile')
        js("closeSheet(); choisirPlan(true)")
        time.sleep(0.4)
        capture('12-choix-plan-mobile')
        js("closeSheet()")
        vue(1280, 800, False)
        time.sleep(0.5)
        js("setJour('CG'); openPrise(prisesDe(DB.plans[7].id)[1].id)")
        time.sleep(0.5)
        capture('08-grand-ecran')
        try:
            cdp.appel('Browser.close')
        except Exception:
            pass
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        serveur.kill(); serveur.wait()
        shutil.rmtree(profil, ignore_errors=True)
        shutil.rmtree(data, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
