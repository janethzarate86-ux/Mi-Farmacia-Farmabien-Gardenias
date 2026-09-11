from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

if 'id="deleteOrderHistory"' in s:
    raise SystemExit('El botón ya está aplicado')

old='<section id="orderHistoryPanel" class="order-history" aria-label="Historial de pedidos"><div class="order-history-head"><div><strong>Mis pedidos</strong><small>Historial reciente guardado en este dispositivo</small></div><button id="enableOrderNotifications" type="button">🔔 Activar avisos</button></div><div id="orderHistoryList" class="order-history-list"></div></section>'
new='<section id="orderHistoryPanel" class="order-history" aria-label="Historial de pedidos"><div class="order-history-head"><div class="order-history-copy"><strong>Mis pedidos</strong><small>Historial reciente guardado en este dispositivo</small></div><div class="order-history-actions"><button id="deleteOrderHistory" class="danger-soft" type="button">🗑 Eliminar pedidos</button><button id="enableOrderNotifications" type="button">🔔 Activar avisos</button></div></div><div id="orderHistoryList" class="order-history-list"></div></section>'
if old not in s: raise SystemExit('No se encontró el encabezado del historial')
s=s.replace(old,new,1)

css='.order-history-head button{border:1px solid #cfe0ed;background:#eef6fc;color:#0b66ae;border-radius:10px;padding:7px 9px;font-size:.62rem;font-weight:900}'
extra='.order-history-actions{display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap}.order-history-head .order-history-actions button{white-space:nowrap}.order-history-head .order-history-actions .danger-soft{border-color:#f1cbd2;background:#fff3f5;color:#b4243f}.order-history-head .order-history-actions .danger-soft:hover{background:#fde9ed}.order-history-head .order-history-actions .danger-soft:disabled{opacity:.45;cursor:not-allowed}@media(max-width:520px){.order-history-head{align-items:flex-start}.order-history-actions{max-width:58%;justify-content:flex-end}.order-history-head .order-history-actions button{padding:7px 8px;font-size:.58rem}}'
if css not in s: raise SystemExit('No se encontró el estilo del historial')
s=s.replace(css,css+extra,1)

anchor='function renderOrderHistory(){\n'
if anchor not in s: raise SystemExit('No se encontró renderOrderHistory')
funcs=r'''function protectedHistoryOrderIds(rows=localOrders()){
  const protectedIds=new Set(),ordered=Array.isArray(rows)?rows:[];
  for(const o of ordered){const e=text(o?.estado||'NUEVO').toUpperCase();if(['EN_PROCESO','PREPARANDO','PREPARANDO_PEDIDO'].includes(e)&&o?.id)protectedIds.add(o.id)}
  const newestPending=ordered.find(o=>text(o?.estado||'NUEVO').toUpperCase()==='NUEVO'&&o?.id);if(newestPending?.id)protectedIds.add(newestPending.id);
  return protectedIds;
}
function removableHistoryOrders(rows=localOrders()){const protectedIds=protectedHistoryOrderIds(rows);return (Array.isArray(rows)?rows:[]).filter(o=>o?.id&&!protectedIds.has(o.id))}
function refreshDeleteHistoryButton(){const b=$('deleteOrderHistory');if(!b)return;const removable=removableHistoryOrders();b.disabled=!removable.length;b.title=removable.length?`Eliminar ${removable.length} pedido(s) del historial`:'No hay pedidos eliminables; el pedido activo o en proceso está protegido'}
function deleteOrderHistory(){
  const rows=localOrders(),protectedIds=protectedHistoryOrderIds(rows),removable=rows.filter(o=>o?.id&&!protectedIds.has(o.id));
  if(!removable.length){toast('No hay pedidos para eliminar. El pedido activo o en proceso está protegido.');refreshDeleteHistoryButton();return}
  const protectedCount=rows.length-removable.length,msg=`¿Deseas eliminar ${removable.length} pedido(s) del historial de este dispositivo? Esta acción no se puede deshacer.${protectedCount?`\n\nSe conservará${protectedCount===1?'':'n'} ${protectedCount} pedido(s) activo(s) o en proceso.`:''}`;
  if(!window.confirm(msg))return;
  const removedIds=new Set(removable.map(o=>o.id)),keep=rows.filter(o=>!removedIds.has(o.id));if(state.historyOrderOpenId&&removedIds.has(state.historyOrderOpenId))state.historyOrderOpenId='';saveLocalOrders(keep);renderOrderHistory();renderOrderProgress();toast(`${removable.length} pedido(s) eliminado(s) del historial.`)
}
'''
s=s.replace(anchor,funcs+anchor,1)

old_empty="    if(!rows.length){cont.innerHTML='<div class=\"order-history-empty\">Cuando envíes un pedido aparecerá aquí y podrás ver si fue surtido o cancelado.</div>';return}"
new_empty="    if(!rows.length){cont.innerHTML='<div class=\"order-history-empty\">Cuando envíes un pedido aparecerá aquí y podrás ver si fue surtido o cancelado.</div>';refreshDeleteHistoryButton();return}"
if old_empty not in s: raise SystemExit('No se encontró estado vacío')
s=s.replace(old_empty,new_empty,1)

end="    }).join('');\n  }\n  function toggleHistoryOrderDetail"
if end not in s: raise SystemExit('No se encontró cierre del historial')
s=s.replace(end,"    }).join('');\n    refreshDeleteHistoryButton();\n  }\n  function toggleHistoryOrderDetail",1)

bind="$('orderHistoryButton').addEventListener('click',openHistory);document.querySelectorAll('[data-close=\"history\"]').forEach(el=>el.addEventListener('click',closeHistory));"
if bind not in s: raise SystemExit('No se encontró listener del historial')
s=s.replace(bind,"$('orderHistoryButton').addEventListener('click',openHistory);$('deleteOrderHistory').addEventListener('click',deleteOrderHistory);document.querySelectorAll('[data-close=\"history\"]').forEach(el=>el.addEventListener('click',closeHistory));",1)

p.write_text(s,encoding='utf-8')
