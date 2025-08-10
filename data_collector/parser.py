import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re
import io
from pypdf import PdfReader

BASE_URLS = [
    "https://abit.itmo.ru/program/master/ai",
    "https://abit.itmo.ru/program/master/ai_product",
]

# Регулярное выражение для поиска ID программы в javascript коде на странице
PROGRAM_ID_PATTERN = re.compile(r'"apiProgram":{"id":(\d+)')


def fetch_page(url: str) -> str:
    """Загружает HTML страницы."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return ""


def fetch_and_parse_pdf(program_id: str) -> list:
    """Скачивает PDF учебного плана и парсит его."""
    pdf_url = f"https://api.itmo.su/constructor-ep/api/v1/static/programs/{program_id}/plan/abit/pdf"
    print(f"[parser] fetching curriculum from {pdf_url}")
    try:
        response = requests.get(pdf_url, timeout=15)
        response.raise_for_status()

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)

        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        return parse_curriculum_text(full_text)

    except requests.RequestException as e:
        print(f"Error fetching or parsing PDF for program_id {program_id}: {e}")
        return []


def parse_curriculum_text(text: str) -> list:
    """
    Извлекает список дисциплин из сырого текста PDF.
    Это самая хрупкая часть, т.к. зависит от формата PDF.
    """
    courses = []
    lines = text.split("\n")

    current_semester = None
    current_type = "Обязательная"  # По умолчанию считаем дисциплину обязательной

    # Ключевые слова-маркеры
    semester_keywords = [f"{i} семестр" for i in range(1, 5)]
    elective_keyword = "Дисциплины по выбору"

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Определяем текущий семестр
        for keyword in semester_keywords:
            if keyword in line.lower():
                current_semester = keyword.split()[0]
                # После смены семестра сбрасываем тип на обязательный
                current_type = "Обязательная"
                break

        # Определяем тип дисциплин
        if elective_keyword.lower() in line.lower():
            current_type = "По выбору"
            continue  # Пропускаем саму строку-заголовок

        # Простая эвристика для определения строки с дисциплиной:
        # Она не является заголовком и часто содержит цифры (часы, з.е.)
        is_course_line = (
            not any(
                kw in line.lower()
                for kw in semester_keywords + [elective_keyword.lower()]
            )
            and "з.е." in line
            and not line.lower().startswith("итого")
        )

        if is_course_line and current_semester:
            # Убираем лишнее из строки (часы, з.е. и т.д.)
            # Этот паттерн может потребовать доработки под конкретный формат
            course_name = re.split(r"\s\d", line)[0].strip()
            # Исключаем артефакты парсинга
            if len(course_name) > 3 and "практика" not in course_name.lower():
                courses.append(
                    {
                        "name": course_name,
                        "semester": int(current_semester),
                        "type": current_type,
                    }
                )

    return courses


def parse_program_page(html: str, program_url: str) -> dict:
    """
    Парсит описание программы и учебный план.
    Возвращает структуру: {title, description, courses: [..]}
    """
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown program"

    description_tag = soup.find(
        "div", class_="AboutProgram_aboutProgram__textWrapper___j1KQ"
    )
    description = (
        (
            description_tag.get_text(separator="\n", strip=True)
            if description_tag
            else ""
        )
        .rstrip("Показать все")
        .strip()
    )

    career_tag = soup.find("div", class_="Career_career__container___st5X")
    career = (
        career_tag.get_text(separator="\n", strip=True) if career_tag else ""
    ).strip()

    program_id_match = PROGRAM_ID_PATTERN.search(html)
    courses = []
    if program_id_match:
        program_id = program_id_match.group(1)
        courses = fetch_and_parse_pdf(program_id)
    else:
        print(f"[parser] Warning: Program ID not found for {program_url}")

    return {
        "title": title,
        "url": program_url,
        "description": description,
        "career": career,
        "courses": courses,
    }


def save_json(data: list, filename: str):
    Path(filename).parent.mkdir(exist_ok=True)
    Path(filename).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    all_data = []
    for url in BASE_URLS:
        print(f"[parser] fetching {url}")
        html = fetch_page(url)
        if html:
            program_data = parse_program_page(html, url)
            all_data.append(program_data)

    save_json(all_data, "data/structured_programs.json")
    print("[parser] Done. Saved to data/structured_programs.json")


if __name__ == "__main__":
    main()
