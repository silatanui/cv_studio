<?php
/**
 * Simple Git Webhook Deployment Script for cPanel.
 * 
 * If you cannot find the Webhook in cPanel Git Version Control,
 * or if your Python app is throwing 500 errors preventing internal endpoints from running:
 * 1. Place this file in your public_html/cv_studio/ directory.
 * 2. Point GitHub Webhook to: https://tanuisila.dev/cv_studio/deploy.php
 * 3. Optional: Set $secret if you set a Secret in GitHub Webhook.
 */

$secret = ''; // Set this if you configure a Secret in GitHub (matches Secret field)

if ($secret !== '') {
    $hubSignature = $_SERVER['HTTP_X_HUB_SIGNATURE_256'] ?? '';
    if (!$hubSignature) {
        http_response_code(403);
        die('No signature provided');
    }
    $payload = file_get_contents('php://input');
    $hash = 'sha256=' . hash_hmac('sha256', $payload, $secret);
    if (!hash_equals($hash, $hubSignature)) {
        http_response_code(403);
        die('Invalid signature');
    }
}

// Path to your repository (usually current directory or parent directory)
$repoDir = __DIR__;

// Execute git pull
$output = [];
$returnCode = 0;
exec("cd {$repoDir} && git pull origin main 2>&1", $output, $returnCode);

// Restart Phusion Passenger by creating/touching restart.txt
@mkdir($repoDir . '/tmp', 0755, true);
@touch($repoDir . '/tmp/restart.txt');

header('Content-Type: application/json');
echo json_encode([
    'status' => $returnCode === 0 ? 'success' : 'error',
    'code' => $returnCode,
    'output' => $output,
    'restarted' => true
]);
