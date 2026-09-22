# -*- coding: utf-8 -*-
"""L'enchainement des champs : une valeur posee ouvre la ligne suivante du bloc.

Dans la fiche d'un plan, le contexte compte neuf lignes. On les descend en
tapant une valeur par ligne : chaque choix referme sa ligne et ouvre la
suivante, jusqu'a la derniere qui referme tout. Retirer une valeur laisse la
ligne ouverte ; une liste a choix multiples (distribution) reste ouverte.

  py tests/verif_enchainement.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

OUVERT = "(document.querySelector('#sbody .champ.ouvert') || {dataset:{}}).dataset.champ || ''"
PREMIERE_TUILE = "(document.querySelector('#sbody .champ.ouvert .tuile[data-f]') || {dataset:{}}).dataset.f || ''"
TUILE = ("(() => { const b = [...document.querySelectorAll('#sbody .champ.ouvert .tuile')]"
         ".find(x => x.dataset.f === %r); if (!b) return 'absente'; b.click(); return 'ok'; })()")
# ouvrirChamp bascule : sur une ligne deja ouverte (la premiere vide s'ouvre seule
# a l'ouverture du plan), il la refermerait. On n'ouvre que si besoin.
OUVRIR = "(champOuvert === %r ? 'deja' : (ouvrirChamp(%r), 'ok'))"

essais = Essais(largeur=50)
with Banc(8796, 9381, taille=(430, 932)) as banc:
    banc.ouvrir()
    banc.nommer()

    def ouvrir(k):
        banc.js(OUVRIR % (k, k)); time.sleep(0.3)

    def poser(valeur):
        banc.js(TUILE % valeur); time.sleep(0.4)

    def poser_la_premiere():
        poser(banc.js(PREMIERE_TUILE))

    # un plan vierge de contexte, pour que la chaine parte du debut
    banc.js("""
      const p = DB.plans[0];
      ['lieu','intExt','momentJour','meteo','cadrage','mouv','support','focale'].forEach(k => p[k] = '');
      p.acteurs = [];
      openPlan(p.id);
    """)
    time.sleep(0.6)
    ordre = banc.js("document.querySelector('#sbody .champs[data-champs]').dataset.champs.split(',')")
    essais.verifier('le bloc contexte a ses neuf lignes', len(ordre), 9)

    # -- on descend : Int/Ext -> Moment -> Meteo, une tuile par ligne
    ouvrir('intExt')
    essais.verifier('Int/Ext est ouvert', banc.js(OUVERT), 'intExt')
    poser('Ext')
    essais.verifier('Ext pose -> Moment s ouvre', banc.js(OUVERT), 'momentJour')
    essais.verifier('la valeur est bien enregistree', banc.js('DB.plans[0].intExt'), 'Ext')
    poser('Nuit')
    essais.verifier('Nuit pose -> Meteo s ouvre', banc.js(OUVERT), 'meteo')

    # -- retirer une valeur ne fait pas avancer
    ouvrir('intExt')
    poser('Ext')
    essais.verifier('re-taper Ext le retire', banc.js('DB.plans[0].intExt'), '')
    essais.verifier('et la ligne reste ouverte', banc.js(OUVERT), 'intExt')

    # -- la distribution, a choix multiples, reste ouverte
    ouvrir('acteurs')
    premier = banc.js(PREMIERE_TUILE)
    if premier:
        poser(premier)
        essais.verifier('un acteur coche laisse la distribution ouverte', banc.js(OUVERT), 'acteurs')
    else:
        print('  (pas d acteur connu dans ce projet : distribution non testee)')

    # -- la fin du bloc referme tout
    ouvrir('support')
    poser_la_premiere()
    essais.verifier('Support pose -> Focale s ouvre', banc.js(OUVERT), 'focale')
    poser_la_premiere()
    essais.verifier('Focale, derniere ligne : tout se referme', banc.js(OUVERT), '')

    # -- le decor redessine toute la fiche, la chaine tient quand meme
    ouvrir('lieu')
    banc.js(TUILE % banc.js(PREMIERE_TUILE)); time.sleep(0.6)
    essais.verifier('Decor pose (fiche redessinee) -> Int/Ext s ouvre', banc.js(OUVERT), 'intExt')

    essais.exceptions(banc)
essais.bilan()
