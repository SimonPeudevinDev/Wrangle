# -*- coding: utf-8 -*-
"""Le serveur PHP chez l'hebergeur, en vrai : on parle a api/ sur le site
publie, comme la page le fait, dans deux espaces d'essai (essai-a, essai-b)
vides a la fin. Le decoupage etant commun a tous les espaces, l'essai ne
touche qu'aux prises, et a un plan jetable ajoute puis retire. A lancer a la
main apres une publication ; il faut le reseau.

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

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'https://foresight-movie.com').rstrip('/')


def api(chemin, corps=None):
    url = BASE + '/api/' + chemin
    try:
        if corps is None:
            r = urllib.request.urlopen(url, timeout=25)
        else:
            req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'})
            r = urllib.request.urlopen(req, timeout=25)
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


def cles(db):
    return [(p.get('seq'), p.get('plan')) for p in db['plans']]


# le projet qu'un telephone neuf enverrait : son propre decoupage, seme a part
PROPRE = {'prod': {'titre': 'Essai'}, 'optiques': [], 'prises': [],
          'plans': [{'id': 'pA', 'plan': '01', 'seq': '01', 'jour': 'J1'}, {'id': 'pB', 'plan': '02', 'seq': '01', 'jour': 'J1'}]}
VIDE = {'prod': {}, 'optiques': [], 'plans': [], 'prises': []}

essais = Essais(largeur=64)
statut, e = api('etat.php?espace=essai-a')
essais.verifier('api/etat.php repond en JSON, pour l espace demande', [statut, e.get('serveur'), e.get('espace')], [200, 'php', 'essai-a'])
statut, l = api('espaces.php')
equipe = [x for x in l['espaces'] if not x['espace'].startswith('essai-')]
ref = etat(equipe[0]['espace'])['db'] if equipe else None
print('  (espaces de l equipe : %s)' % ', '.join(x['nom'] for x in equipe))

# -- un nouveau venu (espace vide, siVide) recoit le decoupage de l'equipe, pas le sien
r = ops('testA', 'Alice', 'essai-a', [{'op': 'remplacer', 'db': PROPRE, 'siVide': True}])
rev0 = r['rev']
a = etat('essai-a')['db']
if ref:
    essais.verifier('un nouveau venu arrive sur le decoupage de l equipe, memes identifiants', [p['id'] for p in a['plans']] == [p['id'] for p in ref['plans']], True)
    essais.verifier('et son arrivee n a rien change chez les autres', cles(etat(equipe[0]['espace'])['db']), cles(ref))
else:
    essais.verifier('premier arrive : son decoupage devient celui de l equipe', cles(a), [('01', '01'), ('01', '02')])
pA = a['plans'][0]['id']

# -- deux appareils de la meme personne
statut, d = api('depuis.php?rev=0&client=testA2&nom=Alice&espace=essai-a')
essais.verifier('un second appareil qui arrive recoit le projet entier', [len(d['db']['plans']) == len(a['plans']), d['rev']], [True, rev0])
r1 = ops('testA', 'Alice', 'essai-a', [{'op': 'add', 'kind': 'prise', 'data': {'id': 't1', 'planId': pA, 'n': 1, 'statut': 'OK'}}])
r2 = ops('testA2', 'Alice', 'essai-a', [{'op': 'add', 'kind': 'prise', 'data': {'id': 't2', 'planId': pA, 'n': 1, 'statut': 'NG'}}])
essais.verifier('deux prises au meme plan, meme numero : le serveur tranche', [r1['ops'][0]['data']['n'], r2['ops'][0]['data']['n']], [1, 2])
statut, d = api('depuis.php?rev=%d&client=testA2&espace=essai-a' % rev0)
essais.verifier('depuis : les operations des deux appareils, dans l ordre, sans le projet', ['db' in d, [x['client'] for x in d.get('ops', [])], d['rev']], [False, ['testA', 'testA2'], rev0 + 2])
r = ops('testA', 'Alice', 'essai-a', [{'op': 'patch', 'kind': 'prise', 'id': 't1', 'data': {'carte': 'A001'}}])
essais.verifier('une modification de champ', [o['op'] for o in r['ops']], ['patch'])
r = ops('testA', 'Alice', 'essai-a', [{'op': 'del', 'kind': 'prise', 'id': 't1', 'planId': pA}])
essais.verifier('une suppression renumerote l autre prise', [(o['op'], o.get('data', {}).get('n')) for o in r['ops']], [('del', None), ('patch', 1)])
statut, d = api('depuis.php?rev=999999999&client=testA2&espace=essai-a')
essais.verifier('une revision inconnue recoit le projet entier', 'db' in d, True)

# -- une autre personne, qui ne voit pas les prises de A
ops('testB', 'Bob', 'essai-b', [{'op': 'remplacer', 'db': PROPRE, 'siVide': True},
                                {'op': 'add', 'kind': 'prise', 'data': {'id': 'b1', 'planId': pA, 'n': 1, 'statut': 'OK'}}])
essais.verifier('Bob a son espace, avec sa prise, sans celle d Alice', [len(etat('essai-b')['db']['prises']), len(etat('essai-a')['db']['prises'])], [1, 1])

# -- le decoupage est commun : un plan jetable ajoute par Alice apparait chez Bob, puis disparait
ops('testA', 'Alice', 'essai-a', [{'op': 'add', 'kind': 'plan', 'data': {'id': 'jetable', 'seq': '99', 'plan': 'ESSAI', 'jour': 'J1', 'elements': {}}, 'apres': ''}])
essais.verifier('un plan ajoute par Alice arrive chez Bob', ('99', 'ESSAI') in cles(etat('essai-b')['db']), True)
if equipe:
    essais.verifier('et chez toute l equipe', ('99', 'ESSAI') in cles(etat(equipe[0]['espace'])['db']), True)
ops('testA', 'Alice', 'essai-a', [{'op': 'del', 'kind': 'plan', 'id': 'jetable'}])
essais.verifier('retire par Alice, il disparait partout', [('99', 'ESSAI') in cles(etat('essai-b')['db'])] + ([('99', 'ESSAI') in cles(etat(equipe[0]['espace'])['db'])] if equipe else []), [False] * (2 if equipe else 1))

statut, l = api('espaces.php')
essai = [(x['espace'], x['nom'], x['prises']) for x in l['espaces'] if x['espace'].startswith('essai-')]
essais.verifier('la liste des espaces, pour le DIT', essai, [('essai-a', 'Alice', 1), ('essai-b', 'Bob', 1)])
statut, m = api('mail.php')
essais.verifier('la boite d envoi de l hebergeur', [statut, m.get('possible'), '@' in m.get('expediteur', '')], [200, True, True])
statut, r = api('ops.php', {'client': '', 'ops': []})
essais.verifier('un appel sans client est refuse', statut, 400)

# -- on vide les espaces d'essai (vider un espace ne touche pas aux autres)
ops('testA', 'Alice', 'essai-a', [{'op': 'remplacer', 'db': VIDE}])
ops('testB', 'Bob', 'essai-b', [{'op': 'remplacer', 'db': VIDE}])
statut, l = api('espaces.php')
essais.verifier('les espaces d essai sont vides et hors liste', [etat('essai-a')['db'], [x['espace'] for x in l['espaces'] if x['espace'].startswith('essai-')]], [None, []])
if ref:
    essais.verifier('le decoupage de l equipe est intact', cles(etat(equipe[0]['espace'])['db']), cles(ref))
essais.bilan()
