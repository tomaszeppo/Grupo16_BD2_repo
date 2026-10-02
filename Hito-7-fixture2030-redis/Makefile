.PHONY: up down restart status ping demo evidence measure clean

up:
	mkdir -p ~/docker/data/redis
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

status:
	docker compose ps

ping:
	docker compose exec -T redis redis-cli PING

demo:
	bash scripts/run_all.sh

evidence:
	bash scripts/capturar_evidencia.sh

measure:
	bash scripts/medir.sh

clean:
	bash scripts/limpieza.sh
