#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lance Chrome (ou Edge) en mode invisible, ouvre tests/scenario.html sur le
serveur local et affiche les résultats. Bibliothèque standard uniquement.

  py tests\\lancer_scenario.py                 (serveur sur http://localhost:8765)
  py tests\\lancer_scenario.py http://localhost:9000
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

# Par defaut, le pilote demarre son propre serveur sur un port et un dossier
# temporaires : le projet reel n'est jamais touche. Avec une adresse en
# argument, il utilise le serveur indique (attention : le scenario y ecrit).
BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 and sys.argv[1].startswith('http') else ''
PORT_TEST = 8799
PORT_CDP = 9333
ICI = os.path.dirname(os.path.abspath(__file__))

NAVIGATEURS = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
]


# ------------------------------------------------ WebSocket minimal (client)

def ws_connect(url):
    m = re.match(r'ws://([^:/]+):(\d+)(/.*)', url)
    host, port, path = m.group(1), int(m.group(2)), m.group(3)
    s = socket.create_connection((host, port), timeout=120)
    key = base64.b64encode(os.urandom(16)).decode()
    requete = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n') % (path, host, port, key)
    s.sendall(requete.encode())
    buf = b''
    while b'\r\n\r\n' not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise RuntimeError('poignée de main WebSocket interrompue')
        buf += chunk
    head, rest = buf.split(b'\r\n\r\n', 1)
    if b' 101 ' not in head.split(b'\r\n')[0]:
        raise RuntimeError('WebSocket refusé : ' + head.decode('latin1'))
    return s, rest


def ws_send(s, text, op=0x1):
    data = text.encode() if isinstance(text, str) else text
    mask = os.urandom(4)
    n = len(data)
    hdr = bytes([0x80 | op])
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0x80 | 126]) + struct.pack('>H', n)
    else:
        hdr += bytes([0x80 | 127]) + struct.pack('>Q', n)
    s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


class Lecteur:
    def __init__(self, s, rest):
        self.s, self.buf = s, rest

    def _besoin(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 16)
            if not chunk:
                raise RuntimeError('WebSocket fermé')
            self.buf += chunk

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
    def __init__(self, url):
        self.s, rest = ws_connect(url)
        self.lecteur = Lecteur(self.s, rest)
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


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    exe = next((n for n in NAVIGATEURS if os.path.exists(n)), None)
    if not exe:
        print('Aucun navigateur Chrome/Edge trouvé.'); return 2
    global BASE
    serveur = None
    dossier_data = None
    if not BASE:
        dossier_data = tempfile.mkdtemp(prefix='fstdw-data-')
        serveur = subprocess.Popen([sys.executable, os.path.join(ICI, '..', 'serveur.py'), str(PORT_TEST), '--data', dossier_data],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        BASE = 'http://localhost:%d' % PORT_TEST
    URL = BASE + '/tests/scenario.html'
    pret = False
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + '/api/etat', timeout=2).read(); pret = True; break
        except Exception:
            time.sleep(0.2)
    if not pret:
        print('Serveur injoignable sur', BASE); return 2
    print('Serveur :', BASE, '(dossier temporaire)' if dossier_data else '')

    profil = tempfile.mkdtemp(prefix='fstdw-test-')
    proc = subprocess.Popen([exe, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
                             '--disable-extensions', '--disable-background-networking', '--disable-sync',
                             '--remote-debugging-port=%d' % PORT_CDP, '--user-data-dir=' + profil,
                             '--window-size=1200,900', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    code = 1
    try:
        cible = None
        for _ in range(100):
            try:
                pages = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT_CDP, timeout=2).read())
                cible = next((p for p in pages if p.get('type') == 'page'), None)
                if cible:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not cible:
            print('Chrome ne répond pas sur le port de débogage.'); return 2

        cdp = CDP(cible['webSocketDebuggerUrl'])
        cdp.appel('Runtime.enable')
        cdp.appel('Page.enable')
        cdp.appel('Page.navigate', url=URL)

        debut = time.time()
        texte = ''
        while time.time() - debut < 120:
            time.sleep(0.5)
            texte = cdp.evaluer("(document.getElementById('out')||{}).innerText||''") or ''
            if 'FIN' in texte:
                break
        print(texte)
        exceptions = [e for e in cdp.evenements if e['method'] == 'Runtime.exceptionThrown']
        for e in exceptions:
            d = e['params']['exceptionDetails']
            print('EXCEPTION :', d.get('text'), (d.get('exception') or {}).get('description', ''),
                  '—', d.get('url'), 'ligne', d.get('lineNumber'), 'col', d.get('columnNumber'))
        if 'FIN' not in texte:
            print('\nLe scénario ne s est pas terminé en 120 s.')
        code = 0 if ('FIN' in texte and 'FAIL' not in texte and not exceptions) else 1
        try:
            cdp.appel('Browser.close')
        except Exception:
            pass
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(profil, ignore_errors=True)
        if serveur:
            serveur.kill()
            serveur.wait()
            shutil.rmtree(dossier_data, ignore_errors=True)
    print('\nRÉSULTAT :', 'tout passe' if code == 0 else 'des échecs')
    return code


if __name__ == '__main__':
    sys.exit(main())
