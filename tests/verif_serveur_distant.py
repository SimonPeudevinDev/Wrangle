# -*- coding: utf-8 -*-
"""Le mode partage doit s'allumer meme quand le serveur n'est pas sur le Wi-Fi du plateau.

Tant que la page jugeait sur l'adresse seule, un serveur pose derriere un nom de domaine
ou sur un reseau prive (Tailscale, 100.x) etait ignore : chacun saisissait dans son coin
sans le savoir. C'est serveur.py qui annonce desormais sa presence en tete de la page.
Le site publie, lui, n'a pas de serveur derriere et doit rester en mode local.

  py tests/verif_serveur_distant.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, RACINE                             # noqa: E402

essais = Essais(largeur=56)
with Banc(8782, 9367) as banc:
    banc.ouvrir()
    essais.verifier('serveur.py a signe la page', banc.js('window.WRANGLE_SERVEUR'), 1)
    essais.verifier('le mode partage est allume', banc.js('RESEAU.possible'), True)
    essais.verifier('et la connexion est etablie', banc.js('RESEAU.etat'), 'ok')

    # l'adresse seule n'aurait pas suffi : c'est bien la signature qui decide
    essais.verifier('un nom de domaine ne passerait pas le test d adresse',
                    banc.js("serveurPossible('carnet.foresight-movie.com')"), False)
    essais.verifier('une IP de reseau prive Tailscale non plus',
                    banc.js("serveurPossible('100.101.102.103')"), False)
    essais.verifier('le Wi-Fi du plateau, si', banc.js("serveurPossible('192.168.1.20')"), True)

# le site publie n'a pas de serveur derriere : la signature ne doit pas s'y trouver
sortie = tempfile.mkdtemp(prefix='wrangle-site-')
try:
    subprocess.run([sys.executable, os.path.join(RACINE, 'outils', 'construire_site.py'), sortie],
                   stdout=subprocess.DEVNULL, check=True)
    index = open(os.path.join(sortie, 'index.html'), encoding='utf-8').read()
    # la page lit window.WRANGLE_SERVEUR, le nom s'y trouve donc forcement :
    # c'est la balise posee par le serveur qui ne doit pas y etre.
    essais.verifier('le site publie ne porte pas la signature du serveur',
                    '<script>window.WRANGLE_SERVEUR=1</script>' in index, False)
finally:
    shutil.rmtree(sortie, ignore_errors=True)

essais.bilan()
