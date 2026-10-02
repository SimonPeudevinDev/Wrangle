<?php
// La place prise chez l'hebergeur, pour la jauge des reglages :
// GET -> { utilise, quota, parties: [{ cle, nom, octets }], quand }.
// Le quota de l'offre (1 Go) couvre tout l'hebergement, pas seulement le
// site : on mesure donc tout le dossier de l'hebergement (le parent de www/).
// Les projets des espaces se detaillent par type : les shots (le decoupage),
// les schemas (croquis et plans de decor importes), les prises ; puis les
// sauvegardes horodatees (des copies de tout cela), les journaux et reglages,
// la page et les scripts, et le reste de l'hebergement.
require __DIR__ . '/commun.php';
define('QUOTA_OCTETS', 1024 * 1024 * 1024);   // l'offre OVH : 1 Go = 1024 Mo

// la taille d'un dossier, sous-dossiers compris ; ce qui ne se lit pas ne compte pas
function taille($d, $sauf = []) {
    if (!is_dir($d)) {
        return 0;
    }
    $n = 0;
    try {
        // un sous-dossier interdit en lecture est saute, sans arreter le compte
        $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($d, FilesystemIterator::SKIP_DOTS),
                                            RecursiveIteratorIterator::LEAVES_ONLY, RecursiveIteratorIterator::CATCH_GET_CHILD);
        foreach ($it as $f) {
            if (!$f->isFile() || $f->isLink()) {
                continue;
            }
            $p = $f->getPathname();
            foreach ($sauf as $s) {
                if (strpos($p, $s . DIRECTORY_SEPARATOR) === 0) {
                    continue 2;
                }
            }
            $n += $f->getSize();
        }
    } catch (Throwable $e) {
        // un dossier interdit en lecture : on garde ce qui a ete compte
    }
    return $n;
}

// un projet, reparti par type au prorata de ce que chaque partie pese dans le fichier
function repartir($f, &$t) {
    $n = filesize($f);
    $db = json_decode(file_get_contents($f), true);
    $long = function ($x) { return strlen(json_encode($x, JSON_SORTIE)); };
    if (!is_array($db)) {
        $t['autre'] += $n;
        return;
    }
    $schemas = 0;
    $shots = 0;
    foreach (($db['plans'] ?? []) as $p) {
        $c = 0;
        foreach (['croquis', 'croquisPlus'] as $k) {
            if (!empty($p[$k])) {
                $c += $long($p[$k]);
            }
        }
        $schemas += $c;
        $shots += $long($p) - $c;
    }
    $schemas += !empty($db['prod']['fonds']) ? $long($db['prod']['fonds']) : 0;   // des plans de decor gardes en image
    $prises = $long($db['prises'] ?? []);
    $tout = max(1, $long($db));
    $t['shots'] += $n * $shots / $tout;
    $t['schemas'] += $n * $schemas / $tout;
    $t['prises'] += $n * $prises / $tout;
}

$t = ['shots' => 0, 'schemas' => 0, 'prises' => 0, 'autre' => 0];
$sauv = 0;
foreach (glob(DONNEES . '/espaces/*', GLOB_ONLYDIR) ?: [] as $d) {
    if (is_file($d . '/projet.json')) {
        repartir($d . '/projet.json', $t);
    }
    $sauv += taille($d . '/sauvegardes');
}
$t['schemas'] += taille(DONNEES . '/fonds');   // les plans de decor importes, en fichiers
$donnees = taille(DONNEES);
// les journaux, la production et le reste des donnees
$divers = max(0, $donnees - $t['shots'] - $t['schemas'] - $t['prises'] - $sauv);
$www = dirname(__DIR__);
$site = taille($www, [DONNEES]);
// le dossier de l'hebergement n'est pas toujours lisible : alors, le site seul
$tout = @is_readable(dirname($www)) ? taille(dirname($www)) : 0;
$tout = max($tout, $donnees + $site);
repondre(200, [
    'utilise' => $tout, 'quota' => QUOTA_OCTETS,
    'parties' => [
        ['cle' => 'shots', 'nom' => 'Shots', 'octets' => (int) round($t['shots'])],
        ['cle' => 'schemas', 'nom' => 'Schémas', 'octets' => (int) round($t['schemas'])],
        ['cle' => 'prises', 'nom' => 'Prises', 'octets' => (int) round($t['prises'])],
        ['cle' => 'sauvegardes', 'nom' => 'Sauvegardes', 'octets' => $sauv],
        ['cle' => 'divers', 'nom' => 'Journaux et réglages', 'octets' => (int) round($divers)],
        ['cle' => 'site', 'nom' => 'Page et scripts', 'octets' => $site],
        ['cle' => 'reste', 'nom' => 'Reste de l’hébergement', 'octets' => max(0, $tout - $donnees - $site)],
    ],
    'quand' => date('c'),
]);
