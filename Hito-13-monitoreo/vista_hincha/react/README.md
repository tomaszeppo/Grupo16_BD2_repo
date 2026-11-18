# Vista React en vivo

Desde esta carpeta ejecutar `npm install` y `npm run build`. Iniciar el servidor de la vista según el README del directorio superior y abrir `http://127.0.0.1:8086/react`.

En modo conectado requiere la API del Hito 10 actualizada, las bases y una sesión sembrada. En demostración usa los datos sintéticos del servidor de la vista. El selector de región forma parte de la sesión; el servidor agrega el país al publicar y lo usa para consultar comentarios recientes.

La vista precarga hasta 20 comentarios cada 8 segundos y muestra uno cada 0,5 segundos, conservando hasta 20 visibles. La cola se limita a 40: ante una carga alta muestra una selección reciente, no todos los mensajes. El estado de partido se consulta cada 15 segundos. El minuto y marcador de una simulación continua aún no están disponibles.
