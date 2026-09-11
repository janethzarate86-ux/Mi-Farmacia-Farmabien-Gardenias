from pathlib import Path
import re

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

# 1) Sustituir verificación bloqueante por comprobación informativa.
new_integrity=r'''  async function checkCatalogIntegrity(meta,productos){
    const result={available:false,ok:null,reason:''};
    try{
      const signature=meta?.firmaCatalogo;
      const jwk=state.store?.clavePublicaFirmaCatalogo||CONFIG_FILE.clavePublicaFirmaCatalogo;
      const expectedId=text(state.store?.claveFirmaCatalogoId||CONFIG_FILE.claveFirmaCatalogoId);
      if(!signature?.value||!signature?.keyId||!jwk?.x||!jwk?.y){result.reason='Firma de catálogo no disponible';return result;}
      result.available=true;
      if(expectedId&&text(signature.keyId)!==expectedId){result.ok=false;result.reason='La firma pertenece a otra clave';return result;}
      if(!window.crypto?.subtle){result.available=false;result.reason='WebCrypto no disponible';return result;}
      const publicKey=await window.crypto.subtle.importKey('jwk',jwk,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
      const payload={version:2,tiendaId:state.storeId,revision:Number(meta?.revision||0)||0,productos};
      result.ok=await window.crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},publicKey,fromB64(signature.value),new TextEncoder().encode(canonicalJson(payload)));
      result.reason=result.ok?'Firma válida':'Firma no coincidente';
      return result;
    }catch(error){result.available=true;result.ok=false;result.reason=text(error?.message||error);return result;}
  }
'''
pat_integrity=r"  async function verifyCatalogIntegrity\(meta, productos\)\{.*?\n  \}\n(?=  async function encryptOrderContent\(payload\)\{)"
s,n=re.subn(pat_integrity,new_integrity,s,count=1,flags=re.S)
if n!=1: raise SystemExit(f'No se pudo sustituir verifyCatalogIntegrity: {n}')

# 2) Reemplazar por completo el cargador anterior. La nueva lógica siempre puede
# mostrar el catálogo válido de Firebase aunque la firma auxiliar esté desfasada.
new_loader=r'''  async function loadCatalog({quiet=false,forceNetwork=false}={}){
    if(state.loading)return false;
    state.loading=true;
    if(!quiet&&!state.cacheLoaded){$('loadingState').hidden=false;$('emptyState').hidden=true;$('productGrid').innerHTML='';}
    let cache=null;
    try{
      if(!state.firebaseUrl||!state.storeId||forceNetwork)await resolvePublication();

      cache=loadCatalogCache();
      const cacheValida=!!(cache?.storeId===state.storeId&&cache?.productos&&typeof cache.productos==='object');
      if(cacheValida&&!state.cacheLoaded){
        applyProductsObject(cache.productos);
        state.catalogMeta={version:2,revision:Number(cache.revision||0),baseRevision:Number(cache.baseRevision||0),actualizadoEn:text(cache.actualizadoEn||'')};
        state.cacheLoaded=true;
        renderCategories();renderProducts();reconcileCart();$('loadingState').hidden=true;setStatus(true,'Actualizando');refreshConnectionInfo();
      }

      const metaPath=`mi_farmacia/catalogo/${state.storeId}/meta`;
      const productosPath=`mi_farmacia/catalogo/${state.storeId}/productos`;
      const cambiosPath=`mi_farmacia/catalogo/${state.storeId}/cambios`;

      // Configuración de tienda y metadatos son solicitudes pequeñas y van en paralelo.
      const [tiendaR,metaR]=await Promise.allSettled([
        (!state.store||state.store.id!==state.storeId)?loadStore():Promise.resolve(state.store),
        request(metaPath,{timeoutMs:FIREBASE_META_TIMEOUT_MS})
      ]);
      if(tiendaR.status==='rejected'&&!state.store)throw tiendaR.reason;
      const meta=(metaR.status==='fulfilled'&&metaR.value&&typeof metaR.value==='object')?metaR.value:{};
      refreshConnectionInfo();
      if(storePaused()){state.lastError='';setStatus(true,'Mantenimiento');$('loadingState').hidden=true;refreshStoreAvailability();return true;}

      const metaRevision=Number(meta.revision||0)||0;
      const baseRevision=Number(meta.baseRevision||metaRevision)||0;
      const metaTotal=Number(meta.totalProductos);
      const cacheRevision=cacheValida?Number(cache.revision||0)||0:0;
      let productos=cacheValida?cache.productos:null;
      let debeDescargarCompleto=!productos;

      if(productos){
        const cacheTotal=Object.keys(productos).length;
        if(Number.isFinite(metaTotal)&&metaTotal>=0&&cacheTotal!==metaTotal)debeDescargarCompleto=true;
        if(metaRevision&&cacheRevision>metaRevision)debeDescargarCompleto=true;
        if(metaRevision&&cacheRevision<baseRevision)debeDescargarCompleto=true;
      }

      // Si existe base compatible, aplicar únicamente cambios incrementales.
      if(!debeDescargarCompleto&&metaRevision&&cacheRevision<metaRevision){
        try{
          const cambios=await request(cambiosPath,{timeoutMs:FIREBASE_META_TIMEOUT_MS})||{};
          productos=applyChanges(productos,cambios);
          const totalTrasCambios=Object.keys(productos||{}).length;
          if(Number.isFinite(metaTotal)&&metaTotal>=0&&totalTrasCambios!==metaTotal)debeDescargarCompleto=true;
        }catch(_){debeDescargarCompleto=true;}
      }

      // Sin metadatos fiables se prioriza la fuente real de productos.
      if(!metaRevision)debeDescargarCompleto=true;
      if(debeDescargarCompleto){
        productos=await request(productosPath,{timeoutMs:FIREBASE_CATALOG_TIMEOUT_MS});
        if(!productos||typeof productos!=='object'||Array.isArray(productos))throw new Error('El catálogo publicado no contiene productos válidos.');
      }

      // Si meta/productos fueron escritos en instantes distintos, reintentar una vez
      // antes de aceptar una diferencia de conteo.
      if(metaRevision&&Number.isFinite(metaTotal)&&metaTotal>=0&&Object.keys(productos||{}).length!==metaTotal){
        await new Promise(r=>setTimeout(r,180));
        const [meta2,productos2]=await Promise.all([
          request(metaPath,{timeoutMs:FIREBASE_META_TIMEOUT_MS}).catch(()=>meta),
          request(productosPath,{timeoutMs:FIREBASE_CATALOG_TIMEOUT_MS})
        ]);
        if(productos2&&typeof productos2==='object'&&!Array.isArray(productos2)){productos=productos2;Object.assign(meta,meta2||{});}
      }

      const totalReal=Object.keys(productos||{}).length;
      const metaFinal={
        ...meta,
        version:2,
        revision:Number(meta.revision||Date.now())||Date.now(),
        baseRevision:Number(meta.baseRevision||meta.revision||Date.now())||Date.now(),
        totalProductos:totalReal,
        actualizadoEn:text(meta.actualizadoEn||state.publication?.actualizadoEn||nowISO())
      };

      // La firma sigue comprobándose, pero jamás vuelve a ocultar un catálogo que
      // acaba de descargarse correctamente desde la conexión configurada.
      const integridad=await checkCatalogIntegrity(metaFinal,productos||{});
      state.catalogIntegrity=integridad;
      if(integridad.available&&integridad.ok===false)console.warn('Mi Farmacia: catálogo cargado; firma auxiliar pendiente de corregir.',integridad.reason);

      state.catalogMeta=metaFinal;
      applyProductsObject(productos||{});
      saveCatalogCache(productos||{},metaFinal);
      state.cacheLoaded=true;
      $('storeName').textContent=text(state.store?.nombreActivo||state.store?.nombre||state.publication?.nombre||'Catálogo en línea');
      state.lastError='';setStatus(true,'En línea');refreshConnectionInfo();renderCategories();renderProducts();reconcileCart();$('loadingState').hidden=true;
      return true;
    }catch(e){
      state.lastError=text(e?.message||e);console.warn('Mi Farmacia no pudo sincronizar:',e);
      // Mantener visible el último catálogo útil; solo mostrar pantalla vacía cuando
      // realmente no existe ningún catálogo utilizable.
      const catalogoUtil=state.products.length>0||state.cacheLoaded;
      if(catalogoUtil){state.lastError='';setStatus(true,navigator.onLine?'En línea':'Sin internet');}
      else setStatus(false,navigator.onLine?'Sin sincronizar':'Sin internet');
      refreshConnectionInfo();$('loadingState').hidden=true;
      if(!state.products.length){$('emptyState').hidden=false;$('emptyMessage').textContent=state.lastError||'Catálogo temporalmente no disponible.';}
      if(!quiet)toast(navigator.onLine?'No se pudo actualizar el catálogo.':'Sin conexión a internet.');
      return false;
    }finally{state.loading=false;}
  }

'''
pat_loader=r"  async function loadCatalog\(\{quiet=false,forceNetwork=false\}=\{\}\)\{.*?\n  \}\n\n\n(?=  function categories\(\))"
s,n=re.subn(pat_loader,new_loader,s,count=1,flags=re.S)
if n!=1: raise SystemExit(f'No se pudo sustituir loadCatalog: {n}')

# 3) El sondeo periódico ya no fuerza resolver identidad en cada ciclo.
s=s.replace("setInterval(()=>{if(document.visibilityState==='visible'&&navigator.onLine){loadMasterImageCatalog().catch(()=>{});loadCatalog({quiet:true,forceNetwork:true})}},META_POLL_MS);","setInterval(()=>{if(document.visibilityState==='visible'&&navigator.onLine){loadMasterImageCatalog().catch(()=>{});loadCatalog({quiet:true})}},META_POLL_MS);")

# 4) Identificador de compilación.
s=re.sub(r'<meta name="mi-farmacia-build" content="[^"]+">','<meta name="mi-farmacia-build" content="single-file-v2.0.0-catalog-loader-clean">',s,count=1)

# Validaciones: no deben quedar dos lógicas oficiales.
checks_absent=['async function verifyCatalogIntegrity','try{await verifyCatalogIntegrity','firma del catálogo. Sincroniza nuevamente desde Macroxel']
for x in checks_absent:
    if x in s: raise SystemExit('Quedó lógica vieja: '+x)
if s.count('async function loadCatalog(')!=1: raise SystemExit('Debe quedar un solo loadCatalog')
if s.count('async function checkCatalogIntegrity(')!=1: raise SystemExit('Debe quedar una sola comprobación de integridad')
if 'single-file-v2.0.0-catalog-loader-clean' not in s: raise SystemExit('No cambió build')

p.write_text(s,encoding='utf-8')
print('OK reemplazo catálogo',len(s))
