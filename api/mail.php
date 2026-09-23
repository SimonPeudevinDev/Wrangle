<?php
// Le journal DIT par mail, expedie par l'hebergeur (la fonction mail de PHP).
//   GET  -> { possible, expediteur, envois }
//   POST { destinataires, sujet, texte, nom, pdf (base64), auto, creneau, jour, nomClient }
// L'expediteur se regle dans donnees/mail.json : { "expediteur": "journal@…" } ;
// a defaut, wrangle@ le domaine du site. Un envoi automatique ne part qu'une
// fois par creneau, quel que soit le nombre d'appareils qui le tentent.
require __DIR__ . '/commun.php';

function expediteur() {
    $cfg = lire_json(DONNEES . '/mail.json');
    if (is_object($cfg) && !empty($cfg->expediteur)) {
        return (string) $cfg->expediteur;
    }
    $hote = preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'wrangle.local');
    return 'wrangle@' . preg_replace('/^www\./', '', $hote);
}

function envois_mail() {
    $l = lire_json(DONNEES . '/mails.json');
    return is_array($l) ? $l : [];
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    preparer();
    repondre(200, ['possible' => function_exists('mail'), 'expediteur' => expediteur(),
                   'envois' => array_slice(envois_mail(), -10)]);
}

$c = corps();
if ($c === null) {
    repondre(400, ['erreur' => 'JSON attendu']);
}
$a = [];
foreach ((array) ($c->destinataires ?? []) as $x) {
    $x = trim((string) $x);
    if ($x !== '' && filter_var($x, FILTER_VALIDATE_EMAIL)) {
        $a[] = $x;
    }
}
if (!$a) {
    repondre(400, ['erreur' => 'destinataires attendus']);
}
$pdf = base64_decode((string) ($c->pdf ?? ''), true);
if ($pdf === false || strncmp($pdf, '%PDF', 4) !== 0) {
    repondre(400, ['erreur' => 'PDF attendu']);
}
$auto = !empty($c->auto);
$cle = couper($c->creneau ?? '', 60);   // « 2026-09-23 J1 14h » : un envoi par creneau

verrouiller();
if ($auto && $cle !== '') {
    foreach (envois_mail() as $e) {
        if (!empty($e->auto) && ($e->cle ?? '') === $cle) {
            deverrouiller();
            repondre(200, ['ok' => false, 'deja' => true]);
        }
    }
}
$nom = preg_replace('/[^A-Za-z0-9._-]+/', '-', (string) ($c->nom ?? 'journal-DIT.pdf'));
$sujet = (string) ($c->sujet ?? 'Journal DIT');
$texte = (string) ($c->texte ?? '');
$frontiere = 'wrangle-' . bin2hex(random_bytes(12));
$entetes = "From: " . expediteur() . "\r\nMIME-Version: 1.0\r\n"
         . "Content-Type: multipart/mixed; boundary=\"$frontiere\"";
$corpsMail = "--$frontiere\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: 8bit\r\n\r\n"
           . $texte . "\r\n\r\n--$frontiere\r\nContent-Type: application/pdf; name=\"$nom\"\r\n"
           . "Content-Transfer-Encoding: base64\r\nContent-Disposition: attachment; filename=\"$nom\"\r\n\r\n"
           . chunk_split(base64_encode($pdf)) . "--$frontiere--\r\n";
$parti = function_exists('mail')
      && @mail(implode(', ', $a), '=?UTF-8?B?' . base64_encode($sujet) . '?=', $corpsMail, $entetes);
if (!$parti) {
    deverrouiller();
    repondre(502, ['erreur' => "l'hébergeur a refusé l'envoi"]);
}
$entree = ['quand' => date('Y-m-d H:i'), 'cle' => $cle, 'jour' => (string) ($c->jour ?? ''), 'a' => $a,
           'auto' => $auto, 'par' => couper($c->nomClient ?? '', 40), 'octets' => strlen($pdf)];
$liste = envois_mail();
$liste[] = $entree;
ecrire_json(DONNEES . '/mails.json', array_slice($liste, -200));
deverrouiller();
repondre(200, ['ok' => true, 'a' => $a, 'quand' => $entree['quand']]);
