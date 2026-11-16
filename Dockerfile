FROM python:3.11-slim
WORKDIR /srv
COPY docs/ .
RUN useradd --system --uid 10001 web
USER web
EXPOSE 8000
CMD ["python", "-m", "http.server", "8000", "--bind", "0.0.0.0"]
