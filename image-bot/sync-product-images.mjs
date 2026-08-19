import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = process.cwd();
const RUNTIME_CONFIG = path.join(ROOT, 'macroxel-config.json');
const MANIFEST = path.join(ROOT, 'catalogo-imagenes.json');
const ASSET_DIR = path.join(ROOT, 'assets', 'products');
const MAX_LOOKUPS = Math.max(1, Number(process.env.MAX_IMAGE_LOOKUPS || 40));
const RETRY_NOT_FOUND_MS = 3 * 24 * 60 * 60 * 1000;
const GAP_MS = 4300;
const MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const text = v => String(v ?? '').trim();
const norm = v => text(v).toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const validBarcode = v => {
  const raw = String(v ?? '').replace(/\D/g, '');
  return /^(?:\d{8}|\d{12,14})$/.test(raw) ? raw : '';
};

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
  if (entry?.status === 'verified_ean' && assetExists) return false;
  if (entry?.status === 'not_found') {
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
  const payload = { version:1, firebaseUrl:text(firebaseUrl).replace(/\/+$/, ''), githubUrl:'', tiendaId:text(storeId), updatedAt:new Date().toISOString() };
  await fs.writeFile(RUNTIME_CONFIG, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

async function main() {
  const bootstrap = await readRuntimeBootstrap();
  if (!bootstrap) throw new Error('Configura la variable del repositorio MACROXEL_FIREBASE_URL con la URL Firebase de este cliente.');
  const { firebaseUrl, storeId } = await resolveFirebase(bootstrap);
  await writeRuntimeConfig(firebaseUrl, storeId);
  const products = await fetchJson(firebasePath(firebaseUrl, `mi_farmacia/catalogo/${storeId}/productos`)) || {};
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
    const hit = await lookupImage(item.product, item.code);
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
        status: 'verified_ean',
        image: `assets/products/${item.code}.webp`,
        source: hit.source,
        sourceUrl: hit.imageUrl,
        matchedBy: 'EAN',
        sourceProductName: hit.productName,
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
  manifest.totalImageEntries = Object.values(manifest.products).filter(v => v?.status === 'verified_ean').length;
  await fs.writeFile(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(`Revisados: ${lookups}. Nuevas imágenes: ${found}. Catálogo con imagen: ${manifest.totalImageEntries}.`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
