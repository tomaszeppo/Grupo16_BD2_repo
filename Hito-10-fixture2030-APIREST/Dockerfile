FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt requirements-drivers.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-drivers.txt
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
