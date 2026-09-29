# -*- coding: utf-8 -*-
"""Une vraie coupure, comme en 4G en zone blanche : le serveur s'arrete, on
saisit une prise, et l'appli est fermee avant le retour du reseau (la memoire
de l'onglet part avec lui). Rouverte plus tard, dans un onglet neuf, la page
doit retrouver la prise et l'envoyer au serveur, au lieu de la perdre sous la
copie du serveur. La page est en mode « php », comme sur le site."""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, CDP, Essais, RACINE, patienter              # noqa: E402

PORT, PORT_CDP = 8791, 9411
essais = Essais(largeur=62)


def etat(espace):
    return json.loads(urllib.request.urlopen('http://localhost:%d/api/etat.php?espace=%s' % (PORT, espace), timeout=5).read())


def prises(espace):
    return len((etat(espace)['db'] or {}).get('prises', []))


def onglets():
    return [t for t in json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT_CDP).read())
            if t.get('type') == 'page']


with Banc(PORT, PORT_CDP) as b:
    b.ouvrir('/?php=1')
    b.js("changerDePersonne('Wanda'); document.getElementById('voile-nom').hidden = true")
    patienter(lambda: b.js("RESEAU.etat === 'ok'"), tours=40)
    b.js("operer({op:'add', kind:'plan', data:{id:'p1', seq:'01', plan:'01', jour:'J1', elements:{}}, apres:''});"
         "DB.plans.push({id:'p1', seq:'01', plan:'01', jour:'J1', elements:{}}); save(); ajouterPrise('p1')")
    patienter(lambda: prises('wanda') == 1, tours=40)
    essais.verifier('une prise en ligne, sur le serveur', prises('wanda'), 1)

    # la 4G tombe : plus de serveur du tout
    b.serveur.terminate()
    b.serveur.wait(5)
    b.js("var t = ajouterPrise('p1'); patch('prise', t.id, {clip:'HORS001'})")
    coupe = patienter(lambda: b.js("RESEAU.etat === 'coupe'"), tours=40, pause=0.5)
    essais.verifier('hors reseau : pastille hors ligne, 2 prises sur le telephone', [bool(coupe), b.js("DB.prises.length")], [True, 2])

    # l'appli est fermee pendant la coupure ; plus tard, on la rouvre : un onglet neuf
    vieux = onglets()
    neuf = json.loads(urllib.request.urlopen(urllib.request.Request(
        'http://127.0.0.1:%d/json/new?about:blank' % PORT_CDP, method='PUT')).read())
    for t in vieux:
        urllib.request.urlopen('http://127.0.0.1:%d/json/close/%s' % (PORT_CDP, t['id'])).read()
    time.sleep(4)
    essais.verifier('l ancien onglet est ferme', [t['url'] for t in onglets()], ['about:blank'])
    b.cdp = CDP(neuf['webSocketDebuggerUrl'])
    for quoi in ('Runtime', 'Page', 'Log'):
        b.cdp.appel(quoi + '.enable')
    time.sleep(18)   # l'onglet ferme ne redate plus sa file : elle devient orpheline

    # le reseau revient, puis on rouvre l'appli
    b.serveur = subprocess.Popen([sys.executable, os.path.join(RACINE, 'serveur.py'), str(PORT), '--data', b.data],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    patienter(lambda: urllib.request.urlopen('http://localhost:%d/api/etat' % PORT, timeout=2).read(), tours=60)
    essais.verifier('au retour du reseau, le serveur n a que la prise d avant', prises('wanda'), 1)
    b.ouvrir('/?php=1')
    essais.verifier('reouverture : meme prenom, en ligne', patienter(lambda: b.js("UI.nom === 'Wanda' && RESEAU.etat === 'ok'"), tours=40), True)
    patienter(lambda: prises('wanda') == 2, tours=40, pause=0.5)
    essais.verifier('la prise saisie hors reseau est toujours sur le telephone',
                    b.js("DB.prises.map(t => t.clip || '').filter(Boolean)"), ['HORS001'])
    essais.verifier('et elle est partie au serveur, avec son clip',
                    [t.get('clip', '') for t in etat('wanda')['db']['prises'] if t.get('clip')], ['HORS001'])
    essais.verifier('la file reprise est vide une fois envoyee', b.js("[RESEAU.attente.length, Object.keys(localStorage).filter(k => k.indexOf('fstdw.attente.') === 0).length]"), [0, 0])
    essais.exceptions(b)
essais.bilan()
