from pathlib import Path
p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

# Estado para abrir/cerrar el detalle de un pedido del historial.
if "historyOrderOpenId:''" not in s:
    s=s.replace("orderStatusBusy:false", "orderStatusBusy:false, historyOrderOpenId:''", 1)

css="""
/* Mi Farmacia · stock visible directamente en tarjeta + detalle de historial */
.stock-badge{z-index:3}.stock-badge.is-low{background:#fff3d6!important;color:#9a5a00!important;border-color:#f1cb7a!important}
.stock-inline{display:flex;align-items:center;gap:5px;width:fit-content;max-width:100%;margin-top:5px;border-radius:9px;padding:5px 7px;background:#e9f8f1;color:#087653;border:1px solid #bfe8d8;font-size:.59rem;font-weight:950;line-height:1.2}
.stock-inline.is-low{background:#fff3d6;color:#9a5a00;border-color:#f1cb7a}.stock-inline.is-out{background:#fdebed;color:#aa203b;border-color:#f4bfc8}.stock-inline.is-out::before{content:'●';font-size:.65rem}.stock-inline.is-low::before{content:'⚠';font-size:.7rem}
.order-history-item{cursor:pointer;transition:.15s}.order-history-item:hover,.order-history-item.open{border-color:#9fc7e9;background:#f8fbfe}.order-history-detail{grid-column:1/-1;border-top:1px solid #e4ebf2;margin-top:4px;padding-top:9px}.order-history-detail h3{margin:0 0 7px;color:var(--navy);font-size:.71rem}.order-history-detail-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;padding:6px 0;border-bottom:1px dashed #e5ebf1}.order-history-detail-row:last-child{border-bottom:0}.order-history-detail-row span{font-size:.62rem;color:#40566b;line-height:1.35}.order-history-detail-row b{font-size:.62rem;color:var(--navy);white-space:nowrap}.order-history-detail-meta{margin-top:7px;padding:7px 8px;border-radius:9px;background:#eef5fb;color:#53697e;font-size:.61rem;line-height:1.4}.order-history-item .history-hint{display:block;margin-top:5px;color:#0b66ae;font-size:.58rem;font-weight:900}
"""
if 'stock visible directamente en tarjeta + detalle de historial' not in s:
    s=s.replace('</style>',css+'</style>',1)

# Estado visible en la propia tarjeta, sin necesidad de abrir el producto.
if 'AGOTADO · TEMPORALMENTE SIN EXISTENCIAS' not in s:
    old="visible.map(p=>{const stock=stockInfo(p);return `"
    new="visible.map(p=>{const stock=stockInfo(p);const estadoDirecto=stock.className==='is-out'?'AGOTADO · TEMPORALMENTE SIN EXISTENCIAS':stock.className==='is-low'?stock.label:'DISPONIBLE';return `"
    if old not in s: raise SystemExit('No se encontró renderProducts esperado')
    s=s.replace(old,new,1)
if '<div class="stock-inline ${stock.className}">' not in s:
    old="<h2 class=\"product-name\">${esc(p.nombre||'Producto')}</h2>${isAntibiotic(p)?"
    new="<h2 class=\"product-name\">${esc(p.nombre||'Producto')}</h2><div class=\"stock-inline ${stock.className}\">${esc(estadoDirecto)}</div>${isAntibiotic(p)?"
    if old not in s: raise SystemExit('No se encontró nombre de producto esperado')
    s=s.replace(old,new,1)

history_fn=r'''function renderOrderHistory(){
    const rows=localOrders();const cont=$('orderHistoryList');if(!cont)return;
    if(!rows.length){cont.innerHTML='<div class="order-history-empty">Cuando envíes un pedido aparecerá aquí y podrás ver si fue surtido o cancelado.</div>';return}
    cont.innerHTML=rows.slice(0,8).map(o=>{
      const estado=text(o.estado||'NUEVO').toUpperCase();
      const tipo=o.entrega?.tipo==='DOMICILIO'?'Entrega a domicilio':'Recoger en sucursal';
      const abierto=state.historyOrderOpenId===o.id;
      const items=Array.isArray(o.items)?o.items:[];
      const detalleItems=items.length
        ? items.map(it=>`<div class="order-history-detail-row"><span><b>${Number(it.cantidad||0).toLocaleString('es-MX')} pza(s)</b> · ${esc(it.nombre||it.codigo||'Producto')}<br>${esc(it.presentacion||'')}</span><b>${money(Number(it.importe||0)||Number(it.precioUnitario||0)*Number(it.cantidad||0))}</b></div>`).join('')
        : '<div class="order-history-detail-meta">Este pedido fue guardado con una versión anterior. El detalle de productos no quedó almacenado en este dispositivo.</div>';
      const detalleEntrega=o.entrega?.tipo==='DOMICILIO'
        ? `Entrega a domicilio${o.entrega?.direccion?` · ${esc(o.entrega.direccion)}`:''}`
        : `Recoger en sucursal${o.entrega?.fechaEstimada?` · ${esc(o.entrega.fechaEstimada)}`:''}${o.entrega?.horaEstimada?` ${esc(o.entrega.horaEstimada)}`:''}`;
      const total=Number(o.total||0);
      const detalle=abierto?`<div class="order-history-detail"><h3>Detalle del pedido</h3>${detalleItems}<div class="order-history-detail-meta"><b>${esc(detalleEntrega)}</b>${Number(o.pieces||0)?` · ${Number(o.pieces).toLocaleString('es-MX')} pieza(s)`:''}${total?` · Total ${money(total)}`:''}</div></div>`:'';
      return `<div class="order-history-item ${abierto?'open':''}" data-history-order="${esc(o.id)}" role="button" tabindex="0" aria-expanded="${abierto?'true':'false'}"><div><strong>${esc(o.id)}</strong><small>${esc(localOrderDate(o.createdAt))} · ${esc(tipo)}<br>${esc(o.mensaje||'Pedido enviado a la farmacia.')}</small><span class="history-hint">${abierto?'Ocultar detalle':'Ver detalle del pedido'}</span></div><span class="order-status-pill ${esc(estado.toLowerCase().replace(/_/g,'-'))}">${esc(publicOrderStatusLabel(estado))}</span>${detalle}</div>`;
    }).join('');
  }
  function toggleHistoryOrderDetail(id=''){
    state.historyOrderOpenId=state.historyOrderOpenId===id?'':id;
    renderOrderHistory();
  }
'''
if 'data-history-order=' not in s:
    start=s.find('function renderOrderHistory(){')
    end=s.find('function addLocalOrder',start)
    if start<0 or end<0: raise SystemExit('No se pudo ubicar renderOrderHistory')
    s=s[:start]+history_fn+s[end:]

if "toggleHistoryOrderDetail(row.dataset.historyOrder)" not in s:
    old="$('orderHistoryButton').addEventListener('click',openHistory);document.querySelectorAll('[data-close=\"history\"]').forEach(el=>el.addEventListener('click',closeHistory));"
    new=old+"$('orderHistoryList').addEventListener('click',e=>{const row=e.target.closest('[data-history-order]');if(row)toggleHistoryOrderDetail(row.dataset.historyOrder)});$('orderHistoryList').addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('[data-history-order]')){e.preventDefault();toggleHistoryOrderDetail(e.target.dataset.historyOrder)}});"
    if old not in s: raise SystemExit('No se encontró binding de historial')
    s=s.replace(old,new,1)

if 'items:items.map' not in s:
    old="addLocalOrder({id,storeId:state.storeId,token,createdAt:creadoEn,estado:'NUEVO',mensaje:statusPayload.mensaje,entrega:{tipo:entrega.tipo,fechaEstimada:entrega.fechaEstimada||'',horaEstimada:entrega.horaEstimada||'',direccion:entrega.direccion||''},total:Math.round(totals.total*100)/100})"
    new="addLocalOrder({id,storeId:state.storeId,token,createdAt:creadoEn,estado:'NUEVO',mensaje:statusPayload.mensaje,entrega:{tipo:entrega.tipo,fechaEstimada:entrega.fechaEstimada||'',horaEstimada:entrega.horaEstimada||'',direccion:entrega.direccion||''},items:items.map(it=>({codigo:it.codigo,nombre:it.nombre,presentacion:it.presentacion,cantidad:Number(it.cantidad||0),precioUnitario:Number(it.precioUnitario||0),importe:Number(it.importe||0)})),pieces:totals.pieces,total:Math.round(totals.total*100)/100})"
    if old not in s: raise SystemExit('No se encontró addLocalOrder esperado')
    s=s.replace(old,new,1)

for needle in ['AGOTADO · TEMPORALMENTE SIN EXISTENCIAS','data-history-order','Detalle del pedido','items:items.map']:
    if needle not in s: raise SystemExit('Faltó aplicar '+needle)
p.write_text(s,encoding='utf-8')
