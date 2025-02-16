FROM python:3.13-slim

WORKDIR /app

# install uv
RUN pip install uv

# copy project files
COPY . .

# create venv and install deps
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e '.[dev]'

# expose port
EXPOSE 8000

# run app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
