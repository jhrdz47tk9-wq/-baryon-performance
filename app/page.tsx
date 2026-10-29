'use client'
import {useState} from 'react'

const fields=[
 ['production_t','Producción anual vendible','t/año','132160'],
 ['planned_h','Tiempo planificado','h',''],
 ['running_h','Tiempo en marcha','h',''],
 ['ideal_t_h','Tasa ideal por grado','t/h',''],
 ['total_t','Producción total del período','t',''],
 ['good_t','Producción conforme del período','t',''],
 ['dry_gain_pp','Mejora de seco en formación','puntos','2'],
 ['transfer','Transferencia formación / prensas','puntos/punto','0.25'],
 ['margin','Margen incremental constante','USD/t','125'],
 ['seal_temp','Temperatura agua de sello','°C','32'],
 ['infiltration','Aire falso / aire útil','%','35'],
 ['noise_pp','Desviación de seco observada','puntos',''],
 ['power_kw','Potencia eléctrica medida','kW',''],
 ['extra_cost','Costo operativo adicional','USD/año',''],
] as const
export default function Performance(){
 const [values,setValues]=useState<Record<string,string>>(Object.fromEntries(fields.map(f=>[f[0],f[3]])))
 const [plant,setPlant]=useState('FPC · MP1')
 const [tab,setTab]=useState('Operación')
 const [risk,setRisk]=useState('PENDIENTE')
 const [source,setSource]=useState('')
 const [message,setMessage]=useState('')
 const [status,setStatus]=useState('Conexión no comprobada')
 const [busy,setBusy]=useState(false)
 const [capture,setCapture]=useState('1')
 const [price,setPrice]=useState('')
 const [freight,setFreight]=useState('')
 const [fx,setFx]=useState('')
 const [evidence,setEvidence]=useState('ASSUMED')
 async function check(){
  setBusy(true);setStatus('Comprobando conexión…')
  try{
   const r=await fetch('/api/baryon/v1/capability-runtime',{cache:'no-store',signal:AbortSignal.timeout(15000)})
   setStatus(r.ok?'Backend accesible; contrato de índices pendiente':r.status===503?'Backend no configurado':r.status===401||r.status===403?'Acceso no autorizado':'Backend no disponible')
  }catch{setStatus('No se pudo comprobar la conexión')}
  finally{setBusy(false)}
 }
 function exportInput(){
  if(!plant.trim()){setMessage('Indica una planta.');return}
  if(evidence==='MEASURED'&&!source.trim()){setMessage('Indica la fuente de las mediciones.');return}
  const inputs:Record<string,number|null>={}
  for(const [k,v] of Object.entries(values)){
   if(v.trim()===''){inputs[k]=null;continue}
   const n=Number(v)
   if(!Number.isFinite(n)||n<0){setMessage('Revisa el campo '+k);return}
   inputs[k]=n
  }
  if(inputs.running_h!==null&&inputs.planned_h!==null&&inputs.running_h>inputs.planned_h){setMessage('Las horas de marcha superan las planificadas.');return}
  if(inputs.good_t!==null&&inputs.total_t!==null&&inputs.good_t>inputs.total_t){setMessage('La producción conforme supera el total.');return}
  const payload={schema:'baryon-performance-intake/0.1-candidate',plant,evidence,source,created_at:new Date().toISOString(),inputs,capture_fraction:Number(capture),external_assumptions:{sale_price:price||null,freight:freight||null,fx:fx||null},risk_review:risk,execution_status:'NOT_EXECUTED',results:{baryon:null,oee:null,ebitda_normalized:null},notes:['Regla 4:1 pendiente de validación FPC','No se ha enviado ni guardado este escenario en Google Cloud']}
  const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}))
  const a=document.createElement('a');a.href=url;a.download='baryon-escenario.json';a.click()
  setTimeout(()=>URL.revokeObjectURL(url),1000);setMessage('Escenario exportado. No se ejecutaron cálculos.')
 }
 return <main>
  <section className="hero">
   <span className="badge warn">ESCENARIO · SIN VALIDACIÓN DE PLANTA</span>
   <h1>BARYON / OEE / EBITDA</h1>
   <p>Del estado de los activos al desempeño operacional y al valor económico.</p>
   <p aria-live="polite">{status}</p>
   <button onClick={check} disabled={busy}>Comprobar conexión</button>
  </section>
  <section className="grid" aria-label="Indicadores">
   {['Índice BARYON','OEE observado','EBITDA normalizado'].map(t=><article className="card" key={t}><h2>{t}</h2><strong style={{fontSize:36}}>—</strong><p>Sin resultado calculado por el backend.</p></article>)}
  </section>
  <div className="toolbar" aria-label="Secciones">{['Operación','Sensibilidad','Factores externos','Evidencia y riesgo'].map(t=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{t}</button>)}</div>
  <section className="card">
   <h2>{tab}</h2>
   <label>Planta / línea <input value={plant} onChange={e=>setPlant(e.target.value)}/></label>
   <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(230px,1fr))',gap:20,marginTop:24}}>
    {fields.filter((f,i)=>tab==='Operación'?i<6:tab==='Sensibilidad'?i>=6: false).map(([k,label,unit])=><label key={k}>{label} <small>({unit})</small><input style={{display:'block',width:'100%',marginTop:8}} type="number" min="0" step="any" value={values[k]} onChange={e=>setValues({...values,[k]:e.target.value})}/></label>)}
   </div>
   {tab==='Sensibilidad'&&<><p>La mejora de seco es una hipótesis. El ruido del proceso puede impedir detectarla. Los modelos se ejecutarán en Google Cloud.</p><label>Fracción de capacidad que puede convertirse en ventas <select value={capture} onChange={e=>setCapture(e.target.value)}><option value="0">0% · sin captura</option><option value=".5">50% · parcial</option><option value="1">100% · escenario máximo</option></select></label></>}
   {tab==='Factores externos'&&<><p>Separar el desempeño a precios constantes del efecto de mercado. Las tasas de interés no se descuentan automáticamente del EBITDA.</p><label>Precio de venta de referencia (USD/t)<input type="number" value={price} onChange={e=>setPrice(e.target.value)}/></label><label>Transporte de referencia (USD/t)<input type="number" value={freight} onChange={e=>setFreight(e.target.value)}/></label><label>Tipo de cambio y moneda de referencia<input value={fx} onChange={e=>setFx(e.target.value)}/></label></>}
   {tab==='Evidencia y riesgo'&&<><label>Clasificación de las entradas <select value={evidence} onChange={e=>setEvidence(e.target.value)}><option value="ASSUMED">Supuestos / escenario</option><option value="MEASURED">Medidos con fuente</option></select></label><label>Fuente y período de medición<textarea value={source} onChange={e=>setSource(e.target.value)} placeholder="Informe, fecha, instrumentos y condiciones"/></label><label>Revisión de seguridad y ambiente <select value={risk} onChange={e=>setRisk(e.target.value)}><option>PENDIENTE</option><option>NO_GO</option><option>REVISADO</option></select></label><p role="status">{risk==='NO_GO'?'NO GO: escenario excluido de recomendaciones operativas. Activar el procedimiento autorizado de planta.':'Registrar criticidad, repuestos, competencias y responsables antes de una prueba de planta.'}</p><p>Esta interfaz no acciona equipos. “Revisado” no sustituye una autorización de planta.</p></>}
  </section>
  <section className="card" style={{marginTop:24}}><h2>Evaluación y trazabilidad</h2><p>Resultados posibles: mejora detectable, inconcluso o evidencia contraria. No confundir ausencia de datos con valor cero.</p><button onClick={exportInput}>Exportar escenario JSON</button><p role="status">{message}</p><p>La ejecución de índices permanece pendiente de conectar un contrato validado en Google Cloud. No se calculan índices propietarios en el navegador.</p></section>
 </main>
}

