
init-local:
	export POSTGRES_HOST=localhost

run:
	docker-compose --env-file .env up -d

test:
	python -m pytest tests/

clean:
	sudo rm -rf volumes/postgresql/pgdata

psql:
	docker exec -it s3-postgresql psql