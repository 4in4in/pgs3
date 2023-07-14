
activate:
	. .venv/bin/activate

up:
	docker-compose --env-file .env up -d

test:
	python -m pytest tests/

clean:
	sudo rm -rf volumes/postgresql/pgdata

psql:
	docker exec -it s3-postgresql psql -d template1

run:
	uvicorn app.main:app

repo-test:
	docker exec -it s3-postgresql psql -d template1 -c "create database test"
	POSTGRES_DB=test alembic upgrade head
	POSTGRES_DB=test python -m pytest tests/test_repo.py
	docker exec -it s3-postgresql psql -d template1 -c "drop database test"
