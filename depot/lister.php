<?php
// Wrangle : les depots de tout le monde, pour le DIT (POST JSON { cle }).
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

if (!file_exists(__DIR__ . '/cle.php')) {
    http_response_code(503);
    echo json_encode(['erreur' => 'dépôt non configuré : la clé du tournage manque']);
    exit;
}
require __DIR__ . '/cle.php';

$corps = json_decode(file_get_contents('php://input'), true);
if (!is_array($corps) || !hash_equals(CLE, (string) ($corps['cle'] ?? ''))) {
    http_response_code(401);
    echo json_encode(['erreur' => 'clé du tournage refusée']);
    exit;
}

$depots = [];
foreach (glob(__DIR__ . '/saisies/*.json') ?: [] as $fichier) {
    $d = json_decode(file_get_contents($fichier), true);
    if (is_array($d) && isset($d['nom'], $d['projet'])) {
        $depots[] = $d;
    }
}
usort($depots, function ($a, $b) { return strcmp($a['nom'], $b['nom']); });
echo json_encode(['depots' => $depots], JSON_UNESCAPED_UNICODE);
