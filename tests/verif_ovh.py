# -*- coding: utf-8 -*-
"""Le serveur PHP chez l'hebergeur, en vrai : on parle a api/ sur le site
publie, comme la page le fait, dans deux espaces d'essai (essai-a, essai-b)
qui sont vides a la fin. A lancer a la main apres une publication ; il faut
le reseau.

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


def ops(client, nom, espace, liste):
    return api('ops.php', {'client': client, 'nom': nom, 'espace': espace, 'ops': liste})[1]


def etat(espace):
    return api('etat.php?espace=' + espace)[1]


PROJET = {'prod': {'titre': 'Essai'}, 'optiques': [], 'prises': [],
          'plans': [{'id': 'pA', 'plan': '01', 'seq': '01', 'jour': 'J1'}, {'id': 'pB', 'plan': '02', 'seq': '01', 'jour': 'J1'}]}
VIDE = {'prod': {}, 'optiques': [], 'plans': [], 'prises': []}

essais = Essais(largeur=62)
statut, e = api('etat.php?espace=essai-a')
essais.verifier('api/etat.php repond en JSON, pour l espace demande', [statut, e.get('serveur'), e.get('espace')], [200, 'php', 'essai-a'])

# -- l'espace d'essai A : deux appareils de la meme personne
r = ops('testA', 'Alice', 'essai-a', [{'op': 'remplacer', 'db': PROJET}])
rev0 = r['rev']
essais.verifier('remplacer : le projet d essai est en place', r['ops'], [{'op': 'remplacer'}])
statut, d = api('depuis.php?rev=0&client=testA2&nom=Alice&espace=essai-a')
essais.verifier('un second appareil qui arrive recoit le projet entier', [len(d['db']['plans']), d['rev']], [2, rev0])
r1 = ops('testA', 'Alice', 'essai-a', [{'op': 'add', 'kind': 'prise', 'data': {'id': 't1', 'planId': 'pA', 'n': 1, 'statut': 'OK'}}])
r2 = ops('testA2', 'Alice', 'essai-a', [{'op': 'add', 'kind': 'prise', 'data': {'id': 't2', 'planId': 'pA', 'n': 1, 'statut': 'NG'}}])
essais.verifier('deux prises au meme plan, meme numero : le serveur tranche', [r1['ops'][0]['data']['n'], r2['ops'][0]['data']['n']], [1, 2])
statut, d = api('depuis.php?rev=%d&client=testA2&espace=essai-a' % rev0)
essais.verifier('depuis : les operations des deux appareils, dans l ordre, sans le projet', ['db' in d, [x['client'] for x in d.get('ops', [])], d['rev']], [False, ['testA', 'testA2'], rev0 + 2])
statut, d = api('depuis.php?rev=%d&client=testA2&espace=essai-a' % (rev0 + 1))
essais.verifier('depuis la revision suivante : la derniere seulement', [x['ops'][0]['data']['id'] for x in d.get('ops', [])], ['t2'])
r = ops('testA', 'Alice', 'essai-a', [{'op': 'patch', 'kind': 'prise', 'id': 't1', 'data': {'carte': 'A001'}},
                                       {'op': 'patch', 'kind': 'prod', 'data': {'titre': 'Essai 2'}}])
essais.verifier('des modifications de champs', [o['op'] for o in r['ops']], ['patch', 'patch'])
r = ops('testA', 'Alice', 'essai-a', [{'op': 'del', 'kind': 'prise', 'id': 't1', 'planId': 'pA'}])
essais.verifier('une suppression renumerote l autre prise', [(o['op'], o.get('data', {}).get('n')) for o in r['ops']], [('del', None), ('patch', 1)])
r = ops('testA', 'Alice', 'essai-a', [{'op': 'move', 'kind': 'plan', 'id': 'pB', 'apres': ''}])
e = etat('essai-a')
essais.verifier('un plan deplace en tete', [p['id'] for p in e['db']['plans']], ['pB', 'pA'])
essais.verifier('le projet a bout : une prise, le titre change', [len(e['db']['prises']), e['db']['prod']['titre']], [1, 'Essai 2'])
statut, d = api('depuis.php?rev=999999999&client=testA2&espace=essai-a')
essais.verifier('une revision inconnue recoit le projet entier', 'db' in d, True)

# -- l'espace d'essai B : une autre personne, qui ne voit pas A
r = ops('testB', 'Bob', 'essai-b', [{'op': 'remplacer', 'db': PROJET},
                                    {'op': 'add', 'kind': 'prise', 'data': {'id': 'b1', 'planId': 'pB', 'n': 1, 'statut': 'OK'}}])
essais.verifier('Bob a son espace, avec sa prise', [len(etat('essai-b')['db']['prises']), len(etat('essai-a')['db']['prises'])], [1, 1])
statut, l = api('espaces.php')
essai = [(x['espace'], x['nom'], x['plans'], x['prises']) for x in l['espaces'] if x['espace'].startswith('essai-')]
essais.verifier('la liste des espaces, pour le DIT', essai, [('essai-a', 'Alice', 2, 1), ('essai-b', 'Bob', 2, 1)])
presents = sorted((x['nom'], x['espace']) for x in etat('essai-a')['presence'] if x['client'] in ('testA', 'testA2', 'testB'))
essais.verifier('la presence : les deux appareils d Alice et celui de Bob, chacun dans son espace',
                presents, [('Alice', 'essai-a'), ('Alice', 'essai-a'), ('Bob', 'essai-b')])
statut, m = api('mail.php')
essais.verifier('la boite d envoi de l hebergeur', [statut, m.get('possible'), '@' in m.get('expediteur', '')], [200, True, True])
statut, r = api('ops.php', {'client': '', 'ops': []})
essais.verifier('un appel sans client est refuse', statut, 400)

# -- on vide les espaces d'essai : ils disparaissent de la liste
ops('testA', 'Alice', 'essai-a', [{'op': 'remplacer', 'db': VIDE}])
ops('testB', 'Bob', 'essai-b', [{'op': 'remplacer', 'db': VIDE}])
statut, l = api('espaces.php')
essais.verifier('les espaces d essai sont vides et hors liste', [etat('essai-a')['db'], [x['espace'] for x in l['espaces'] if x['espace'].startswith('essai-')]], [None, []])
essais.bilan()
