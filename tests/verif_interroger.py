# -*- coding: utf-8 -*-
"""La page en mode « php », comme sur le site chez l'hebergeur : pas de flux,
elle interroge le serveur toutes les deux secondes (api/depuis.php). Ici c'est
serveur.py qui repond aux memes adresses, avec ?php=1 dans l'adresse de la
page. Un autre appareil est joue a la main, par des appels directs a l'API :
ce qu'il fait arrive dans la page, ce que la page fait lui revient corrige."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

PORT = 8774


def api(chemin, corps=None):
    """Un appel a l'API, en .php comme la page le ferait sur le site."""
    url = 'http://localhost:%d/api/%s' % (PORT, chemin)
    if corps is None:
        r = urllib.request.urlopen(url, timeout=5)
    else:
        req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req, timeout=5)
    return json.loads(r.read())


def ops(client, nom, liste):
    return api('ops.php', {'client': client, 'nom': nom, 'ops': liste})


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


essais = Essais(largeur=60)
with Banc(PORT, 9374, taille=(1200, 900)) as banc:
    banc.ouvrir('/?php=1')
    banc.nommer()
    essais.verifier('la page est en mode php : partage, sans flux', [banc.js('RESEAU.possible'), banc.js('RESEAU.php'), banc.js('RESEAU.src')], [True, True, None])
    essais.verifier('ses appels vont a api/….php', banc.js("API('ops')"), 'api/ops.php')
    essais.verifier('le serveur etait vide : la page lui envoie son projet',
                    attendre(lambda: banc.js("RESEAU.etat === 'ok' && RESEAU.rev >= 1 && !RESEAU.attente.length")), True)
    e = api('etat.php')
    essais.verifier('le serveur a le decoupage, une seule fois', [len(e['db']['plans']), e['rev']], [56, 1])
    essais.verifier('la page est a la revision du serveur', banc.js('RESEAU.rev'), 1)
    essais.verifier('la pastille dit en ligne', banc.js("$('pres').textContent.trim()"), 'En ligne')

    # -- un autre appareil ajoute une prise : elle arrive dans la page a l'interrogation suivante
    pid = e['db']['plans'][0]['id']
    r = ops('autre', 'Alice', [{'op': 'add', 'kind': 'prise', 'data': {'id': 'x1', 'planId': pid, 'n': 1, 'statut': 'OK', 'par': 'Alice', 'plan': e['db']['plans'][0].get('plan')}}])
    essais.verifier('le serveur prend la prise d Alice', [r['rev'], r['ops'][0]['data']['n']], [2, 1])
    essais.verifier('la page la recoit en quelques secondes', attendre(lambda: banc.js("!!prise('x1') && RESEAU.rev === 2")), True)
    essais.verifier('et le dit, avec le nom d Alice', banc.js("$('toast-msg').textContent"), 'Alice : prise 1 · plan ' + str(e['db']['plans'][0].get('plan') or 'sans n°'))
    essais.verifier('la liste des connectes a Alice et Simon', sorted(banc.js('RESEAU.presence.map(x => x.nom)')), ['Alice', 'Simon'])
    essais.verifier('la prise est dans la liste', attendre(lambda: banc.js("document.querySelectorAll('.prise[data-id=\"x1\"]').length") == 1), True)

    # -- la page ajoute une prise au meme plan, meme numero : le serveur tranche, la page suit
    banc.js("ajouterPrise(%s, false, { n: 1 })" % json.dumps(pid))
    essais.verifier('la page envoie, le serveur renumerote, la page reprend le numero',
                    attendre(lambda: banc.js("prisesDe(%s).map(t => t.n).sort().join()" % json.dumps(pid)) == '1,2'), True)
    e = api('etat.php')
    essais.verifier('le serveur a les deux prises, numerotees 1 et 2', sorted(t['n'] for t in e['db']['prises']), [1, 2])
    essais.verifier('la page a suivi la revision', attendre(lambda: banc.js('RESEAU.rev') == e['rev']), True)

    # -- une modification de champ, dans les deux sens
    ops('autre', 'Alice', [{'op': 'patch', 'kind': 'prise', 'id': 'x1', 'data': {'notes': 'boum'}}])
    essais.verifier('une note d Alice arrive', attendre(lambda: banc.js("prise('x1').notes") == 'boum'), True)
    banc.js("patch('prise', 'x1', { carte: 'A007' })")
    essais.verifier('une carte saisie ici part au serveur', attendre(lambda: [t for t in api('etat.php')['db']['prises'] if t['id'] == 'x1'][0].get('carte') == 'A007'), True)

    # -- une suppression chez Alice renumerote ; un remplacement complet fait recharger le projet entier
    ops('autre', 'Alice', [{'op': 'del', 'kind': 'prise', 'id': 'x1', 'planId': pid}])
    essais.verifier('la prise d Alice disparait, l autre redevient 1', attendre(lambda: banc.js("!prise('x1') && prisesDe(%s).map(t => t.n).join() === '1'" % json.dumps(pid))), True)
    db2 = api('etat.php')['db']
    db2['prod']['titre'] = 'Remplacé'
    ops('autre', 'Alice', [{'op': 'remplacer', 'db': db2}])
    essais.verifier('apres un remplacement, la page recoit le projet entier', attendre(lambda: banc.js('DB.prod.titre') == 'Remplacé'), True)
    essais.verifier('et se retrouve a jour', attendre(lambda: banc.js('RESEAU.rev') == api('etat.php')['rev']), True)

    # -- trop de retard : le serveur renvoie le projet entier plutot que le journal
    r = api('depuis.php?rev=1&client=autre')
    essais.verifier('un appareil en retard sur un remplacement recoit tout', ['db' in r, 'ops' in r], [True, False])
    r = api('depuis.php?rev=%d&client=autre' % api('etat.php')['rev'])
    essais.verifier('a jour, il ne recoit que la revision et la presence', [('db' in r) or ('ops' in r), sorted(x['nom'] for x in r['presence'])], [False, ['Alice', 'Simon']])
    essais.exceptions(banc)
essais.bilan()
