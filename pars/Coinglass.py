import asyncio

from selenium import webdriver
from selenium.common import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


async def get_basketball_matches():
    # Настройка Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск без отображения окна браузера
    # options.add_argument("--disable-gpu")  # Отключаем GPU для работы в headless
    # options.add_argument("--no-sandbox")  # Отключаем sandbox (если это нужно)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://www.coinglass.com/ru")
        wait = WebDriverWait(driver, 20)
        #driver.execute_script("document.body.style.zoom='50%'")  # Масштабируем страницу
        await asyncio.sleep(2)
        close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fc-close.fc-icon-button"))
        )

        # Кликаем на крестик в асинхронном режиме
        await asyncio.to_thread(close_button.click)


        # # Находим первый div с классом ant-table-wrapper (таблица)
        # table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ant-table-wrapper")))
        #
        #
        # # Функция для извлечения данных из таблицы
        # def extract_table_data():
        #     rows = table.find_elements(By.TAG_NAME, "tr")
        #     print(f'{rows=}')
        #     for row in rows:
        #         cols = row.find_elements(By.TAG_NAME, "td")
        #         data = [col.text.strip() for col in cols]
        #         if data:
        #             print(data)  # Вывод строки таблицы

        # Получаем первую страницу
        #extract_table_data()

        page_num = 2

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ant-table-wrapper")))
            # Функция для извлечения данных из таблицы
            def extract_table_data():
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    data = [col.text.strip() for col in cols]
                    if data:
                        print(data)  # Вывод строки таблицы

            #Получаем первую страницу
            extract_table_data()


            try:
                page_next = wait.until(EC.presence_of_element_located((By.CLASS_NAME, f"rc-pagination-item-{page_num}")))
                page_num += 1
                page_next.click()
                await asyncio.sleep(1)

            except (NoSuchElementException, ElementClickInterceptedException):
                print("Достигнута последняя страница")
                break


    finally:
        driver.quit()

asyncio.run(get_basketball_matches())