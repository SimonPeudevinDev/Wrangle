<?php
// Wrangle : chacun depose ici ses saisies (POST JSON { cle, nom, projet }),
// le DIT les recupere toutes avec lister.php. La cle du tournage vit dans
// cle.php, ecrit a la publication ; sans elle, rien ne passe. Un fichier par
// personne, le dernier depot remplace le precedent.
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
$nom = trim((string) ($corps['nom'] ?? ''));
$projet = $corps['projet'] ?? null;
if ($nom === '' || !is_array($projet) || !isset($projet['plans'])) {
    http_response_code(400);
    echo json_encode(['erreur' => 'nom et projet attendus']);
    exit;
}

// un nom de fichier sans accent ni espace : « Marie-Lou » -> marie-lou.json
$ascii = @iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $nom);
$slug = trim(preg_replace('/[^a-z0-9]+/', '-', strtolower($ascii !== false ? $ascii : $nom)), '-');
if ($slug === '') {
    $slug = 'sans-nom';
}

$dossier = __DIR__ . '/saisies';
if (!is_dir($dossier)) {
    mkdir($dossier, 0755, true);
}
if (!file_exists($dossier . '/.htaccess')) {
    file_put_contents($dossier . '/.htaccess', "Require all denied\n");
}
$quand = date('c');
$donnees = json_encode(['nom' => $nom, 'quand' => $quand, 'projet' => $projet], JSON_UNESCAPED_UNICODE);
if ($donnees === false || file_put_contents($dossier . '/' . $slug . '.json', $donnees, LOCK_EX) === false) {
    http_response_code(500);
    echo json_encode(['erreur' => 'écriture impossible sur le serveur']);
    exit;
}
echo json_encode(['ok' => true, 'nom' => $nom, 'quand' => $quand, 'octets' => strlen($donnees)]);
