from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')
original=s

def rep(old,new,label,count=1):
    global s
    n=s.count(old)
    if n < count:
        raise SystemExit(f'{label}: esperado al menos {count}, encontrado {n}')
    s=s.replace(old,new,count)

rep("  const STORAGE_ORDERS = 'mi_farmacia:orders:v1';\n", "  const STORAGE_ORDERS = 'mi_farmacia:orders:v1';\n  const STORAGE_PROGRESS_DISMISS = 'mi_farmacia:progress_dismiss:v1';\n", 'storage dismiss')

# Estilo compacto para la X del seguimiento.
style='''\n  .order-progress-panel{position:relative}\n  .order-progress-close{position:absolute;top:8px;right:8px;width:28px;height:28px;border:1px solid #d8e2ec;border-radius:50%;background:#fff;color:#536579;font-size:18px;line-height:1;display:grid;place-items:center;cursor:pointer;z-index:2;padding:0}\n  .order-progress-close:hover{background:#f1f5f9}\n  .order-progress-top{padding-right:32px}\n'''
idx=s.find('</style>')
if idx < 0: raise SystemExit('style close no encontrado')
s=s[:idx]+style+s[idx:]

old="""    let cat=revision?`Revisión ${revision.toLocaleString('es-MX')}`:'Esperando sincronización';
    if(actualizado){try{cat+=` · ${new Date(actualizado).toLocaleString('es-MX',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})}`}catch(_){}}
    $('connectionCatalog').textContent=cat;
"""
new="""    let cat=revision?`Revisión ${revision.toLocaleString('es-MX')}`:(state.products.length?`Catálogo disponible · ${state.products.length.toLocaleString('es-MX')} producto(s)`:'Esperando sincronización');
    if(actualizado){try{cat+=` · ${new Date(actualizado).toLocaleString('es-MX',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})}`}catch(_){}}
    $('connectionCatalog').textContent=cat;
"""
rep(old,new,'catalog status')
rep("    const online=!!(state.store&&state.firebaseUrl&&!state.lastError);\n", "    const catalogoUtil=!!(Number(state.catalogMeta?.revision||0)||state.products.length||state.cacheLoaded);\n    const online=!!(state.store&&state.firebaseUrl&&catalogoUtil);\n", 'online robusto')

old="      if(Number(meta.version||0)!==2||!Number(meta.revision||0)) throw new Error('El catálogo todavía no ha sido sincronizado con la versión móvil actual.');\n"
new="""      if(Number(meta.version||0)!==2||!Number(meta.revision||0)){
        let productosFallback=cacheValida?cache.productos:null;
        if(!productosFallback){
          if(productosInicialPromise){const inicial=await productosInicialPromise;if(!inicial.ok)throw inicial.error;productosFallback=inicial.value;}
          else productosFallback=await request(productosPath,{timeoutMs:FIREBASE_CATALOG_TIMEOUT_MS});
        }
        productosFallback=productosFallback||{};
        const revisionFallback=Date.now();
        const metaFallback={...meta,version:2,revision:Number(meta.revision||revisionFallback),baseRevision:Number(meta.baseRevision||meta.revision||revisionFallback),totalProductos:Object.keys(productosFallback).length,actualizadoEn:text(meta.actualizadoEn||state.publication?.actualizadoEn||nowISO())};
        state.catalogMeta=metaFallback;applyProductsObject(productosFallback);saveCatalogCache(productosFallback,metaFallback);state.cacheLoaded=true;
        $('storeName').textContent=text(state.store?.nombreActivo||state.store?.nombre||state.publication?.nombre||'Catálogo en línea');
        state.lastError='';setStatus(true,'En línea');refreshConnectionInfo();renderCategories();renderProducts();reconcileCart();$('loadingState').hidden=true;return true;
      }
"""
rep(old,new,'fallback meta')

old="""      setStatus(false,navigator.onLine?'Sin sincronizar':'Sin internet'); refreshConnectionInfo(); $('loadingState').hidden=true;
"""
new="""      const catalogoUtil=!!(state.store&&state.firebaseUrl&&(Number(state.catalogMeta?.revision||0)||state.products.length||state.cacheLoaded));
      setStatus(catalogoUtil,true?'En línea':'En línea':(navigator.onLine?'Sin sincronizar':'Sin internet')); refreshConnectionInfo(); $('loadingState').hidden=true;
"""
# Fix expression after insert below to avoid confusing ternary.
if old not in s: raise SystemExit('catch loadCatalog no encontrado')
s=s.replace(old,"""      const catalogoUtil=!!(state.store&&state.firebaseUrl&&(Number(state.catalogMeta?.revision||0)||state.products.length||state.cacheLoaded));
      if(catalogoUtil){state.lastError='';setStatus(true,'En línea');}else setStatus(false,navigator.onLine?'Sin sincronizar':'Sin internet'); refreshConnectionInfo(); $('loadingState').hidden=true;
""",1)

# Seguimiento cerrable por pedido + estado: si cambia el estado, vuelve a mostrarse.
old="""function visibleOrderProgress(){
  const now=Date.now();
  return localOrders().find(o=>{
    const e=text(o?.estado||'NUEVO').toUpperCase();
    if(!['SURTIDO','CANCELADO'].includes(e))return true;
    const t=orderTerminalTime(o);return !!t&&(now-t)<ORDER_PROGRESS_TTL_MS;
  })||null;
}
"""
new="""function progressDismissKey(order){return `${text(order?.id)}|${text(order?.estado||'NUEVO').toUpperCase()}`}
function progressDismissedFor(order){const saved=readJsonStorage(STORAGE_PROGRESS_DISMISS,{});return !!order&&text(saved?.key)===progressDismissKey(order)}
function dismissOrderProgress(){const o=visibleOrderProgress();if(!o)return;writeJsonStorage(STORAGE_PROGRESS_DISMISS,{key:progressDismissKey(o),at:Date.now()});renderOrderProgress()}
function visibleOrderProgress(){
  const now=Date.now();
  const o=localOrders().find(o=>{
    const e=text(o?.estado||'NUEVO').toUpperCase();
    if(!['SURTIDO','CANCELADO'].includes(e))return true;
    const t=orderTerminalTime(o);return !!t&&(now-t)<ORDER_PROGRESS_TTL_MS;
  })||null;
  return o&&!progressDismissedFor(o)?o:null;
}
"""
rep(old,new,'progress dismiss functions')

old="  panel.innerHTML=`<div class=\"order-progress-top\"><div class=\"order-progress-title\"><strong>Seguimiento de tu pedido</strong><small>${esc(o.id||'')}</small></div><span class=\"order-progress-badge ${esc(e.toLowerCase().replace(/_/g,'-'))}\">${esc(publicOrderStatusLabel(e))}</span></div><div class=\"order-progress-message\">${esc(mensaje)}</div><div class=\"order-progress-steps\">${steps}</div>`;\n"
new="  panel.innerHTML=`<button class=\"order-progress-close\" type=\"button\" data-close-progress aria-label=\"Cerrar seguimiento\">×</button><div class=\"order-progress-top\"><div class=\"order-progress-title\"><strong>Seguimiento de tu pedido</strong><small>${esc(o.id||'')}</small></div><span class=\"order-progress-badge ${esc(e.toLowerCase().replace(/_/g,'-'))}\">${esc(publicOrderStatusLabel(e))}</span></div><div class=\"order-progress-message\">${esc(mensaje)}</div><div class=\"order-progress-steps\">${steps}</div>`;\n"
rep(old,new,'progress close html')

old="    $('orderProgressPanel').addEventListener('click',openHistory);$('orderProgressPanel').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openHistory()}});"
new="    $('orderProgressPanel').addEventListener('click',e=>{if(e.target.closest('[data-close-progress]')){e.stopPropagation();dismissOrderProgress();return}openHistory()});$('orderProgressPanel').addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&!e.target.closest('[data-close-progress]')){e.preventDefault();openHistory()}});"
rep(old,new,'progress bind')

# El catch inicial tampoco debe pintar rojo si ya existe catálogo funcional en caché.
old="      $('loadingState').hidden=true;setStatus(false,navigator.onLine?'Sin sincronizar':'Sin internet');refreshConnectionInfo();\n"
new="      $('loadingState').hidden=true;const catalogoUtil=!!(state.store&&state.firebaseUrl&&(Number(state.catalogMeta?.revision||0)||state.products.length||state.cacheLoaded));if(catalogoUtil){state.lastError='';setStatus(true,'En línea');}else setStatus(false,navigator.onLine?'Sin sincronizar':'Sin internet');refreshConnectionInfo();\n"
rep(old,new,'init catch')

if s==original: raise SystemExit('sin cambios')
p.write_text(s,encoding='utf-8')
print('PATCH_OK', len(original), '->', len(s))
