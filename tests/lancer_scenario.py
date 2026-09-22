#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deux appareils qui saisissent en meme temps : le scenario complet, joue dans
un Chrome invisible. La page tests/scenario.html tient les deux appareils et
ecrit ses resultats ; ce pilote la charge et les lit.

  py tests\\lancer_scenario.py                 (serveur temporaire, projet reel intact)
  py tests\\lancer_scenario.py http://localhost:9000   (un serveur deja en place, qui sera ecrit)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, texte_exception                            # noqa: E402

PORT_TEST = 8799
PORT_CDP = 9333
ATTENTE = 120          # secondes laissees au scenario pour aller jusqu'au bout


def main():
    # une adresse en argument : on se branche sur ce serveur-la plutot que d'en monter un
    base = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith('http') else ''
    with Banc(PORT_TEST, PORT_CDP, base=base, taille=(1200, 900)) as banc:
        print('Serveur :', banc.base, '' if base else '(dossier temporaire)')
        banc.cdp.appel('Page.navigate', url=banc.base + '/tests/scenario.html')

        debut, texte = time.time(), ''
        while time.time() - debut < ATTENTE:
            time.sleep(0.5)
            texte = banc.js("(document.getElementById('out')||{}).innerText||''") or ''
            if 'FIN' in texte:
                break
        print(texte)

        exceptions = banc.exceptions()
        for e in exceptions:
            print('EXCEPTION :', texte_exception(e))
        if 'FIN' not in texte:
            print('\nLe scenario ne s est pas termine en %d s.' % ATTENTE)
        code = 0 if ('FIN' in texte and 'FAIL' not in texte and not exceptions) else 1

    print('\nRÉSULTAT :', 'tout passe' if code == 0 else 'des échecs')
    return code


if __name__ == '__main__':
    sys.exit(main())
