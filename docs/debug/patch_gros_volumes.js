const fs = require('fs');
const w = JSON.parse(fs.readFileSync('./docs/debug/wf-gros-volumes.json', 'utf8'));
const conf = w.nodes.find(x => x.name.includes('Confirmation client'));

// Rewrite the message using template literals (backticks) so we can safely keep ASCII apostrophes in French text.
// Use $json or named refs to keep concise.
const newMsg = "={{ (() => {\n"
+ "  const J = $('Construire Draft Order + HTML').item.json;\n"
+ "  const firstname = (J.client && J.client.firstname || '').trim();\n"
+ "  const greeting = firstname ? `Bonjour ${firstname},` : 'Bonjour Madame, Monsieur,';\n"
+ "  const ref = J.ref;\n"
+ "  const ttc = Number(J.total_ttc).toFixed(2);\n"
+ "  return `<p>${greeting}</p>`\n"
+ "    + `<p>Merci d\u2019avoir pris le temps de configurer votre devis sur MY.LAB \u2014 j\u2019ai h\u00e2te de d\u00e9couvrir votre projet en d\u00e9tail.</p>`\n"
+ "    + `<p>Vous trouverez ci-dessous le r\u00e9capitulatif de votre demande <strong>${ref}</strong>, pour un montant de <strong>${ttc} \u20ac TTC</strong>.</p>`\n"
+ "    + `<p>Je l\u2019\u00e9tudie personnellement et reviens vers vous sous <strong>48h ouvr\u00e9es</strong> pour affiner les formats, conditionnements et d\u00e9lais avec vous, et vous accompagner dans le lancement de votre gamme.</p>`\n"
+ "    + `<p>Si vous avez la moindre question d\u2019ici l\u00e0, r\u00e9pondez simplement \u00e0 cet email \u2014 je suis joignable directement.</p>`\n"
+ "    + `<p>\u00c0 tr\u00e8s vite,<br><strong>Yoann Durand</strong><br>Fondateur \u00b7 MY.LAB<br>yoann@mylab-shop.com \u00b7 mylab-shop.com</p>`\n"
+ "    + `<hr>`\n"
+ "    + J.htmlDevis;\n"
+ "})() }}";

conf.parameters.message = newMsg;

// Same potential apostrophe issue likely in "Email — Notification MY.LAB" — inspect later
const allowedSettings = ['executionOrder','callerPolicy','errorWorkflow','saveDataErrorExecution','saveDataSuccessExecution','saveExecutionProgress','saveManualExecutions','executionTimeout','timezone'];
const cleanSettings = {};
for (const k of allowedSettings) if (w.settings && w.settings[k] !== undefined) cleanSettings[k] = w.settings[k];

const payload = { name: w.name, nodes: w.nodes, connections: w.connections, settings: cleanSettings };
fs.writeFileSync('./docs/debug/wf-gros-volumes-patched.json', JSON.stringify(payload, null, 2));
console.log('written. new message length:', newMsg.length);
