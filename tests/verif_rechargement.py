# -*- coding: utf-8 -*-
"""Le second chargement : la page demarre-t-elle encore quand le navigateur a deja une
copie locale du projet ? C'est le cas de tous les appareils du plateau apres la premiere
visite. Une constante lue avant sa declaration dans normaliser() ne casse que dans ce cas :
un navigateur vierge n'a aucun plan a normaliser et ne voit rien.

  py tests/verif_rechargement.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, texte_console, texte_exception     # noqa: E402

essais = Essais()
with Banc(8776, 9361, taille=(1300, 800)) as banc:
    erreurs = banc.ouvrir(vider=True)
    n = banc.js('DB.plans.length')
    essais.verifier('premier chargement : le decoupage est la, sans erreur', [n > 0, len(erreurs)], [True, 0])

    # on touche au projet, pour que la copie locale contienne une prise et un plan modifies
    banc.nommer()
    banc.js("ajouterPrise(DB.plans[0].id, false); patch('plan', DB.plans[1].id, {mouv:'Handheld'}); flush()")
    time.sleep(0.5)
    essais.verifier('copie locale ecrite, sous le prenom', banc.js("!!localStorage.getItem('fstdw.v1:simon')"), True)

    erreurs = banc.ouvrir(vider=True)
    essais.verifier('second chargement, copie locale en place : la page demarre',
                    [banc.js('DB.plans.length'),
                     banc.js("document.querySelectorAll('#l-shoot .plan').length > 0"),
                     len(erreurs)],
                    [n, True, 0])
    for e in erreurs[:3]:
        essais.detail(texte_exception(e))

    essais.verifier('le reseau se connecte apres le second chargement', banc.js('RESEAU.etat'), 'ok')
    # une erreur rattrapee au chargement jette la copie locale et passe par console.error : on la voit ici
    essais.verifier('la copie locale est toujours la (rien n a ete rattrape en silence)',
                    banc.js("!!localStorage.getItem('fstdw.v1:simon')"), True)
    consoles = banc.erreurs_console()
    essais.verifier('aucun message d erreur en console', len(consoles), 0)
    for e in consoles[:2]:
        essais.detail(texte_console(e))

    essais.verifier('l ancien Handheld est range en support',
                    banc.js('[DB.plans[1].mouv, DB.plans[1].support]'), ['', 'Épaule'])

    # -- « Recharger le decoupage » : le meme ordre pour tout le monde, sans doublon.
    #    Un carnet melange (plans dans le desordre, un plan en double avec une prise
    #    dessus, un plan ajoute sur le plateau) revient dans l'ordre du DT, les
    #    doubles se replient sur le premier, le plan du plateau suit a la fin.
    banc.js("""
      const seedOrdre = SEED.plans.map(s => clePlan(s));
      DB.plans.reverse();
      const double = Object.assign({}, DB.plans[3], { id: 'double', etat: 'todo' });
      DB.plans.splice(10, 0, double);
      ajouterPrise('double', false, { clip: 'DBL_001' });
      DB.plans[5].etat = 'done'; DB.plans[5].notesInternes = 'gardee';
      DB.plans.push(Object.assign({ id: 'plateau' }, PLAN_NEUF(), { seq: '99', plan: '77', jour: 'J1' }));
      window.__attendu = { seedOrdre, garde: clePlan(DB.plans[5]), origine: DB.plans[3].id };
      resync();
    """)
    time.sleep(0.4)
    banc.js("$('dlg-oui').click()"); time.sleep(0.8)
    essais.verifier('les plans reprennent l ordre du decoupage, le plan du plateau a la fin',
                    banc.js("[DB.plans.slice(0, SEED.plans.length).map(p => clePlan(p)).join() === window.__attendu.seedOrdre.join(), DB.plans[DB.plans.length - 1].id, DB.plans.length]"),
                    [True, 'plateau', n + 1])
    essais.verifier('le doublon est replie et sa prise rendue au plan d origine',
                    banc.js("[DB.plans.some(p => p.id === 'double'), prise(DB.prises.find(t => t.clip === 'DBL_001').id).planId === window.__attendu.origine]"), [False, True])
    essais.verifier('ce qui a ete saisi sur le plateau est garde',
                    banc.js("(() => { const p = DB.plans.find(x => clePlan(x) === window.__attendu.garde); return [p.etat, p.notesInternes]; })()"), ['done', 'gardee'])
    essais.verifier('la page le dit', banc.js("$('toast-msg').textContent"), '%d plans mis à jour, 0 ajouté, 1 doublon replié' % n)
essais.bilan()
