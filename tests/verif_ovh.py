# -*- coding: utf-8 -*-
"""Le serveur PHP chez l'hebergeur, en vrai : on parle a api/ sur le site
publie, comme la page le fait. A lancer a la main apres une publication ;
il faut le reseau. Le projet qui s'y trouve est remis en place a la fin.

  py tests/verif_ovh.py                         (le site chez OVH)
  py tests/verif_ovh.py https://autre.site      (un autre hebergeur)
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Essais                                           # noqa: E402

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'http://peojfus.cluster129.hosting.ovh.net').rstrip('/')


def api(chemin, corps=None):
    url = BASE + '/api/' + chemin
    try:
        if corps is None:
            r = urllib.request.urlopen(url, timeout=20)
        else:
            req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'})
            r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        brut = e.read()
        try:
            return e.code, json.loads(brut)
        except ValueError:
            return e.code, {'erreur': brut[:200].decode('utf-8', 'replace')}


def ops(client, nom, liste):
    return api('ops.php', {'client': client, 'nom': nom, 'ops': liste})[1]


PROJET = {'prod': {'titre': 'Essai'}, 'optiques': [], 'prises': [],
          'plans': [{'id': 'pA', 'plan': '01', 'seq': '01', 'jour': 'J1'}, {'id': 'pB', 'plan': '02', 'seq': '01', 'jour': 'J1'}]}

essais = Essais(largeur=60)
statut, e = api('etat.php')
essais.verifier('api/etat.php repond en JSON', [statut, e.get('serveur')], [200, 'php'])
avant = e.get('db')
print('  (projet en place : %s ; il sera remis a la fin)' % ('%d plans, %d prises' % (len(avant['plans']), len(avant['prises'])) if avant else 'aucun'))

# -- un projet d'essai, deux appareils
r = ops('testA', 'Alice', [{'op': 'remplacer', 'db': PROJET}])
rev0 = r['rev']
essais.verifier('remplacer : le projet d essai est en place', r['ops'], [{'op': 'remplacer'}])
statut, d = api('depuis.php?rev=0&client=testB&nom=Bob')
essais.verifier('un appareil qui arrive recoit le projet entier', [len(d['db']['plans']), d['rev']], [2, rev0])
r1 = ops('testA', 'Alice', [{'op': 'add', 'kind': 'prise', 'data': {'id': 't1', 'planId': 'pA', 'n': 1, 'statut': 'OK'}}])
r2 = ops('testB', 'Bob', [{'op': 'add', 'kind': 'prise', 'data': {'id': 't2', 'planId': 'pA', 'n': 1, 'statut': 'NG'}}])
essais.verifier('deux prises au meme plan, meme numero : le serveur tranche', [r1['ops'][0]['data']['n'], r2['ops'][0]['data']['n']], [1, 2])
statut, d = api('depuis.php?rev=%d&client=testB' % rev0)
essais.verifier('depuis : les operations des deux, dans l ordre, sans le projet', ['db' in d, [x['client'] for x in d.get('ops', [])], d['rev']], [False, ['testA', 'testB'], rev0 + 2])
statut, d = api('depuis.php?rev=%d&client=testB' % (rev0 + 1))
essais.verifier('depuis la revision suivante : la derniere seulement', [x['ops'][0]['data']['id'] for x in d.get('ops', [])], ['t2'])
essais.verifier('la presence : Alice et Bob', sorted(x['nom'] for x in d['presence'] if x['client'] in ('testA', 'testB')), ['Alice', 'Bob'])
r = ops('testA', 'Alice', [{'op': 'patch', 'kind': 'prise', 'id': 't1', 'data': {'carte': 'A001'}},
                            {'op': 'patch', 'kind': 'prod', 'data': {'titre': 'Essai 2'}}])
essais.verifier('des modifications de champs', [o['op'] for o in r['ops']], ['patch', 'patch'])
r = ops('testA', 'Alice', [{'op': 'del', 'kind': 'prise', 'id': 't1', 'planId': 'pA'}])
essais.verifier('une suppression renumerote l autre prise', [(o['op'], o.get('data', {}).get('n')) for o in r['ops']], [('del', None), ('patch', 1)])
r = ops('testA', 'Alice', [{'op': 'move', 'kind': 'plan', 'id': 'pB', 'apres': ''}])
statut, e = api('etat.php')
essais.verifier('un plan deplace en tete', [p['id'] for p in e['db']['plans']], ['pB', 'pA'])
essais.verifier('le projet a bout : une prise, le titre change', [len(e['db']['prises']), e['db']['prod']['titre']], [1, 'Essai 2'])
statut, d = api('depuis.php?rev=999999999&client=testB')
essais.verifier('une revision inconnue recoit le projet entier', 'db' in d, True)
statut, d = api('depuis.php?rev=%d&client=testB' % (rev0 - 1) if rev0 > 1 else 'depuis.php?rev=0&client=testB')
essais.verifier('en retard sur le remplacement : le projet entier', 'db' in d, True)
statut, m = api('mail.php')
essais.verifier('la boite d envoi de l hebergeur', [statut, m.get('possible'), '@' in m.get('expediteur', '')], [200, True, True])
statut, r = api('ops.php', {'client': '', 'ops': []})
essais.verifier('un appel sans client est refuse', statut, 400)

# -- remise en place
r = ops('testA', 'Alice', [{'op': 'remplacer', 'db': avant or {'prod': {}, 'optiques': [], 'plans': [], 'prises': []}}])
statut, e = api('etat.php')
essais.verifier('le projet d avant est remis en place', (len(e['db']['plans']) if e['db'] else None), (len(avant['plans']) if avant else None))
essais.bilan()
