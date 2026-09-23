# -*- coding: utf-8 -*-
"""Le journal DIT : une journee par page, qui s'ouvre sur les prises retenues
pour le montage, donne les plans tournes avec leurs prises et qui a saisi quoi
a quelle heure, puis ce qui reste a tourner en liste. Il se telecharge en PDF,
ecrit par la page elle-meme."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=56)
with Banc(8792, 9392, taille=(1100, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    ids = banc.js('DB.plans.slice(0, 4).map(p => p.id)')
    banc.js("""
      ajouterPrise(%s, false, { clip:'A001C001', carte:'A001', statut:'NG', notes:'faux départ', par:'Alice', heure:'09:12' });
      ajouterPrise(%s, false, { clip:'A001C002', carte:'A001', statut:'OK', retenue:true, tcIn:'10:22:31:04',
                                tcOut:'10:23:02:12', duree:'31s', par:'Bob', heure:'09:15' });
      ajouterPrise(%s, false, { clip:'A001C003', carte:'A001', statut:'OK', par:'Alice', heure:'09:40' });
      patch('plan', %s, { etat:'drop' });
    """ % (json.dumps(ids[0]), json.dumps(ids[0]), json.dumps(ids[1]), json.dumps(ids[3])))
    j = banc.js('DB.plans[0].jour')
    n_jour = banc.js('plansDuJour(%s).length' % json.dumps(j))

    # -- le modele : une journee, ce qu'elle dit
    jours = banc.js("modeleDIT('*')")
    essais.verifier('« Tout » donne un journal par journee', len(jours), banc.js('joursConnus().filter(x => plansDuJour(x).length).length'))
    m = jours[0]
    essais.verifier('la premiere journee est celle des plans', m['jour'], j)
    essais.verifier('les plans tournes sont ceux qui ont des prises', [b['plan'] for b in m['tournes']],
                    banc.js('DB.plans.slice(0, 2).map(p => p.plan)'))
    essais.verifier('la sequence est nommee', m['tournes'][0]['seq'], 'Séquence 06')
    essais.verifier('le montage ne garde que la prise retenue', [t['clip'] for t in m['montage']], ['A001C002'])
    essais.verifier('qui a saisi, et quand', [t['qui'] for t in m['tournes'][0]['prises']], ['Alice · 09:12', 'Bob · 09:15'])
    essais.verifier('la prise retenue est marquee', [t['retenue'] for t in m['tournes'][0]['prises']], [False, True])
    essais.verifier('le reste a tourner : les autres plans du jour, en liste', len(m['reste']), n_jour - 3)
    essais.verifier('une ligne du reste nomme sequence et plan', m['reste'][0]['ref'].startswith('Séquence 06 · Plan '), True)
    essais.verifier('le plan abandonne est a part', len(m['abandonnes']), 1)
    essais.verifier('l en-tete compte', [c[0] for c in m['chiffres']][:4], [2, n_jour - 3, 3, 1])
    essais.verifier('et nomme la carte', m['chiffres'][6][1], 'carte · A001')
    essais.verifier('a sauvegarder : un fichier par prise', m['sauvegarde']['total'], 3)
    essais.verifier('carte par carte, du premier au dernier clip', m['sauvegarde']['cartes'],
                    [{'carte': 'A001', 'n': 3, 'premier': 'A001C001', 'dernier': 'A001C003'}])
    essais.verifier('rien ne manque pour les retrouver', [m['sauvegarde']['sansCarte'], m['sauvegarde']['sansClip']], [0, 0])
    essais.verifier('une journee seule : un seul journal', len(banc.js('modeleDIT(%s)' % json.dumps(j))), 1)

    essais.verifier('le projet en titre, le journal en sous-titre', [m['titre'], m['sous'].startswith('Journal DIT · Jour 1')], ['Foresight', True])

    # -- le PDF : un vrai fichier, lisible sans compression, avec le logo trace
    banc.js('chargerLogo()'); time.sleep(0.8)
    essais.verifier('le logo est lu dans son SVG', banc.js('!!(LOGO_PDF && LOGO_PDF.mot && LOGO_PDF.touche)'), True)
    pdf = banc.js("Array.from(pdfDIT('*'), b => String.fromCharCode(b)).join('')")
    essais.verifier('le logo est trace en tete de chaque journee', pdf.count(' h f*'), len(jours))
    essais.verifier('le fichier est un PDF', pdf[:8], '%PDF-1.4')
    pages = len(re.findall(r'/Type /Page /', pdf))
    essais.verifier('au moins une page par journee', pages >= len(jours), True)
    essais.detail('%d pages, %d Ko' % (pages, len(pdf) // 1024))
    essais.verifier('la table des adresses se termine bien', pdf.rstrip().endswith('%%EOF'), True)
    essais.verifier('les objets sont numerotes d un trait',
                    [int(x) for x in re.findall(r'(?m)^(\d+) 0 obj', pdf)] == list(range(1, pdf.count(' 0 obj') + 1)), True)
    essais.verifier('le clip retenu s y lit', '(A001C002)' in pdf, True)
    essais.verifier('les accents passent en WinAnsi', 'S\xc9QUENCE 06' in pdf and '(Reste \xe0 tourner' not in pdf and 'RESTE \xc0 TOURNER' in pdf, True)
    essais.verifier('le montage vient avant le reste a tourner', 0 < pdf.find('(A001C002)') < pdf.find('RESTE \xc0 TOURNER'), True)
    essais.verifier('la sauvegarde ouvre le journal', 0 < pdf.find('SAUVEGARDER : 3 FICHIERS SUR 1 CARTE') < pdf.find('(A001C002)'), True)
    essais.verifier('la prise retenue est en gras sur fond gris', '/CB 7.5 Tf' in pdf and ' re f' in pdf, True)
    essais.verifier('qui a saisi, et quand, dans le PDF', '(Bob \xb7 09:15)' in pdf, True)
    essais.verifier('les notes a parentheses sont echappees', banc.js(
        "Array.from(pdfDIT('*'), b => String.fromCharCode(b)).join('').indexOf('(faux d\\xe9part)') > 0"), True)

    # -- le bouton du rapport telecharge
    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.4)
    essais.verifier('le bouton Journal DIT est dans le rapport',
                    banc.js("""!!document.querySelector('#report button[onclick="telechargerDIT()"]')"""), True)
    banc.js('telechargerDIT()'); time.sleep(0.5)
    essais.verifier('cliquer telecharge le fichier', banc.js("$('toast-msg').textContent"), 'Fichier exporté')

    # -- les listes du rapport : cinq lignes, puis elles defilent
    banc.js("""for (let k = 0; k < 7; k++){ const t = ajouterPrise(%s, false, { clip:'B00' + k }); patch('prise', t.id, { carte:'' }); }
               renderReport()""" % json.dumps(ids[2])); time.sleep(0.4)
    mesure = banc.js("""(() => { const c = document.querySelector('#report .cinq'); const l = c.querySelectorAll('.alert');
      return [l.length, c.scrollHeight > c.clientHeight, c.clientHeight <= 5 * l[0].getBoundingClientRect().height + 2]; })()""")
    essais.verifier('sept alertes : la liste defile au-dela de cinq', mesure, [mesure[0], True, True])
    essais.verifier('et il y en a bien plus de cinq', mesure[0] > 5, True)
    essais.exceptions(banc)
essais.bilan()
