<?php
// Se connecter : POST { nom, mdp } -> { ok, jeton, nom, dit }.
require __DIR__ . '/commun.php';
$c = corps();
$comptes = lire_comptes();
$compte = $comptes[slug((string) ($c['nom'] ?? ''))] ?? null;
if (!$compte || !password_verify((string) ($c['mdp'] ?? ''), $compte['hash'])) {
    repondre(401, ['erreur' => 'prénom ou mot de passe incorrect']);
}
repondre(200, ['ok' => true, 'jeton' => signer($compte['nom'], !empty($compte['dit'])),
               'nom' => $compte['nom'], 'dit' => !empty($compte['dit'])]);
