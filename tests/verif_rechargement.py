# -*- coding: utf-8 -*-
"""Le second chargement : la page demarre-t-elle encore quand le navigateur a deja une
copie locale du projet ? C'est le cas de tous les appareils du plateau apres la premiere
visite. Une constante lue avant sa declaration dans normaliser() ne casse que dans ce cas :
un navigateur vierge n'a aucun plan a normaliser et ne voit rien.

  py tests/verif_rechargement.py
"""
import json, os, subprocess, sys, tempfile, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ICI, 'tests'))
from lancer_scenario import CDP, NAVIGATEURS          # noqa: E402

PORT, CDP_PORT = 8776, 9361
essais = []


def verifier(quoi, obtenu, attendu):
    ok = obtenu == attendu
    essais.append(ok)
    print('  %s  %-52s %r' % ('ok ' if ok else 'ECHEC', quoi, obtenu))


data = tempfile.mkdtemp(prefix='wrangle-rc-'); profil = tempfile.mkdtemp(prefix='wrangle-profil-')
serveur = subprocess.Popen([sys.executable, os.path.join(ICI, 'serveur.py'), str(PORT), '--data', data],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = 'http://localhost:%d' % PORT
exe = next(n for n in NAVIGATEURS if os.path.exists(n))
chrome = subprocess.Popen([exe, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                           '--no-default-browser-check', '--disable-extensions',
                           '--remote-debugging-port=%d' % CDP_PORT, '--user-data-dir=' + profil,
                           '--window-size=1300,800', 'about:blank'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(base + '/api/etat', timeout=2).read(); break
        except Exception:
            time.sleep(0.2)
    cible = None
    for _ in range(80):
        try:
            pages = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % CDP_PORT, timeout=2).read())
            cible = next((p for p in pages if p.get('type') == 'page'), None)
            if cible: break
        except Exception:
            pass
        time.sleep(0.2)
    cdp = CDP(cible['webSocketDebuggerUrl'])
    cdp.appel('Runtime.enable'); cdp.appel('Log.enable'); cdp.appel('Page.enable')

    def charger():
        cdp.evenements.clear()
        cdp.appel('Page.navigate', url=base + '/')
        for _ in range(80):
            if cdp.evaluer("typeof DB !== 'undefined' && document.readyState === 'complete'") is True: break
            time.sleep(0.25)
        time.sleep(1.2)
        return [e for e in cdp.evenements if e.get('method') == 'Runtime.exceptionThrown']

    erreurs = charger()
    n = cdp.evaluer("DB.plans.length")
    verifier('premier chargement : le decoupage est la, sans erreur', [n > 0, len(erreurs)], [True, 0])
    # on touche au projet, pour que la copie locale contienne une prise et un plan modifies
    cdp.evaluer("document.querySelectorAll('#choix-nom .btn')[1].click(); ajouterPrise(DB.plans[0].id, false); patch('plan', DB.plans[1].id, {mouv:'Handheld'}); flush()")
    time.sleep(0.5)
    verifier('copie locale ecrite', cdp.evaluer("!!localStorage.getItem('fstdw.v1')"), True)

    erreurs = charger()
    verifier('second chargement, copie locale en place : la page demarre', [cdp.evaluer("DB.plans.length"), cdp.evaluer("document.querySelectorAll('#l-shoot .plan').length > 0"), len(erreurs)], [n, True, 0])
    for e in erreurs[:3]:
        d = e['params']['exceptionDetails']
        print('   ', (d.get('exception') or {}).get('description', d.get('text'))[:300].replace('\n', ' | '))
    verifier('le reseau se connecte apres le second chargement', cdp.evaluer("RESEAU.etat"), 'ok')
    # une erreur rattrapee au chargement jette la copie locale et passe par console.error : on la voit ici
    verifier('la copie locale est toujours la (rien n a ete rattrape en silence)', cdp.evaluer("!!localStorage.getItem('fstdw.v1')"), True)
    consoles = [e for e in cdp.evenements if e.get('method') == 'Runtime.consoleAPICalled' and e['params'].get('type') == 'error']
    verifier('aucun message d erreur en console', len(consoles), 0)
    for e in consoles[:2]:
        print('   ', ' '.join(str(a.get('value', a.get('description', '')))[:160] for a in e['params'].get('args', [])))
    verifier('l ancien Handheld est range en support', cdp.evaluer("[DB.plans[1].mouv, DB.plans[1].support]"), ['', 'Épaule'])
finally:
    for p in (chrome, serveur):
        try: p.terminate()
        except Exception: pass
print('\n%d/%d verifications passees' % (sum(essais), len(essais)))
sys.exit(0 if all(essais) else 1)
