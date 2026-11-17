#!/bin/bash
# Arma el conjunto de réplicas rs0 y crea el usuario administrador. Se puede correr todas las veces que haga falta.
set -euo pipefail

con_usuario() {
  mongosh --quiet -u "$MONGO_USER" -p "$MONGO_PASSWORD" --authenticationDatabase admin --eval "$1"
}

if con_usuario 'rs.status().ok' >/dev/null 2>&1; then
  echo "El conjunto de réplicas ya estaba armado."
else
  echo "Armando el conjunto de réplicas rs0..."
  mongosh --quiet --eval '
    try { rs.status() } catch (e) {
      rs.initiate({_id: "rs0", members: [
        {_id: 0, host: "mongo1:27017", priority: 2},
        {_id: 1, host: "mongo2:27017", priority: 1},
        {_id: 2, host: "mongo3:27017", priority: 1}
      ]})
    }' >/dev/null 2>&1 || true

  echo "Esperando a que este nodo sea primario..."
  for _ in $(seq 1 60); do
    if [ "$(mongosh --quiet --eval 'db.hello().isWritablePrimary')" = "true" ]; then break; fi
    sleep 1
  done

  echo "Creando el usuario administrador..."
  mongosh --quiet --eval '
    db.getSiblingDB("admin").createUser({
      user: process.env.MONGO_USER, pwd: process.env.MONGO_PASSWORD, roles: [{role: "root", db: "admin"}]
    })' >/dev/null
fi

echo "Esperando primario y dos secundarios..."
for _ in $(seq 1 60); do
  estados=$(con_usuario 'rs.status().members.map(m => m.stateStr).sort().join(",")' 2>/dev/null || true)
  if [ "$estados" = "PRIMARY,SECONDARY,SECONDARY" ]; then
    echo "Listo: $estados"
    exit 0
  fi
  sleep 1
done
echo "El conjunto no quedó completo: ${estados:-sin respuesta}" >&2
exit 1
