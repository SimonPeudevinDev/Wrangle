<?php
// La porte du site chez l'hebergeur (construire_site.py --php la pose en
// index.php, a cote de la page) : un appareil qui a deja donne le mot de passe
// recoit la page ; les autres, le formulaire. Sans mot de passe regle
// (api/acces-config.php), la page est servie a tous, comme avant.
require __DIR__ . '/api/acces.php';

$rate = false;
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    if (acces_ouvrir((string) ($_POST['mdp'] ?? ''))) {
        header('Location: ./', true, 303);   // le laissez-passer est pose : on recharge, en GET
        exit;
    }
    $rate = true;
    sleep(1);   // un essai par seconde : deviner le mot de passe devient tres long
}

if (acces_ok()) {
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-cache, must-revalidate');
    readfile(__DIR__ . '/index.html');
    exit;
}

http_response_code($rate ? 401 : 200);
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
?><!doctype html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#171110">
<title>Wrangle</title>
<style>
  :root{ color-scheme:dark }
  *{ box-sizing:border-box }
  body{ margin:0; min-height:100vh; display:grid; place-items:center; padding:24px; background:#171110; color:#f6e9d8;
        font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif }
  form{ width:100%; max-width:330px }
  h1{ margin:0; font-size:30px; font-weight:800; letter-spacing:-.01em; color:#e7b04a }
  .sous{ margin:2px 0 28px; color:#b8a08c; font-size:14px }
  label{ display:block; margin-bottom:8px; font-size:12px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#8e7a69 }
  input{ width:100%; padding:14px 15px; border-radius:10px; border:1px solid rgba(246,233,216,.28); background:#221a17; color:inherit; font-size:17px }
  input:focus{ outline:none; border-color:#e7b04a }
  button{ width:100%; margin-top:14px; padding:14px; border:0; border-radius:999px; background:#e7b04a; color:#1c1410; font-size:16px; font-weight:700; cursor:pointer }
  .rate{ margin-top:16px; padding:10px 12px; border-radius:10px; background:rgba(232,103,94,.15); color:#f07a70; font-size:14px }
  .note{ margin-top:22px; color:#8e7a69; font-size:13px }
</style>
</head><body>
<form method="post" action="./">
  <h1>Wrangle</h1>
  <p class="sous">Foresight · journal de plateau</p>
  <label for="mdp">Mot de passe du tournage</label>
  <input id="mdp" name="mdp" type="password" autocomplete="current-password" autofocus required>
  <button type="submit">Entrer</button>
  <?php if ($rate) { ?><div class="rate">Mot de passe incorrect.</div><?php } ?>
  <p class="note">Une seule fois par appareil : il s’en souviendra ensuite.</p>
</form>
</body></html>
