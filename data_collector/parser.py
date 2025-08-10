import re
import io
import json
import requests
from pathlib import Path
from pypdf import PdfReader
from bs4 import BeautifulSoup

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

        return parse_curriculum_text(pdf_file)

    except requests.RequestException as e:
        print(f"Error fetching or parsing PDF for program_id {program_id}: {e}")
        return []


def parse_curriculum_text(pdf_file) -> list:
    """
    Извлекает список дисциплин из сырого текста PDF.
    Это самая хрупкая часть, т.к. зависит от формата PDF.
    """

    reader = PdfReader(pdf_file)
    disciplines = []
    current_block = None
    current_semester = None

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.split("\n")
        for line in lines:
            line = line.strip()

            intensity_hour = None
            intensity_ze = None

            if not line:
                continue

            if "Блок" in line:
                current_block = line
                continue

            splitted_line = line.split()

            # Определение семестра (цифра в начале строки или отдельно)
            if splitted_line[0].isdigit():
                current_semester = splitted_line[0]

            # Определяем Трудоемкость в з.е. и в час
            if splitted_line[-2].isdigit():
                intensity_ze = splitted_line[-2]

            if splitted_line[-1].isdigit():
                intensity_hour = splitted_line[-1]

            # Пропускаем строки с трудоемкостью и пустые/служебные строки
            if "Трудоемкость" in line or line.replace(" ", "").isdigit():
                continue

            if current_semester and current_block and line:
                # Убираем номер семестра из названия дисциплины (если есть)
                discipline_name = line.replace(current_semester, "").strip()
                if intensity_hour:
                    discipline_name = (
                        discipline_name.replace(intensity_hour, "").strip()
                    )
                
                if intensity_ze:
                    discipline_name = (
                        discipline_name.replace(intensity_ze, "").strip()
                    )
                if not discipline_name.startswith(
                    "Обязательные дисциплины"
                ) and not discipline_name.startswith("Пул выборных дисциплин"):
                    disciplines.append(
                        {
                            "Дисциплина": discipline_name,
                            "Тип": current_block,
                            "Семестр": current_semester,
                            "Трудоемкость в часах": intensity_hour,
                            "Трудоемкость в з.е.": intensity_ze,
                        }
                    )

    return disciplines


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
