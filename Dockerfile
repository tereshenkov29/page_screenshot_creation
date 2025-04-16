# Используем официальный Python-образ
FROM python:3.11-slim

# Обновим apt и установим зависимости для Playwright
RUN apt-get update && apt-get install -y \
    curl wget gnupg unzip fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libxss1 libasound2 libxshmfence1 libgbm1 libgtk-3-0 libdrm2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Создадим рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright + Chromium
RUN pip install playwright && playwright install chromium

# Экспонируем порт Flask-приложения
EXPOSE 5000

# Запуск Flask
CMD ["python", "app.py"]
