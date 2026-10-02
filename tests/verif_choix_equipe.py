# -*- coding: utf-8 -*-
"""Le DIT choisit qui reunir : une personne, plusieurs, ou « Tous ». Sur le
serveur, Alice et Bob ont saisi ; Zoe a choisi son prenom un jour, sans rien
saisir. « Tous », ce sont Alice et Bob ; Zoe est proposee, grisee, et se coche
comme les autres. Le choix vaut pour tout le rapport et survit a un
rechargement. Le bouton Data wrangling du rapprochement n'est plus la : il
reste le seul, avec le DIT et le VFX. La page est en mode « php »."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, patienter                         # noqa: E402

PORT = 8799


def api(chemin, corps=None):
    url = 'http://localhost:%d/api/%s' % (PORT, chemin)
    if corps is None:
        return json.loads(urllib.request.urlopen(url, timeout=5).read())
    req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


def ops(nom, liste):
    return api('ops.php', {'client': nom.lower() + '1', 'nom': nom, 'espace': nom.lower(), 'ops': liste})


def sources(banc):
    return banc.js("RAP.sources.map(s => s.nom)")


def pastilles(banc):
    return banc.js("[...document.querySelectorAll('#rapprocher .rsource.coche')].map(b => "
                   "b.firstChild.textContent.trim() + (b.classList.contains('on') ? ' +' : '') + (b.classList.contains('vide') ? ' vide' : ''))")


essais = Essais(largeur=62)
with Banc(PORT, 9399, taille=(1200, 900)) as banc:
    banc.ouvrir('/?php=1')
    banc.nommer()                                    # Simon
    patienter(lambda: banc.js("RESEAU.etat === 'ok' && RESEAU.rev >= 1 && !RESEAU.attente.length"), tours=60)
    db = api('etat.php?espace=simon')['db']
    pid = db['plans'][0]['id']
    vide = dict(db, prises=[])
    ops('Alice', [{'op': 'remplacer', 'db': vide}, {'op': 'add', 'kind': 'prise', 'data': {'id': 'a1', 'planId': pid, 'n': 1, 'statut': 'NG', 'par': 'Alice'}}])
    ops('Bob', [{'op': 'remplacer', 'db': vide}, {'op': 'add', 'kind': 'prise', 'data': {'id': 'b1', 'planId': pid, 'n': 1, 'statut': 'OK', 'par': 'Bob'}},
                {'op': 'add', 'kind': 'prise', 'data': {'id': 'b2', 'planId': pid, 'n': 2, 'statut': 'OK', 'par': 'Bob'}}])
    ops('Zoe', [{'op': 'remplacer', 'db': vide}])

    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.4)
    essais.verifier('un seul bouton Data wrangling, avec le DIT et le VFX',
                    banc.js("[...document.querySelectorAll('#report button')].filter(b => /Data wrangling/.test(b.textContent)).length"), 1)
    essais.verifier('plus de bouton Data wrangling dans le rapprochement',
                    banc.js("[...document.querySelectorAll('#rapprocher button')].some(b => /Data wrangling/.test(b.textContent))"), False)

    banc.js("reunirEquipe()")
    essais.verifier('Tous : ceux qui ont saisi, Alice et Bob', patienter(lambda: sources(banc) == ['Alice', 'Bob'], tours=40), True)
    essais.verifier('et le dit', banc.js("$('toast-msg').textContent"), '2 personnes réunies')
    essais.verifier('une pastille par personne ; Zoe, hors equipe et sans saisie, n en a pas', pastilles(banc), ['Tous +', 'Alice +', 'Bob +'])
    essais.verifier('le bilan reunit Alice et Bob : la prise 1 des deux ne fait qu une ligne',
                    banc.js("projetEquipe().prises.map(t => t.n + ' ' + t.par).sort()"), ['1 Alice, Bob', '2 Bob'])
    essais.verifier('le bouton de recuperation devient Actualiser', banc.js("document.querySelector('#rapprocher .rsources .btn.p').textContent"), 'Actualiser')

    # -- une seule personne
    banc.js("basculerChoix('alice')")
    essais.verifier('Alice decochee : Bob seul', [sources(banc), pastilles(banc)], [['Bob'], ['Tous', 'Alice', 'Bob +']])
    essais.verifier('le rapprochement ne compare que Simon et Bob', banc.js("rapprocher(sourcesRap()).noms"), ['Simon', 'Bob'])
    essais.verifier('les prises d Alice ne sont plus dans le projet reuni', banc.js("projetEquipe().prises.some(t => t.id === 'a1')"), False)

    # -- plusieurs, dont quelqu'un qui n'a rien saisi
    banc.js("basculerChoix('zoe')")
    essais.verifier('Zoe se coche aussi', sources(banc), ['Bob', 'Zoe'])

    # -- le choix survit a un rechargement, et aux PDF qui vont rechercher les saisies
    banc.ouvrir('/?php=1')
    banc.js("""document.querySelector('nav button[data-v="report"]').click()""")
    essais.verifier('apres rechargement, le meme choix', patienter(lambda: sources(banc) == ['Bob', 'Zoe'], tours=40), True)
    banc.js("RAP.sources = []; avecEquipeAJour(() => 0)")
    essais.verifier('un PDF recharge les saisies de ceux-la seulement', patienter(lambda: sources(banc) == ['Bob', 'Zoe'], tours=40), True)

    # -- personne, puis Tous
    banc.js("basculerChoix('bob'); basculerChoix('zoe')")
    essais.verifier('personne de coche : vos saisies seulement', [sources(banc), banc.js("equipeReunie()")], [[], False])
    essais.verifier('la note le dit', 'Personne n’est coché' in banc.js("$('perimetre').textContent"), True)
    banc.js("choisirTous()")
    essais.verifier('Tous : de nouveau Alice et Bob', [sources(banc), banc.js("UI.choixEquipe")], [['Alice', 'Bob'], None])
    essais.exceptions(banc)
essais.bilan()
