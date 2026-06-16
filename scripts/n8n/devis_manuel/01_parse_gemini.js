// Parse la demande client avec Gemini (text OR file mode)
const GEMINI_KEY = $env.GEMINI_API_KEY;

const input = $input.first().json;
const email = input.body?.email || '';
const clientName = input.body?.client_name || '';
const demande = input.body?.demande || '';
const fileB64 = input.body?.file_base64 || '';
const fileMime = input.body?.file_mime || '';
const fileName = input.body?.file_name || '';

const source = fileB64 ? 'file' : 'text';

// Validation entree
if (!demande && !fileB64) {
  return [{ json: { error: true, message: 'Demande ou fichier requis.' } }];
}
if (fileB64 && !['application/pdf', 'image/jpeg', 'image/jpg'].includes(fileMime)) {
  return [{ json: { error: true, message: 'Format non supporte (PDF ou JPEG uniquement).' } }];
}

const catalogue = `CATALOGUE PRODUITS MY.LAB (cosmetiques capillaires professionnels B2B) :

SHAMPOINGS - 200ml, 500ml, 1000ml :
nourrissant | boucles | lissant | HA repulpe | volume | purifiant | protecteur de couleur
Gloss (200ml et 1000ml uniquement)
Homme : shampoing gel douche (200ml/500ml/1000ml) - NOM ODOO EXACT = "shampoing gel douche 200ml" SANS suffixe "homme"

MASQUES CAPILLAIRES - 200ml, 400ml, 1000ml :
nourrissant | boucles | lissant | HA repulpe | volume | protecteur de couleur
Gloss (200ml et 1000ml uniquement)
Homme : masque intense (200ml seulement) - NOM ODOO EXACT = "masque intense 200ml" SANS suffixe "homme"

CREMES SANS RINCAGE - 200ml (boucles aussi en 500ml) :
boucles | HA repulpe | lissante | nourrissante | volume

SPRAYS - 200ml :
masque reparateur sans rincage | spray texturisant
ATTENTION : le nom Odoo est "masque reparateur sans rincage 200ml" SANS le prefixe "spray".

SERUMS - 50ml :
serum finition ultime | serum barbe (homme - NOM ODOO EXACT = "serum barbe 50ml" SANS suffixe "homme")

HUILES - 50ml :
bain miraculeux (NOM ODOO: "bain miraculeux", PAS "huile bain miraculeux") | huile a barbe (homme - NOM ODOO EXACT = "huile a barbe 50ml" SANS suffixe "homme")

COLORISTEURS/DEJAUNISSEURS - shampoings ET masques - 200ml, 1000ml :
blond soleil | blond vanille | chocolat | cuivre | marron noisette | dejaunisseur platine
Tulipe noire : MASQUE uniquement (shampoing tulipe noire n'existe plus)
ATTENTION masque cuivre : nom Odoo = "masque coloristeur cuivre intense" (avec "intense"). Shampoing cuivre = "shampoing coloristeur cuivre" (sans "intense").

FRAIS / SERVICES (PAS de contenance, quantite par defaut = 1) :
- search_name "creation du dossier cosmetologique" — Odoo "Creation du dossier cosmetologique" (389,90 EUR)
  Alias clients : "dossier cosmetologique", "DIP", "PIF", "creation dossier"
- search_name "frais de creation design etiquette" — Odoo "Frais de creation design etiquette" (390,00 EUR)
  Alias clients : "creation d etiquettes sur mesure", "design etiquette", "creation etiquette"
- search_name "forfait d impression standard" — Odoo "Forfait d'impression standard" (99,00 EUR)
  Alias clients : "forfait impression noir", "forfait impression standard", "impression noir et blanc"
- search_name "forfait d impression couleur" — Odoo "Forfait d'impression couleur" (250,00 EUR)
  Alias clients : "forfait impression couleur", "impression couleur"

PRODUITS DISCONTINUES (TOUJOURS RETOURNER search_name = "INCONNU") :
- shampoing cerise (toutes contenances)
- masque cerise (toutes contenances)
- shampoing tulipe noire (toutes contenances)

NOMS COMMERCIAUX (alias utilises par les clients) :
- "brillance" ou "protecteur de couleur" = protecteur de couleur (shampoing/creme/masque)
- "blond polaire" ou "platine" = dejaunisseur platine
- "blond cuivre" ou "cuivre" = coloristeur cuivre
- "blond ble" ou "ble" = coloristeur blond soleil (shampoing ET masque)
- "roucou" = coloristeur cuivre (shampoing) / coloristeur cuivre intense (masque)
- "tulipe noire" = coloristeur tulipe noire (masque uniquement)
- "spray volume" ou "spray detox" ou "spray volume & detox" = spray texturisant
- "spray masque reparateur" = "masque reparateur sans rincage" (PAS de prefixe "spray" dans Odoo)
- "1L" ou "1 litre" = 1000ml
- "demi-litre" ou "0.5L" = 500ml
- "dossier cosmetologique" / "DIP" / "PIF" = creation du dossier cosmetologique (PAS de contenance, quantite 1 par defaut)
- "creation d etiquettes sur mesure" / "design etiquette" = frais de creation design etiquette (PAS de contenance, quantite 1 par defaut)
- "forfait impression noir" / "forfait impression standard" = forfait d impression standard (PAS de contenance, quantite 1 par defaut)
- "forfait impression couleur" = forfait d impression couleur (PAS de contenance, quantite 1 par defaut)

ATTENTION creme protectrice de couleur : le nom Odoo est "creme protectrice de couleur" (pas "creme protecteur")`;

const introText = fileB64
  ? `Le document joint (PDF ou photo) est une commande client MY.LAB. Lis-le integralement (toutes les pages si PDF), identifie les produits et quantites demandees, et extrais-les dans le format ci-dessous.`
  : `Analyse cette demande client MY.LAB et extrais les produits et quantites.`;

const extraRule = fileB64
  ? `\n11. Inclus aussi un champ "raw_ocr" en string contenant la transcription textuelle brute des elements de commande visibles dans le document (lignes produits, quantites, en-tete si present). Sert de fallback si aucun produit n'est extrait.`
  : '';

const prompt = `${introText}

${catalogue}

REGLES :
1. Retourne UNIQUEMENT du JSON valide, rien d autre
2. Format : { "products": [{ "search_name": "...", "display_name": "...", "quantity": N }] }
3. search_name = nom normalise minuscule pour Odoo, format EXACT : "type variante contenanceml"
   Exemples : "shampoing nourrissant 200ml", "masque boucles 400ml", "creme lissante 200ml",
   "serum finition ultime 50ml", "shampoing coloristeur blond soleil 200ml"
4. display_name = nom lisible avec majuscules
5. Contenance par defaut si non precisee : 200ml (50ml pour serums/huiles).
   EXCEPTION : pour les FRAIS / SERVICES (dossier cosmetologique, design etiquette, forfaits impression), AUCUNE contenance dans search_name.
6. Quantite par defaut si non precisee : 6 (minimum B2B). EXCEPTION FRAIS / SERVICES : quantite par defaut = 1.
7. Si un produit demande n existe pas dans le catalogue, search_name = "INCONNU"
8. search_name doit etre le NOM EXACT tel que dans Odoo, SANS prefixe de type
   Correct: "bain miraculeux 50ml", "serum finition ultime 50ml"
   Incorrect: "huile bain miraculeux 50ml", "serum de finition ultime 50ml"
9. TOUJOURS traduire les noms commerciaux vers les noms Odoo
   "shampoing brillance" -> "shampoing protecteur de couleur 200ml"
   "creme brillance" -> "creme protectrice de couleur 200ml"
   "shampoing blond polaire" -> "shampoing dejaunisseur platine 200ml"
   "masque blond polaire 1L" -> "masque dejaunisseur platine 1000ml"
   "shampoing blond ble 1L" -> "shampoing coloristeur blond soleil 1000ml"
   "masque blond ble 1L" -> "masque coloristeur blond soleil 1000ml"
   "shampoing roucou 1L" -> "shampoing coloristeur cuivre 1000ml"
   "masque roucou 1L" -> "masque coloristeur cuivre intense 1000ml"
   "masque tulipe noire 1L" -> "masque coloristeur tulipe noire 1000ml"
   "spray masque reparateur sans rincage" -> "masque reparateur sans rincage 200ml"
   "spray volume & detox" -> "spray texturisant 200ml"
10. INTERDICTION ABSOLUE d'ajouter "homme" dans search_name (meme si le document mentionne "homme" / "gamme homme" / "men").
    Les produits homme sont identifies par leur nom de base, JAMAIS par un suffixe.
    "shampoing gel douche homme 200ml" -> "shampoing gel douche 200ml"
    "shampoing gel douche homme 1L" -> "shampoing gel douche 1000ml"
    "huile a barbe homme 50ml" -> "huile a barbe 50ml"
    "serum barbe homme 50ml" -> "serum barbe 50ml"
    "masque intense homme 200ml" -> "masque intense 200ml"${extraRule}

${demande ? 'DEMANDE :\n' + demande : ''}`;

const parts = [{ text: prompt }];
if (fileB64) {
  parts.unshift({ inlineData: { mimeType: fileMime, data: fileB64 } });
}

const response = await this.helpers.httpRequest({
  method: 'POST',
  url: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + GEMINI_KEY,
  headers: { 'Content-Type': 'application/json' },
  body: {
    contents: [{ parts }],
    generationConfig: { temperature: 0.1, responseMimeType: 'application/json' }
  }
});

if (!response.candidates || !response.candidates[0]?.content?.parts?.[0]?.text) {
  return [{ json: { error: true, message: 'Reponse Gemini vide ou bloquee (quota, safety filter, ou format inattendu).' } }];
}
const text = response.candidates[0].content.parts[0].text;

let parsed;
try {
  parsed = JSON.parse(text);
} catch (e) {
  return [{ json: { error: true, message: 'Reponse Gemini non-JSON : ' + (e.message || String(e)) } }];
}

return [{
  json: {
    email,
    client_name: clientName,
    products: parsed.products || [],
    raw_demande: demande || null,
    source,
    raw_ocr: parsed.raw_ocr || null,
    file_base64: fileB64 || null,
    file_mime: fileMime || null,
    file_name: fileName || null
  }
}];
