# -*- coding: utf-8 -*-
"""Le banc d'essai commun aux vérifications.

Chaque script veut la même chose : un serveur Wrangle sur son propre port avec
un dossier de données temporaire, un Chrome invisible avec son propre profil, et
de quoi lui parler. Tout cela vit ici une fois, au lieu d'être recopié dans
chaque script. Bibliothèque standard uniquement, comme le reste du projet.

Le projet réel n'est jamais touché : le serveur travaille dans un dossier
temporaire, effacé à la sortie.

Un script type :

    from banc import Banc, Essais

    essais = Essais()
    with Banc(8776, 9361) as banc:
        banc.ouvrir()
        banc.nommer()
        essais.verifier('le découpage est là', banc.js('DB.plans.length') > 0, True)
        essais.exceptions(banc)
    essais.bilan()
"""
import base64
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)

NAVIGATEURS = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
]


def navigateur():
    """Le premier Chrome ou Edge installé sur cette machine."""
    exe = next((n for n in NAVIGATEURS if os.path.exists(n)), None)
    if not exe:
        raise SystemExit('Aucun navigateur Chrome/Edge trouvé.')
    return exe


def patienter(essai, tours=80, pause=0.25):
    """Rappelle `essai` jusqu'à ce qu'il rende quelque chose de vrai, ou renonce."""
    for _ in range(tours):
        try:
            v = essai()
            if v:
                return v
        except Exception:
            pass
        time.sleep(pause)
    return None


# ------------------------------------------------ WebSocket minimal (client)

def ws_connect(url):
    m = re.match(r'ws://([^:/]+):(\d+)(/.*)', url)
    host, port, path = m.group(1), int(m.group(2)), m.group(3)
    s = socket.create_connection((host, port), timeout=120)
    cle = base64.b64encode(os.urandom(16)).decode()
    requete = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n') % (path, host, port, cle)
    s.sendall(requete.encode())
    buf = b''
    while b'\r\n\r\n' not in buf:
        morceau = s.recv(4096)
        if not morceau:
            raise RuntimeError('poignée de main WebSocket interrompue')
        buf += morceau
    tete, reste = buf.split(b'\r\n\r\n', 1)
    if b' 101 ' not in tete.split(b'\r\n')[0]:
        raise RuntimeError('WebSocket refusé : ' + tete.decode('latin1'))
    return s, reste


def ws_send(s, texte, op=0x1):
    data = texte.encode() if isinstance(texte, str) else texte
    masque = os.urandom(4)
    n = len(data)
    hdr = bytes([0x80 | op])
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0x80 | 126]) + struct.pack('>H', n)
    else:
        hdr += bytes([0x80 | 127]) + struct.pack('>Q', n)
    s.sendall(hdr + masque + bytes(b ^ masque[i % 4] for i, b in enumerate(data)))


class Lecteur:
    def __init__(self, s, reste):
        self.s, self.buf = s, reste

    def _besoin(self, n):
        while len(self.buf) < n:
            morceau = self.s.recv(1 << 16)
            if not morceau:
                raise RuntimeError('WebSocket fermé')
            self.buf += morceau

    def trame(self):
        self._besoin(2)
        b0, b1 = self.buf[0], self.buf[1]
        fin, op, masque, n, i = b0 & 0x80, b0 & 0x0f, b1 & 0x80, b1 & 0x7f, 2
        if n == 126:
            self._besoin(4); n = struct.unpack('>H', self.buf[2:4])[0]; i = 4
        elif n == 127:
            self._besoin(10); n = struct.unpack('>Q', self.buf[2:10])[0]; i = 10
        cle = b''
        if masque:
            self._besoin(i + 4); cle = self.buf[i:i + 4]; i += 4
        self._besoin(i + n)
        charge, self.buf = self.buf[i:i + n], self.buf[i + n:]
        if masque:
            charge = bytes(b ^ cle[k % 4] for k, b in enumerate(charge))
        return fin, op, charge

    def message(self):
        parts = b''
        while True:
            fin, op, charge = self.trame()
            if op == 0x8:
                raise RuntimeError('WebSocket fermé par le navigateur')
            if op == 0x9:
                ws_send(self.s, charge, 0xA); continue
            if op == 0xA:
                continue
            parts += charge
            if fin:
                return parts.decode('utf-8', 'replace')


# ------------------------------------------------------------- CDP simple

class CDP:
    """Le strict nécessaire du protocole de débogage de Chrome."""

    def __init__(self, url):
        self.s, reste = ws_connect(url)
        self.lecteur = Lecteur(self.s, reste)
        self.n = 0
        self.evenements = []

    def appel(self, methode, **params):
        self.n += 1
        ws_send(self.s, json.dumps({'id': self.n, 'method': methode, 'params': params}))
        while True:
            m = json.loads(self.lecteur.message())
            if m.get('id') == self.n:
                if 'error' in m:
                    raise RuntimeError(methode + ' : ' + json.dumps(m['error']))
                return m.get('result', {})
            if 'method' in m:
                self.evenements.append(m)

    def evaluer(self, expression):
        r = self.appel('Runtime.evaluate', expression=expression, returnByValue=True)
        return r.get('result', {}).get('value')


# ------------------------------------------------------------------ Banc

class Banc:
    """Un serveur et un navigateur, montés à l'entrée, démontés à la sortie.

    `base` donné, le serveur n'est pas démarré : on se branche sur celui-là.
    `taille` est la fenêtre du navigateur, `repos` le temps laissé à la page
    après chaque chargement."""

    def __init__(self, port, cdp, base='', taille=(1300, 900), repos=1.2):
        self.port, self.port_cdp = port, cdp
        self.base = base.rstrip('/')
        self.sien = not base
        self.taille, self.repos = taille, repos
        self.serveur = self.chrome = self.cdp = None
        self.data = self.profil = None

    # -- montage et demontage -------------------------------------------

    def __enter__(self):
        exe = navigateur()
        if self.sien:
            self.data = tempfile.mkdtemp(prefix='wrangle-data-')
            self.serveur = subprocess.Popen(
                [sys.executable, os.path.join(RACINE, 'serveur.py'), str(self.port), '--data', self.data],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.base = 'http://localhost:%d' % self.port
        # serveur.py repond a /api/etat ; le site chez l'hebergeur, a api/etat.php
        def repond():
            for chemin in ('/api/etat', '/api/etat.php'):
                try:
                    return urllib.request.urlopen(self.base + chemin, timeout=4).read() or True
                except Exception:
                    pass
            raise RuntimeError('pas de serveur')
        if not patienter(repond, tours=60, pause=0.25):
            self.fermer()
            raise SystemExit('Serveur injoignable sur %s. Un serveur d une precedente '
                             'execution occupe peut-etre le port.' % self.base)

        self.profil = tempfile.mkdtemp(prefix='wrangle-profil-')
        self.chrome = subprocess.Popen(
            [exe, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
             '--no-default-browser-check', '--disable-extensions', '--disable-background-networking',
             '--disable-sync', '--remote-debugging-port=%d' % self.port_cdp,
             '--user-data-dir=' + self.profil,
             '--window-size=%d,%d' % self.taille, 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cible = patienter(lambda: next(
            (p for p in json.loads(urllib.request.urlopen(
                'http://127.0.0.1:%d/json' % self.port_cdp, timeout=2).read())
             if p.get('type') == 'page'), None), tours=100, pause=0.2)
        if not cible:
            self.fermer()
            raise SystemExit('Chrome ne repond pas sur le port de debogage.')
        self.cdp = CDP(cible['webSocketDebuggerUrl'])
        for quoi in ('Runtime', 'Page', 'Log'):
            self.cdp.appel(quoi + '.enable')
        return self

    def __exit__(self, *_):
        self.fermer()
        return False

    def fermer(self):
        for p in (self.chrome, self.serveur):
            if not p:
                continue
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        # les dossiers temporaires partent avec : une execution ne laisse rien
        for d in (self.profil, self.data):
            if d:
                shutil.rmtree(d, ignore_errors=True)
        self.chrome = self.serveur = None
        self.profil = self.data = None

    # -- la page ---------------------------------------------------------

    def js(self, expression):
        """Évalue une expression dans la page et rend sa valeur."""
        return self.cdp.evaluer(expression)

    def ouvrir(self, chemin='/', vider=False, repos=None):
        """Charge la page et attend qu'elle soit prête. `vider` oublie ce qui
        a été observé avant : on ne compte alors que ce chargement-ci.
        Rend les exceptions levées pendant."""
        if vider:
            self.cdp.evenements.clear()
        self.cdp.appel('Page.navigate', url=self.base + chemin)
        patienter(lambda: self.js("typeof DB !== 'undefined' && document.readyState === 'complete'") is True)
        time.sleep(self.repos if repos is None else repos)
        return self.exceptions()

    def nommer(self, i=1):
        """Le voile « Qui saisit sur cet appareil ? » barre la page au premier
        lancement : on choisit un prénom pour passer."""
        self.js("document.querySelectorAll('#choix-nom .btn')[%d].click()" % i)
        time.sleep(0.4)

    def vue(self, largeur, hauteur, mobile=True, echelle=3):
        """Le format de l'écran simulé : un téléphone, une tablette, un bureau."""
        self.cdp.appel('Emulation.setDeviceMetricsOverride', width=largeur, height=hauteur,
                       deviceScaleFactor=echelle, mobile=mobile)
        time.sleep(0.4)

    # -- ce que la page a dit ---------------------------------------------

    def exceptions(self):
        return [e for e in self.cdp.evenements if e.get('method') == 'Runtime.exceptionThrown']

    def erreurs_console(self):
        return [e for e in self.cdp.evenements
                if e.get('method') == 'Runtime.consoleAPICalled' and e['params'].get('type') == 'error']


# ------------------------------------------------------------- Essais

def texte_exception(e):
    d = e['params']['exceptionDetails']
    return ((d.get('exception') or {}).get('description') or d.get('text') or '')[:300].replace('\n', ' | ')


def texte_console(e):
    return ' '.join(str(a.get('value', a.get('description', '')))[:160] for a in e['params'].get('args', []))


class Essais:
    """Le compte des vérifications, et le bilan en fin de script."""

    def __init__(self, largeur=54):
        self.faits = []
        self.largeur = largeur

    def verifier(self, quoi, obtenu, attendu):
        ok = obtenu == attendu
        self.faits.append(ok)
        print('  %s  %-*s %r' % ('ok ' if ok else 'ECHEC', self.largeur, quoi, obtenu))
        if not ok:
            print('        attendu : %r' % (attendu,))
        return ok

    def detail(self, ligne):
        print('        %s' % ligne)

    def exceptions(self, banc, erreurs=None, quoi='aucune exception en console'):
        """Le dernier contrôle de tous les scripts : la page n'a rien lâché."""
        err = banc.exceptions() if erreurs is None else erreurs
        self.verifier(quoi, len(err), 0)
        for e in err[:3]:
            self.detail(texte_exception(e))

    def bilan(self):
        print('\n%d/%d verifications passees' % (sum(self.faits), len(self.faits)))
        sys.exit(0 if all(self.faits) else 1)


try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
