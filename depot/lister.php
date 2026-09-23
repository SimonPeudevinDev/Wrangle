<?php
// Wrangle : les depots de tout le monde, pour le DIT (POST, sans parametre).
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$depots = [];
foreach (glob(__DIR__ . '/saisies/*.json') ?: [] as $fichier) {
    $d = json_decode(file_get_contents($fichier), true);
    if (is_array($d) && isset($d['nom'], $d['projet'])) {
        $depots[] = $d;
    }
}
usort($depots, function ($a, $b) { return strcmp($a['nom'], $b['nom']); });
echo json_encode(['depots' => $depots], JSON_UNESCAPED_UNICODE);
