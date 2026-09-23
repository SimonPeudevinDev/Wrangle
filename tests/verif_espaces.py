# -*- coding: utf-8 -*-
"""Chacun ses saisies, sur le serveur de plateau aussi : serveur.py tient un
espace par prenom, sur le disque (data/espaces/<prenom>/), et le flux d'un
appareil ne porte que son espace. Simon ne voit pas ce que Romain saisit ;
passer le telephone a Romain change d'espace ; le DIT ramene les saisies de
tous dans le rapprochement. La pastille en haut dit qui saisit. Et le projet
du temps ou le serveur n'avait qu'un carnet (data/projet.json) devient
l'espace « commun » au demarrage, sans rien perdre.

  py tests/verif_espaces.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, RACINE, patienter                  # noqa: E402

PORT = 8777


def api(chemin, corps=None, port=PORT):
    url = 'http://localhost:%d/api/%s' % (port, chemin)
    if corps is None:
        r = urllib.request.urlopen(url, timeout=5)
    else:
        req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req, timeout=5)
    return json.loads(r.read())


def etat(espace):
    return api('etat?espace=' + espace)


def ops(client, nom, espace, liste):
    return api('ops', {'client': client, 'nom': nom, 'espace': espace, 'ops': liste})


def attendre(f, secondes=6.0):
    fin = time.time() + secondes
    while time.time() < fin:
        try:
            if f():
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


essais = Essais(largeur=64)
with Banc(PORT, 9376, taille=(1200, 900)) as banc:
    banc.ouvrir()
    essais.verifier('sans prenom, pas de flux : l espace, c est le prenom', [banc.js('RESEAU.src'), banc.js('RESEAU.etat')], [None, 'local'])
    essais.verifier('la pastille dit Local en attendant', banc.js("$('pres').textContent"), 'Local')
    banc.nommer()                                    # Simon
    essais.verifier('nomme, l appareil se branche sur son espace', attendre(lambda: banc.js('RESEAU.etat') == 'ok'), True)
    essais.verifier('le flux porte l espace de Simon', 'espace=simon' in (banc.js('RESEAU.src && RESEAU.src.url') or ''), True)
    essais.verifier('la pastille porte son prenom', banc.js("$('pres').textContent"), 'Simon')
    essais.verifier('la copie locale est rangee sous son prenom', [banc.js("!!localStorage.getItem('fstdw.v1:simon')"), banc.js("localStorage.getItem('fstdw.v1')")], [True, None])

    banc.js("ajouterPrise(DB.plans[0].id, false, { clip:'A001C001', par:'Simon' }); flush()")
    essais.verifier('sa prise arrive dans son espace sur le serveur',
                    attendre(lambda: len((etat('simon')['db'] or {}).get('prises', [])) == 1), True)
    essais.verifier('l espace de Romain, lui, est vide', etat('romain')['db'], None)
    essais.verifier('le projet de Simon est ecrit sur le disque, dans son dossier',
                    attendre(lambda: os.path.exists(os.path.join(banc.data, 'espaces', 'simon', 'projet.json'))), True)
    essais.verifier('et son prenom tel qu il l ecrit, a cote',
                    open(os.path.join(banc.data, 'espaces', 'simon', 'nom.txt'), encoding='utf-8').read(), 'Simon')

    # -- Romain saisit de son telephone (joue par l'API) : Simon n'en voit rien
    d = etat('simon')['db']
    d['prises'] = []
    q = d['plans'][1]
    prise_romain = {'id': 'romain1', 'planId': q['id'], 'seq': q['seq'], 'plan': q['plan'], 'jour': q['jour'],
                    'n': 1, 'clip': 'B001C001', 'statut': 'OK', 'par': 'Romain'}
    ops('tel-romain', 'Romain', 'romain', [{'op': 'remplacer', 'db': d, 'siVide': True},
                                            {'op': 'add', 'kind': 'prise', 'data': prise_romain}])
    time.sleep(1.5)
    essais.verifier('Romain a sa prise dans son espace', [t['clip'] for t in etat('romain')['db']['prises']], ['B001C001'])
    essais.verifier('Simon ne la voit pas : il n a que la sienne', banc.js('DB.prises.map(t => t.clip)'), ['A001C001'])
    essais.verifier('la liste des connectes, elle, est commune',
                    sorted(x['nom'] for x in etat('simon')['presence']), ['Romain', 'Simon'])

    # -- Simon passe le telephone a Romain : l'appareil change d'espace
    banc.js('choisirNom(0)')
    essais.verifier('Romain retrouve ses saisies, venues du serveur',
                    attendre(lambda: banc.js("DB.prises.map(t => t.par + ' ' + t.clip)") == ['Romain B001C001']), True)
    essais.verifier('le flux est reparti sur son espace', 'espace=romain' in (banc.js('RESEAU.src && RESEAU.src.url') or ''), True)
    essais.verifier('la pastille dit Romain', banc.js("$('pres').textContent").startswith('Romain'), True)
    banc.js("ajouterPrise(DB.plans[1].id, false, { clip:'B001C002', par:'Romain' }); flush()")
    essais.verifier('ce qu il saisit part dans son espace a lui',
                    attendre(lambda: [t['clip'] for t in etat('romain')['db']['prises']] == ['B001C001', 'B001C002']), True)
    essais.verifier('celui de Simon n a pas bouge', [t['clip'] for t in etat('simon')['db']['prises']], ['A001C001'])

    # -- retour a Simon, depuis la fiche Journee
    banc.js('openProd()'); time.sleep(0.3)
    banc.js("[...document.querySelectorAll('#sbody .choix .btn')].find(b => b.textContent === 'Simon').click()")
    essais.verifier('Simon retrouve sa prise, et rien d autre',
                    attendre(lambda: banc.js('DB.prises.map(t => t.clip)') == ['A001C001']), True)

    # -- le DIT reunit tout : les espaces des autres, pas le sien
    esp = api('espaces')['espaces']
    essais.verifier('le serveur liste les espaces qui ont un projet',
                    [(e['espace'], e['nom'], e['prises']) for e in esp], [('romain', 'Romain', 2), ('simon', 'Simon', 1)])
    banc.js("view = 'report'; renderAll(); recupererEspaces()")
    essais.verifier('le rapprochement ramene les saisies de Romain',
                    attendre(lambda: banc.js('RAP.sources.map(s => s.nom + \" \" + s.db.prises.length)') == ['Romain 2']), True)
    essais.verifier('le bouton est dans le rapport', banc.js("!!document.querySelector('#rapprocher button[onclick=\"recupererEspaces()\"]')"), True)

    # -- « Toute l'equipe » : le bilan et les exports du DIT portent sur tous, sans toucher a son projet
    essais.verifier('le bilan porte d abord sur mes saisies', banc.js("$('report').querySelector('.kpi .v').textContent"), '1')
    banc.js('voirEquipe(true)'); time.sleep(0.4)
    essais.verifier('« Toute l equipe » : le bilan compte les prises de tous', banc.js("$('report').querySelector('.kpi .v').textContent"), '3')
    essais.verifier('les exports lisent le projet reuni', banc.js('surLePerimetre(() => DB.prises.map(t => t.par + " " + t.clip).sort())'), ['Romain B001C001', 'Romain B001C002', 'Simon A001C001'])
    essais.verifier('le projet de cet appareil n a pas bouge', banc.js('DB.prises.map(t => t.clip)'), ['A001C001'])
    essais.verifier('les fichiers exportes le disent', banc.js("fname('journal-DIT', 'pdf')").endswith('_equipe.pdf'), True)
    essais.verifier('le bilan dit qui est reuni', 'Romain' in banc.js("$('perimetre').textContent") and 'Simon (ici)' in banc.js("$('perimetre').textContent"), True)
    banc.js('voirEquipe(false)'); time.sleep(0.3)
    essais.verifier('« Mes saisies » : retour a mon bilan', [banc.js("$('report').querySelector('.kpi .v').textContent"), banc.js("fname('x', 'csv')").endswith('_equipe.csv')], ['1', False])

    # -- recharger la page garde la personne et son espace
    banc.ouvrir('/?t=2')
    essais.verifier('au rechargement, toujours Simon, branche sur son espace',
                    [banc.js('UI.nom'), attendre(lambda: banc.js('RESEAU.etat') == 'ok'), banc.js('DB.prises.map(t => t.clip)')],
                    ['Simon', True, ['A001C001']])
    essais.exceptions(banc)

# -- le projet d'avant les espaces devient l'espace « commun »
data = tempfile.mkdtemp(prefix='wrangle-migration-')
try:
    vieux = {'version': 2, 'prod': {'titre': 'Ancien'}, 'optiques': [],
             'plans': [{'id': 'p1', 'seq': '01', 'plan': '01', 'jour': 'J1', 'elements': {}}],
             'prises': [{'id': 't1', 'planId': 'p1', 'n': 1, 'clip': 'Z001C001', 'par': 'Simon'}]}
    with open(os.path.join(data, 'projet.json'), 'w', encoding='utf-8') as f:
        json.dump(vieux, f)
    os.makedirs(os.path.join(data, 'sauvegardes'))
    with open(os.path.join(data, 'sauvegardes', 'projet_2026-01-01_000000.json'), 'w', encoding='utf-8') as f:
        json.dump(vieux, f)
    port = PORT + 1
    srv = subprocess.Popen([sys.executable, os.path.join(RACINE, 'serveur.py'), str(port), '--data', data],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        patienter(lambda: api('etat', port=port) or True, tours=60, pause=0.25)
        commun = api('etat?espace=commun', port=port)['db']
        essais.verifier('l ancien projet est servi comme espace « commun »',
                        [commun['prod']['titre'], [t['clip'] for t in commun['prises']]], ['Ancien', ['Z001C001']])
        essais.verifier('le fichier a demenage, avec ses sauvegardes',
                        [os.path.exists(os.path.join(data, 'projet.json')),
                         os.path.exists(os.path.join(data, 'espaces', 'commun', 'projet.json')),
                         os.path.exists(os.path.join(data, 'espaces', 'commun', 'sauvegardes', 'projet_2026-01-01_000000.json'))],
                        [False, True, True])
        essais.verifier('et le DIT le voit dans la liste des espaces',
                        [(e['espace'], e['nom']) for e in api('espaces', port=port)['espaces']], [('commun', 'Commun')])
        essais.verifier('un appareil sans espace tombe dans commun', api('etat', port=port)['db']['prod']['titre'], 'Ancien')
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()
finally:
    shutil.rmtree(data, ignore_errors=True)
essais.bilan()
