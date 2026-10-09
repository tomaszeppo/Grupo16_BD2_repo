// 03-load-data.js
// Solo arranca la carga. La logica esta en scripts/cargar-datos.js (montada en
// /scripts dentro del contenedor) para poder reejecutarla despues del primer
// arranque, cosa que los init-scripts no permiten.

load("/scripts/cargar-datos.js");
