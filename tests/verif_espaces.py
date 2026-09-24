# -*- coding: utf-8 -*-
"""Chacun ses saisies, sur le serveur de plateau aussi : serveur.py tient un
espace par prenom, sur le disque (data/espaces/<prenom>/), et le flux d'un
appareil ne porte que son espace. Simon ne voit pas ce que Romain saisit ;
passer le telephone a Romain change d'espace ; le DIT ramene les saisies de
tous dans le rapprochement. La pastille en haut dit qui saisit. Et le projet
du temps ou le serveur n'avait qu'un carnet (data/projet.json) devient
l'espace « commun » au demarrage, sans rien perdre.

  py tests/verif_espaces.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, RACINE, patienter                  # noqa: E402

PORT = 8777


def api(chemin, corps=None, port=PORT):
    url = 'http://localhost:%d/api/%s' % (port, chemin)
    if corps is None:
        r = urllib.request.urlopen(url, timeout=5)
    else:
        req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req, timeout=5)
    return json.loads(r.read())


def etat(espace):
    return api('etat?espace=' + espace)


def ops(client, nom, espace, liste):
    return api('ops', {'client': client, 'nom': nom, 'espace': espace, 'ops': liste})


def attendre(f, secondes=6.0):
    fin = time.time() + secondes
    while time.time() < fin:
        try:
            if f():
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


essais = Essais(largeur=64)
with Banc(PORT, 9376, taille=(1200, 900)) as banc:
    banc.ouvrir()
    essais.verifier('sans prenom, pas de flux : l espace, c est le prenom', [banc.js('RESEAU.src'), banc.js('RESEAU.etat')], [None, 'local'])
    essais.verifier('la pastille dit Local en attendant', banc.js("$('pres').textContent"), 'Local')
    banc.nommer()                                    # Simon
    essais.verifier('nomme, l appareil se branche sur son espace', attendre(lambda: banc.js('RESEAU.etat') == 'ok'), True)
    essais.verifier('le flux porte l espace de Simon', 'espace=simon' in (banc.js('RESEAU.src && RESEAU.src.url') or ''), True)
    essais.verifier('la pastille porte son prenom', banc.js("$('pres').textContent"), 'Simon')
    essais.verifier('la copie locale est rangee sous son prenom', [banc.js("!!localStorage.getItem('fstdw.v1:simon')"), banc.js("localStorage.getItem('fstdw.v1')")], [True, None])

    banc.js("ajouterPrise(DB.plans[0].id, false, { clip:'A001C001', par:'Simon' }); flush()")
    essais.verifier('sa prise arrive dans son espace sur le serveur',
                    attendre(lambda: len((etat('simon')['db'] or {}).get('prises', [])) == 1), True)
    essais.verifier('l espace de Romain, lui, est vide', etat('romain')['db'], None)
    essais.verifier('le projet de Simon est ecrit sur le disque, dans son dossier',
                    attendre(lambda: os.path.exists(os.path.join(banc.data, 'espaces', 'simon', 'projet.json'))), True)
    essais.verifier('et son prenom tel qu il l ecrit, a cote',
                    open(os.path.join(banc.data, 'espaces', 'simon', 'nom.txt'), encoding='utf-8').read(), 'Simon')

    # -- Romain saisit de son telephone (joue par l'API) : Simon n'en voit rien
    d = etat('simon')['db']
    d['prises'] = []
    q = d['plans'][1]
    prise_romain = {'id': 'romain1', 'planId': q['id'], 'seq': q['seq'], 'plan': q['plan'], 'jour': q['jour'],
                    'n': 1, 'clip': 'B001C001', 'statut': 'OK', 'par': 'Romain'}
    ops('tel-romain', 'Romain', 'romain', [{'op': 'remplacer', 'db': d, 'siVide': True},
                                            {'op': 'add', 'kind': 'prise', 'data': prise_romain}])
    time.sleep(1.5)
    essais.verifier('Romain a sa prise dans son espace', [t['clip'] for t in etat('romain')['db']['prises']], ['B001C001'])
    essais.verifier('Simon ne la voit pas : il n a que la sienne', banc.js('DB.prises.map(t => t.clip)'), ['A001C001'])
    essais.verifier('la liste des connectes, elle, est commune',
                    sorted(x['nom'] for x in etat('simon')['presence']), ['Romain', 'Simon'])

    # -- Simon passe le telephone a Romain : l'appareil change d'espace
    banc.js('choisirNom(0)')
    essais.verifier('Romain retrouve ses saisies, venues du serveur',
                    attendre(lambda: banc.js("DB.prises.map(t => t.par + ' ' + t.clip)") == ['Romain B001C001']), True)
    essais.verifier('le flux est reparti sur son espace', 'espace=romain' in (banc.js('RESEAU.src && RESEAU.src.url') or ''), True)
    essais.verifier('la pastille dit Romain', banc.js("$('pres').textContent").startswith('Romain'), True)
    banc.js("ajouterPrise(DB.plans[1].id, false, { clip:'B001C002', par:'Romain' }); flush()")
    essais.verifier('ce qu il saisit part dans son espace a lui',
                    attendre(lambda: [t['clip'] for t in etat('romain')['db']['prises']] == ['B001C001', 'B001C002']), True)
    essais.verifier('celui de Simon n a pas bouge', [t['clip'] for t in etat('simon')['db']['prises']], ['A001C001'])

    # -- retour a Simon, depuis la fiche Journee
    banc.js('openProd()'); time.sleep(0.3)
    banc.js("[...document.querySelectorAll('#sbody .choix .btn')].find(b => b.textContent === 'Simon').click()")
    essais.verifier('Simon retrouve sa prise, et rien d autre',
                    attendre(lambda: banc.js('DB.prises.map(t => t.clip)') == ['A001C001']), True)

    # -- le decoupage est a tout le monde : un plan ajoute, modifie, deplace ou
    #    supprime par Simon vaut chez Romain ; ses prises, elles, restent a lui
    cles = lambda esp: [(p.get('seq'), p.get('plan')) for p in etat(esp)['db']['plans']]
    banc.js("""
      const n = Object.assign({ id: 'plan-simon' }, PLAN_NEUF(), { seq: '42', plan: '01', jour: 'J1', desc: 'Ajouté par Simon' });
      DB.plans.splice(0, 0, n); operer({ op: 'add', kind: 'plan', data: n, apres: '' });
    """)
    essais.verifier('un plan ajoute par Simon arrive en tete chez Romain',
                    attendre(lambda: cles('romain')[0] == ('42', '01')), True)
    banc.js("patch('plan', 'plan-simon', { desc: 'Corrigé par Simon' })")
    essais.verifier('sa fiche modifiee suit chez Romain',
                    attendre(lambda: etat('romain')['db']['plans'][0].get('desc') == 'Corrigé par Simon'), True)
    banc.js("operer({ op: 'del', kind: 'plan', id: DB.plans[3].id }); DB.plans.splice(3, 1)")
    essais.verifier('un plan sans prise supprime par Simon disparait chez Romain',
                    attendre(lambda: len(cles('romain')) == len(cles('simon'))), True)
    romain_avec_prises = cles('romain')[2]      # plans[1] d'origine : Romain y a deux prises
    banc.js("operer({ op: 'del', kind: 'plan', id: DB.plans[2].id }); DB.plans.splice(2, 1)"); time.sleep(0.8)
    essais.verifier('mais un plan ou Romain a des prises reste chez lui, avec elles',
                    [romain_avec_prises in cles('romain'), [t['clip'] for t in etat('romain')['db']['prises']]], [True, ['B001C001', 'B001C002']])
    essais.verifier('les prises de Simon n ont pas bouge non plus', [t['clip'] for t in etat('simon')['db']['prises']], ['A001C001'])
    # -- des plans encore sans numero (une journee preparee en nombre) : chacun
    #    se retrouve chez Romain par son identifiant, pas par une cle vide commune
    banc.js("""
      ['vide-a', 'vide-b'].forEach(id => {
        const n = Object.assign({ id }, PLAN_NEUF(), { seq: '', plan: '', jour: 'J9' });
        DB.plans.push(n); operer({ op: 'add', kind: 'plan', data: n, apres: DB.plans[DB.plans.length - 2].id });
      });
      patch('plan', 'vide-b', { desc: 'Le second' });
    """)
    essais.verifier('deux plans sans numero arrivent chez Romain, memes identifiants',
                    attendre(lambda: [p['id'] for p in etat('romain')['db']['plans'][-2:]] == ['vide-a', 'vide-b']), True)
    essais.verifier('et la description va au bon, pas au premier sans numero',
                    [(p.get('desc') or '') for p in etat('romain')['db']['plans'][-2:]], ['', 'Le second'])
    # -- un nouveau venu, avec son propre decoupage seme a part, recoit celui de l'equipe
    tom = banc.js("(() => { const d = normaliser(null); seed(d); d.prises = [Object.assign({}, NEUVE(), { id:'t1', planId: d.plans[5].id, seq: d.plans[5].seq, plan: d.plans[5].plan, jour: d.plans[5].jour, n: 1, clip: 'T001', par: 'Tom' })]; return d; })()")
    api('ops', {'client': 'tel-tom', 'nom': 'Tom', 'espace': 'tom', 'ops': [{'op': 'remplacer', 'db': tom, 'siVide': True}]})
    et = etat('tom')['db']
    essais.verifier('Tom arrive sur le decoupage de l equipe, memes plans, memes identifiants, avec sa prise',
                    [[p['id'] for p in et['plans']] == [p['id'] for p in etat('simon')['db']['plans']], [t['clip'] for t in et['prises']],
                     any(p['id'] == et['prises'][0]['planId'] for p in et['plans'])], [True, ['T001'], True])
    essais.verifier('et son arrivee n a rien change chez Simon', len(cles('simon')), len(cles('tom')))
    avant_vide = (len(cles('simon')), len(cles('romain')))
    api('ops', {'client': 'tel-tom', 'nom': 'Tom', 'espace': 'tom', 'ops': [{'op': 'remplacer', 'db': {'prod': {}, 'optiques': [], 'plans': [], 'prises': []}}]})
    essais.verifier('vider son espace ne touche pas aux autres, et il reste servi, vide', [etat('tom')['db']['plans'], (len(cles('simon')), len(cles('romain')))], [[], avant_vide])

    # -- le DIT reunit tout : les espaces des autres, pas le sien
    esp = api('espaces')['espaces']
    essais.verifier('le serveur liste les espaces qui ont un projet',
                    [(e['espace'], e['nom'], e['prises']) for e in esp], [('romain', 'Romain', 2), ('simon', 'Simon', 1)])
    banc.js("view = 'report'; renderAll(); recupererEspaces()")
    essais.verifier('le rapprochement ramene les saisies de Romain',
                    attendre(lambda: banc.js('RAP.sources.map(s => s.nom + \" \" + s.db.prises.length)') == ['Romain 2']), True)
    essais.verifier('le bouton est dans le rapport', banc.js("!!document.querySelector('#rapprocher button[onclick=\"reunirEquipe()\"]')"), True)

    # -- « Toute l'equipe » : le bilan et les exports du DIT portent sur tous, sans toucher a son projet
    essais.verifier('le bilan porte d abord sur mes saisies', banc.js("$('report').querySelector('.kpi .v').textContent"), '1')
    banc.js('voirEquipe(true)'); time.sleep(0.4)
    essais.verifier('« Toute l equipe » : le bilan compte les prises de tous', banc.js("$('report').querySelector('.kpi .v').textContent"), '3')
    essais.verifier('les exports lisent le projet reuni', banc.js('surLePerimetre(() => DB.prises.map(t => t.par + " " + t.clip).sort())'), ['Romain B001C001', 'Romain B001C002', 'Simon A001C001'])
    essais.verifier('le projet de cet appareil n a pas bouge', banc.js('DB.prises.map(t => t.clip)'), ['A001C001'])
    essais.verifier('les fichiers exportes le disent', banc.js("fname('journal-DIT', 'pdf')").endswith('_equipe.pdf'), True)
    essais.verifier('le bilan dit qui est reuni', 'Romain' in banc.js("$('perimetre').textContent") and 'Simon (ici)' in banc.js("$('perimetre').textContent"), True)
    banc.js('voirEquipe(false)'); time.sleep(0.3)
    essais.verifier('« Mes saisies » : retour a mon bilan', [banc.js("$('report').querySelector('.kpi .v').textContent"), banc.js("fname('x', 'csv')").endswith('_equipe.csv')], ['1', False])
    # -- le bouton du rapprochement fait la meme chose : tout le rapport passe sur l'equipe
    banc.js("document.querySelector('#rapprocher button[onclick=\"reunirEquipe()\"]').click()")
    essais.verifier('« Récupérer les saisies de l equipe » met aussi le bilan sur toute l equipe',
                    [attendre(lambda: banc.js("$('report').querySelector('.kpi .v').textContent") == '3'), banc.js('RAP.equipe && UI.equipe')], [True, True])
    banc.js('voirEquipe(false)'); time.sleep(0.3)

    # -- le PDF du DIT va rechercher les saisies de chacun avant de se fabriquer :
    #    meme si la liste reunie est vide ou perimee, rien ne manque
    banc.js('voirEquipe(true)'); time.sleep(0.4)
    api('ops', {'client': 'tel-romain', 'nom': 'Romain', 'espace': 'romain', 'ops': [
        {'op': 'add', 'kind': 'prise', 'data': {'id': 'r3', 'planId': banc.js('RAP.sources[0].db.plans[1].id'), 'n': 3, 'clip': 'B001C003', 'statut': 'OK', 'par': 'Romain'}}]})
    banc.js("RAP.sources = []; chargerLogo()"); time.sleep(0.6)     # la liste reunie est perdue (rechargement, longue attente…)
    texte = banc.cdp.appel('Runtime.evaluate', expression="avecEquipeAJour(() => { const t = surLePerimetre(() => Array.from(pdfDIT('*'), b => String.fromCharCode(b)).join('')); direPerimetre('Journal DIT exporté'); return t; })",
                           awaitPromise=True, returnByValue=True)['result']['value']
    essais.verifier('le PDF DIT porte les prises de tous, la derniere de Romain comprise',
                    [c in texte for c in ('A001C001', 'B001C001', 'B001C002', 'B001C003', 'Romain', 'Simon')], [True] * 6)
    essais.verifier('et la page dit sur quoi il porte', banc.js("$('toast-msg').textContent"), 'Journal DIT exporté : toute l’équipe · Simon, Romain')
    # -- deux personnes ont saisi la meme prise : une seule ligne, et seuls les ecarts qui comptent
    banc.js("patch('prise', DB.prises[0].id, { statut: 'OK', focale: '35 mm', heure: '10:02', duree: '0:12', carte: 'A001' }); flush()"); time.sleep(0.4)
    api('ops', {'client': 'tel-romain', 'nom': 'Romain', 'espace': 'romain', 'ops': [
        {'op': 'add', 'kind': 'prise', 'data': {'id': 'r-double', 'planId': banc.js('DB.prises[0].planId'), 'n': banc.js('DB.prises[0].n'),
                                                'clip': 'A001C001', 'statut': 'NG', 'focale': '50 mm', 'heure': '10:03', 'duree': '', 'carte': 'A001', 'par': 'Romain'}}]})
    banc.js("RAP.sources = []"); time.sleep(0.2)
    reuni = banc.cdp.appel('Runtime.evaluate', expression="avecEquipeAJour(() => surLePerimetre(() => JSON.stringify(DB.prises.filter(t => t.clip === 'A001C001'))))",
                           awaitPromise=True, returnByValue=True)['result']['value']
    reuni = json.loads(reuni)
    essais.verifier('la prise saisie par les deux ne fait qu une ligne, aux deux noms',
                    [len(reuni), reuni[0]['par']], [1, 'Simon, Romain'])
    essais.verifier('elle note les ecarts qui comptent, pas l heure ni la duree',
                    sorted((e['champ'], [v for _, v in e['valeurs']]) for e in reuni[0]['ecarts']), [('Focale', ['35 mm', '50 mm']), ('Statut', ['OK', 'NG'])])
    texte = banc.cdp.appel('Runtime.evaluate', expression="avecEquipeAJour(() => surLePerimetre(() => Array.from(pdfDIT('*'), b => String.fromCharCode(b)).join('')))",
                           awaitPromise=True, returnByValue=True)['result']['value']
    essais.verifier('le PDF DIT les signale sous le plan, et compte les ecarts en tete',
                    ['CART prise 1 \x97 Focale : Simon 35 mm \xb7 Romain 50 mm' in texte, 'Statut : Simon OK \xb7 Romain NG' in texte, '2 \xc9CARTS ENTRE LES SAISIES' in texte, '10:02' in texte or '10:03' in texte],
                    [True, True, True, True])

    # -- recharger la page garde la personne, son espace, et le choix « Toute l'equipe »
    banc.ouvrir('/?t=2')
    essais.verifier('au rechargement, toujours Simon, branche sur son espace',
                    [banc.js('UI.nom'), attendre(lambda: banc.js('RESEAU.etat') == 'ok'), banc.js('DB.prises.map(t => t.clip)')],
                    ['Simon', True, ['A001C001']])
    banc.js("view = 'report'; renderAll()")
    essais.verifier('« Toute l equipe » est retenu, et le rapport va chercher les saisies tout seul',
                    [banc.js('RAP.equipe'), attendre(lambda: banc.js('RAP.sources.map(s => s.nom + " " + s.db.prises.length)') == ['Romain 4'])], [True, True])
    essais.verifier('le bilan compte a nouveau les prises de tous', attendre(lambda: banc.js("$('report').querySelector('.kpi .v').textContent") == '4'), True)
    essais.exceptions(banc)

# -- le projet d'avant les espaces se partage entre ses auteurs : chacun recoit le
#    decoupage et ses prises ; les prises sans nom vont dans « commun »
data = tempfile.mkdtemp(prefix='wrangle-migration-')
try:
    vieux = {'version': 2, 'prod': {'titre': 'Ancien'}, 'optiques': [],
             'plans': [{'id': 'p1', 'seq': '01', 'plan': '01', 'jour': 'J1', 'elements': {}}],
             'prises': [{'id': 't1', 'planId': 'p1', 'n': 1, 'clip': 'Z001C001', 'par': 'Simon'},
                        {'id': 't2', 'planId': 'p1', 'n': 2, 'clip': 'Z001C002', 'par': 'Noémie'},
                        {'id': 't3', 'planId': 'p1', 'n': 3, 'clip': 'Z001C003', 'par': 'Simon'},
                        {'id': 't4', 'planId': 'p1', 'n': 4, 'clip': 'Z001C004'}]}
    with open(os.path.join(data, 'projet.json'), 'w', encoding='utf-8') as f:
        json.dump(vieux, f)
    os.makedirs(os.path.join(data, 'sauvegardes'))
    with open(os.path.join(data, 'sauvegardes', 'projet_2026-01-01_000000.json'), 'w', encoding='utf-8') as f:
        json.dump(vieux, f)
    port = PORT + 1
    srv = subprocess.Popen([sys.executable, os.path.join(RACINE, 'serveur.py'), str(port), '--data', data],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        patienter(lambda: api('etat', port=port) or True, tours=60, pause=0.25)
        simon, noemie, commun = (api('etat?espace=' + e, port=port)['db'] for e in ('simon', 'noemie', 'commun'))
        essais.verifier('Simon recoit le decoupage et ses deux prises',
                        [simon['prod']['titre'], len(simon['plans']), [t['clip'] for t in simon['prises']]], ['Ancien', 1, ['Z001C001', 'Z001C003']])
        essais.verifier('Noemie la sienne, dans un espace a son nom sans accent',
                        [[t['clip'] for t in noemie['prises']], [(e['espace'], e['nom']) for e in api('espaces', port=port)['espaces'] if e['espace'] == 'noemie']],
                        [['Z001C002'], [('noemie', 'Noémie')]])
        essais.verifier('la prise sans nom attend dans « commun »', [t['clip'] for t in commun['prises']], ['Z001C004'])
        essais.verifier('le fichier d avant reste a cote, avec ses sauvegardes',
                        [os.path.exists(os.path.join(data, 'projet.json')),
                         os.path.exists(os.path.join(data, 'projet.json.ancien')),
                         os.path.exists(os.path.join(data, 'sauvegardes-avant-espaces', 'projet_2026-01-01_000000.json'))],
                        [False, True, True])
        essais.verifier('le DIT voit les trois espaces',
                        [e['espace'] for e in api('espaces', port=port)['espaces']], ['commun', 'noemie', 'simon'])
        essais.verifier('un appareil sans espace tombe dans commun', api('etat', port=port)['db']['prod']['titre'], 'Ancien')
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()
finally:
    shutil.rmtree(data, ignore_errors=True)
essais.bilan()
