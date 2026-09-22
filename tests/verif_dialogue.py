# -*- coding: utf-8 -*-
"""Les boites de dialogue de la page (confirmer, demanderTexte, prevenir), a la
place des fenetres du navigateur : ce qu'elles montrent, ce qu'elles rendent,
et les gestes qui les ferment."""
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOITE = """[!$('dlg').hidden, $('dlg-titre').textContent, $('dlg-msg').hidden ? '' : $('dlg-msg').textContent,
            $('dlg-oui').textContent, $('dlg-oui').className, $('dlg-non').hidden, $('dlg-saisie').hidden,
            document.activeElement && document.activeElement.id]"""
TOUCHE = "$('dlg').dispatchEvent(new KeyboardEvent('keydown', { key: %s, bubbles: true }))"

essais = Essais(largeur=56)

# plus une seule fenetre du navigateur dans la page
src = io.open(os.path.join(RACINE, 'wrangle.html'), encoding='utf-8').read()
natives = re.findall(r'(?<![\w.])(?:confirm|prompt|alert)\(', src)
essais.verifier('plus aucun confirm / prompt / alert du navigateur', len(natives), 0)

with Banc(8795, 9395, taille=(430, 932)) as banc:
    banc.ouvrir()
    banc.nommer()

    # -- supprimer une prise : la question, Annuler, puis Supprimer
    pid = banc.js('DB.plans[0].id')
    banc.js('ajouterPrise(%s, true)' % json.dumps(pid)); time.sleep(0.4)
    tid = banc.js('openId')
    essais.verifier('une prise est ouverte', banc.js('openType'), 'prise')
    banc.js('delPrise()'); time.sleep(0.3)
    b = banc.js(BOITE)
    essais.verifier('la boite s ouvre a la place du confirm', b[0], True)
    essais.verifier('elle pose la question', b[1], 'Supprimer la prise 1 ?')
    essais.verifier('le bouton dit ce qu il fait, en rouge', [b[3], b[4]], ['Supprimer', 'btn d'])
    essais.verifier('le bouton de validation a le clavier', b[7], 'dlg-oui')
    banc.js("$('dlg-non').click()"); time.sleep(0.2)
    essais.verifier('Annuler referme la boite', banc.js("$('dlg').hidden"), True)
    essais.verifier('et la prise est toujours la', banc.js('!!prise(%s)' % json.dumps(tid)), True)
    banc.js('delPrise()'); time.sleep(0.3)
    banc.js("$('dlg-oui').click()"); time.sleep(0.4)
    essais.verifier('Supprimer supprime la prise', banc.js('!!prise(%s)' % json.dumps(tid)), False)
    essais.verifier('et referme la fiche', banc.js('openType'), None)

    # -- demander un texte : Entree valide, Echap renonce, le voile aussi
    banc.js("window.__r = 'rien'; demanderTexte('Adresse du serveur', { valeur:'http://a', ok:'Continuer' })"
            ".then(v => window.__r = v)"); time.sleep(0.3)
    b = banc.js(BOITE)
    essais.verifier('le champ est la, deja rempli, avec le clavier',
                    [b[6], b[7], banc.js("$('dlg-saisie').value")], [False, 'dlg-saisie', 'http://a'])
    banc.js("$('dlg-saisie').value = 'http://b'; " + TOUCHE % "'Enter'"); time.sleep(0.2)
    essais.verifier('Entree rend le texte tape', banc.js('window.__r'), 'http://b')
    banc.js("window.__r = 'rien'; demanderTexte('Adresse').then(v => window.__r = v)"); time.sleep(0.3)
    banc.js(TOUCHE % "'Escape'"); time.sleep(0.2)
    essais.verifier('Echap rend null', banc.js('window.__r'), None)
    banc.js("window.__r = 'rien'; confirmer('Sûr ?').then(v => window.__r = v)"); time.sleep(0.3)
    banc.js("$('dlg').click()"); time.sleep(0.2)
    essais.verifier('toucher le voile, c est renoncer', banc.js('window.__r'), False)

    # -- prevenir : un seul bouton, Entree prend acte
    banc.js("window.__r = 'rien'; prevenir('Serveur injoignable.', { detail:'Relancez.' })"
            ".then(() => window.__r = 'lu')"); time.sleep(0.3)
    b = banc.js(BOITE)
    essais.verifier('prevenir n a qu un bouton, et son detail', [b[3], b[5], b[2]], ['Compris', True, 'Relancez.'])
    banc.js(TOUCHE % "'Enter'"); time.sleep(0.2)
    essais.verifier('Entree prend acte', banc.js('window.__r'), 'lu')

    # -- les fleches ne changent pas de jour derriere une boite ouverte
    banc.js("setJour(joursConnus()[0]); confirmer('Sûr ?')"); time.sleep(0.3)
    avant = banc.js('fJour')
    banc.js("document.dispatchEvent(new KeyboardEvent('keydown', { key:'ArrowRight', bubbles:true }))"); time.sleep(0.2)
    essais.verifier('les fleches attendent derriere la boite', banc.js('fJour'), avant)
    banc.js(TOUCHE % "'Escape'"); time.sleep(0.2)

    # -- une boite chasse l'autre : la premiere rend « non »
    banc.js("window.__a = 'rien'; window.__b = 'rien'; confirmer('Un').then(v => window.__a = v);"
            " confirmer('Deux').then(v => window.__b = v)"); time.sleep(0.3)
    essais.verifier('la seconde boite prend la place', banc.js("$('dlg-titre').textContent"), 'Deux')
    essais.verifier('la premiere a rendu non', banc.js('window.__a'), False)
    banc.js("$('dlg-oui').click()"); time.sleep(0.2)
    essais.verifier('la seconde rend oui', banc.js('window.__b'), True)

    essais.exceptions(banc)
essais.bilan()
