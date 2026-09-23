<?php
// Les depots de tout le monde, pour le DIT : POST { jeton } -> { depots: [...] }.
require __DIR__ . '/commun.php';
$q = qui();
if (!$q['dit']) {
    repondre(403, ['erreur' => 'réservé au DIT']);
}
$depots = [];
foreach (glob(dossier_prive('saisies') . '/*.json') ?: [] as $fichier) {
    $d = json_decode(file_get_contents($fichier), true);
    if (is_array($d) && isset($d['nom'], $d['projet'])) {
        $depots[] = $d;
    }
}
usort($depots, function ($a, $b) { return strcmp($a['nom'], $b['nom']); });
repondre(200, ['depots' => $depots]);
