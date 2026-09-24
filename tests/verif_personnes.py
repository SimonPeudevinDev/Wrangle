# -*- coding: utf-8 -*-
"""Chacun ses saisies sur le site : la copie locale est rangee sous le prenom
choisi a l'entree. Passer de Simon a Romain change de saisies, revenir les
retrouve, recharger la page aussi.

Et le carnet d'avant les prenoms, celui que le site rangeait tout seul : il
revient a qui l'a saisi — les prises portent son nom — jamais au premier venu.
S'il n'a pas d'auteur clair, la page demande. Et un carnet deja herite par
erreur se rend a son proprietaire.

Une ouverture par adresse : naviguer deux fois vers la meme ne recharge pas la
page. On pose DB en meme temps que la copie locale, sinon le flush de sortie
de page la reecrit."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

# le carnet d'avant : le decoupage, deux prises saisies par %s (vide : sans nom de saisisseur)
POSE = """(() => {
    const d = normaliser(null); seed(d);
    d.prises = [1, 2].map(n => Object.assign({}, NEUVE(), { id:'vieux' + n, planId:d.plans[0].id, seq:d.plans[0].seq,
        plan:d.plans[0].plan, jour:d.plans[0].jour, n, clip:'A001_001' + n, statut:'OK', par:%s }));
    localStorage.setItem(%s, JSON.stringify(d));
    localStorage.setItem('fstdw.ui', JSON.stringify(%s));
    DB = d;   // sans cela, le flush de sortie de page reecrit la cle avec le carnet vide
  })()"""


def pose(banc, par='Simon', cle='fstdw.v1', ui=None):
    banc.js(POSE % (json.dumps(par), json.dumps(cle), json.dumps(ui or {})))


essais = Essais(largeur=62)
with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- comme sur le site : pas de serveur (?seul=1)
    banc.ouvrir('/?seul=1&t=1')
    essais.verifier('sans serveur, la page travaille seule', banc.js('RESEAU.possible'), False)
    essais.verifier('et demande quand meme le prenom a l entree', banc.js("!$('voile-nom').hidden"), True)
    banc.nommer()                                    # Simon
    essais.verifier('Simon est entre', [banc.js('UI.nom'), banc.js("$('voile-nom').hidden")], ['Simon', True])
    banc.js("ajouterPrise(DB.plans[0].id, false, { clip:'A001C001', par:'Simon' }); flush()")
    essais.verifier('sa copie locale est rangee sous son prenom', [banc.js("!!localStorage.getItem('fstdw.v1:simon')"), banc.js("localStorage.getItem('fstdw.v1')")], [True, None])

    # -- Romain prend l'appareil : ses saisies a lui, vides
    banc.js("choisirNom(0)"); time.sleep(0.4)
    essais.verifier('Romain arrive sur le decoupage seul, sans les prises de Simon', [banc.js('UI.nom'), banc.js('DB.prises.length'), banc.js('DB.plans.length')], ['Romain', 0, 56])
    essais.verifier('rien ne lui est demande : ce carnet est le sien', banc.js("$('dlg').hidden"), True)
    essais.verifier('la liste des prises est rendue a vide', banc.js("document.querySelectorAll('.prise').length"), 0)
    banc.js("ajouterPrise(DB.plans[1].id, false, { clip:'B001C001', par:'Romain' }); ajouterPrise(DB.plans[1].id, false, { clip:'B001C002', par:'Romain' }); flush()")
    essais.verifier('Romain saisit deux prises, rangees sous son prenom', [banc.js('DB.prises.length'), banc.js("!!localStorage.getItem('fstdw.v1:romain')")], [2, True])

    # -- retour a Simon, depuis la fiche Journee cette fois
    banc.js("openProd()"); time.sleep(0.3)
    banc.js("[...document.querySelectorAll('#sbody .choix .btn')].find(b => b.textContent === 'Simon').click()"); time.sleep(0.4)
    essais.verifier('Simon retrouve sa prise', [banc.js('UI.nom'), banc.js('DB.prises.map(t => t.clip)')], ['Simon', ['A001C001']])
    essais.verifier('la fiche Journee s est refermee', banc.js('openType'), None)

    # -- recharger garde la personne et ses saisies
    banc.ouvrir('/?seul=1&t=2')
    essais.verifier('au rechargement, toujours Simon et sa prise', [banc.js('UI.nom'), banc.js('DB.prises.map(t => t.clip)'), banc.js("$('voile-nom').hidden")], ['Simon', ['A001C001'], True])
    banc.js("choisirNom(0)"); time.sleep(0.4)
    essais.verifier('et Romain a toujours ses deux', banc.js('DB.prises.map(t => t.clip)'), ['B001C001', 'B001C002'])
    essais.exceptions(banc)

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- un telephone qui avait deja travaille avant les prenoms : le carnet est a Simon
    banc.ouvrir('/?seul=1&t=3')
    pose(banc, par='Simon')
    banc.ouvrir('/?seul=1&t=4', repos=1.5)
    essais.verifier('a l ouverture, le carnet d avant est la, sans prenom', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['', 2])
    banc.js("choisirNom(0)"); time.sleep(0.6)     # Romain se nomme le premier
    essais.verifier('Romain ne recupere pas les prises de Simon', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['Romain', 0])
    essais.verifier('et on ne lui demande rien', banc.js("$('dlg').hidden"), True)
    essais.verifier('le carnet d avant reste en place, pour son proprietaire', banc.js("!!localStorage.getItem('fstdw.v1')"), True)
    banc.js("choisirNom(1)"); time.sleep(0.6)     # Simon arrive
    essais.verifier('Simon, lui, le reprend : ce sont ses prises', [banc.js('UI.nom'), banc.js("DB.prises.map(t => t.par + ' ' + t.clip)")], ['Simon', ['Simon A001_0011', 'Simon A001_0012']])
    essais.verifier('et il passe sous son prenom', [banc.js("localStorage.getItem('fstdw.v1')"), banc.js("!!localStorage.getItem('fstdw.v1:simon')")], [None, True])
    essais.exceptions(banc, quoi='aucune exception en console (carnet d avant)')

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- un carnet d'avant sans nom de saisisseur : la page demande
    banc.ouvrir('/?seul=1&t=5')
    pose(banc, par='')
    banc.ouvrir('/?seul=1&t=6', repos=1.5)
    banc.js("choisirNom(0)"); time.sleep(0.6)
    essais.verifier('sans auteur, la page demande a qui est le carnet', [banc.js("!$('dlg').hidden"), banc.js("$('dlg-titre').textContent")], [True, 'Reprendre le carnet déjà commencé sur cet appareil ?'])
    essais.verifier('elle dit combien de prises et qu on peut le laisser', ['2 prise' in banc.js("$('dlg-msg').textContent"), banc.js("$('dlg-non').textContent")], [True, 'Pas à moi'])
    banc.js("$('dlg-non').click()"); time.sleep(0.4)
    essais.verifier('« pas a moi » laisse le carnet ou il est', [banc.js('DB.prises.length'), banc.js("!!localStorage.getItem('fstdw.v1')")], [0, True])
    banc.js("choisirNom(1)"); time.sleep(0.6)
    essais.verifier('la question est reposee au suivant', banc.js("!$('dlg').hidden"), True)
    banc.js("$('dlg-oui').click()"); time.sleep(0.5)
    essais.verifier('« reprendre » le met sous son prenom', [banc.js('UI.nom'), banc.js('DB.prises.length'), banc.js("localStorage.getItem('fstdw.v1')")], ['Simon', 2, None])
    banc.ouvrir('/?seul=1&t=7')
    essais.verifier('et il y reste au rechargement', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['Simon', 2])
    essais.exceptions(banc, quoi='aucune exception en console (carnet sans auteur)')

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- un carnet herite par erreur, deja range sous le mauvais prenom : on le rend
    banc.ouvrir('/?seul=1&t=8')
    pose(banc, par='Simon', cle='fstdw.v1:romain', ui={'nom': 'Romain'})
    banc.ouvrir('/?seul=1&t=9', repos=1.5)
    essais.verifier('la page voit que ce carnet n est pas celui de Romain', [banc.js("!$('dlg').hidden"), banc.js("$('dlg-titre').textContent")], [True, 'Ce carnet a été saisi par Simon, pas par vous.'])
    essais.verifier('elle propose de le rendre', [banc.js("$('dlg-oui').textContent"), banc.js("$('dlg-non').textContent")], ['Les rendre à Simon', 'C’est le mien'])
    banc.js("$('dlg-oui').click()"); time.sleep(0.6)
    essais.verifier('Romain repart du decoupage', [banc.js('UI.nom'), banc.js('DB.prises.length'), banc.js('DB.plans.length')], ['Romain', 0, 56])
    essais.verifier('et le carnet est passe chez Simon', banc.js("(() => { const d = JSON.parse(localStorage.getItem('fstdw.v1:simon')); return [d.prises.length, d.prises[0].par]; })()"), [2, 'Simon'])
    essais.verifier('la page le dit', banc.js("$('toast-msg').textContent"), '2 prises rendues à Simon')
    banc.js("choisirNom(1)"); time.sleep(0.6)
    essais.verifier('Simon ouvre son carnet, rendu', [banc.js('UI.nom'), banc.js('DB.prises.length')], ['Simon', 2])
    essais.verifier('et on ne lui demande rien : ce sont ses prises', banc.js("$('dlg').hidden"), True)
    banc.ouvrir('/?seul=1&t=10')
    essais.verifier('rien n est redemande au rechargement', [banc.js("$('dlg').hidden"), banc.js('DB.prises.length')], [True, 2])
    essais.exceptions(banc, quoi='aucune exception en console (carnet rendu)')

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- « c'est le mien » : la question ne revient plus
    banc.ouvrir('/?seul=1&t=11')
    pose(banc, par='Simon', cle='fstdw.v1:romain', ui={'nom': 'Romain'})
    banc.ouvrir('/?seul=1&t=12', repos=1.5)
    banc.js("$('dlg-non').click()"); time.sleep(0.4)
    essais.verifier('« c est le mien » garde le carnet ou il est', [banc.js('DB.prises.length'), banc.js("$('dlg').hidden")], [2, True])
    banc.ouvrir('/?seul=1&t=13')
    essais.verifier('et la question ne revient pas', [banc.js("$('dlg').hidden"), banc.js('DB.prises.length')], [True, 2])
    essais.exceptions(banc, quoi='aucune exception en console (c est le mien)')

# le carnet d'avant, quand tout le monde y saisissait : douze prises de Simon, une de Romain
POSE_MIXTE = """(() => {
    const d = normaliser(null); seed(d);
    const p = d.plans[0], q = d.plans[1];
    const prise = (n, plan, par, clip) => Object.assign({}, NEUVE(), { id:'melange' + n, planId:plan.id, seq:plan.seq,
        plan:plan.plan, jour:plan.jour, n, clip, statut:'OK', par });
    d.prises = [prise(1, p, 'Simon', 'A001_0012'), prise(2, p, 'Simon', 'A001_0013'), prise(3, p, 'Romain', 'A001_0023'),
                prise(1, q, 'Simon', 'A001_0016')];
    localStorage.setItem(%s, JSON.stringify(d));
    localStorage.setItem('fstdw.ui', JSON.stringify(%s));
    DB = d;
  })()"""

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- un carnet d'avant a plusieurs auteurs se partage : chacun y prend ses prises
    banc.ouvrir('/?seul=1&t=14')
    banc.js(POSE_MIXTE % (json.dumps('fstdw.v1'), '{}'))
    banc.ouvrir('/?seul=1&t=15', repos=1.5)
    banc.js("choisirNom(0)"); time.sleep(0.6)     # Romain, le premier
    essais.verifier('Romain prend le decoupage et sa prise, pas celles de Simon',
                    [banc.js('UI.nom'), banc.js("DB.prises.map(t => t.clip)"), banc.js("$('dlg').hidden")], ['Romain', ['A001_0023'], True])
    essais.verifier('les prises de Simon restent dans le carnet d avant',
                    banc.js("JSON.parse(localStorage.getItem('fstdw.v1')).prises.map(t => t.par)"), ['Simon', 'Simon', 'Simon'])
    banc.js("choisirNom(1)"); time.sleep(0.6)     # puis Simon
    essais.verifier('Simon prend les siennes, sur les memes plans',
                    [banc.js("DB.prises.map(t => t.clip)"), banc.js("DB.plans[0].id === JSON.parse(localStorage.getItem('fstdw.v1:romain')).plans[0].id")],
                    [['A001_0012', 'A001_0013', 'A001_0016'], True])
    essais.verifier('plus rien a prendre : le carnet d avant s efface', banc.js("localStorage.getItem('fstdw.v1')"), None)
    banc.js("choisirNom(0)"); time.sleep(0.5)
    essais.verifier('Romain retrouve la sienne, et rien d autre', banc.js("DB.prises.map(t => t.par + ' ' + t.clip)"), ['Romain A001_0023'])
    essais.exceptions(banc, quoi='aucune exception en console (carnet partage)')

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- un carnet deja repris en bloc sous un prenom : on rend aux autres leurs prises, on garde les siennes
    banc.ouvrir('/?seul=1&t=16')
    banc.js(POSE_MIXTE % (json.dumps('fstdw.v1:romain'), json.dumps({'nom': 'Romain'})))
    banc.ouvrir('/?seul=1&t=17', repos=1.5)
    essais.verifier('la page voit les prises des autres dans le carnet de Romain',
                    [banc.js("!$('dlg').hidden"), banc.js("$('dlg-titre').textContent"), banc.js("$('dlg-oui').textContent"), banc.js("$('dlg-non').textContent")],
                    [True, 'Ce carnet porte 3 prises saisies par Simon.', 'Les rendre à Simon', 'Elles sont à moi'])
    banc.js("$('dlg-oui').click()"); time.sleep(0.8)
    essais.verifier('Romain garde la sienne', [banc.js('UI.nom'), banc.js("DB.prises.map(t => t.clip)")], ['Romain', ['A001_0023']])
    essais.verifier('Simon recoit les siennes, sur le meme decoupage',
                    banc.js("(() => { const d = JSON.parse(localStorage.getItem('fstdw.v1:simon')); return [d.prises.map(t => t.clip), d.plans.length, d.plans[0].id === DB.plans[0].id]; })()"),
                    [['A001_0012', 'A001_0013', 'A001_0016'], 56, True])
    essais.verifier('la page le dit', banc.js("$('toast-msg').textContent"), '3 prises rendues à Simon')
    banc.js("choisirNom(1)"); time.sleep(0.6)
    essais.verifier('Simon ouvre son carnet, sans question', [banc.js("DB.prises.map(t => t.clip)"), banc.js("$('dlg').hidden")], [['A001_0012', 'A001_0013', 'A001_0016'], True])
    essais.exceptions(banc, quoi='aucune exception en console (prises rendues)')

with Banc(8775, 9375, taille=(1200, 900)) as banc:
    # -- avec le serveur du plateau aussi, chacun ses saisies : changer de prenom change d'espace
    banc.ouvrir('/')
    banc.nommer()
    banc.js("ajouterPrise(DB.plans[2].id, false, { clip:'C001C001' }); flush()"); time.sleep(0.8)
    banc.js("choisirNom(2)"); time.sleep(1.0)
    essais.verifier('sur le plateau, Tom arrive sur le decoupage seul, sans la prise de Simon', [banc.js('UI.nom'), banc.js('DB.prises.length'), banc.js("$('dlg').hidden")], ['Tom', 0, True])
    essais.verifier('et son appareil est branche sur son espace a lui', banc.js("RESEAU.src && RESEAU.src.url.indexOf('espace=tom') > 0"), True)
    banc.js("choisirNom(1)"); time.sleep(1.0)
    essais.verifier('Simon retrouve sa prise, venue de son espace', [banc.js('UI.nom'), banc.js('DB.prises.map(t => t.clip)')], ['Simon', ['C001C001']])
    essais.exceptions(banc, quoi='aucune exception en console (plateau)')
essais.bilan()
