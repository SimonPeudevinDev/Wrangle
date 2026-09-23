# -*- coding: utf-8 -*-
"""Rapprocher les saisies : chacun saisit de son cote, le DIT depose les
sauvegardes des autres. Le rapport met les prises cote a cote (ecarts,
complements, prises chez un seul), la fusion garde tout, le PDF le relit."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=58)
with Banc(8778, 9378, taille=(1200, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    # -- les saisies de ce navigateur (Simon) et celles d'Alice, faites a part
    banc.js("""
      const p = DB.plans[0];
      ajouterPrise(p.id, false, { clip:'A001C001', carte:'A001', statut:'OK', par:'Simon', heure:'09:10' });
      ajouterPrise(p.id, false, { clip:'A001C002', statut:'NG', par:'Simon', heure:'09:14' });
      const d2 = structuredClone(DB); d2.prises = [];
      const q = d2.plans[0]; q.etat = 'drop';
      // Alice a les memes reglages de plan (focale, mouvement) que Simon : on ne compare que ce qui compte
      const com = { focale: p.focale, mouvement: p.mouv };
      d2.prises.push(Object.assign({ id:'a1', planId:q.id, seq:q.seq, plan:q.plan, jour:q.jour }, NEUVE(), com, { n:1, statut:'NG', par:'Alice', heure:'09:10' }));
      d2.prises.push(Object.assign({ id:'a2', planId:q.id, seq:q.seq, plan:q.plan, jour:q.jour }, NEUVE(), com, { n:2, statut:'NG', carte:'A001', notes:'boom', par:'Alice', heure:'09:14' }));
      d2.prises.push(Object.assign({ id:'a3', planId:q.id, seq:q.seq, plan:q.plan, jour:q.jour }, NEUVE(), com, { n:3, statut:'OK', clip:'A001C003', par:'Alice', heure:'09:20' }));
      window.__d2 = d2;
      RAP.sources.push({ nom: nomDeSource(normaliser(structuredClone(d2)), 'alice.json'), db: normaliser(structuredClone(d2)), fichier:'alice.json' });
    """)
    essais.verifier('un fichier est nomme d apres qui a saisi', banc.js('RAP.sources[0].nom'), 'Alice')
    r = banc.js('rapprocher(sourcesRap())')
    essais.verifier('les sources : ce navigateur d abord', r['noms'], ['Simon', 'Alice'])
    essais.verifier('le bilan : ecarts, complements, prises chez un seul', [r['total']['ecarts'], r['total']['complements'], r['total']['seuls']], [2, 4, 1])
    b = r['plans'][0]
    essais.verifier('un seul plan en cause', len(r['plans']), 1)
    essais.verifier('l etat du plan ne concorde pas', [[e['champ'], [v[1] for v in e['valeurs']]] for e in b['plan_']['ecarts']], [['État', ['Tourné', 'Abandonné']]])
    p1 = [t for t in b['prises'] if t['n'] == '1'][0]
    essais.verifier('prise 1 : le statut est un ecart', [[e['champ'], [v[0] + ' ' + v[1] for v in e['valeurs']]] for e in p1['ecarts']], [['Statut', ['Simon OK', 'Alice NG']]])
    essais.verifier('prise 1 : le clip et la carte, seulement chez Simon', sorted(c['champ'] for c in p1['complements']), ['Carte', 'Clip'])
    p2 = [t for t in b['prises'] if t['n'] == '2'][0]
    essais.verifier('prise 2 : le clip vient de Simon, la note d Alice', sorted((c['champ'], c['par'][0]) for c in p2['complements']), [('Clip', 'Simon'), ('Note', 'Alice')])
    essais.verifier('prise 2 : le clip de Simon est un complement, pas un ecart', [e['champ'] for e in p2['ecarts']], [])
    p3 = [t for t in b['prises'] if t['n'] == '3'][0]
    essais.verifier('prise 3 : seulement chez Alice', p3['seuls'], ['Alice'])

    # -- le rapport dans l onglet Rapport
    banc.js("""document.querySelector('nav button[data-v="report"]').click()"""); time.sleep(0.5)
    essais.verifier('le bloc montre les deux sources', banc.js("[...document.querySelectorAll('#rapprocher .rsource')].map(s => s.firstChild.textContent.trim())"), ['Simon', 'Alice'])
    essais.verifier('et le bilan', banc.js("document.querySelector('#rapprocher .rresume').textContent"), '2 écarts · 4 compléments · 1 prise chez un seul')
    essais.verifier('les ecarts en avertissement, le reste en gris',
                    [banc.js("document.querySelectorAll('#rapprocher .alert.o').length"), banc.js("document.querySelectorAll('#rapprocher .alert:not(.o)').length")], [2, 5])

    # -- le PDF des ecarts
    banc.js('chargerLogo()'); time.sleep(0.6)
    pdf = banc.js("Array.from(pdfRapprochement(), b => String.fromCharCode(b)).join('')")
    essais.verifier('le PDF des ecarts est un PDF', pdf[:8], '%PDF-1.4')
    essais.verifier('il nomme les sources et l ecart', '(Rapprochement des saisies \xb7 Simon, Alice)' in pdf and 'Simon OK \xb7 Alice NG' in pdf, True)

    # -- la fusion : Simon fait foi, Alice comble et apporte sa prise 3
    f = banc.js('(() => { const f = fusionRap(sourcesRap()); const p = f.plans[0]; return { etat: p.etat, prises: f.prises.filter(t => t.planId === p.id).map(t => [t.n, t.statut, t.clip, t.carte, t.notes]) }; })()')
    essais.verifier('l etat du plan reste celui de Simon', f['etat'], 'done')
    essais.verifier('les prises : Simon fait foi, Alice comble, sa prise 3 arrive', f['prises'],
                    [[1, 'OK', 'A001C001', 'A001', ''], [2, 'NG', 'A001C002', 'A001', 'boom'], [3, 'OK', 'A001C003', '', '']])
    banc.js('garderFusion()'); time.sleep(0.3)
    essais.verifier('garder la fusion demande confirmation', banc.js("$('dlg-oui').textContent"), 'Fusionner')
    banc.js("$('dlg-oui').click()"); time.sleep(0.5)
    essais.verifier('le projet est fusionne', [banc.js('DB.prises.length'), banc.js("$('toast-msg').textContent"), banc.js('RAP.sources.length')], [3, 'Projet fusionné', 0])
    banc.js("retirerSource(0); $('rap-in')")
    essais.verifier('sans fichier, le bloc n a que ce navigateur', banc.js("document.querySelectorAll('#rapprocher .rsource').length"), 1)
    essais.exceptions(banc)
essais.bilan()
