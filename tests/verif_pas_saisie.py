# -*- coding: utf-8 -*-
"""Deux marques sur une prise.

« Prise non saisie », a cote de Supprimer la prise : la prise reste,
marquee dans la liste ; elle sort de « A completer », et quand l'equipe est
reunie, ce sont les saisies des autres qui comptent pour elle — ce que la page
a repris de la prise d'avant ne fait pas de faux ecart.

La focale : le plan prevoit 14 mm, la prise dit 35 mm. La liste et la fiche
le signalent ; « 14 » vaut « 14 mm », et un zoom prevu (18-35) accepte tout
ce qui tombe dedans."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=62)
with Banc(8787, 9387, taille=(420, 900)) as banc:
    banc.vue(390, 844)
    banc.ouvrir()
    banc.nommer()                                    # Simon
    banc.js("""
      window.p = DB.plans[0]; patch('plan', p.id, { focale: '14 mm' });
      window.t1 = ajouterPrise(p.id, false, { clip:'A001C001', carte:'A001', focale:'14', statut:'OK', par:'Simon' });
      window.t2 = ajouterPrise(p.id, false, { par:'Simon' });
      patch('prise', t2.id, { clip:'', carte:'', focale:'35 mm', statut:'' });   // la page reprend la prise d'avant : on efface
      renderList();
    """)

    # -- la focale
    focale = lambda i: banc.js("(() => { const s = document.querySelector('.prise[data-id=\"' + %s.id + '\"] .tmeta .hors'); return s ? s.textContent.trim() + ' | ' + s.title : ''; })()" % i)
    essais.verifier('14 et 14 mm : la meme focale, rien a signaler', focale('t1'), '')
    essais.verifier('35 mm sur un plan a 14 mm : la liste le signale', focale('t2'), '⚠ 35 mm | Le plan prévoit 14 mm')
    banc.js("openPrise(t2.id)")
    essais.verifier('et la fiche le dit en tete', banc.js("document.querySelector('#alertes-prise .alert div').textContent.trim()"), 'Focale 35 mm : le plan prévoit 14 mm.')
    banc.js("patch('prise', t2.id, { focale: '14 mm' }); majBoutonsPrise()")
    essais.verifier('la focale corrigee, l alerte s en va', banc.js("document.querySelector('#alertes-prise').textContent.trim()"), '')
    banc.js("patch('prise', t2.id, { focale: '14 mm', focaleStop: '35 mm' }); majBoutonsPrise()")
    essais.verifier('un zoom pendant la prise, vers 35 : signale', 'le plan prévoit 14 mm' in banc.js("document.querySelector('#alertes-prise').textContent"), True)
    banc.js("patch('plan', p.id, { focale: '18-35 zoom' }); patch('prise', t2.id, { focale: '24 mm', focaleStop: '' }); majBoutonsPrise()")
    essais.verifier('un zoom prevu 18-35, la prise a 24 : rien', banc.js("focaleHorsPlan(t2)"), '')
    banc.js("patch('prise', t2.id, { focale: '50 mm' })")
    essais.verifier('la prise a 50 : hors du zoom', banc.js("focaleHorsPlan(t2)"), '18-35 zoom')

    # -- prise non saisie
    essais.verifier('avant : la prise 2, sans clip ni carte, est a completer', banc.js("priseIncomplete(t2)"), True)
    essais.verifier('le bouton est a cote de Supprimer la prise',
                    banc.js("[...document.querySelectorAll('#sbody .sec.btns button')].map(b => b.textContent.trim())"),
                    ['Supprimer la prise', 'Prise non saisie'])
    banc.js("basculerPasSaisie()")
    essais.verifier('un appui : la prise est marquee', [banc.js("t2.pasSaisie"), banc.js("$('btn-pas-saisie').textContent.trim()")], [True, '✓ Prise non saisie'])
    essais.verifier('la fiche le dit', 'Prise non saisie : les saisies des autres font foi' in banc.js("document.querySelector('#alertes-prise').textContent"), True)
    essais.verifier('elle n est plus a completer', banc.js("priseIncomplete(t2)"), False)
    essais.verifier('la liste la marque', banc.js("(document.querySelector('.prise[data-id=\"' + t2.id + '\"] .tstat.pas') || {}).textContent"), 'non saisie')

    # Alice a note la prise 2, elle : ses valeurs comptent, la copie de Simon ne fait pas d'ecart
    banc.js("""
      const d = structuredClone(DB); const q = d.plans.find(x => x.id === p.id);
      d.prises = [Object.assign({}, structuredClone(t1), { id:'a1', par:'Alice' }),
                  Object.assign({}, structuredClone(t2), { id:'a2', par:'Alice', pasSaisie:false, clip:'A001C002', carte:'A001', statut:'NG', focale:'35 mm' })];
      RAP.sources = [{ nom:'Alice', db: normaliser(d) }];
    """)
    r = banc.js("rapprocher(sourcesRap())")
    b = r['plans'][0] if r['plans'] else {'prises': []}
    # ni ecart, ni complement, ni « chez un seul » : la prise 2 n'a plus rien a dire
    essais.verifier('rapprochement : la prise 2 de Simon s efface devant celle d Alice',
                    [x['n'] for x in b['prises'] if x['n'] == '2'], [])
    f = banc.js("(() => { const t = fusionRap(sourcesRap()).prises.find(x => x.planId === p.id && x.n === 2); return [t.clip, t.carte, t.statut, t.par, (t.ecarts || []).length]; })()")
    essais.verifier('fusion : la prise 2 est celle d Alice, sans ecart', f, ['A001C002', 'A001', 'NG', 'Alice', 0])
    banc.js("RAP.sources = [{ nom:'Alice', db: normaliser(Object.assign(structuredClone(DB), { prises: [] })) }]")
    essais.verifier('personne d autre ne l a : elle reste',
                    banc.js("fusionRap(sourcesRap()).prises.filter(x => x.planId === p.id).map(x => x.n)"), [1, 2])

    banc.js("basculerPasSaisie()")
    essais.verifier('un second appui retire la marque', [banc.js("t2.pasSaisie"), banc.js("$('btn-pas-saisie').textContent.trim()")], [False, 'Prise non saisie'])
    import base64
    banc.js("basculerPasSaisie(); patch('plan', p.id, { focale: '14 mm' }); patch('prise', t2.id, { focale: '35 mm' }); openPrise(t2.id)"); time.sleep(0.5)
    if os.environ.get('CAPTURE'):
        open(os.environ['CAPTURE'], 'wb').write(base64.b64decode(banc.cdp.appel('Page.captureScreenshot', format='png')['data']))
    essais.exceptions(banc)
essais.bilan()
