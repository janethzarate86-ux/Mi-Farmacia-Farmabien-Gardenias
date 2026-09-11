from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

old="""      const data=await r.json();
      const firebase=cleanBaseUrl(data?.firebaseUrl||'');
      const tienda=text(data?.tiendaId||'');
      if(Number(data?.version||0)!==2 || !firebase || !tienda){
        throw new Error('macroxel-config.json está vacío o incompleto. Genera la carpeta GitHub completa desde Macroxel con la conexión actual.');
      }
      RUNTIME_CONFIG={...data,firebaseUrl:firebase,tiendaId:tienda};
"""
new="""      const data=await r.json();
      const firebase=cleanBaseUrl(data?.firebaseUrl||'');
      if(Number(data?.version||0)!==2 || !firebase){
        throw new Error('macroxel-config.json está vacío o incompleto. Genera la carpeta GitHub completa desde Macroxel con la conexión actual.');
      }
      // El archivo GitHub solo arranca la conexión del cliente. La identidad de
      // farmacia se obtiene siempre de Firebase para no anclar este visor a un ID.
      RUNTIME_CONFIG={...data,firebaseUrl:firebase,tiendaId:text(data?.tiendaId||'')};
"""
if old not in s:
    raise SystemExit('No se encontró loadRuntimeConfig esperado')
s=s.replace(old,new,1)

old="""    state.bootstrapUrl=cleanBaseUrl(RUNTIME_CONFIG.firebaseUrl||CONFIG_FILE.bootstrapUrl||CONFIG_FILE.firebaseUrl||'');
    state.firebaseUrl=state.bootstrapUrl;
    state.githubUrl=cleanWebBaseUrl(RUNTIME_CONFIG.githubUrl||CONFIG_FILE.githubUrl||'');
    state.storeId=text(RUNTIME_CONFIG.tiendaId||CONFIG_FILE.tiendaId||'');
"""
new="""    state.bootstrapUrl=cleanBaseUrl(RUNTIME_CONFIG.firebaseUrl||CONFIG_FILE.bootstrapUrl||CONFIG_FILE.firebaseUrl||'');
    state.firebaseUrl=state.bootstrapUrl;
    state.githubUrl=cleanWebBaseUrl(RUNTIME_CONFIG.githubUrl||CONFIG_FILE.githubUrl||'');
    // Nunca fijar la tienda desde GitHub: /publicacion de Firebase manda.
    state.storeId='';
"""
if old not in s:
    raise SystemExit('No se encontró loadBootstrap esperado')
s=s.replace(old,new,1)

start=s.index('  async function resolvePublication(){')
end=s.index('  async function loadStore(){', start)
new_resolver="""  async function resolvePublication(){
    const bootstrap=cleanBaseUrl(state.bootstrapUrl||RUNTIME_CONFIG.firebaseUrl||CONFIG_FILE.bootstrapUrl||CONFIG_FILE.firebaseUrl||'');
    if(!bootstrap) throw new Error('Mi Farmacia no tiene configuración central. Genera macroxel-config.json desde el sistema principal y publícalo en este GitHub.');
    state.firebaseUrl=bootstrap;

    // La publicación de Firebase es la autoridad de identidad. De esta forma el
    // mismo visor sirve para cualquier cliente y sigue automáticamente el nombre
    // de farmacia/sucursal configurado en el sistema principal.
    const anterior=text(state.storeId||'');
    const pub=await requestAt(bootstrap,'mi_farmacia/publicacion',{timeoutMs:FIREBASE_META_TIMEOUT_MS})||{};
    state.publication=pub;
    state.githubUrl=cleanWebBaseUrl(pub.githubUrl||state.githubUrl||RUNTIME_CONFIG.githubUrl||CONFIG_FILE.githubUrl||'');
    state.storeId=text(pub.tiendaId||'');

    // Compatibilidad con instalaciones antiguas que aún no han publicado el
    // registro /publicacion. El tiendaId del archivo solo se usa como último recurso.
    if(!state.storeId) state.storeId=text(RUNTIME_CONFIG.tiendaId||CONFIG_FILE.tiendaId||'');
    if(!state.storeId){
      const stores=await requestAt(bootstrap,'mi_farmacia/tiendas',{timeoutMs:FIREBASE_META_TIMEOUT_MS})||{};
      const ids=Object.keys(stores);
      if(ids.length===1)state.storeId=ids[0]; else throw new Error('No hay una tienda activa publicada desde Macroxel.');
    }
    if(anterior&&anterior!==state.storeId){state.store=null;state.catalogMeta={};state.cacheLoaded=false;}
    state.lastResolveAt=Date.now(); saveResolver(); refreshConnectionInfo(); return pub;
  }

"""
s=s[:start]+new_resolver+s[end:]

old="      if(!state.firebaseUrl||!state.storeId) await resolvePublication();"
new="      if(forceNetwork||!state.firebaseUrl||!state.storeId) await resolvePublication();"
if old not in s:
    raise SystemExit('No se encontró condición loadCatalog esperada')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
