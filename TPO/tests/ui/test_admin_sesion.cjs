const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const almacenes = new Map([['admin_clave', 'clave']]);
const storage = { getItem: k => almacenes.get(k) || null, setItem: (k,v) => almacenes.set(k,v), removeItem: k => almacenes.delete(k) };
const elementos = new Map();
function elemento(id) {
  if (!elementos.has(id)) {
    const item = { id, _html:'', hidden:false, isConnected:true, botones:[], addEventListener(){}, focus(){},
      querySelectorAll(){return this.botones},
      set innerHTML(value) {
        this._html = value;
        this.botones = [...value.matchAll(/data-tabla="([^"]+)"/g)].map(m => ({dataset:{tabla:m[1]},
          addEventListener(_evento, accion){this.accion=accion}, setAttribute(_clave, valor){this.pressed=valor}}));
      }, get innerHTML(){return this._html} };
    elementos.set(id, item);
  }
  return elementos.get(id);
}
const document = {getElementById: elemento, querySelectorAll: () => [], querySelector: () => null};
const respuestas = {
  '/administracion/acceso': {autorizado:true},
  '/administracion/usuario-prueba': {usuario:{id:'U0000121',nombre:'Administrador de prueba',pais:'ARG'},prode:{id:'PR-70716a12'}},
  '/usuarios/U0000121/prodes': {fuente:'mongodb',prodes:[{id:'PR-70716a12',nombre:'Grupo X',codigo:'ADC801C9',integrantes:['U0000121']},{id:'PR-11111111',nombre:'Amigos',codigo:'ABCD1234',integrantes:['U0000121']}]},
  '/prodes/PR-70716a12/tabla': {fuente:'redis',prode:{nombre:'Grupo X'},tabla:[{puesto:1,usuario_id:'U0000121',nombre:'Administrador',puntos:3,exactos:1,tiempo_seg:0}]},
  '/prodes/PR-11111111/tabla': {fuente:'redis',prode:{nombre:'Amigos'},tabla:[{puesto:1,usuario_id:'U0000121',nombre:'Administrador',puntos:3,exactos:1,tiempo_seg:0}]},
  '/health/dependencias': {mongodb:{estado:'ok'},neo4j:{estado:'ok'},calendario:{cargado:false}}
};
const ctx = {document, localStorage:storage, sessionStorage:{getItem:()=>null,removeItem(){}}, location:{hash:'#/prodes'},
  window:{scrollTo(){},addEventListener(){}}, setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){},
  fetch: async url => ({ok:true,status:200,json:async()=>respuestas[url] || {}}), console};
vm.createContext(ctx);
const codigo=fs.readFileSync('ui/app.js','utf8').split('window.addEventListener("hashchange", navegar);')[0];
vm.runInContext(codigo,ctx);
(async()=>{
  await vm.runInContext('navegar()',ctx);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(JSON.parse(almacenes.get('usuario')).id,'U0000121');
  assert.match(elemento('contenido').innerHTML,/Mis prodes/);
  assert.doesNotMatch(elemento('contenido').innerHTML,/Elegí un usuario/);
  assert.match(elemento('mios').innerHTML,/Grupo X/);
  assert.match(elemento('tabla').innerHTML,/Administrador/);
  await elemento('mios').botones[1].accion();
  assert.match(elemento('tabla').innerHTML,/Amigos/);
  assert.equal(elemento('mios').botones[1].pressed, 'true');
  respuestas['/usuarios/U0000121/prodes'] = {fuente:'mongodb', prodes:[]};
  await vm.runInContext('navegar()',ctx);
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(elemento('mios').innerHTML,/Todavía no tenés grupos/);
  assert.match(elemento('tabla').innerHTML,/Cuando formes parte/);
  console.log('Sesión administrativa anterior recuperada y Grupo X visible');
})().catch(e=>{console.error(e);process.exitCode=1});
