import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = process.cwd();
const RUNTIME_CONFIG = path.join(ROOT, 'macroxel-config.json');
const MANIFEST = path.join(ROOT, 'catalogo-imagenes.json');
const ASSET_DIR = path.join(ROOT, 'assets', 'products');
const MAX_LOOKUPS = Math.max(1, Number(process.env.MAX_IMAGE_LOOKUPS || 120));
const RETRY_NOT_FOUND_MS = 3 * 24 * 60 * 60 * 1000;
const GAP_MS = 2200;
const MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const text = v => String(v ?? '').trim();
const norm = v => text(v).toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const validBarcode = v => {
  const raw = String(v ?? '').replace(/\D/g, '');
  return /^(?:\d{8}|\d{12,14})$/.test(raw) ? raw : '';
};

const informativeTokens = value => {
  const stop = new Set(['DE','DEL','LA','LAS','LOS','PARA','CON','SIN','Y','EN','UN','UNA','PAQ','PAQ.','PZA','PZAS','C','CJ','CAJA','BOLSA','BOTE','BOTELLA','FRASCO','ML','MG','GR','G','TAB','TABS','TABLETA','TABLETAS','CAP','CAPS','CAPSULA','CAPSULAS','JARABE','SOL','SOLUCION','GENERICO','GENERICA']);
  return norm(value)
    .replace(/[^A-Z0-9]+/g, ' ')
    .split(/\s+/)
    .map(v => v.trim())
    .filter(v => v.length >= 3 && !stop.has(v));
};

function buildSearchTerms(product) {
  const parts = [text(product?.nombre), text(product?.presentacion), text(product?.departamento)];
  const tokens = informativeTokens(parts.join(' '));
  return Array.from(new Set(tokens)).slice(0, 8);
}

function scoreCandidate(product, candidateName) {
  const wanted = buildSearchTerms(product);
  const actual = new Set(informativeTokens(candidateName));
  let overlap = 0;
  for (const token of wanted) if (actual.has(token)) overlap += 1;
  const minNeeded = wanted.length >= 5 ? 2 : 1;
  return { overlap, ok: overlap >= minNeeded };
}

function firebasePath(base, route) {
  const clean = text(base).replace(/\/+$/, '');
  return `${clean}/${String(route).replace(/^\/+|\/+$/g, '')}.json`;
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: { Accept: 'application/json', 'User-Agent': 'Macroxel-Image-Catalog/1.0' },
    signal: AbortSignal.timeout(20000)
  });
  if (!response.ok) throw new Error(`HTTP ${response.status} ${url}`);
  return response.json();
}

async function resolveFirebase(bootstrap) {
  let current = text(bootstrap).replace(/\/+$/, '');
  if (!/^https:\/\//i.test(current)) throw new Error('bootstrapUrl HTTPS no encontrado en index.html');
  let publication = null;
  for (let hop = 0; hop < 4; hop += 1) {
    publication = await fetchJson(firebasePath(current, 'mi_farmacia/publicacion')) || {};
    const next = text(publication.firebaseUrl).replace(/\/+$/, '');
    if (next && next !== current) { current = next; continue; }
    break;
  }
  const storeId = text(publication?.tiendaId);
  if (!storeId) throw new Error('Mi Farmacia todavía no publicó tiendaId. Sincroniza desde Macroxel.');
  return { firebaseUrl: current, storeId };
}

function sourceOrder(product) {
  const dep = norm(product?.departamento || '');
  const food = /(BEBIDA|SNACK|ALIMENTO|DULCE|LACTEO|ABARROTE|CEREAL|BOTANA)/.test(dep);
  return food
    ? [['off', 'https://world.openfoodfacts.org'], ['opf', 'https://world.openproductsfacts.org']]
    : [['opf', 'https://world.openproductsfacts.org'], ['off', 'https://world.openfoodfacts.org']];
}

async function lookupImage(product, code) {
  for (const [source, host] of sourceOrder(product)) {
    try {
      const endpoint = `${host}/api/v2/product/${encodeURIComponent(code)}?fields=code,product_name,image_front_url,image_url`;
      const data = await fetchJson(endpoint);
      const returnedCode = validBarcode(data?.code || data?.product?.code || code);
      const imageUrl = text(data?.product?.image_front_url || data?.product?.image_url);
      if (returnedCode === code && /^https:\/\//i.test(imageUrl)) {
        return { source, imageUrl, productName: text(data?.product?.product_name) };
      }
    } catch (error) {
      console.log(`[${code}] ${source}: ${error.message}`);
    }
    await sleep(500);
  }
  return null;
}


async function searchImageByText(product) {
  const terms = buildSearchTerms(product);
  if (!terms.length) return null;
  const query = encodeURIComponent(terms.join(' '));
  for (const [source, host] of sourceOrder(product)) {
    try {
      const endpoint = `${host}/cgi/search.pl?search_terms=${query}&search_simple=1&action=process&json=1&page_size=8&fields=code,product_name,image_front_url,image_url`;
      const data = await fetchJson(endpoint);
      const list = Array.isArray(data?.products) ? data.products : [];
      let best = null;
      for (const item of list) {
        const imageUrl = text(item?.image_front_url || item?.image_url);
        const productName = text(item?.product_name);
        if (!/^https:\/\//i.test(imageUrl) || !productName) continue;
        const scored = scoreCandidate(product, productName);
        if (!scored.ok) continue;
        if (!best || scored.overlap > best.overlap) best = { source, imageUrl, productName, overlap: scored.overlap, code: validBarcode(item?.code || '') };
      }
      if (best) return { ...best, matchedBy: 'TEXT' };
    } catch (error) {
      console.log(`[text-search] ${source}: ${error.message}`);
    }
    await sleep(500);
  }
  return null;
}

async function downloadWebp(url, destination) {
  const response = await fetch(url, {
    headers: { Accept: 'image/*', 'User-Agent': 'Macroxel-Image-Catalog/1.0' },
    signal: AbortSignal.timeout(30000)
  });
  if (!response.ok) throw new Error(`Imagen HTTP ${response.status}`);
  const type = text(response.headers.get('content-type')).toLowerCase();
  if (!type.startsWith('image/')) throw new Error(`Contenido no es imagen: ${type || 'desconocido'}`);
  const announced = Number(response.headers.get('content-length') || 0);
  if (announced > MAX_DOWNLOAD_BYTES) throw new Error('Imagen demasiado grande');
  const buffer = Buffer.from(await response.arrayBuffer());
  if (buffer.length > MAX_DOWNLOAD_BYTES) throw new Error('Imagen demasiado grande');
  await sharp(buffer, { failOn: 'none' })
    .rotate()
    .resize({ width: 900, height: 900, fit: 'inside', withoutEnlargement: true })
    .webp({ quality: 84, effort: 5 })
    .toFile(destination);
}

async function readManifest() {
  try {
    const data = JSON.parse(await fs.readFile(MANIFEST, 'utf8'));
    if (Number(data?.version) === 1 && data?.products && typeof data.products === 'object') return data;
  } catch (_) {}
  return { version: 1, updatedAt: '', products: {} };
}

function shouldLookup(entry, assetExists, now) {
  const status = text(entry?.status).toLowerCase();
  if ((status === 'verified_ean' || status === 'verified_text') && assetExists) return false;
  if (status === 'not_found') {
    const checked = Date.parse(entry.checkedAt || '') || 0;
    if (now - checked < RETRY_NOT_FOUND_MS) return false;
  }
  return true;
}

async function readRuntimeBootstrap() {
  const env = text(process.env.MACROXEL_FIREBASE_URL);
  if (env) return env;
  try { const cfg = JSON.parse(await fs.readFile(RUNTIME_CONFIG, 'utf8')); return text(cfg?.firebaseUrl); } catch (_) { return ''; }
}

async function writeRuntimeConfig(firebaseUrl, storeId) {
  let current = {};
  try { current = JSON.parse(await fs.readFile(RUNTIME_CONFIG, 'utf8')) || {}; } catch (_) {}
  const payload = {
    version: 1,
    firebaseUrl: text(firebaseUrl).replace(/\/+$/, ''),
    githubUrl: text(current.githubUrl || ''),
    tiendaId: text(storeId || current.tiendaId || '')
  };
  const normalizedCurrent = {
    version: Number(current.version) || 1,
    firebaseUrl: text(current.firebaseUrl).replace(/\/+$/, ''),
    githubUrl: text(current.githubUrl || ''),
    tiendaId: text(current.tiendaId || '')
  };
  if (JSON.stringify(payload) === JSON.stringify(normalizedCurrent)) return false;
  await fs.writeFile(RUNTIME_CONFIG, `${JSON.stringify(payload, null, 2)}
`, 'utf8');
  return true;
}

async function main() {
  const bootstrap = await readRuntimeBootstrap();
  if (!bootstrap) throw new Error('Configura la variable del repositorio MACROXEL_FIREBASE_URL con la URL Firebase de este cliente.');
  const { firebaseUrl, storeId } = await resolveFirebase(bootstrap);
  await writeRuntimeConfig(firebaseUrl, storeId);
  const products = await fetchJson(firebasePath(firebaseUrl, `mi_farmacia/catalogo/${storeId}/productos`)) || {};
  if (!Object.keys(products).length) {
    console.log('No hay productos publicados todavía para Mi Farmacia.');
  }
  const manifest = await readManifest();
  await fs.mkdir(ASSET_DIR, { recursive: true });

  const now = Date.now();
  const candidates = [];
  for (const [id, product] of Object.entries(products)) {
    if (!product || product.activo === false) continue;
    const code = validBarcode(product.imagenClave || product.codigo);
    if (!code) continue;
    const asset = path.join(ASSET_DIR, `${code}.webp`);
    let exists = false;
    try { await fs.access(asset); exists = true; } catch (_) {}
    const entry = manifest.products[code];
    if (shouldLookup(entry, exists, now)) candidates.push({ id, product, code, asset });
  }

  candidates.sort((a, b) => {
    const aa = manifest.products[a.code]?.status === 'not_found' ? 1 : 0;
    const bb = manifest.products[b.code]?.status === 'not_found' ? 1 : 0;
    return aa - bb || a.code.localeCompare(b.code);
  });

  let lookups = 0;
  let found = 0;
  for (const item of candidates) {
    if (lookups >= MAX_LOOKUPS) break;
    if (lookups > 0) await sleep(GAP_MS);
    lookups += 1;
    const checkedAt = new Date().toISOString();
    console.log(`[${lookups}/${Math.min(candidates.length, MAX_LOOKUPS)}] ${item.code} ${text(item.product.nombre)}`);
    let hit = await lookupImage(item.product, item.code);
    let matchedStatus = 'verified_ean';
    let matchedBy = 'EAN';
    if (!hit) {
      hit = await searchImageByText(item.product);
      matchedStatus = hit ? 'verified_text' : 'not_found';
      matchedBy = hit?.matchedBy || 'TEXT';
    }
    if (!hit) {
      manifest.products[item.code] = {
        status: 'not_found',
        checkedAt,
        name: text(item.product.nombre),
        presentation: text(item.product.presentacion)
      };
      continue;
    }
    try {
      await downloadWebp(hit.imageUrl, item.asset);
      manifest.products[item.code] = {
        status: matchedStatus,
        image: `assets/products/${item.code}.webp`,
        source: hit.source,
        sourceUrl: hit.imageUrl,
        matchedBy,
        sourceProductName: hit.productName,
        sourceCode: text(hit.code || ''),
        matchOverlap: Number(hit.overlap || 0),
        name: text(item.product.nombre),
        presentation: text(item.product.presentacion),
        checkedAt,
        updatedAt: checkedAt
      };
      found += 1;
    } catch (error) {
      console.log(`[${item.code}] descarga: ${error.message}`);
      manifest.products[item.code] = {
        status: 'error_retry',
        checkedAt,
        source: hit.source,
        sourceUrl: hit.imageUrl,
        matchedBy,
        name: text(item.product.nombre),
        presentation: text(item.product.presentacion)
      };
    }
  }

  if (!lookups) {
    console.log('No hay códigos nuevos o pendientes para revisar.');
    return;
  }
  manifest.version = 1;
  manifest.updatedAt = new Date().toISOString();
  manifest.storeId = storeId;
  manifest.totalCatalogProducts = Object.keys(products).length;
  manifest.totalImageEntries = Object.values(manifest.products).filter(v => ['verified_ean','verified_text'].includes(text(v?.status).toLowerCase())).length;
  manifest.totalNotFound = Object.values(manifest.products).filter(v => text(v?.status).toLowerCase() === 'not_found').length;
  manifest.totalErrors = Object.values(manifest.products).filter(v => text(v?.status).toLowerCase() === 'error_retry').length;
  await fs.writeFile(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(`Revisados: ${lookups}. Nuevas imágenes: ${found}. Catálogo con imagen: ${manifest.totalImageEntries}.`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 0;
});
