<?php
// Wrangle : chacun depose ici ses saisies (POST JSON { nom, projet }), le DIT
// les recupere toutes avec lister.php. Un fichier par personne, sous son
// prenom ; le dernier depot remplace le precedent. Pas de cle : le site est
// prive, seule l'equipe en connait l'adresse.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$corps = json_decode(file_get_contents('php://input'), true);
$nom = is_array($corps) ? trim((string) ($corps['nom'] ?? '')) : '';
$projet = is_array($corps) ? ($corps['projet'] ?? null) : null;
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
