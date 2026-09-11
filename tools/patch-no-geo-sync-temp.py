from pathlib import Path
import re
p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

s=s.replace('<div><small>CONEXIÓN AUTOMÁTICA</small><h2 id="connectionTitle">Mi Farmacia</h2><p>Datos publicados desde Macroxel FarmaControl. No son editables desde este visor.</p></div>', '<div><small>CONEXIÓN AUTOMÁTICA</small><h2 id="connectionTitle">Mi Farmacia</h2></div>')
s=s.replace('      <p class="connection-note">La conexión se recibe desde la configuración central generada por el sistema principal. Este visor no almacena ni muestra direcciones de Firebase.</p>\n','')

s=re.sub(r'<div id="deliveryRadiusNotice" class="delivery-radius-notice warning">.*?</div>\s*(?=<label>Dirección de entrega)', '<div id="deliveryRadiusNotice" class="delivery-radius-notice warning"><strong>🚚 Entrega a domicilio cerca del establecimiento</strong><span>La entrega a domicilio se realiza únicamente en zonas cercanas a la farmacia, aproximadamente dentro de 1 km.</span></div>\n          ', s, count=1, flags=re.S)

for line in [
"  const STORAGE_LOCATION_PERMISSION = 'mi_farmacia:location_permission:v1';\n",
"  const MAX_DELIVERY_DISTANCE_KM = 1;\n",
"  const LOCATION_ACCURACY_LIMIT_M = 350;\n",
"  const LOCATION_CACHE_MS = 3 * 60 * 1000;\n",
]: s=s.replace(line,'')
s=s.replace("historyOrderOpenId:'', deviceLocation:null, deviceLocationAt:0, deliveryLocationCheck:null }", "historyOrderOpenId:'' }")

s=re.sub(r'  function coordinatesFromMapsUrl\(raw\)\{.*?(?=  function refreshStoreAvailability\()', '', s, count=1, flags=re.S)
s=s.replace("toast('Datos listos para tu pedido');requestLocationOnActivation().catch(()=>{});", "toast('Datos listos para tu pedido');")

s=re.sub(r'''  function deliveryType\(\)\{return document\.querySelector\('input\[name="deliveryType"\]:checked'\)\?\.value\|\|'RECOGER_SUCURSAL'\}\n  function refreshDeliveryFields\(\)\{.*?\n  function hasActiveLocalOrder\(\)''', '''  function deliveryType(){return document.querySelector('input[name="deliveryType"]:checked')?.value||'RECOGER_SUCURSAL'}
  function refreshDeliveryFields(){const home=deliveryType()==='DOMICILIO';$('pickupFields').hidden=home;$('homeDeliveryFields').hidden=!home;if(!home)$('checkoutMessage').textContent='';}
  function clearPrivateCustomerData(){for(const id of ['customerName','customerPhone','customerNote','deliveryAddress']){const el=$(id);if(el)el.value='';}clearFacade();}
  function hasActiveLocalOrder()''', s, count=1, flags=re.S)

s=re.sub(r"    let verificacionUbicacion=null;if\(tipo==='DOMICILIO'\)\{verificacionUbicacion=await ensureDeliveryLocation\(\{force:true\}\);if\(!verificacionUbicacion\.ok\)\{.*?\}\}\n", '', s, count=1, flags=re.S)
s=re.sub(r"    let verificacionUbicacion=null;\n    if\(tipo==='DOMICILIO'\)\{verificacionUbicacion=await ensureDeliveryLocation\(\{force:true\}\);if\(!verificacionUbicacion\.ok\)\{.*?\}\}\n", '', s, count=1, flags=re.S)
s=re.sub(r"const entregaPrivada=tipo==='DOMICILIO'\?\{\.\.\.entrega,validacionUbicacion:\{.*?\}\}:entrega;const contenidoCifrado=await encryptOrderContent\(\{cliente:\{nombre:name,telefono:phone\},observaciones:note,entrega:entregaPrivada,", "const contenidoCifrado=await encryptOrderContent({cliente:{nombre:name,telefono:phone},observaciones:note,entrega,", s, count=1, flags=re.S)

s=s.replace("$('deliveryPickup').addEventListener('change',onDeliveryTypeChanged);$('deliveryHome').addEventListener('change',onDeliveryTypeChanged);$('validateDeliveryLocation')?.addEventListener('click',()=>ensureDeliveryLocation({force:true}));", "$('deliveryPickup').addEventListener('change',refreshDeliveryFields);$('deliveryHome').addEventListener('change',refreshDeliveryFields);")
s=s.replace("      if($('welcomeModal')?.hidden) setTimeout(()=>requestLocationOnActivation().catch(()=>{}),700);\n",'')

old="""      const [tiendaResultado,metaResultado]=await Promise.allSettled([tiendaPromise,metaPromise]);
      if(metaResultado.status!=='fulfilled') throw metaResultado.reason;
      if(tiendaResultado.status!=='fulfilled') throw tiendaResultado.reason;
      const meta=metaResultado.value||{};"""
new="""      const [tiendaResultado,metaResultado]=await Promise.allSettled([tiendaPromise,metaPromise]);
      if(tiendaResultado.status!=='fulfilled') throw tiendaResultado.reason;
      const meta=metaResultado.status==='fulfilled'?(metaResultado.value||{}):{};"""
if old in s: s=s.replace(old,new,1)
s=s.replace('const FIREBASE_CATALOG_TIMEOUT_MS = 7000;', 'const FIREBASE_CATALOG_TIMEOUT_MS = 15000;')
s=s.replace('single-file-v1.6.2-fast-bootstrap-v1.7.1-runtime-fixed-orders-status-delivery', 'single-file-v1.9.0-no-geolocation-catalog-recovery')

bad=['navigator.geolocation','requestLocationOnActivation','validateDeliveryLocation','ensureDeliveryLocation','Datos publicados desde Macroxel FarmaControl. No son editables desde este visor.','La conexión se recibe desde la configuración central generada por el sistema principal. Este visor no almacena ni muestra direcciones de Firebase.']
for x in bad:
    if x in s: raise SystemExit('Aún aparece: '+x)
if 'aproximadamente dentro de 1 km' not in s: raise SystemExit('Falta aviso de cercanía')
if "metaResultado.status==='fulfilled'" not in s: raise SystemExit('Falta recuperación de meta')
p.write_text(s,encoding='utf-8')
print('OK',len(s))
