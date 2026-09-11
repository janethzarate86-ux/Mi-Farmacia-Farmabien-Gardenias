from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

if 'id="orderProgressPanel"' in s:
    raise SystemExit('El seguimiento ya está aplicado')

s=s.replace('.header-actions{display:flex;align-items:center;gap:8px}', '.header-actions{display:flex;align-items:center;gap:8px;position:relative}', 1)

anchor='.order-status-pill.nuevo{background:#e3f4ff;color:#075f9a}'
css='''\n.order-progress-panel{position:absolute;right:0;top:calc(100% + 10px);width:min(365px,calc(100vw - 20px));border:1px solid #cfe0ed;border-radius:17px;background:rgba(255,255,255,.98);box-shadow:0 18px 45px rgba(7,59,111,.2);padding:12px 13px;color:#31475b;cursor:pointer;backdrop-filter:blur(14px);z-index:65}.order-progress-panel[hidden]{display:none!important}.order-progress-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.order-progress-title{min-width:0}.order-progress-title strong{display:block;color:var(--navy);font-size:.72rem}.order-progress-title small{display:block;margin-top:2px;color:#7a8999;font-size:.57rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.order-progress-badge{flex:0 0 auto;border-radius:999px;padding:5px 8px;background:#e3f4ff;color:#075f9a;font-size:.56rem;font-weight:950;white-space:nowrap}.order-progress-badge.en-proceso{background:#fff4d8;color:#8b5c00}.order-progress-badge.surtido{background:#e2f7ec;color:#087653}.order-progress-badge.cancelado{background:#fdebed;color:#aa203b}.order-progress-message{margin-top:8px;font-size:.65rem;font-weight:800;line-height:1.35;color:#53697e}.order-progress-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:10px}.order-progress-step{position:relative;padding-top:12px;text-align:center;color:#8a98a7;font-size:.51rem;font-weight:900;line-height:1.15}.order-progress-step::before{content:'';position:absolute;top:2px;left:50%;width:8px;height:8px;transform:translateX(-50%);border-radius:50%;background:#d7e1ea;box-shadow:0 0 0 3px #f4f7fa}.order-progress-step:not(:last-child)::after{content:'';position:absolute;top:5px;left:calc(50% + 7px);width:calc(100% - 14px);height:2px;background:#e2e8ee}.order-progress-step.done,.order-progress-step.current{color:#0a5b95}.order-progress-step.done::before,.order-progress-step.current::before{background:#1681c4;box-shadow:0 0 0 3px #dff1fc}.order-progress-step.done:not(:last-child)::after{background:#70b9e4}.order-progress-step.current::before{animation:orderPulse 1.4s ease-in-out infinite}.order-progress-panel.terminal .order-progress-step{color:#087653}.order-progress-panel.terminal .order-progress-step::before{background:#17a36d;box-shadow:0 0 0 3px #dff5eb}.order-progress-panel.terminal .order-progress-step:not(:last-child)::after{background:#74cdaa}.order-progress-panel.cancelled .order-progress-steps{display:none}.order-progress-panel.cancelled .order-progress-message{color:#9d2940}@keyframes orderPulse{0%,100%{box-shadow:0 0 0 3px #dff1fc}50%{box-shadow:0 0 0 7px rgba(22,129,196,.12)}}@media(max-width:520px){.order-progress-panel{right:-1px;top:calc(100% + 8px);width:min(350px,calc(100vw - 12px));padding:11px}.order-progress-message{font-size:.63rem}}'''
if anchor not in s: raise SystemExit('CSS anchor not found')
s=s.replace(anchor,anchor+css,1)

cart='      <button id="cartButton" class="cart-button" type="button" aria-label="Abrir carrito">🛒<b id="cartCount">0</b></button>'
replacement=cart+'\n      <section id="orderProgressPanel" class="order-progress-panel" role="button" tabindex="0" aria-live="polite" aria-label="Seguimiento del pedido" hidden></section>'
if cart not in s: raise SystemExit('cart not found')
s=s.replace(cart,replacement,1)

const='  const ORDER_STATUS_POLL_MS = 15000;'
if const not in s: raise SystemExit('poll const not found')
s=s.replace(const,const+'\n  const ORDER_PROGRESS_TTL_MS = 10 * 60 * 1000;',1)

old="  function publicOrderStatusLabel(estado=''){const e=text(estado||'NUEVO').toUpperCase();return e==='EN_PROCESO'?'SURTIENDO':e.replace(/_/g,' ')}"
new="  function publicOrderStatusLabel(estado=''){const e=text(estado||'NUEVO').toUpperCase();if(e==='NUEVO')return 'ENVIADO A SUCURSAL';if(e==='EN_PROCESO')return 'SURTIENDO PEDIDO';if(e==='SURTIDO')return 'PEDIDO SURTIDO';if(e==='CANCELADO')return 'PEDIDO CANCELADO';return e.replace(/_/g,' ')}"
if old not in s: raise SystemExit('status mapper not found')
s=s.replace(old,new,1)

voice="  function orderVoiceText(estado=''){"
funcs=r'''  function orderTerminalTime(order){
    const raw=order?.canceladoEn||order?.surtidoEn||order?.updatedAt||order?.createdAt||'';
    const t=new Date(raw).getTime();return Number.isFinite(t)?t:0;
  }
  function visibleOrderProgress(){
    const now=Date.now();
    return localOrders().find(o=>{
      const e=text(o?.estado||'NUEVO').toUpperCase();
      if(!['SURTIDO','CANCELADO'].includes(e))return true;
      const t=orderTerminalTime(o);return !!t&&(now-t)<ORDER_PROGRESS_TTL_MS;
    })||null;
  }
  function renderOrderProgress(){
    const panel=$('orderProgressPanel');if(!panel)return;
    const o=visibleOrderProgress();if(!o){panel.hidden=true;panel.innerHTML='';panel.className='order-progress-panel';return}
    const e=text(o.estado||'NUEVO').toUpperCase();
    const terminal=e==='SURTIDO',cancelled=e==='CANCELADO';
    const step=e==='NUEVO'?1:e==='EN_PROCESO'?2:e==='SURTIDO'?3:0;
    const mensaje=e==='NUEVO'?'Tu pedido fue enviado a la sucursal.':e==='EN_PROCESO'?'La farmacia está surtiendo tu pedido.':e==='SURTIDO'?'Tu pedido ya fue surtido.':e==='CANCELADO'?'Tu pedido fue cancelado por la farmacia.':(o.mensaje||'Seguimiento del pedido.');
    const steps=[['Enviado','a sucursal'],['Surtiendo','pedido'],['Pedido','surtido']].map((parts,i)=>{const n=i+1;const cls=terminal?'done':n<step?'done':n===step?'current':'';return `<div class="order-progress-step ${cls}">${parts[0]}<br>${parts[1]}</div>`}).join('');
    panel.className=`order-progress-panel${terminal?' terminal':''}${cancelled?' cancelled':''}`;
    panel.innerHTML=`<div class="order-progress-top"><div class="order-progress-title"><strong>Seguimiento de tu pedido</strong><small>${esc(o.id||'')}</small></div><span class="order-progress-badge ${esc(e.toLowerCase().replace(/_/g,'-'))}">${esc(publicOrderStatusLabel(e))}</span></div><div class="order-progress-message">${esc(mensaje)}</div><div class="order-progress-steps">${steps}</div>`;
    panel.hidden=false;
  }
'''
if voice not in s: raise SystemExit('voice anchor not found')
s=s.replace(voice,funcs+voice,1)
s=s.replace("if(e==='EN_PROCESO')return 'Tu pedido se está surtiendo. La farmacia ya está preparando tus productos.';", "if(e==='EN_PROCESO')return 'Surtiendo pedido. La farmacia ya está preparando tus productos.';",1)
s=s.replace("if(e==='SURTIDO')return 'Pedido surtido, favor de estar atento en el punto de encuentro.';", "if(e==='SURTIDO')return 'Pedido surtido.';",1)

old_add="  function addLocalOrder(order){const rows=localOrders().filter(o=>o.id!==order.id);rows.unshift(order);saveLocalOrders(rows);renderOrderHistory()}"
if old_add not in s: raise SystemExit('addLocalOrder not found')
s=s.replace(old_add,"  function addLocalOrder(order){const rows=localOrders().filter(o=>o.id!==order.id);rows.unshift(order);saveLocalOrders(rows);renderOrderHistory();renderOrderProgress()}",1)

frag="o.estado=next;o.mensaje=text(remote.mensaje)||o.mensaje;o.updatedAt=remote.actualizadoEn||nowISO();if(next!==before){"
if frag not in s: raise SystemExit('refresh fragment not found')
s=s.replace(frag,"o.estado=next;o.mensaje=text(remote.mensaje)||o.mensaje;o.updatedAt=remote.actualizadoEn||nowISO();if(remote.surtidoEn)o.surtidoEn=remote.surtidoEn;if(remote.canceladoEn)o.canceladoEn=remote.canceladoEn;if(next!==before){",1)
s=s.replace("    }finally{state.orderStatusBusy=false;if(changed)saveLocalOrders(rows);renderOrderHistory()}","    }finally{state.orderStatusBusy=false;if(changed)saveLocalOrders(rows);renderOrderHistory();renderOrderProgress()}",1)
s=s.replace("mensaje:'Tu pedido fue recibido por la farmacia.'","mensaje:'Pedido enviado a sucursal.'",1)

bind="    $('orderHistoryButton').addEventListener('click',openHistory);"
if bind not in s: raise SystemExit('bind not found')
s=s.replace(bind,"    $('orderProgressPanel').addEventListener('click',openHistory);$('orderProgressPanel').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openHistory()}});\n"+bind,1)

init="    loadCart();bind();renderOrderHistory();refreshNotificationButton();refreshConnectionInfo();showWelcomeIfNeeded();"
if init not in s: raise SystemExit('init not found')
s=s.replace(init,"    loadCart();bind();renderOrderHistory();renderOrderProgress();refreshNotificationButton();refreshConnectionInfo();showWelcomeIfNeeded();",1)

interval="      setInterval(()=>{if(navigator.onLine)refreshOrderStatuses()},ORDER_STATUS_POLL_MS);"
if interval not in s: raise SystemExit('interval not found')
s=s.replace(interval,interval+'\n      setInterval(renderOrderProgress,30000);',1)

p.write_text(s,encoding='utf-8')
