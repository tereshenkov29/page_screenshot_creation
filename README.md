# Создание скриншотов страниц

## 📦 Локальный запуск

### ✅ Что делает программа?

- Принимает список ссылок на веб-страницы.
- Делает полноразмерные скриншоты страниц с помощью **Playwright**.
- Загружает скриншоты в **Shared Drive** на Google Drive (если настроен доступ).
- Показывает процесс выполнения через простой веб-интерфейс.

---

### 🧰 Что нужно установить один раз

1. **Python 3.11+**
2. **Google Chrome** (опционально, но рекомендуется)
3. Установить Playwright и Chromium:
   ```bash
   pip install playwright
   playwright install chromium
   ```
4. Установить зависимости проекта:
    ```bash
    pip install -r requirements.txt
    ```
---

### 🗂️ Как подготовить проект
1. Клонировать репозиторий:
    ```bash
    git clone https://github.com/tereshenkov29/page_screenshot_creation.git
    cd page_screenshot_creation
    ```
2. Убедиться, что в корне проекта находятся:
* **credentials.json** – OAuth 2.0 креды Google (скачиваются в Google Cloud Console)
* **token.pickle** – токен авторизации (создаётся автоматически при первом запуске)
3. Создать папку для скриншотов (если не существует):
    ```bash
    mkdir screenshots
    ```
---

### ▶️ Как запустить локально
**В PyCharm:**
Открыть файл app_local.py и нажать ▶️ Run.

**Или в терминале:**
   ```bash
   python app_local.py
   ```
---

### 🌐 Как использовать

1. Открыть файл docs/index_local.html в браузере
(например, в PyCharm: Right click → Open in browser).
2. Вставить список ссылок (по одной на строку).
3. Нажать кнопку "Создать скриншоты".
4. Через 30–60 секунд появится ссылка на папку в Google Drive.

---

### 🛠️ Частые проблемы

* **Ошибка авторизации** - Удалите token.pickle и перезапустите приложение — при следующем запуске авторизация пройдёт 
  заново.
* **Playwright не запускается** - Убедитесь, что установлен Chromium:
    ```bash
    playwright install chromium
    ```
* **Скриншоты не загружаются в Drive** - Проверьте наличие и корректность credentials.json и token.pickle.