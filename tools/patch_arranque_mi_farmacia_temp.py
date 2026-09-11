from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')
old="""      if(!state.firebaseUrl||!state.storeId)throw new Error('La conexión central de Mi Farmacia está incompleta. Genera la carpeta GitHub completa desde Macroxel.');
      await loadCatalog({quiet:!!state.products.length,forceNetwork:true});
"""
new="""      // En modo dinámico el tiendaId se resuelve desde /mi_farmacia/publicacion.
      // No debe exigirse antes de loadCatalog(), porque loadBootstrap lo deja vacío
      // a propósito para evitar anclar el visor a una farmacia fija.
      if(!state.firebaseUrl)throw new Error('La conexión central de Mi Farmacia está incompleta. Genera la carpeta GitHub completa desde Macroxel.');
      await loadCatalog({quiet:!!state.products.length,forceNetwork:true});
"""
if old not in s:
    raise SystemExit('No se encontró el bloque de arranque esperado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
