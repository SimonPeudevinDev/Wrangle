# -*- coding: utf-8 -*-
"""La fiche VFX : une journee par page, chaque plan tourne avec la prise qui
fait foi, ses reglages camera et optique, les releves du matchmove, les
elements captes et les autres prises. Elle se telecharge en PDF, ecrite par la
page elle-meme, dans la charte du journal DIT."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=56)
with Banc(8793, 9393, taille=(1100, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    ids = banc.js('DB.plans.slice(0, 3).map(p => p.id)')
    banc.js("""
      const a = ajouterPrise(%s, false, {}), b = ajouterPrise(%s, false, {}), c = ajouterPrise(%s, false, {});
      patch('prise', a.id, { clip:'A001C001', carte:'A001', statut:'OK', notes:'plaque (sans comédiens)' });
      patch('prise', b.id, { clip:'A001C002', carte:'A001', statut:'OK', retenue:true, camModel:'ARRI Alexa 35', codec:'ARRIRAW',
                             fps:'24', ei:'800', objectif:'Cooke S4/i', focale:'35 mm', diaph:'T2.8', focusStart:'3 m', focusStop:'2 m',
                             hauteurStart:'1,40 m', mesureDepuis:'sol', tiltStart:'-3°', mouvement:'Travelling arrière', support:'Dolly',
                             meteo:'Soleil' });
      patch('prise', c.id, { clip:'A001C003', statut:'OK' });
      patch('plan', %s, { vfxDesc:'Onde de choc', assets:'Chronoscope CG', tags:['LIVE', 'VFX'], intExt:'INT',
                          elements:{ hdri:true, chrome:true }, elementsAutre:'lidar du décor' });
      patch('plan', %s, { vfxDesc:'', assets:'', tags:['LIVE'], elements:{}, elementsAutre:'' });   // un plan sans effet
      Object.assign(DB.prod, { vfxSuper:'Camille', dit:'Alex' });
    """ % (json.dumps(ids[0]), json.dumps(ids[0]), json.dumps(ids[1]), json.dumps(ids[0]), json.dumps(ids[1])))
    j = banc.js('DB.plans[0].jour')

    # -- le modele
    m = banc.js('modeleVFX(%s)' % json.dumps(j))[0]
    essais.verifier('les plans tournes, pas les autres', [b['plan'] for b in m['plans']], banc.js('DB.plans.slice(0, 2).map(p => p.plan)'))
    b = m['plans'][0]
    essais.verifier('le plan VFX est reconnu, avec ses tags', [b['vfx'], b['tags'], m['plans'][1]['vfx']], [True, ['VFX'], False])
    essais.verifier('toutes les prises, la retenue marquee', [(t['clip'], t['retenue']) for t in b['prises']], [('A001C001', False), ('A001C002', True)])
    essais.verifier('les colonnes : camera, optique, matchmove, elements', [g[0] for g in b['groupes']], ['Caméra', 'Optique', 'Matchmove', 'Éléments captés'])
    # toutes les prises sont a l'Alexa 35 (la camera du tournage, d'office) : elle monte en tete de journee
    essais.verifier('la camera, chaque reglage nomme', dict(b['groupes'][0][1]), {'Format': 'ARRIRAW', 'Cadence': '24 i/s', 'Exposition': 'EI 800'})
    essais.verifier('le point et la hauteur, d ou elle est mesuree',
                    [dict(b['groupes'][1][1])['Point'], dict(b['groupes'][2][1])['Hauteur']], ['3 m → 2 m', '1,40 m · depuis sol'])
    essais.verifier('ni description du plan ni titre de sequence', 'desc' in b or b['meta'].startswith(banc.js('DB.plans[0].seqTitre') or '#'), False)
    essais.verifier('pas de meteo en interieur', 'Météo' in dict(b['groupes'][2][1]), False)
    essais.verifier('les elements, l autre element compris', b['elements'], ['Chrome / grey ball', 'HDRI', 'lidar du décor'])
    essais.verifier('en commun : seulement la camera du tournage', m['communs'], [['Caméra', 'ARRI Alexa 35']])
    # la derniere prise du plan 2 a les memes camera, format et objectif : ils montent en tete de journee
    banc.js("patch('prise', DB.prises.find(t => t.clip === 'A001C003').id, { camModel:'ARRI Alexa 35', codec:'ARRIRAW', fps:'24', ei:'800', objectif:'Cooke S4/i', diaph:'T4' })")
    m2 = banc.js('modeleVFX(%s)' % json.dumps(j))[0]
    essais.verifier('ce que tous les plans partagent s ecrit une fois en tete',
                    m2['communs'], [['Caméra', 'ARRI Alexa 35'], ['Format', 'ARRIRAW'], ['Cadence', '24 i/s'], ['Exposition', 'EI 800'], ['Objectif', 'Cooke S4/i']])
    essais.verifier('et chaque plan ne garde que le sien : focale, diaph qui differe, point, matchmove',
                    [g[0] for g in m2['plans'][0]['groupes']], ['Optique', 'Matchmove', 'Éléments captés'])
    essais.verifier('le diaph qui change d un plan a l autre reste sur le plan', dict(m2['plans'][0]['groupes'][0][1]).get('Diaph'), 'T2.8')
    essais.verifier('avec leur note', [t['note'] for t in b['prises']], ['plaque (sans comédiens)', ''])
    essais.verifier('pas d ecart dans la fiche VFX : ils se tranchent sur la fiche data wrangling', 'ecarts' in m, False)
    essais.verifier('sans prise retenue, les reglages de la derniere bonne', m['plans'][1]['ref'], {'n': 1, 'clip': 'A001C003'})
    essais.verifier('l en-tete nomme la fiche, le superviseur, le DIT',
                    [m['sous'].startswith('Fiche VFX · Jour 1'), 'Superviseur Camille' in m['sous'], m['sous'].endswith('DIT Alex')], [True, True, True])
    essais.verifier('et compte la journee', [c[0] for c in m['chiffres']][:4], [2, 1, 1, 1])

    # -- le PDF
    banc.js('chargerLogo()'); time.sleep(0.8)
    pdf = banc.js("Array.from(pdfVFX('*'), b => String.fromCharCode(b)).join('')")
    essais.verifier('le fichier est un PDF entier', [pdf[:8], pdf.rstrip().endswith('%%EOF')], ['%PDF-1.4', True])
    essais.verifier('le logo en tete de chaque journee', pdf.count(' h f*'), len(banc.js("modeleVFX('*')")))
    essais.verifier('le clip qui fait foi et la description VFX s y lisent', ['(A001C002)' in pdf, '(Onde de choc)' in pdf], [True, True])
    essais.verifier('la fleche, que WinAnsi n a pas, devient >', '(3 m > 2 m)' in pdf, True)
    essais.verifier('les notes a parentheses sont echappees', '\\(sans com\xe9diens\\)' in pdf, True)
    essais.verifier('les objets sont numerotes d un trait',
                    [int(x) for x in re.findall(r'(?m)^(\d+) 0 obj', pdf)] == list(range(1, pdf.count(' 0 obj') + 1)), True)

    # -- le bouton du rapport telecharge
    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.4)
    essais.verifier('le bouton VFX du rapport telecharge la fiche',
                    banc.js("""!!document.querySelector('#report button[onclick="telechargerVFX()"]')"""), True)
    banc.js('telechargerVFX()'); time.sleep(0.5)
    essais.verifier('et dit sur quoi elle porte', banc.js("$('toast-msg').textContent"), 'Fiche VFX exportée : vos saisies')
    essais.exceptions(banc)
essais.bilan()
