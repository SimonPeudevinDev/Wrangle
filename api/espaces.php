<?php
// Les espaces qui ont un projet, pour le DIT qui reunit les saisies de tous :
// GET -> { espaces: [{ espace, nom, rev, plans, prises, quand }] }.
// Le projet de chacun se lit ensuite par etat.php?espace=…
require __DIR__ . '/commun.php';
$liste = [];
foreach (glob(DONNEES . '/espaces/*', GLOB_ONLYDIR) ?: [] as $d) {
    $f = $d . '/projet.json';
    if (!file_exists($f)) {
        continue;
    }
    $db = json_decode(file_get_contents($f));
    if (!is_object($db) || empty($db->plans)) {
        continue;
    }
    $nom = file_exists($d . '/nom.txt') ? trim(file_get_contents($d . '/nom.txt')) : '';
    $liste[] = ['espace' => basename($d), 'nom' => $nom !== '' ? $nom : basename($d),
                'rev' => file_exists($d . '/rev.txt') ? (int) file_get_contents($d . '/rev.txt') : 0,
                'plans' => count($db->plans), 'prises' => is_array($db->prises ?? null) ? count($db->prises) : 0,
                'quand' => date('c', filemtime($f))];
}
usort($liste, function ($a, $b) { return strcasecmp($a['nom'], $b['nom']); });
repondre(200, ['espaces' => $liste]);
