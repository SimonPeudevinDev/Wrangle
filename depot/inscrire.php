<?php
// Cree ou remplace un compte : POST { nom, mdp, dit }. Refaire son compte
// change son mot de passe.
require __DIR__ . '/commun.php';
$c = corps();
$nom = trim(str_replace('|', ' ', (string) ($c['nom'] ?? '')));
$mdp = (string) ($c['mdp'] ?? '');
if ($nom === '' || strlen($mdp) < 4) {
    repondre(400, ['erreur' => 'prénom et mot de passe (quatre caractères au moins) attendus']);
}
$nom = mb_substr($nom, 0, 40);
$comptes = lire_comptes();
$comptes[slug($nom)] = ['nom' => $nom, 'hash' => password_hash($mdp, PASSWORD_DEFAULT), 'dit' => !empty($c['dit'])];
ecrire_comptes($comptes);
repondre(200, ['ok' => true, 'nom' => $nom, 'dit' => !empty($c['dit'])]);
