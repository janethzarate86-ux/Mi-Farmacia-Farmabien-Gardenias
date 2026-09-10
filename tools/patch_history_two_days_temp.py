from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

s=s.replace('const MAX_LOCAL_ORDERS = 8;', "const MAX_LOCAL_ORDERS = 200;\n  const MAX_STATUS_CHECK_ORDERS = 30;", 1)

old="""  function localOrders(){const rows=readJsonStorage(STORAGE_ORDERS,[]);return Array.isArray(rows)?rows:[]}
  function saveLocalOrders(rows){writeJsonStorage(STORAGE_ORDERS,(Array.isArray(rows)?rows:[]).slice(0,MAX_LOCAL_ORDERS))}
  function localOrderDate(raw){try{return new Date(raw).toLocaleString('es-MX',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'})}catch(_){return raw||'—'}}"""
new="""  function localDayKey(raw){const d=raw instanceof Date?raw:new Date(raw);if(!Number.isFinite(d.getTime()))return '';return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
  function historyAllowedDayKeys(){const hoy=new Date();const ayer=new Date(hoy.getFullYear(),hoy.getMonth(),hoy.getDate()-1);return new Set([localDayKey(hoy),localDayKey(ayer)])}
  function depurarHistorialLocal(rows){const permitidos=historyAllowedDayKeys();return (Array.isArray(rows)?rows:[]).filter(o=>permitidos.has(localDayKey(o?.createdAt))).sort((a,b)=>new Date(b.createdAt||0)-new Date(a.createdAt||0)).slice(0,MAX_LOCAL_ORDERS)}
  function localOrders(){const original=readJsonStorage(STORAGE_ORDERS,[]);const rows=depurarHistorialLocal(original);if(Array.isArray(original)&&rows.length!==original.length)writeJsonStorage(STORAGE_ORDERS,rows);return rows}
  function saveLocalOrders(rows){writeJsonStorage(STORAGE_ORDERS,depurarHistorialLocal(rows))}
  function localOrderDate(raw){try{return new Date(raw).toLocaleString('es-MX',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'})}catch(_){return raw||'—'}}"""
if old not in s:
    raise SystemExit('No se encontró bloque localOrders esperado')
s=s.replace(old,new,1)

if 'cont.innerHTML=rows.slice(0,8).map(o=>{' not in s:
    raise SystemExit('No se encontró límite de 8 pedidos')
s=s.replace('cont.innerHTML=rows.slice(0,8).map(o=>{','cont.innerHTML=rows.map(o=>{',1)

old_loop="""    try{for(const o of rows.slice(0,MAX_LOCAL_ORDERS)){if(!o.token||!o.storeId)continue;try{const remote=await request(`mi_farmacia/pedidos_estado/${o.storeId}/${o.token}`,{timeoutMs:3500});if(!remote||!remote.estado)continue;const next=text(remote.estado).toUpperCase();const before=text(o.estado).toUpperCase();o.estado=next;o.mensaje=text(remote.mensaje)||o.mensaje;o.updatedAt=remote.actualizadoEn||nowISO();if(next!==before){changed=true;const msg=o.mensaje||`El pedido ${o.id} cambió a ${publicOrderStatusLabel(next)}.`;toast(msg);speakOrderStatus(next);if('Notification'in window&&Notification.permission==='granted'){try{new Notification('Mi Farmacia',{body:msg,tag:`pedido-${o.id}`})}catch(_){}}}}catch(_){/* pedido antiguo/sin reglas de seguimiento */}}"""
new_loop="""    const pendientes=rows.filter(o=>!['SURTIDO','CANCELADO'].includes(text(o?.estado).toUpperCase())).slice(0,MAX_STATUS_CHECK_ORDERS);
    try{for(const o of pendientes){if(!o.token||!o.storeId)continue;try{const remote=await request(`mi_farmacia/pedidos_estado/${o.storeId}/${o.token}`,{timeoutMs:3500});if(!remote||!remote.estado)continue;const next=text(remote.estado).toUpperCase();const before=text(o.estado).toUpperCase();o.estado=next;o.mensaje=text(remote.mensaje)||o.mensaje;o.updatedAt=remote.actualizadoEn||nowISO();if(next!==before){changed=true;const msg=o.mensaje||`El pedido ${o.id} cambió a ${publicOrderStatusLabel(next)}.`;toast(msg);speakOrderStatus(next);if('Notification'in window&&Notification.permission==='granted'){try{new Notification('Mi Farmacia',{body:msg,tag:`pedido-${o.id}`})}catch(_){}}}}catch(_){/* pedido antiguo/sin reglas de seguimiento */}}"""
if old_loop not in s:
    raise SystemExit('No se encontró bucle de seguimiento esperado')
s=s.replace(old_loop,new_loop,1)

for needle in ['historyAllowedDayKeys','depurarHistorialLocal','MAX_STATUS_CHECK_ORDERS = 30','cont.innerHTML=rows.map(o=>']:
    if needle not in s:
        raise SystemExit('Faltó aplicar '+needle)

p.write_text(s,encoding='utf-8')
