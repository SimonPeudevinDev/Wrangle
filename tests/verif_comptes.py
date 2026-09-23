# -*- coding: utf-8 -*-
"""Les comptes : prenom et mot de passe a l'entree, crees avec la cle du
tournage. La connexion tient d'un chargement a l'autre, un mauvais mot de
passe est refuse, le DIT voit les comptes de l'equipe. Sans reseau, on
continue sans compte, avec un prenom."""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402


def api(port, quoi, corps):
    req = urllib.request.Request('http://localhost:%d/api/%s' % (port, quoi), data=json.dumps(corps).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


essais = Essais(largeur=58)
with Banc(8776, 9376, taille=(1100, 900)) as banc:
    banc.ouvrir()
    essais.verifier('au premier lancement, l entree barre la page', banc.js("!$('voile-nom').hidden"), True)
    essais.verifier('elle demande un prenom et un mot de passe', banc.js("!!$('entree-nom') && $('entree-mdp').type === 'password' && $('entree-ok').textContent"), 'Entrer')

    # -- personne n'a encore de compte : on en cree un, celui du DIT
    banc.js("basculerEntree()")
    essais.verifier('creer un compte demande la cle du tournage', banc.js("!document.querySelector('.entree-creer').hidden && $('entree-ok').textContent"), 'Créer et entrer')
    with open(os.path.join(banc.data, 'cle.txt'), 'w', encoding='utf-8') as f:   # la cle du tournage, posee sur le serveur
        f.write('foresight\n')
    banc.js("$('entree-nom').value = 'Simon'; $('entree-mdp').value = 'abc'; $('entree-cle').value = 'foresight'; validerEntree()"); time.sleep(0.5)
    essais.verifier('un mot de passe trop court est refuse', banc.js("$('entree-erreur').textContent"), 'prénom et mot de passe (quatre caractères au moins) attendus')
    banc.js("$('entree-mdp').value = 'plateau-2026'; $('entree-cle').value = 'devine'; validerEntree()"); time.sleep(0.5)
    essais.verifier('une mauvaise cle du tournage aussi', [banc.js("$('entree-erreur').textContent"), banc.js('UI.nom')], ['clé du tournage refusée', ''])
    banc.js("$('entree-cle').value = 'foresight'; validerEntree()"); time.sleep(0.6)
    essais.verifier('avec la cle, le compte est cree et on est entre, sans etre DIT', [banc.js('UI.nom'), banc.js('UI.dit'), banc.js("!!UI.jeton"), banc.js("$('voile-nom').hidden")], ['Simon', False, True, True])
    banc.js("ouvrirCreation(); $('entree-nom').value = 'Simon'; $('entree-mdp').value = 'plateau-2026'; $('entree-cle').value = 'foresight'; $('entree-dit').checked = true; validerEntree()"); time.sleep(0.6)
    essais.verifier('refaire son propre compte en DIT : le role suit', [banc.js('UI.nom'), banc.js('UI.dit'), banc.js("$('voile-nom').hidden")], ['Simon', True, True])
    essais.verifier('et salue', banc.js("$('toast-msg').textContent"), 'Bonjour Simon')

    # -- la connexion tient d'un chargement a l'autre
    banc.ouvrir(repos=1.5)
    essais.verifier('au rechargement, toujours connecte', [banc.js('UI.nom'), banc.js("$('voile-nom').hidden")], ['Simon', True])

    # -- changer de compte, se tromper, revenir
    banc.js("deconnecter()"); time.sleep(0.3)
    essais.verifier('changer de compte rouvre l entree, vide', [banc.js("!$('voile-nom').hidden"), banc.js('UI.nom'), banc.js("$('entree-titre').textContent")], [True, '', 'Qui saisit sur cet appareil ?'])
    banc.js("$('entree-nom').value = 'Simon'; $('entree-mdp').value = 'faux'; validerEntree()"); time.sleep(0.5)
    essais.verifier('un mauvais mot de passe est refuse', banc.js("$('entree-erreur').textContent"), 'prénom ou mot de passe incorrect')
    banc.js("$('entree-mdp').value = 'plateau-2026'; validerEntree()"); time.sleep(0.5)
    essais.verifier('le bon mot de passe entre, meme ecrit « simon »', [banc.js('UI.nom'), banc.js("$('voile-nom').hidden")], ['Simon', True])

    # -- le DIT ouvre un compte a Alice sans quitter le sien, et voit l'equipe
    banc.js("openProd(); voirComptes()"); time.sleep(0.6)
    essais.verifier('la fiche Journee montre le compte et son role', 'Simon · DIT' in banc.js("$('sbody').textContent"), True)
    essais.verifier('le DIT voit les comptes de l equipe', banc.js("[...document.querySelectorAll('#comptes-liste .ligne')].map(l => l.textContent.trim())"), ['SimonDIT'])
    banc.js("ouvrirCreation(); $('entree-nom').value = 'Alice'; $('entree-mdp').value = 'scripte-2026'; $('entree-cle').value = 'foresight'; $('entree-dit').checked = false; validerEntree()"); time.sleep(0.6)
    essais.verifier('le compte d Alice est cree, Simon reste connecte', [banc.js("$('toast-msg').textContent"), banc.js('UI.nom'), banc.js("$('voile-nom').hidden")], ['Compte créé pour Alice', 'Simon', True])
    statut, rep = api(8776, 'connecter', {'nom': 'alice', 'mdp': 'scripte-2026'})
    essais.verifier('Alice peut se connecter, sans etre DIT', [statut, rep.get('nom'), rep.get('dit')], [200, 'Alice', False])
    statut, rep = api(8776, 'comptes', {'jeton': rep.get('jeton')})
    essais.verifier('mais la liste des comptes lui est fermee', [statut, rep.get('erreur')], [403, 'réservé au DIT'])
    statut, rep = api(8776, 'comptes', {'jeton': 'n|1|9999999999|faux'})
    essais.verifier('un jeton falsifie est refuse', statut, 401)

    # -- sans compte : le prenom seul
    banc.js("deconnecter(); $('entree-nom').value = 'Tom'; continuerSansCompte()"); time.sleep(0.4)
    essais.verifier('continuer sans compte propose le prenom tape', banc.js("$('dlg-saisie').value"), 'Tom')
    banc.js("$('dlg-oui').click()"); time.sleep(0.3)
    essais.verifier('et pose ce prenom, sans jeton', [banc.js('UI.nom'), banc.js('UI.jeton'), banc.js("$('voile-nom').hidden")], ['Tom', '', True])
    essais.exceptions(banc)
essais.bilan()
