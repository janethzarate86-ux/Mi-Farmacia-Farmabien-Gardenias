from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')
old="""      let productos=cacheValida?cache.productos:null;
      const cacheRevision=cacheValida?Number(cache.revision||0):0;
      const revision=Number(meta.revision||0);
      const baseRevision=Number(meta.baseRevision||revision);
      let usoCache=!!productos;
      if(!productos||cacheRevision<baseRevision){"""
new="""      let productos=cacheValida?cache.productos:null;
      const cacheRevision=cacheValida?Number(cache.revision||0):0;
      const revision=Number(meta.revision||0);
      const baseRevision=Number(meta.baseRevision||revision);
      const cacheTotal=productos&&typeof productos==='object'?Object.keys(productos).length:0;
      const metaTotal=Number(meta.totalProductos||0);
      const cacheIncompleta=!!(productos&&metaTotal>=0&&cacheTotal!==metaTotal);
      let usoCache=!!productos&&!cacheIncompleta;
      if(forceNetwork||cacheIncompleta||!productos||cacheRevision<baseRevision){"""
if old not in s:
    raise SystemExit('No se encontró el bloque de caché del catálogo esperado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
