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
from datetime import datetime

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


def version():
    """Le numero de la version publiee : la revision Git, a defaut la date de
    la page. La page le porte en tete et le compare a version.txt, a cote
    d'elle : un telephone qui garde le site ouvert apprend ainsi qu'il tourne
    sur une version d'avant."""
    try:
        import subprocess
        v = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ICI,
                           capture_output=True, text=True, timeout=10)
        if v.returncode == 0 and v.stdout.strip():
            return v.stdout.strip()
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(PAGE)).strftime('%Y%m%d-%H%M%S')


def construire(sortie, vide=False, php=False):
    gardees = lignes_page(vide)
    v = version()
    # en tete de la page : son numero de version, et pour OVH le fait que les
    # scripts d'api/ repondent a cote d'elle (la meme ligne que serveur.py ajoute)
    marque = "<head><script>window.WRANGLE_VERSION='%s'%s</script>" % (v, ";window.WRANGLE_SERVEUR='php'" if php else '')
    i = next(i for i, l in enumerate(gardees) if '<head>' in l)
    gardees[i] = gardees[i].replace('<head>', marque, 1)

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

    # le serveur en PHP (api/) : utile chez un hebergeur qui l'execute (OVH) ;
    # ailleurs, fichiers inertes
    shutil.copytree(os.path.join(ICI, 'api'), os.path.join(sortie, 'api'),
                    ignore=shutil.ignore_patterns('donnees'))
    os.makedirs(os.path.join(sortie, 'api', 'donnees'), exist_ok=True)
    with open(os.path.join(sortie, 'api', 'donnees', '.htaccess'), 'w') as f:
        f.write('Require all denied\n')

    # chez un hebergeur Apache : la page doit etre reverifiee a chaque ouverture,
    # sinon un telephone garde celle d'hier (GitHub Pages ignore ce fichier)
    shutil.copy(os.path.join(PUBLIC, 'htaccess-site.txt'), os.path.join(sortie, '.htaccess'))
    os.remove(os.path.join(sortie, 'public', 'htaccess-site.txt'))

    # le numero de la version publiee, que la page relit de loin en loin
    with open(os.path.join(sortie, 'version.txt'), 'w', encoding='utf-8') as f:
        f.write(v + '\n')

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
