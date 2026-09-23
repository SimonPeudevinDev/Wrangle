<?php
// Wrangle, la boite de depot chez l'hebergeur : ce que les scripts partagent.
// Les comptes (prenom, mot de passe hache, DIT ou pas) et le secret qui signe
// les jetons vivent dans comptes/, interdit au web. Creer un compte est ouvert :
// le site est prive, personne d'autre que l'equipe ne le connait.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function repondre($code, $obj) {
    http_response_code($code);
    echo json_encode($obj, JSON_UNESCAPED_UNICODE);
    exit;
}

function corps() {
    $c = json_decode(file_get_contents('php://input'), true);
    return is_array($c) ? $c : [];
}

// un dossier a l'abri du web, cree au premier besoin
function dossier_prive($nom) {
    $d = __DIR__ . '/' . $nom;
    if (!is_dir($d)) {
        mkdir($d, 0755, true);
    }
    if (!file_exists($d . '/.htaccess')) {
        file_put_contents($d . '/.htaccess', "Require all denied\n");
    }
    return $d;
}

function lire_comptes() {
    $f = dossier_prive('comptes') . '/comptes.json';
    $c = file_exists($f) ? json_decode(file_get_contents($f), true) : null;
    return is_array($c) ? $c : [];
}

function ecrire_comptes($comptes) {
    file_put_contents(dossier_prive('comptes') . '/comptes.json', json_encode($comptes, JSON_UNESCAPED_UNICODE), LOCK_EX);
}

// « Marie-Lou » -> marie-lou : la cle d'un compte, et le nom de son fichier de depot
function slug($nom) {
    $a = @iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $nom);
    $s = trim(preg_replace('/[^a-z0-9]+/', '-', strtolower($a !== false ? $a : $nom)), '-');
    return $s === '' ? 'sans-nom' : $s;
}

function secret() {
    $f = dossier_prive('comptes') . '/secret.txt';
    if (!file_exists($f)) {
        file_put_contents($f, bin2hex(random_bytes(32)));
    }
    return trim(file_get_contents($f));
}

// un jeton : qui, DIT ou pas, jusqu'a quand, signe. La page le garde 90 jours.
function signer($nom, $dit) {
    $msg = $nom . '|' . ($dit ? '1' : '0') . '|' . (time() + 90 * 24 * 3600);
    return $msg . '|' . hash_hmac('sha256', $msg, secret());
}

function verifier_jeton($jeton) {
    $p = explode('|', (string) $jeton);
    if (count($p) !== 4) {
        return null;
    }
    $msg = $p[0] . '|' . $p[1] . '|' . $p[2];
    if (!hash_equals(hash_hmac('sha256', $msg, secret()), $p[3]) || (int) $p[2] < time()) {
        return null;
    }
    return ['nom' => $p[0], 'dit' => $p[1] === '1'];
}

// le compte connecte, ou une reponse 401
function qui() {
    $q = verifier_jeton(corps()['jeton'] ?? '');
    if (!$q) {
        repondre(401, ['erreur' => 'connexion requise']);
    }
    return $q;
}
