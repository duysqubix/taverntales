# justfile

# By default, just uses sh unless overridden, but let's be explicit:
set shell := ["bash", "-c"]

branch := `git rev-parse --abbrev-ref HEAD`
commit-and-push: make-commitmsg push

make-commitmsg:
  git diff --staged | sgpt --role gitcommit | tee /tmp/.commitmsg 
  git commit -F /tmp/.commitmsg

push: 
  git push origin {{branch}}

run:
    poetry run python main.py

# Upgrades your database to the latest Alembic migration.
migrate:
    poetry run python manage.py migrate

# Creates a new Alembic migration revision with a custom message.
# Usage: just revision "Some descriptive message"
makemigrations:
    poetry run python manage.py makemigrations db

