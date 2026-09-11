from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

css='''
/* v1.8 · Maps, imagen de sucursal ampliada y fondo visual */
body.store-wallpaper{background:#eef4fa;}
body.store-wallpaper::before{content:"";position:fixed;inset:51px 0 0;z-index:0;pointer-events:none;background-image:var(--store-wallpaper,none);background-repeat:no-repeat;background-position:center center;background-size:min(980px,88vw) auto;opacity:.13;filter:saturate(.9) contrast(.96);}
main{position:relative;z-index:1}.app-header{z-index:40}.connection-panel,.modal,.drawer{z-index:120}
.store-public-card{width:100%;font:inherit;text-align:left;cursor:pointer;appearance:none;-webkit-appearance:none;transition:.16s border-color,.16s background,.16s transform}
.store-public-card:hover{border-color:#9fc7e9;background:rgba(248,251,254,.92)}.store-public-card:active{transform:scale(.995)}
.store-public-card small{font-size:.73rem}.store-public-card .maps-hint{display:block;margin-top:3px;color:#0b66ae;font-size:.58rem;font-weight:900}
.connection-store-photo{margin:13px 0 10px;border:1px solid #dbe6ef;border-radius:16px;background:#f2f7fb;overflow:hidden;display:grid;place-items:center;min-height:120px}
.connection-store-photo[hidden]{display:none!important}.connection-store-photo img{display:block;width:100%;height:min(320px,42vh);object-fit:contain;background:#f2f7fb}
@media(max-width:520px){body.store-wallpaper::before{background-size:94vw auto;opacity:.11}.connection-store-photo img{height:min(260px,36vh)}}
'''
if '/* v1.8 · Maps, imagen de sucursal ampliada y fondo visual */' not in s:
    if '</style>' not in s: raise SystemExit('No se encontró cierre style')
    s=s.replace('</style>',css+'</style>',1)

old='''      <div class="connection-status"><i id="connectionDot"></i><strong id="connectionState">Conectando…</strong></div>\n      <div class="connection-grid">'''
new='''      <div class="connection-status"><i id="connectionDot"></i><strong id="connectionState">Conectando…</strong></div>\n      <div id="connectionStorePhoto" class="connection-store-photo" hidden><img id="connectionStoreImage" alt="Imagen de la sucursal"></div>\n      <div class="connection-grid">'''
if 'id="connectionStoreImage"' not in s:
    if old not in s: raise SystemExit('No se encontró connection-status')
    s=s.replace(old,new,1)

old='''    <section id="storePublicCard" class="store-public-card" aria-label="Dirección de la sucursal"><span>📍</span><div><strong id="storePublicName">Mi Farmacia</strong><small id="storePublicAddress">Dirección pendiente de sincronizar</small></div></section>'''
new='''    <button id="storePublicCard" class="store-public-card" type="button" aria-label="Abrir ubicación de la sucursal en Google Maps"><span>📍</span><div><small id="storePublicAddress">Dirección pendiente de sincronizar</small><span class="maps-hint">Abrir ubicación en Maps</span></div></button>'''
if 'id="storePublicName"' in s:
    if old not in s: raise SystemExit('No se encontró tarjeta pública')
    s=s.replace(old,new,1)

old="  function refreshStoreImage(){const img=$('brandLogo');if(!img)return;const personalizada=text(state.store?.imagenFarmaciaUrl||'');const valida=/^data:image\\/(?:jpeg|jpg|png|webp);base64,/i.test(personalizada);img.src=valida?personalizada:DEFAULT_BRAND_LOGO_SRC;img.classList.toggle('custom-store-image',valida);img.alt=valida?`Imagen de ${text(state.store?.nombreActivo||state.store?.nombre||'la farmacia')}`:'Mi Farmacia';}\n"
new="""  function refreshStoreImage(){\n    const img=$('brandLogo');\n    const personalizada=text(state.store?.imagenFarmaciaUrl||'');\n    const valida=/^data:image\\/(?:jpeg|jpg|png|webp);base64,/i.test(personalizada);\n    const nombre=text(state.store?.nombreActivo||state.store?.nombre||'la farmacia');\n    if(img){img.src=valida?personalizada:DEFAULT_BRAND_LOGO_SRC;img.classList.toggle('custom-store-image',valida);img.alt=valida?`Imagen de ${nombre}`:'Mi Farmacia';}\n    const detalle=$('connectionStoreImage'),contenedor=$('connectionStorePhoto');\n    if(detalle&&contenedor){detalle.src=valida?personalizada:DEFAULT_BRAND_LOGO_SRC;detalle.alt=valida?`Imagen de ${nombre}`:'Mi Farmacia';contenedor.hidden=!valida;}\n    if(valida){document.body.classList.add('store-wallpaper');document.body.style.setProperty('--store-wallpaper',`url(${JSON.stringify(personalizada)})`);}\n    else{document.body.classList.remove('store-wallpaper');document.body.style.removeProperty('--store-wallpaper');}\n  }\n  function storeMapsUrl(){\n    const directa=text(state.store?.mapsUrl||state.publication?.mapsUrl||'');\n    if(/^https:\\/\\//i.test(directa))return directa;\n    const direccion=text(state.store?.direccion||'');\n    return direccion?`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(direccion)}`:'';\n  }\n  function openStoreMaps(){const url=storeMapsUrl();if(!url){toast('La farmacia aún no ha publicado su ubicación.');return;}window.open(url,'_blank','noopener,noreferrer');}\n"""
if 'function storeMapsUrl()' not in s:
    if old not in s: raise SystemExit('No se encontró refreshStoreImage')
    s=s.replace(old,new,1)

old="""    $('storePublicName').textContent=nombre;\n    $('storePublicAddress').textContent=direccion;\n    $('pickupStoreAddress').textContent=direccion;\n    refreshStoreImage();refreshStoreAvailability();\n"""
new="""    const publicAddress=$('storePublicAddress');if(publicAddress)publicAddress.textContent=direccion;\n    $('pickupStoreAddress').textContent=direccion;\n    const maps=storeMapsUrl(),publicCard=$('storePublicCard');\n    if(publicCard){publicCard.disabled=!maps;publicCard.title=maps?'Abrir ubicación en Google Maps':'Ubicación pendiente de sincronizar';}\n    refreshStoreImage();refreshStoreAvailability();\n"""
if "$('storePublicName').textContent=nombre;" in s:
    if old not in s: raise SystemExit('No se encontró refreshConnectionInfo público')
    s=s.replace(old,new,1)

old="""    $('brandButton').addEventListener('click',openConnectionPanel);\n    $('saveWelcomeProfile').addEventListener('click',saveWelcomeProfile);"""
new="""    $('brandButton').addEventListener('click',openConnectionPanel);\n    $('storePublicCard')?.addEventListener('click',openStoreMaps);\n    $('saveWelcomeProfile').addEventListener('click',saveWelcomeProfile);"""
if "$('storePublicCard')?.addEventListener('click',openStoreMaps);" not in s:
    if old not in s: raise SystemExit('No se encontró bind de logo')
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
