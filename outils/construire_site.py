#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRANGLE — construit le site publie a partir de la page du plateau.

  py outils/construire_site.py [dossier]      (defaut : site/)

Le site publie, c'est la page seule : pas de serveur, et surtout pas les
donnees du tournage en cours. dit-log.html porte, sur deux lignes, le
decoupage (window.DT_SEED) et les vignettes du storyboard (window.DT_THUMBS)
de la production ouverte : ce script les laisse de cote. La page en ligne
s'ouvre sur un carnet vide, chacun charge son propre decoupage par l'import
JSON du bouton engrenage. Le fichier du plateau n'est pas touche.

Le garde-fou en fin de construction refuse d'ecrire un site ou il resterait
une trace de ces donnees : mieux vaut un site casse qu'un decoupage en ligne.
"""

import os
import shutil
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ICI, 'dit-log.html')
PUBLIC = os.path.join(ICI, 'public')
CNAME = os.path.join(ICI, 'CNAME')

# les donnees de production integrees a la page : une ligne chacune
GRAINES = ('window.DT_SEED=', 'window.DT_THUMBS=')


def page_sans_donnees():
    """Les lignes de dit-log.html, moins celles qui portent le tournage."""
    with open(PAGE, 'r', encoding='utf-8', newline='') as f:
        lignes = f.readlines()
    gardees = [l for l in lignes if not l.startswith(GRAINES)]
    print('page : %d lignes, %d de donnees laissees de cote'
          % (len(lignes), len(lignes) - len(gardees)))
    return gardees


def construire(sortie):
    gardees = page_sans_donnees()

    if os.path.isdir(sortie):
        shutil.rmtree(sortie)
    os.makedirs(sortie)

    # un serveur web sert index.html a la racine du domaine
    index = os.path.join(sortie, 'index.html')
    with open(index, 'w', encoding='utf-8', newline='') as f:
        f.writelines(gardees)
    shutil.copytree(PUBLIC, os.path.join(sortie, 'public'))

    # sans ce fichier, GitHub Pages fait passer le site par Jekyll
    open(os.path.join(sortie, '.nojekyll'), 'w').close()
    if os.path.exists(CNAME):
        shutil.copy(CNAME, os.path.join(sortie, 'CNAME'))

    verifier(index)
    print('site construit dans %s' % sortie)
    print('  index.html : %d Ko  (page du plateau : %d Ko)'
          % (os.path.getsize(index) // 1024, os.path.getsize(PAGE) // 1024))


def verifier(index):
    """Refuse de laisser passer une page qui porterait encore le tournage."""
    with open(index, 'r', encoding='utf-8', newline='') as f:
        texte = f.read()
    restes = [g for g in GRAINES if g in texte]
    if restes:
        raise SystemExit('ARRET : %s est encore dans la page construite. '
                         'Le format de dit-log.html a change : corriger '
                         'construire_site.py avant de publier.'
                         % ', '.join(restes))


if __name__ == '__main__':
    construire(os.path.join(ICI, sys.argv[1] if len(sys.argv) > 1 else 'site'))
