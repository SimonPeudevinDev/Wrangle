<?php
// Cree ou remplace un compte : POST { cle, nom, mdp, dit }. La cle du tournage
// est obligatoire : c'est le DIT qui ouvre les comptes de l'equipe.
require __DIR__ . '/commun.php';
$c = corps();
if (!hash_equals(cle_tournage(), (string) ($c['cle'] ?? ''))) {
    repondre(401, ['erreur' => 'clé du tournage refusée']);
}
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
