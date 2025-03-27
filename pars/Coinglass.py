import asyncio
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException,
    StaleElementReferenceException, WebDriverException
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def extract_table_data(table):
    """ Извлекает данные из таблицы и возвращает словарь {data[1]: data[8]} """
    extracted_data = {}

    try:
        rows = table.find_elements(By.TAG_NAME, "tr")

        for row in rows[1:]:  # Пропускаем заголовок
            cols = row.find_elements(By.TAG_NAME, "td")
            data = [col.text.strip() for col in cols]
            if len(data) > 8 and data[1] and data[8]:  # Проверяем, что есть нужные данные
                extracted_data[data[2]] = data[8]

    except Exception as e:
        print(f"Ошибка при извлечении данных из таблицы: {e}")

    return extracted_data


async def get_coinglass():
    """ Основная функция парсинга """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск без отображения окна браузера

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except WebDriverException as e:
        print(f"Ошибка при запуске WebDriver: {e}")
        return {}

    try:
        driver.get("https://www.coinglass.com/ru")
        wait = WebDriverWait(driver, 20)
        await asyncio.sleep(2)

        # Закрытие всплывающего окна
        try:
            close_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fc-close.fc-icon-button"))
            )
            await asyncio.to_thread(close_button.click)
        except (TimeoutException, NoSuchElementException):
            print("Всплывающее окно не появилось или уже закрыто.")
        except ElementClickInterceptedException:
            print("Не удалось кликнуть на кнопку закрытия.")

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Найти кнопку и кликнуть
        try:
            buttons = wait.until(lambda d: d.find_elements(By.CLASS_NAME, "MuiSelect-button"))
            if len(buttons) > 1:
                wait.until(EC.element_to_be_clickable(buttons[1])).click()
            else:
                print("Второй элемент не найден!")
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Ошибка при поиске или клике по кнопке выбора количества строк: {e}")

        # Выбрать "100"
        try:
            option_100 = driver.find_element(By.XPATH, "//li[text()='100']")
            actions = ActionChains(driver)
            actions.move_to_element(option_100).click().perform()
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Ошибка при выборе опции '100': {e}")

        all_data = {}  # Словарь для хранения данных

        page_num = 1
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            try:
                table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ant-table-wrapper")))
                page_data = extract_table_data(table)
                all_data.update(page_data)  # Добавляем данные в общий словарь
            except TimeoutException:
                print("Ошибка: таблица не найдена!")
            if page_num > 6:
                break  # Если достигнута последняя страница, прекращаем парсинг
            try:
                page_next = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, f"rc-pagination-item-{page_num}"))
                )
                page_num += 1
                page_next.click()
                await asyncio.sleep(2)
            except TimeoutException:
                print(f"Пагинация завершена: элемент rc-pagination-item-{page_num} не найден.")
                break
            except (NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException):
                print(f"Ошибка при попытке нажать на страницу {page_num}. Прекращаем парсинг.")
                break

    except Exception as e:
        print(f"Неизвестная ошибка во время работы скрипта: {e}")

    finally:
        driver.quit()

    return all_data  # Возвращаем словарь