<?php
// Deposer ses saisies : POST { jeton, projet }. Un fichier par personne, sous
// le prenom du compte connecte ; le dernier depot remplace le precedent.
require __DIR__ . '/commun.php';
$q = qui();
$projet = corps()['projet'] ?? null;
if (!is_array($projet) || !isset($projet['plans'])) {
    repondre(400, ['erreur' => 'projet attendu']);
}
$quand = date('c');
$donnees = json_encode(['nom' => $q['nom'], 'quand' => $quand, 'projet' => $projet], JSON_UNESCAPED_UNICODE);
if ($donnees === false || file_put_contents(dossier_prive('saisies') . '/' . slug($q['nom']) . '.json', $donnees, LOCK_EX) === false) {
    repondre(500, ['erreur' => 'écriture impossible sur le serveur']);
}
repondre(200, ['ok' => true, 'nom' => $q['nom'], 'quand' => $quand, 'octets' => strlen($donnees)]);
