# -*- coding: utf-8 -*-
"""Le rapport VFX : la feuille camera du plateau (VFX camera report), une par
plan tourne. En tete le projet, le tournage et le script ; la camera ; quatorze
lignes de prises aux releves du matchmove ; la description, les elements, les
notes, le croquis du decor et les distances. Elle se telecharge en PDF, ecrite
par la page elle-meme, dans la charte de Wrangle."""
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
      patch('prise', a.id, { clip:'A001C001', carte:'A001', statut:'OK', notes:'plaque (sans comédiens)', heure:'09:05' });
      patch('prise', b.id, { clip:'A001C002', carte:'A001', statut:'Faux départ', retenue:true, camModel:'ARRI Alexa 35', codec:'ARRIRAW',
                             fps:'24', ei:'800', objectif:'Cooke S4/i', focale:'35 mm', focaleStop:'50 mm', diaph:'2.8', focusStart:'3 m', focusStop:'2 m',
                             hauteurStart:'1.40 m', mesureDepuis:'sol', tiltStart:'-3°', wb:'5600K', shutter:'1/50', mouvement:'Travelling Ar',
                             support:'Steadicam', heure:'09:40' });
      patch('prise', c.id, { clip:'A001C003', statut:'NG' });
      patch('plan', %s, { vfxDesc:'Onde de choc', assets:'Chronoscope CG', tags:['LIVE', 'VFX'], intExt:'Int', momentJour:'Nuit',
                          desc:'Edward entre', notesClient:'Reflet (vitre)', notesInternes:'refaire le HDRI',
                          elements:{ hdri:true, chrome:true, plates:true }, elementsAutre:'lidar du décor', mouv:'Fixe', support:'Trépied',
                          croquis:{ w:1600, h:1200, traits:[], objets:[{ t:'cam', x:500, y:600, a:0 }, { t:'cote', x1:500, y1:700, x2:900, y2:700, txt:'4,20 m' }] } });
      patch('plan', %s, { vfxDesc:'', assets:'', tags:['LIVE'], elements:{}, elementsAutre:'', lieu:'Décor de test' });   // un plan sans effet, dans un decor sans plan
      Object.assign(DB.prod, { titre:'Foresight', real:'Loïs', dop:'Corentin', firstAD:'Loïse', producer:'Romain', vfxSuper:'Camille', vfxStudio:'Tic & Tac' });
    """ % (json.dumps(ids[0]), json.dumps(ids[0]), json.dumps(ids[1]), json.dumps(ids[0]), json.dumps(ids[1])))
    j = banc.js('DB.plans[0].jour')

    # -- le modele : une feuille par plan tourne
    m = banc.js('modeleVFX(%s)' % json.dumps(j))
    essais.verifier('une feuille par plan tourne, pas les autres', [f['plan'] for f in m], banc.js('DB.plans.slice(0, 2).map(p => p.plan)'))
    f = m[0]
    essais.verifier('le projet, pre-rempli', dict(f['projet']),
                    {'Director': 'Loïs', 'DOP': 'Corentin', 'First AD': 'Loïse', 'Producer': 'Romain'})
    champs = lambda l: {c[i]: c[i + 1] for c in l for i in range(0, len(c), 2)}   # une ligne peut porter deux champs
    t = champs(f['tournage'])
    essais.verifier('le tournage : les heures des prises, le jour sur le nombre de jours, le superviseur',
                    [t['Time'], t['Shooting day'].startswith(banc.js("numJour(%s)" % json.dumps(j)) + ' / '), t['VFX Sup.']],
                    ['09:05 – 09:40', True, 'Camille'])
    essais.verifier('la date : celle de l export, sur la ligne du jour de tournage ; le lieu du jour',
                    [t['Date'], f['tournage'][0][2], 'Location' in t], [time.strftime('%d/%m/%Y'), 'Shooting day', True])
    essais.verifier('la sequence seule, le plan sur la meme ligne',
                    f['script'][0], ['Sequence', banc.js('DB.plans[0].seq'), 'Shot', banc.js('DB.plans[0].plan')])
    s = champs(f['script'])
    essais.verifier('le script : INT coche, NIGHT coche',
                    [[n for n, on in s['Int / Ext']['choix'] if on], [n for n, on in s['Time of day']['choix'] if on]], [['INT'], ['NIGHT']])
    essais.verifier('la camera, l objectif, le codec et la cadence', [f['camera'], f['lens'], f['codec']], ['ARRI Alexa 35', 'Sigma Classic Prime', 'ARRIRAW / 24 fps'])
    on = [n for n, on in f['mouvements'] if on]
    essais.verifier('le mouvement lu dans le plan et ses prises',
                    [all(n in on for n in ['STATIC', 'TRAVEL', 'STEADI']), 'HANDHELD' in on], [True, False])
    essais.verifier('la feuille n ecrit que le mouvement du plan', f['mouvement'], ' · '.join(on))
    b = f['prises'][1]
    essais.verifier('les releves, sans l unite que porte la colonne',
                    [b['focale'], b['focus'], b['hauteur'], b['tilt'], b['wb'], b['shutter']],
                    [['35', '50'], ['3', '2'], ['1.40', ''], ['-3', ''], '5600', '1/50'])
    essais.verifier('ni OK ni NG, le resultat et le montage vont dans la note', b['note'], 'Faux départ · Kept for edit')
    essais.verifier('les notes', [f['prises'][0]['note'], f['client'], f['interne']], ['plaque (sans comédiens)', 'Reflet (vitre)', 'refaire le HDRI'])
    essais.verifier('la description de la scene et du VFX', [f['scene'], f['vfx']], ['Edward entre', 'Onde de choc\nAssets: Chronoscope CG'])
    essais.verifier('la liste On set du breakdown, dans son ordre', [e['nom'] for e in f['elements']],
                    ['Photogrammetry', 'HDRI', 'Chrome / grey ball', 'Green / blue screen', 'Gaussian splat',
                     'Color charts', 'Extra plate', 'Clean plate', 'Wide angle camera', 'Trackers'])
    essais.verifier('les elements de la feuille coches', [e['nom'] for e in f['elements'] if e['on']], ['HDRI', 'Chrome / grey ball', 'Extra plate'])
    essais.verifier('les autres elements dans « Other »', f['autres'], 'lidar du décor')
    essais.verifier('les distances : le point, d ou l on mesure, les cotes du croquis',
                    f['distances'], [['Take 2', '3 > 2', '', '', 'sol', ''], ['Set diagram', '', '', '', '', '4,20 m']])
    essais.verifier('le croquis du plan va sur la feuille', f['croquis'], ids[0] + ':0')

    # -- un jour ou rien n'est tourne : les feuilles de ses plans, pretes pour le plateau
    j2 = banc.js("joursConnus().find(x => x && x !== %s && plansDuJour(x).every(p => !prisesDe(p.id).length && p.etat !== 'done'))" % json.dumps(j))
    if j2:
        essais.verifier('un jour a venir : une feuille par plan prevu',
                        len(banc.js('modeleVFX(%s)' % json.dumps(j2))), banc.js("plansDuJour(%s).filter(p => p.etat !== 'drop').length" % json.dumps(j2)))

    # -- le PDF, avec le croquis en image
    banc.js('chargerLogo()'); time.sleep(0.8)
    pdf = banc.cdp.appel('Runtime.evaluate', returnByValue=True, awaitPromise=True, expression="""
      imagesVFX(%s).then(ims => { const u = pdfVFX(%s, ims); let s = '';
        for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192)); return s; })""" % (json.dumps(j), json.dumps(j)))['result']['value']
    essais.verifier('le fichier est un PDF entier', [pdf[:8], pdf.rstrip().endswith('%%EOF')], ['%PDF-1.4', True])
    essais.verifier('une page par feuille', pdf.count('/Type /Page '), len(m))
    essais.verifier('le logo en tete de chaque feuille', pdf.count(' h f*'), len(m))
    essais.verifier('le titre, le clip et la description VFX s y lisent',
                    ['(VFX CAMERA REPORT)' in pdf, '(A001C002)' in pdf, '(Onde de choc)' in pdf], [True, True, True])
    essais.verifier('le croquis est une image JPEG dans la page', ['/Filter /DCTDecode' in pdf, '/Im1 Do' in pdf], [True, True])
    essais.verifier('les notes a parentheses sont echappees', '\\(sans com\xe9diens\\)' in pdf, True)
    essais.verifier('les objets sont numerotes d un trait',
                    [int(x) for x in re.findall(r'(?m)^(\d+) 0 obj', pdf)] == list(range(1, pdf.count(' 0 obj') + 1)), True)

    # -- un second croquis : sa propre page, en grand
    banc.js("patch('plan', %s, { croquisPlus: [{ w:1600, h:1200, traits:[], objets:[{ t:'soleil', x:800, y:600, a:1 }, { t:'cote', x1:100, y1:100, x2:600, y2:100, txt:'3 m' }] }] })" % json.dumps(ids[0]))
    f2 = banc.js('modeleVFX(%s)[0]' % json.dumps(j))
    essais.verifier('le second croquis a sa page, ses cotes rejoignent les distances',
                    [f2['autresCroquis'], f2['distances'][-1][5]], [[ids[0] + ':1'], '4,20 m · 3 m'])
    pdf3 = banc.cdp.appel('Runtime.evaluate', returnByValue=True, awaitPromise=True, expression="""
      imagesVFX(%s).then(ims => { const u = pdfVFX(%s, ims); let s = '';
        for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192)); return s; })""" % (json.dumps(j), json.dumps(j)))['result']['value']
    essais.verifier('une page de plus, deux images', [pdf3.count('/Type /Page '), pdf3.count('/Subtype /Image')], [len(m) + 1, 2])
    banc.js("patch('plan', %s, { croquisPlus: [] })" % json.dumps(ids[0]))

    # -- plus de quatorze prises : la feuille continue sur une page de suite
    banc.js("for (let i = 0; i < 15; i++) patch('prise', ajouterPrise(%s, false, {}).id, { clip:'B00' + i, statut:'OK' })" % json.dumps(ids[1]))
    pdf2 = banc.js("Array.from(pdfVFX(%s), b => String.fromCharCode(b)).join('')" % json.dumps(j))
    essais.verifier('seize prises : la feuille et sa suite', ['(VFX CAMERA REPORT \\267 CONTINUED)' in pdf2 or '(VFX CAMERA REPORT \xb7 CONTINUED)' in pdf2,
                    pdf2.count('/Type /Page ')], [True, len(m) + 1])

    # -- le bouton du rapport telecharge
    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.4)
    essais.verifier('le bouton Rapport VFX du rapport',
                    banc.js("""(document.querySelector('#report button[onclick="telechargerVFX()"]') || {}).textContent"""), 'Rapport VFX (PDF)')
    banc.js('telechargerVFX()'); time.sleep(1.0)
    essais.verifier('et dit sur quoi il porte', banc.js("$('toast-msg').textContent"), 'VFX camera report exporté : vos saisies')
    essais.exceptions(banc)
essais.bilan()
