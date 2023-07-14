
activate:
	. .venv/bin/activate

up:
	docker-compose --env-file .env up -d

test:
	python -m pytest tests/

clean:
	sudo rm -rf volumes/postgresql/pgdata

psql:
	docker exec -it s3-postgresql psql

run:
	uvicorn app.main:app