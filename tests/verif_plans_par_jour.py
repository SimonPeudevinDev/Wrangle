# -*- coding: utf-8 -*-
"""Preparation jour par jour : une barre de jours comme en Tournage (fleches,
« Tout »), et dans l'en-tete de chaque jour son nombre de plans a regler avant
le detail, et de quoi supprimer le jour. Monter le nombre ajoute des cartes
vides a la fin du jour, le baisser ne retire que des cartes encore vides ;
« + Jour » ouvre le jour suivant et ne l'empile pas tant qu'il est vide. Et
comme le decoupage est a tous, les cartes ajoutees arrivent chez Romain, par
leur identifiant : deux cartes sans numero ne se confondent pas. La
distribution se coche dans un menu.

  py tests/verif_plans_par_jour.py
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, patienter                          # noqa: E402


def attendre(f, secondes=6.0):
    return bool(patienter(f, tours=int(secondes / 0.2), pause=0.2))


PORT = 8781


def api(chemin, corps=None):
    url = 'http://localhost:%d/api/%s' % (PORT, chemin)
    if corps is None:
        return json.loads(urllib.request.urlopen(url, timeout=10).read())
    req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def romain(jour):
    db = api('etat?espace=romain')['db'] or {'plans': []}
    return [p['id'] for p in db['plans'] if p.get('jour') == jour]


CHIPS = "[...document.querySelectorAll('#c-jourp .chip')].map(c => c.textContent + (c.classList.contains('on') ? '*' : ''))"
COMPTEUR = "(() => { const i = document.querySelector('#l-prep .jour input[data-jour]'); return i ? i.dataset.jour + ' ' + i.value : null; })()"


def fixer(banc, j, n):
    banc.js("(() => { const i = document.querySelector(`#l-prep .jour input[data-jour='%s']`); i.value = %d; i.dispatchEvent(new Event('change')); })()" % (j, n))
    time.sleep(0.6)


essais = Essais(largeur=66)
with Banc(PORT, 9371, taille=(1300, 900)) as banc:
    banc.ouvrir(vider=True)
    banc.nommer()
    # Romain a un espace, vide expres : il recoit le decoupage que Simon prepare
    api('ops', {'client': 'tel-romain', 'nom': 'Romain', 'espace': 'romain',
                'ops': [{'op': 'remplacer', 'db': {'prod': {}, 'optiques': [], 'plans': [], 'prises': []}}]})
    banc.js('document.querySelector(`nav button[data-v="prep"]`).click()'); time.sleep(0.6)
    jours = banc.js("joursConnus().filter(j => j && j !== 'CG')")
    noms = [banc.js("nomJour('%s')" % j) for j in jours]
    essais.verifier('la barre des jours : Tout, puis chaque jour de tournage', banc.js(CHIPS), ['Tout*'] + noms)
    essais.verifier('sur « Tout », chaque jour a son en-tete, avec son nombre de plans a regler',
                    banc.js("[...document.querySelectorAll('#l-prep .jour input[data-jour]')].map(i => i.dataset.jour + ' ' + i.value)"),
                    ['%s %d' % (j, banc.js("plansDuJour('%s').length" % j)) for j in jours])

    # -- la fleche passe au jour suivant, comme en Tournage
    banc.js("jourVoisin(1, 'prep')"); time.sleep(0.5)
    essais.verifier('la fleche ouvre le premier jour, seul a l ecran',
                    [banc.js(CHIPS)[1], banc.js("document.querySelectorAll('#l-prep .jour').length"), banc.js("document.querySelector('#l-prep .ptitre span').textContent.split(' · ')[0]")],
                    [noms[0] + '*', 1, noms[0]])

    # -- « + Jour » : le jour suivant, sans plan, le curseur dans son nombre
    banc.js("ajouterJourPrep()"); time.sleep(0.5)
    suivant = 'J%d' % (max(int(''.join(c for c in j if c.isdigit()) or 0) for j in jours) + 1)
    nom_suivant = banc.js("nomJour('%s')" % suivant)
    essais.verifier('+ Jour ouvre le jour suivant, a zero, le curseur dedans',
                    [banc.js(CHIPS)[-1], banc.js(COMPTEUR), banc.js("document.activeElement.dataset.jour")], [nom_suivant + '*', suivant + ' 0', suivant])
    banc.js("ajouterJourPrep()"); time.sleep(0.4)
    essais.verifier('+ Jour encore : pas de jour de plus tant que celui-la est vide', banc.js(CHIPS)[-1], nom_suivant + '*')

    # -- monter le nombre pose des cartes vides a la fin du jour
    fixer(banc, suivant, 3)
    ids = banc.js("plansDuJour('%s').map(p => p.id)" % suivant)
    essais.verifier('3 : trois cartes vides dans ce jour, a la fin du decoupage',
                    [len(ids), banc.js("plansDuJour('%s').every(p => !p.plan && !p.desc)" % suivant), banc.js("DB.plans.slice(-3).map(p => p.jour)")],
                    [3, True, [suivant] * 3])
    essais.verifier('la page le dit', banc.js("$('toast-msg').textContent"), '3 plans ajoutés au %s' % nom_suivant.lower())
    essais.verifier('les trois cartes arrivent chez Romain, memes identifiants', attendre(lambda: romain(suivant) == ids), True)

    # -- une carte remplie ne part pas quand on baisse le nombre
    banc.js("patch('plan', '%s', { desc: 'Le premier, déjà décrit' })" % ids[0]); time.sleep(0.3)
    fixer(banc, suivant, 0)
    essais.verifier('0 : les deux cartes vides partent, la carte remplie reste',
                    banc.js("plansDuJour('%s').map(p => p.desc)" % suivant), ['Le premier, déjà décrit'])
    essais.verifier('la page dit ce qui reste', banc.js("$('toast-msg').textContent"), '2 plans vides retirés · 1 plan déjà rempli gardé')
    essais.verifier('chez Romain aussi : la carte decrite reste, par son identifiant, les vides sont parties',
                    attendre(lambda: romain(suivant) == [ids[0]]), True)
    essais.verifier('et sa description y est', [p.get('desc') for p in api('etat?espace=romain')['db']['plans'] if p['id'] == ids[0]], ['Le premier, déjà décrit'])

    # -- la distribution : un menu ou l'on coche
    banc.js("document.querySelector(`#l-prep .prow[data-id='%s'] .w-dist .deroul`).click()" % ids[0]); time.sleep(0.3)
    essais.verifier('le menu de la distribution : les roles connus, la figuration, un autre nom',
                    [banc.js("!!document.querySelector('#l-prep .w-dist .menu')"), banc.js("[...document.querySelectorAll('#l-prep .w-dist .menu button')].slice(-2).map(b => b.textContent)")],
                    [True, ['Figuration', '+ Autre nom…']])
    banc.js("document.querySelector('#l-prep .w-dist .menu button').click(); document.querySelector(`#l-prep .w-dist .menu button[data-v='figu']`).click()"); time.sleep(0.3)
    premier = banc.js("acteursConnus()[0]")
    essais.verifier('cocher un role et la figuration : le plan les porte, le champ les dit, le menu reste ouvert',
                    [banc.js("plan('%s').acteurs" % ids[0]), banc.js("plan('%s').figu" % ids[0]), banc.js("document.querySelector(`#l-prep input[data-dist='%s']`).value" % ids[0]), banc.js("!!document.querySelector('#l-prep .w-dist .menu')")],
                    [[premier], True, premier + ', Figuration', True])
    banc.js("document.querySelector('#l-prep .w-dist .menu button').click()"); time.sleep(0.3)
    essais.verifier('recocher le retire', [banc.js("plan('%s').acteurs" % ids[0]), banc.js("document.querySelector(`#l-prep input[data-dist='%s']`).value" % ids[0])], [[], 'Figuration'])
    banc.js("document.body.click()"); time.sleep(0.2)
    essais.verifier('un clic ailleurs referme le menu', banc.js("!!document.querySelector('#l-prep .menu')"), False)

    # -- supprimer le jour : ses plans avec, apres confirmation
    banc.js("supprimerJourPrep('%s')" % suivant); time.sleep(0.4)
    essais.verifier('supprimer le jour demande confirmation, en comptant ses plans',
                    banc.js("$('dlg-titre').textContent"), 'Supprimer le %s et ses 1 plan ?' % nom_suivant.lower())
    banc.js("$('dlg-oui').click()"); time.sleep(0.8)
    essais.verifier('le jour et son plan sont partis, la page revient sur Tout',
                    [banc.js("plansDuJour('%s').length" % suivant), banc.js(CHIPS)[0], nom_suivant in banc.js(CHIPS), banc.js("$('toast-msg').textContent")],
                    [0, 'Tout*', False, nom_suivant + ' supprimé'])
    essais.verifier('chez Romain aussi', attendre(lambda: romain(suivant) == []), True)
essais.bilan()
