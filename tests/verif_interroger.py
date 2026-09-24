# -*- coding: utf-8 -*-
"""La page en mode « php », comme sur le site chez l'hebergeur : pas de flux,
elle interroge le serveur toutes les deux secondes (api/depuis.php), et chacun
a son espace, nomme d'apres son prenom. Ici c'est serveur.py qui repond aux
memes adresses, avec ?php=1 dans l'adresse de la page. Les autres appareils
sont joues a la main, par des appels directs a l'API : un second appareil de
Simon (meme espace), et Alice (le sien). Ce que Simon fait sur un appareil
lui revient sur l'autre, corrige ; ce qu'Alice saisit reste chez elle, jusqu'a
ce que le DIT le ramene dans le rapprochement."""
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


def ops(client, nom, espace, liste):
    return api('ops.php', {'client': client, 'nom': nom, 'espace': espace, 'ops': liste})


def etat(espace):
    return api('etat.php?espace=' + espace)


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


essais = Essais(largeur=62)
with Banc(PORT, 9374, taille=(1200, 900)) as banc:
    banc.ouvrir('/?php=1')
    essais.verifier('sans prenom, la page attend : rien ne part encore', [banc.js('RESEAU.php'), banc.js('RESEAU.rev'), etat('simon')['db']], [True, 0, None])
    banc.nommer()                                    # Simon
    essais.verifier('la page est en mode php : partage, sans flux, dans l espace de Simon', [banc.js('RESEAU.possible'), banc.js('RESEAU.src'), banc.js('monEspace()')], [True, None, 'simon'])
    essais.verifier('ses appels vont a api/….php', banc.js("API('ops')"), 'api/ops.php')
    # publiee ailleurs (GitHub Pages), la page porte l'adresse du serveur a appeler
    essais.verifier('avec une adresse de serveur en tete, les appels y vont',
                    banc.js("(() => { window.WRANGLE_API = 'http://exemple.test/api'; const u = API('depuis'); delete window.WRANGLE_API; return u; })()"),
                    'http://exemple.test/api/depuis.php')
    essais.verifier('l espace etait vide : la page lui envoie son projet',
                    attendre(lambda: banc.js("RESEAU.etat === 'ok' && RESEAU.rev >= 1 && !RESEAU.attente.length")), True)
    e = etat('simon')
    essais.verifier('l espace de Simon a le decoupage, une seule fois', [len(e['db']['plans']), e['rev']], [56, 1])
    essais.verifier('le projet commun du plateau n a rien recu', api('etat.php')['db'], None)
    essais.verifier('la page est a la revision du serveur', banc.js('RESEAU.rev'), 1)
    essais.verifier('la pastille porte le prenom de qui saisit', banc.js("$('pres').textContent.trim()"), 'Simon')

    # -- le second appareil de Simon ajoute une prise : elle arrive a l'interrogation suivante
    pid = e['db']['plans'][0]['id']
    r = ops('autre', 'Simon', 'simon', [{'op': 'add', 'kind': 'prise', 'data': {'id': 'x1', 'planId': pid, 'n': 1, 'statut': 'OK', 'par': 'Simon', 'plan': e['db']['plans'][0].get('plan')}}])
    essais.verifier('le serveur prend la prise de l autre appareil', [r['rev'], r['ops'][0]['data']['n']], [2, 1])
    essais.verifier('la page la recoit en quelques secondes', attendre(lambda: banc.js("!!prise('x1') && RESEAU.rev === 2")), True)
    essais.verifier('la prise est dans la liste', attendre(lambda: banc.js("document.querySelectorAll('.prise[data-id=\"x1\"]').length") == 1), True)

    # -- la page ajoute une prise au meme plan, meme numero : le serveur tranche, la page suit
    banc.js("ajouterPrise(%s, false, { n: 1 })" % json.dumps(pid))
    essais.verifier('la page envoie, le serveur renumerote, la page reprend le numero',
                    attendre(lambda: banc.js("prisesDe(%s).map(t => t.n).sort().join()" % json.dumps(pid)) == '1,2'), True)
    e = etat('simon')
    essais.verifier('le serveur a les deux prises, numerotees 1 et 2', sorted(t['n'] for t in e['db']['prises']), [1, 2])
    essais.verifier('la page a suivi la revision', attendre(lambda: banc.js('RESEAU.rev') == e['rev']), True)

    # -- une modification de champ, dans les deux sens ; une suppression renumerote
    ops('autre', 'Simon', 'simon', [{'op': 'patch', 'kind': 'prise', 'id': 'x1', 'data': {'notes': 'boum'}}])
    essais.verifier('une note venue de l autre appareil arrive', attendre(lambda: banc.js("prise('x1').notes") == 'boum'), True)
    banc.js("patch('prise', 'x1', { carte: 'A007' })")
    essais.verifier('une carte saisie ici part au serveur', attendre(lambda: [t for t in etat('simon')['db']['prises'] if t['id'] == 'x1'][0].get('carte') == 'A007'), True)
    ops('autre', 'Simon', 'simon', [{'op': 'del', 'kind': 'prise', 'id': 'x1', 'planId': pid}])
    essais.verifier('la prise supprimee disparait, l autre redevient 1', attendre(lambda: banc.js("!prise('x1') && prisesDe(%s).map(t => t.n).join() === '1'" % json.dumps(pid))), True)

    # -- Alice saisit dans son espace : Simon n'en voit rien
    da = json.loads(json.dumps(e['db']))
    da['prises'] = []
    ops('alice1', 'Alice', 'alice', [{'op': 'remplacer', 'db': da},
                                     {'op': 'add', 'kind': 'prise', 'data': {'id': 'a1', 'planId': pid, 'n': 1, 'statut': 'NG', 'par': 'Alice'}}])
    time.sleep(3)
    essais.verifier('la prise d Alice reste chez Alice', [banc.js("!!prise('a1')"), len(etat('alice')['db']['prises']), len(etat('simon')['db']['prises'])], [False, 1, 1])
    essais.verifier('les espaces : Alice et Simon', [(x['espace'], x['nom'], x['prises']) for x in api('espaces.php')['espaces']], [('alice', 'Alice', 1), ('simon', 'Simon', 1)])
    essais.verifier('la liste des connectes : Alice, et les deux appareils de Simon',
                    sorted(banc.js('RESEAU.presence.map(x => x.nom + " " + x.espace)')), ['Alice alice', 'Simon simon', 'Simon simon'])

    # -- le DIT ramene les saisies de l'equipe dans le rapprochement
    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.4)
    essais.verifier('le bloc propose de recuperer les saisies de l equipe', banc.js("document.querySelector('#rapprocher .rsources .btn.p').textContent"), 'Récupérer les saisies de l’équipe')
    banc.js("recupererEspaces()")
    essais.verifier('Alice arrive dans les sources, pas Simon lui-meme', attendre(lambda: banc.js('RAP.sources.map(s => s.nom)') == ['Alice']), True)
    essais.verifier('et le dit', banc.js("$('toast-msg').textContent"), '1 saisie récupérée')
    r = banc.js('rapprocher(sourcesRap())')
    essais.verifier('le rapprochement compare Simon et Alice', [r['noms'], r['total']['ecarts'] + r['total']['complements'] + r['total']['seuls'] > 0], [['Simon', 'Alice'], True])

    # -- Romain prend l'appareil : son espace a lui, vide ; Simon retrouve le sien
    banc.js("choisirNom(0)")
    essais.verifier('Romain arrive dans son espace, avec le decoupage seul', attendre(lambda: banc.js("monEspace() === 'romain' && RESEAU.rev >= 1 && DB.prises.length === 0")), True)
    essais.verifier('le serveur a maintenant trois espaces', [x['espace'] for x in api('espaces.php')['espaces']], ['alice', 'romain', 'simon'])
    banc.js("choisirNom(1)")
    essais.verifier('Simon retrouve sa prise et sa revision', attendre(lambda: banc.js("monEspace() === 'simon' && DB.prises.length === 1 && RESEAU.rev === %d" % etat('simon')['rev'])), True)

    # -- une reponse partie sous l'ancien prenom, qui revient apres le changement :
    #    elle ne doit ni s'appliquer, ni pousser le carnet de Simon dans l'espace de Romain
    banc.js("""
      const vrai = window.fetch;
      window.fetch = (url, o) => {
        const p = vrai(url, o);
        return /depuis\\.php/.test(String(url)) ? p.then(r => new Promise(res => setTimeout(() => res(r), 2000))) : p;
      };
      RESEAU.rev = 0; interrogerBientot();   // la reponse portera le projet entier de Simon
    """)
    time.sleep(0.4)
    banc.js("choisirNom(3)")                 # Victoire, pendant que la reponse de Simon est en route
    time.sleep(4.0)
    essais.verifier('la reponse de Simon n atterrit pas chez Victoire', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['Victoire', 0])
    essais.verifier('et son espace ne recoit que son decoupage', [x for x in api('espaces.php')['espaces'] if x['espace'] == 'victoire'][0]['prises'], 0)
    essais.verifier('l espace de Simon est intact', len(etat('simon')['db']['prises']), 1)
    banc.js("window.fetch = window.fetch")   # le retard reste, il ne gene plus
    banc.js("choisirNom(1)"); time.sleep(3.0)
    essais.verifier('Simon revient sur son carnet', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['Simon', 1])

    # -- changer de personne avec une saisie pas encore partie : elle part sous le prenom de celui qui quitte
    banc.js("RESEAU.envoi = true; ajouterPrise(DB.plans[3].id, false, { clip:'TARD1' })")   # l'envoi est bloque : l'operation reste en attente
    essais.verifier('l operation reste en attente', banc.js('RESEAU.attente.length') >= 1, True)
    banc.js("choisirNom(4)"); time.sleep(2.5)                                                # Marie prend l'appareil
    banc.js("RESEAU.envoi = false")
    essais.verifier('la derniere saisie de Simon arrive dans l espace de Simon', sorted(t.get('clip') or '' for t in etat('simon')['db']['prises']), ['', 'TARD1'])
    essais.verifier('et pas dans celui de Marie', len((etat('marie')['db'] or {'prises': []})['prises']), 0)
    essais.verifier('la file est rangee par prenom', banc.js("cleAttente().indexOf('.marie') > 0"), True)

    # -- la page sait qu'une nouvelle version est en ligne
    banc.js("""
      window.WRANGLE_VERSION = 'vieille';
      const avant = window.fetch;
      window.fetch = (url, o) => /version\\.txt/.test(String(url))
        ? Promise.resolve({ ok: true, text: () => Promise.resolve('neuve\\n') }) : avant(url, o);
      tVersion = 0; verifierVersion();
    """)
    time.sleep(0.5)
    essais.verifier('une nouvelle version en ligne propose de recharger', [banc.js("$('toast-msg').textContent"), banc.js("$('toast-btn').textContent")], ['Une nouvelle version du carnet est en ligne.', 'Recharger'])

    # -- le journal : en retard sur un remplacement, ou trop en retard, on recoit tout
    r = api('depuis.php?rev=999&client=autre&espace=simon')
    essais.verifier('une revision inconnue recoit le projet entier', 'db' in r, True)
    r = api('depuis.php?rev=%d&client=autre&espace=simon' % etat('simon')['rev'])
    essais.verifier('a jour, on ne recoit que la revision et la presence', [('db' in r) or ('ops' in r), 'presence' in r], [False, True])
    essais.exceptions(banc)
essais.bilan()
