import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import zipfile
from docx import Document
import PyPDF2
import shutil

app = Flask(__name__, static_folder='.')

# ===================== НАСТРОЙКИ =====================
XAI_API_KEY = os.environ.get("XAI_API_KEY")
API_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4-fast-reasoning"
MAX_TOKENS = 1900000
OUTPUT_TOKENS = 10000


# Google Drive API Key from environment
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Default folder IDs (user can update these)
FOLDER_IDS = {
    "Декларации": "1ZTDzwp_ywHn8bnpTybfCOG4MvcpblaXn",
    "Стандарты": "1VnlhnmBWvMpIcBJPtdJwlnPku2-_XtTx",
    "FAQ": "1-NrMMZazEkw5N1JvLVo5UuVs62mx97gv",
}

folder_caches = {
    "Декларации": {"doc_cache": "", "processed_files": 0, "file_name_map": {}, "file_id_map": {}, "data_dir": None},
    "Стандарты": {"doc_cache": "", "processed_files": 0, "file_name_map": {}, "file_id_map": {}, "data_dir": None},
    "FAQ": {"doc_cache": "", "processed_files": 0, "file_name_map": {}, "file_id_map": {}, "data_dir": None},
}

BATCH_SIZE = 10
METADATA_FILE = "archive_metadata.json"

# ===================== ПОДДЕРЖИВАЮЩИЕ ФУНКЦИИ =====================

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return "\n".join([p.extract_text() or '' for p in reader.pages])
    except Exception as e:
        return f"Ошибка PDF: {str(e)}"


def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        return f"Ошибка DOCX: {str(e)}"


def has_files_in_dir(data_dir):
    for _, _, files in os.walk(data_dir):
        for fname in files:
            if fname.endswith(".pdf") or fname.endswith(".docx"):
                return True
    return False


def load_cache(folder_name):
    cache_file = f"cache_{folder_name}.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(cache, folder_name):
    cache_file = f"cache_{folder_name}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def delete_old_data(folder_name):
    cache_file = f"cache_{folder_name}.json"
    data_dir = os.path.join(os.getcwd(), f"data_{folder_name}")
    try:
        if os.path.exists(cache_file):
            os.remove(cache_file)
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir, ignore_errors=True)
        folder_caches[folder_name] = {"doc_cache": "", "processed_files": 0,
                                      "file_name_map": {}, "file_id_map": {}, "data_dir": None}
        print(f"🧹 Старые данные очищены для {folder_name}")
    except Exception as e:
        print(f"Ошибка удаления данных {folder_name}: {e}")


# ===================== GOOGLE DRIVE =====================
def download_google_drive_files(file_or_folder_id, folder_name):
    """Пробуем скачать с Google Drive, если не удаётся — создаём локальную папку."""
    cache = folder_caches[folder_name]
    cache["data_dir"] = os.path.join(os.getcwd(), f"data_{folder_name}")
    os.makedirs(cache["data_dir"], exist_ok=True)

    if not GOOGLE_API_KEY:
        print(f"⚠️ Google API ключ не установлен для {folder_name}")
        if not has_files_in_dir(cache["data_dir"]):
            msg = (f"Google API ключ не найден. Установите GOOGLE_API_KEY в Secrets или "
                   f"поместите файлы (.pdf или .docx) в папку '{cache['data_dir']}'.")
            print(msg)
            return False, msg
        else:
            print(f"📁 Используются локальные файлы для {folder_name}.")
            return True, "Используются локальные файлы."

    try:
        service = build('drive', 'v3', developerKey=GOOGLE_API_KEY)
        file_metadata = service.files().get(fileId=file_or_folder_id, fields="mimeType,name").execute()
        mime_type = file_metadata.get("mimeType")
        file_name = file_metadata.get("name")

        if mime_type == "application/vnd.google-apps.folder":
            results = service.files().list(
                q=f"'{file_or_folder_id}' in parents and trashed=false",
                fields="files(id,name,mimeType)"
            ).execute()
            files = results.get("files", [])
            zip_files = [f for f in files if f["name"].lower().endswith(".zip")]
            if not zip_files:
                raise Exception("Нет ZIP-файлов в указанной папке.")
            file = zip_files[0]
            file_id = file["id"]
        elif mime_type == "application/zip":
            file_id = file_or_folder_id
        else:
            raise Exception("ID не является ZIP или папкой.")

        request_obj = service.files().get_media(fileId=file_id)
        zip_path = os.path.join(cache["data_dir"], "archive.zip")
        with io.FileIO(zip_path, "w") as fh:
            downloader = MediaIoBaseDownload(fh, request_obj)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(cache["data_dir"])
        os.remove(zip_path)
        print(f"✅ Успешно загружен архив для {folder_name}")
        return True, "Архив успешно загружен."

    except Exception as e:
        print(f"⚠️ Не удалось скачать файлы для {folder_name}: {e}")
        if not has_files_in_dir(cache["data_dir"]):
            msg = (f"Не удалось загрузить данные для {folder_name}. "
                   f"Создана локальная папка '{cache['data_dir']}'. "
                   f"Пожалуйста, поместите туда файлы (.pdf или .docx).")
            print(msg)
            return False, msg
        else:
            print(f"📁 Используются локальные файлы для {folder_name}.")
            return True, "Используются локальные файлы."


def process_local_folder(folder_name):
    cache = folder_caches[folder_name]
    data_dir = cache["data_dir"]
    if not has_files_in_dir(data_dir):
        return False, f"Нет файлов для {folder_name}."
    cache["doc_cache"] = ""

    for root, _, files in os.walk(data_dir):
        for f in files:
            path = os.path.join(root, f)
            if f.endswith(".pdf"):
                text = extract_text_from_pdf(path)
            elif f.endswith(".docx"):
                text = extract_text_from_docx(path)
            else:
                continue
            cache["doc_cache"] += "\n" + text
            cache["processed_files"] += 1

    save_cache(cache, folder_name)
    return True, f"Обработано {cache['processed_files']} файлов."


# ===================== ИНИЦИАЛИЗАЦИЯ =====================
@app.route('/api/initialize', methods=['POST'])
def initialize():
    for folder_name, folder_id in FOLDER_IDS.items():
        print(f"Инициализация: {folder_name}")
        cache_data = load_cache(folder_name)
        folder_path = os.path.join(os.getcwd(), f"data_{folder_name}")

        if cache_data and has_files_in_dir(folder_path):
            print(f"✅ Используется кэш для {folder_name}")
            folder_caches[folder_name] = cache_data
            continue

        success, msg = download_google_drive_files(folder_id, folder_name)
        if not success:
            return jsonify({"error": msg}), 500

        success, msg = process_local_folder(folder_name)
        if not success:
            return jsonify({"error": msg}), 500

    return jsonify({"message": "Все папки успешно инициализированы."}), 200


# ===================== ПРОВЕРКА ОБНОВЛЕНИЙ =====================
@app.route('/api/check_updates', methods=['POST'])
def check_updates():
    try:
        for folder_name, folder_id in FOLDER_IDS.items():
            delete_old_data(folder_name)
            success, msg = download_google_drive_files(folder_id, folder_name)
            if success:
                success, msg = process_local_folder(folder_name)
        return jsonify({"message": "Обновления успешно проверены и применены."}), 200
    except Exception as e:
        return jsonify({"error": f"Ошибка при проверке обновлений: {str(e)}"}), 500


# ===================== ВОПРОС-ОТВЕТ =====================
@app.route('/api/submit_question', methods=['POST'])
def submit_question():
    data = request.get_json()
    folder_name = data.get("folder")
    question = data.get("question")

    if not question:
        return jsonify({"error": "Введите вопрос"}), 400

    cache = folder_caches.get(folder_name)
    if not cache or not cache["doc_cache"]:
        return jsonify({"error": "Нет данных для поиска"}), 400

    context = cache["doc_cache"]
    max_chars = MAX_TOKENS * 4  # приблизительная длина по токенам
    chunk_size = max_chars
    num_chunks = (len(context) // chunk_size) + 1
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}

    summary = ""
    print(f"🔍 Кэш содержит {len(context)} символов, разделён на {num_chunks} частей")

    # Обработка по чанкам с использованием оригинального промпта
    for i in range(num_chunks):
        start = i * chunk_size
        end = start + chunk_size
        chunk = context[start:end]

        print(f"📖 Обрабатывается часть {i + 1}/{num_chunks} ({len(chunk)} символов)")

        prompt = (
            f"Используя следующий контекст:\n\n{chunk}\n\n"
            f"Ответь на вопрос: {question}. Укажи источники. Информация должна браться из текста находящегося в кэше"
        )

        try:
            resp = requests.post(API_URL, headers=headers, json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": OUTPUT_TOKENS
            })
            resp.raise_for_status()
            part_answer = resp.json()["choices"][0]["message"]["content"]
            summary += f"\n\n=== Часть {i + 1}/{num_chunks} ===\n{part_answer}"
        except Exception as e:
            summary += f"\n\n=== Часть {i + 1}/{num_chunks} ===\nОшибка при обработке: {e}"

    # Финальный сводный ответ (объединение всех частей)
    print("🧠 Формирование финального ответа...")
    try:
        final_prompt = (
            f"Используя ответы из нескольких частей ниже, составь один объединённый ответ "
            f"на вопрос: {question}. Сохрани ссылки на источники и формулировки, "
            f"если они присутствуют.\n\n{summary}"
        )
        final_resp = requests.post(API_URL, headers=headers, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": final_prompt}],
            "max_tokens": OUTPUT_TOKENS
        })
        final_resp.raise_for_status()
        final_answer = final_resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        final_answer = f"Ошибка при финальной обработке: {e}\n\nПромежуточные ответы:\n{summary}"

    return jsonify({"answer": final_answer}), 200


# ===================== ИНТЕРФЕЙС =====================
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/favicon.ico')
def favicon():
    return '', 204


# ===================== СЕРВЕРНЫЙ ЗАПУСК =====================
if __name__ == '__main__':
    print("🚀 Запуск Flask-сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)
