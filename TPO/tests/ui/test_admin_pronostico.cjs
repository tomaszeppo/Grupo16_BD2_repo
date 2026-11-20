const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const datos = new Map([['usuario',JSON.stringify({id:'U0000121',nombre:'Admin',pais:'ARG'})]]);
const storage = {getItem:k=>datos.get(k)||null,setItem:(k,v)=>datos.set(k,v),removeItem:k=>datos.delete(k)};
const elementos = new Map();
function elemento(id) {
  if (!elementos.has(id)) elementos.set(id,{id,innerHTML:'',isConnected:true,querySelectorAll:()=>[],
    querySelector:()=>({addEventListener(){},replaceChildren(){},textContent:''}),addEventListener(){},focus(){}});
  return elementos.get(id);
}
const partido={id:'P-14',estado:'Programado',fecha_hora:'2000-11-23T11:00:00Z',local:{nombre:'Nigeria',codigo:'NGA'},visitante:{nombre:'Egipto',codigo:'EGY'}};
elemento('apartido').value = partido.id;
const ctx={document:{getElementById:elemento,querySelectorAll:()=>[]},localStorage:storage,
 sessionStorage:{getItem:()=>null,removeItem(){}},location:{hash:'#/admin'},window:{scrollTo(){},addEventListener(){}},
 clearInterval(){},setInterval:()=>1,clearTimeout(){},setTimeout:()=>1,console,
 fetch:async url=>({ok:true,status:200,json:async()=>url.startsWith('/partidos/P-14')?{partido,pronosticos_hasta_inicio_real:true}:{pronosticos:[],total:0}})};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('ui/app.js','utf8').split('window.addEventListener("hashchange", navegar);')[0],ctx);
(async()=>{
 await vm.runInContext('operar("P-14")',ctx);
 await new Promise(resolve=>setImmediate(resolve));
 assert.match(elemento('operacion').innerHTML,/id="pronostico"/);
 assert.match(elemento('pronostico').innerHTML,/Guardar pronóstico/);
 assert.match(elemento('pronostico').innerHTML,/Nigeria/);
 assert.match(elemento('pronostico').innerHTML,/Egipto/);
 console.log('Pronóstico visible en administración para Nigeria vs Egipto');
})().catch(e=>{console.error(e);process.exitCode=1});
