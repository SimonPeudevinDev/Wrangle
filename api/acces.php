<?php
// L'acces au site : le mot de passe du tournage, donne une fois par appareil.
// Le navigateur garde ensuite un laissez-passer (un cookie) quatre-vingt-dix
// jours : l'appareil n'est plus jamais interroge. Le mot de passe n'est ecrit
// nulle part en clair : acces-config.php n'en garde qu'une empreinte salee
// (PBKDF2). Sans ce fichier, le site reste ouvert, comme avant. Changer le mot
// de passe change l'empreinte, donc le laissez-passer : tout le monde le redonne.
//   acces-config.php : <?php return ['sel' => '…', 'empreinte' => '…'];
// Ce fichier ne pose aucun en-tete : la page d'entree (index.php) l'inclut aussi.
define('ACCES_COOKIE', 'wrangle_acces');
define('ACCES_DUREE', 90 * 24 * 3600);
define('ACCES_TOURS', 100000);

function acces_config() {
    static $c = null;
    if ($c === null) {
        $f = __DIR__ . '/acces-config.php';
        $c = is_file($f) ? include $f : [];
        if (!is_array($c) || empty($c['empreinte']) || empty($c['sel'])) {
            $c = [];
        }
    }
    return $c;
}

// le laissez-passer : il decoule de l'empreinte seule
function acces_jeton() {
    $c = acces_config();
    return $c ? hash_hmac('sha256', 'wrangle-acces', $c['empreinte']) : '';
}

function acces_ok() {
    if (!acces_config()) {
        return true;   // pas de mot de passe regle : le site est ouvert
    }
    $j = $_COOKIE[ACCES_COOKIE] ?? '';
    return is_string($j) && hash_equals(acces_jeton(), $j);
}

// le mot de passe donne : juste, l'appareil recoit son laissez-passer
function acces_ouvrir($mdp) {
    $c = acces_config();
    if (!$c || !is_string($mdp) || $mdp === '') {
        return false;
    }
    $e = hash_pbkdf2('sha256', $mdp, $c['sel'], ACCES_TOURS);
    if (!hash_equals($c['empreinte'], $e)) {
        return false;
    }
    $https = (($_SERVER['HTTPS'] ?? '') !== '' && $_SERVER['HTTPS'] !== 'off')
          || strtolower($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
    setcookie(ACCES_COOKIE, acces_jeton(), ['expires' => time() + ACCES_DUREE, 'path' => '/',
                                            'secure' => $https, 'httponly' => true, 'samesite' => 'Lax']);
    return true;
}
