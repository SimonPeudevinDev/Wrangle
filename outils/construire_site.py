#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRANGLE — construit le site publie a partir de la page du plateau.

  py outils/construire_site.py [dossier]          (defaut : site/)
  py outils/construire_site.py [dossier] --vide   carnet vide, sans le decoupage

Le site publie, c'est la page seule, sans serveur : dit-log.html devient
index.html a cote de public/. Par defaut la page part telle quelle, decoupage
et vignettes du tournage compris (window.DT_SEED, window.DT_THUMBS) : tout le
monde ouvre le site sur les plans de la production, comme sur le plateau.

Avec --vide, ces deux lignes sont laissees de cote et le site s'ouvre sur un
carnet vide, chacun importe son decoupage par le bouton engrenage. Un
garde-fou refuse alors d'ecrire un site ou il en resterait une trace.
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


def lignes_page(vide):
    """Les lignes de dit-log.html, moins celles du tournage si --vide."""
    with open(PAGE, 'r', encoding='utf-8', newline='') as f:
        lignes = f.readlines()
    if not vide:
        print('page : %d lignes, decoupage et vignettes compris' % len(lignes))
        return lignes
    gardees = [l for l in lignes if not l.startswith(GRAINES)]
    print('page : %d lignes, %d de donnees laissees de cote'
          % (len(lignes), len(lignes) - len(gardees)))
    return gardees


def construire(sortie, vide=False):
    gardees = lignes_page(vide)

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

    if vide:
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
    options = [a for a in sys.argv[1:] if a.startswith('--')]
    reste = [a for a in sys.argv[1:] if not a.startswith('--')]
    construire(os.path.join(ICI, reste[0] if reste else 'site'),
               vide='--vide' in options)
