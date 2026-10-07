FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies first, so this layer only rebuilds when they actually change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV SERVER_PORT=8001
EXPOSE ${SERVER_PORT}

# Apply pending migrations, then start a real WSGI server (not flask run's dev server) —
# see ../docs/deployment.md.
CMD ["sh", "-c", "uv run flask --app app.app db upgrade && exec uv run gunicorn --bind 0.0.0.0:${SERVER_PORT} 'app.app:create_app()'"]
