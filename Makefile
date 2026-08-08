.PHONY: up down build logs shell-backend shell-db migrate revision restart

# Dev
up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

restart:
	docker-compose restart $(s)

# Backend shell
shell-backend:
	docker-compose exec backend bash

# DB shell (psql)
shell-db:
	docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

# Alembic migrations
migrate:
	docker-compose exec backend alembic upgrade head

revision:
	docker-compose exec backend alembic revision --autogenerate -m "$(m)"

# Celery: manually trigger tasks
sync-seasons:
	docker-compose exec collector celery -A celery_app call tasks.sync_seasons.sync_seasons

sync-round:
	docker-compose exec collector celery -A celery_app call tasks.sync_matches.sync_current_round

sync-squads:
	docker-compose exec collector celery -A celery_app call tasks.sync_squads.sync_all_squads

set-prices:
	docker-compose exec -T collector python -c "from tasks.set_prices import set_player_prices; set_player_prices()"

# Prod
up-prod:
	docker-compose -f docker-compose.prod.yml up -d

down-prod:
	docker-compose -f docker-compose.prod.yml down
