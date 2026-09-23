#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRANGLE — construit le site publie a partir de la page du plateau.

  py outils/construire_site.py [dossier]          (defaut : site/)
  py outils/construire_site.py [dossier] --vide   carnet vide, sans le decoupage
  py outils/construire_site.py [dossier] --php    pour un hebergeur qui execute PHP :
                                                  le site fait serveur, la page le sait

Le site publie, c'est la page : wrangle.html devient index.html a cote de
public/. Par defaut la page part telle quelle, decoupage et vignettes du
tournage compris (window.DT_SEED, window.DT_THUMBS) : tout le monde ouvre le
site sur les plans de la production, comme sur le plateau.

Avec --php, une ligne en tete de la page (window.WRANGLE_SERVEUR='php') lui
dit que les scripts d'api/ repondent a cote d'elle : elle partage alors le
projet entre tous, comme avec serveur.py. Sans, elle travaille seule, et les
scripts PHP restent des fichiers inertes (GitHub Pages).

Avec --vide, ces deux lignes et public/vignettes/ sont laisses de cote et le site s'ouvre sur un
carnet vide, chacun importe son decoupage par le bouton engrenage. Un
garde-fou refuse alors d'ecrire un site ou il en resterait une trace.
"""

import os
import shutil
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ICI, 'wrangle.html')
PUBLIC = os.path.join(ICI, 'public')
CNAME = os.path.join(ICI, 'CNAME')

# les donnees de production integrees a la page : une ligne chacune
GRAINES = ('window.DT_SEED=', 'window.DT_THUMBS=')


def lignes_page(vide):
    """Les lignes de wrangle.html, moins celles du tournage si --vide."""
    with open(PAGE, 'r', encoding='utf-8', newline='') as f:
        lignes = f.readlines()
    if not vide:
        print('page : %d lignes, decoupage et vignettes compris' % len(lignes))
        return lignes
    gardees = [l for l in lignes if not l.startswith(GRAINES)]
    print('page : %d lignes, %d de donnees laissees de cote'
          % (len(lignes), len(lignes) - len(gardees)))
    return gardees


MARQUE_PHP = "<head><script>window.WRANGLE_SERVEUR='php'</script>"


def construire(sortie, vide=False, php=False):
    gardees = lignes_page(vide)
    if php:
        # la meme ligne que serveur.py ajoute en tete de la page qu'il sert
        i = next(i for i, l in enumerate(gardees) if '<head>' in l)
        gardees[i] = gardees[i].replace('<head>', MARQUE_PHP, 1)

    if os.path.isdir(sortie):
        shutil.rmtree(sortie)
    os.makedirs(sortie)

    # un serveur web sert index.html a la racine du domaine
    index = os.path.join(sortie, 'index.html')
    with open(index, 'w', encoding='utf-8', newline='') as f:
        f.writelines(gardees)
    # les vignettes vont avec le decoupage : un carnet vide s'en passe
    shutil.copytree(PUBLIC, os.path.join(sortie, 'public'),
                    ignore=shutil.ignore_patterns('vignettes') if vide else None)

    # le serveur de plateau en PHP (api/) et le depot des saisies (depot/) :
    # utiles chez un hebergeur qui les execute (OVH) ; ailleurs, fichiers inertes
    for dossier in ('api', 'depot'):
        shutil.copytree(os.path.join(ICI, dossier), os.path.join(sortie, dossier),
                        ignore=shutil.ignore_patterns('donnees', 'saisies', 'comptes'))
    for dossier in ('api/donnees', 'depot/saisies'):
        os.makedirs(os.path.join(sortie, dossier), exist_ok=True)
        with open(os.path.join(sortie, dossier, '.htaccess'), 'w') as f:
            f.write('Require all denied\n')

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
                         'Le format de wrangle.html a change : corriger '
                         'construire_site.py avant de publier.'
                         % ', '.join(restes))


if __name__ == '__main__':
    options = [a for a in sys.argv[1:] if a.startswith('--')]
    reste = [a for a in sys.argv[1:] if not a.startswith('--')]
    construire(os.path.join(ICI, reste[0] if reste else 'site'),
               vide='--vide' in options, php='--php' in options)
