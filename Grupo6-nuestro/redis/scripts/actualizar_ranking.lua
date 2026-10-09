-- actualizar_ranking.lua
-- Actualiza de forma atomica el puntaje y la antelacion acumulada de un
-- usuario, y recalcula en el mismo paso el score combinado del ranking.
-- Se ejecuta como una unidad indivisible: Redis no intercala ninguna otra
-- operacion en el medio, sin importar cuantas actualizaciones concurrentes
-- lleguen para el mismo usuario o para usuarios distintos.
--
-- KEYS[1] = hash del usuario (ranking:publico:usuario:{id})
-- KEYS[2] = ZSET del ranking (ranking:publico)
-- ARGV[1] = usuario_id
-- ARGV[2] = delta de puntos (puede ser negativo, por si se corrige un resultado)
-- ARGV[3] = delta de antelacion en minutos (siempre positivo)
-- ARGV[4] = cota superior usada para normalizar la antelacion (10000000)
-- ARGV[5] = timestamp de la actualizacion (ISO 8601)
--
-- Devuelve: {puntos_totales, antelacion_total, score_final}

local hash_key = KEYS[1]
local zset_key = KEYS[2]
local usuario_id = ARGV[1]
local delta_puntos = tonumber(ARGV[2])
local delta_antelacion = tonumber(ARGV[3])
local antelacion_max = tonumber(ARGV[4])

local puntos = redis.call('HINCRBY', hash_key, 'puntos', delta_puntos)
local antelacion = redis.call('HINCRBYFLOAT', hash_key, 'antelacion_total', delta_antelacion)
redis.call('HSET', hash_key, 'actualizado_en', ARGV[5])

local score = tonumber(puntos) + (tonumber(antelacion) / antelacion_max)
redis.call('ZADD', zset_key, score, usuario_id)

return {puntos, antelacion, tostring(score)}
