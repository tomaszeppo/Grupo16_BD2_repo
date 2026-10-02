# Ciclo de vida e invalidación

## 1. Ciclo de vida de una sesión

### Crear

1. El usuario completa un login.
2. Se crea `f2030:sesion:{usuario_id}` como Hash.
3. Se asigna `EXPIRE 1800`.
4. La aplicación considera válida la sesión mientras la clave exista, el estado sea `ACTIVA` y el contexto de autenticación corresponda.

### Consultar

La petición usa el `usuario_id` para derivar la clave. Si `HGETALL` encuentra datos, la sesión existe. Si la clave no existe (`TTL = -2`), la aplicación debe tratar la sesión como inexistente y volver al flujo de autenticación.

### Renovar por actividad

Una actividad válida actualiza `ultimo_acceso`, puede incrementar `acciones` y vuelve a aplicar `EXPIRE 1800`. Se agrupan esas acciones con `MULTI/EXEC` para que no exista una ventana en la que se cambie el estado pero no se renueve la vida.

Importante: modificar un campo con `HSET` no renueva por sí mismo el TTL. La renovación es explícita.

### Finalizar

En logout o invalidación de seguridad, se marca brevemente `estado_acceso=CERRADA` para la evidencia y luego se ejecuta `DEL`. La clave deja de estar disponible inmediatamente.

### Expirar

El vencimiento por inactividad lo realiza Redis mediante TTL nativo. No existe un proceso que recorra todas las sesiones periódicamente para detectar las vencidas.

## 2. Política de inactividad

**Duración elegida:** 30 minutos.  
**Renovación:** ante cada actividad autenticada que demuestre que la sesión sigue siendo utilizada.  
**Consecuencia:** si no existe la clave, el usuario debe autenticarse nuevamente.

La elección busca equilibrar una ventana razonable de inactividad para una plataforma de navegación con el crecimiento potencial de 2–3 millones de sesiones simultáneas. En el laboratorio, el TTL de 30 minutos es una regla verificable; no implica que una sesión real siempre sobreviva hasta ese instante porque la presión de memoria puede evictarla antes.

## 3. Caché Cache-Aside

La lectura sigue este flujo:

```text
Aplicación
   │
   ├─ GET f2030:cache:partido:P001:resumen
   │
   ├─ HIT → responde desde Redis
   │
   └─ MISS → consulta fuente de verdad (MongoDB)
                   │
                   └─ SET + EX 30 → responde al usuario
```

### Cache hit

La clave existe: la copia puede devolverse directamente.

### Cache miss

La clave no existe porque nunca se cargó, porque venció por TTL o porque fue eliminada por una invalidación. El consumidor debe consultar la fuente de verdad y luego poblar Redis.

### Invalidación

Cuando cambia el dato de negocio en la fuente de verdad y ese cambio debe verse de inmediato, primero se considera actualizado el dato autoritativo y después se ejecuta `DEL` sobre la copia. Así el siguiente lector no recibe la versión anterior.

### TTL de la caché

Se usa **30 segundos** como límite de permanencia de una copia que no debería vivir indefinidamente. El TTL no reemplaza la invalidación: si un cambio requiere coherencia inmediata, se hace `DEL` antes de que transcurra el TTL.

## 4. Si Redis no está disponible

Redis es una capa de aceleración y estado temporal, no la fuente de verdad del módulo. Si el servidor no responde:

- para una consulta cacheada, la aplicación consulta la fuente de verdad y responde desde allí;
- para una sesión, la plataforma debe aplicar la estrategia de contingencia definida por el sistema de autenticación; este laboratorio no implementa un segundo almacén de sesiones;
- la caída de Redis no convierte una copia caché en autoridad de negocio.

## 5. Diferencia entre expiración e invalidación

- **Expiración:** el producto decidió que la copia deja de ser válida por tiempo.
- **Invalidación:** un cambio de negocio exige dejar obsoleta la copia antes del TTL.

## 6. Diferencia entre expiración y evicción

Una clave puede vencer por TTL o puede ser eliminada antes porque la política de memoria necesita recuperar RAM. Por eso la caché siempre debe ser reconstruible y la aplicación debe contemplar una sesión ausente.
