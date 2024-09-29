import os

import shutil
import requests

from dotenv import load_dotenv
from fake_useragent import UserAgent
from selenium import webdriver
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC

ENV_PATH = '.env'
URL = 'https://agenda-personal-portal.de'
BESCHEINIGUNGS_TYP = {
    'LOHNSTEUER_BESCHEINIGUNG': 'Lohnsteuerbescheinigung',
    'SOZIALVERSICHERUNGS_NACHWEIS': 'Sozialversicherungsnachweis',
    'BRUTTO_NETTO_ABRECHNUNG': 'Brutto-Netto-Abrechnung',
}


def load_environment() -> tuple:
    load_dotenv(ENV_PATH)
    try:
        email = os.getenv('EMAIL')
        password = os.getenv('PASSWORD')
        download_path = os.path.expanduser(os.getenv('DOWNLOAD_PATH'))
    except KeyError as e:
        raise ValueError(f"Missing environment variable: {e}")
    return email, password, download_path


def authenticate(email: str, password: str) -> requests.Session:
    session = requests.Session()
    login_url = f'{URL}/rest/security/login'
    payload = {'mail': email, 'password': password}

    response = session.post(login_url, json=payload)
    response.raise_for_status()

    token = response.json()['result'][0]['employees'][0]['token']
    session.headers.update({'token': token})
    return session


def set_referrer(session: requests.Session) -> str:
    url = f'{URL}/rest/employee/myself'
    session.headers.update(
        {'Referer': f"{URL}/login", 'Accept': 'application/json', 'User-Agent': UserAgent().chrome})
    response = session.get(url)
    response.raise_for_status()

    referrer_id = response.json()['result']['id']
    session.headers.update(
        {'Referer': f'https://agenda-personal-portal.de/employee-view/{referrer_id}/0'})
    return referrer_id


def get_documents_of_type(session: requests.Session, document_type: str) -> list:
    url = f'{URL}/rest/employee/myself/documents?type={document_type}'
    response = session.get(url)
    response.raise_for_status()
    return response.json()['result']


def download_file(session: requests.Session, document: dict, download_path: str):
    download_url = f"{URL}/rest/employee/document/{document['id']}?token={document['token']}"
    response = session.get(download_url)
    response.raise_for_status()

    file_path = os.path.join(
        download_path, document['besch_typ'], document['filename'])
    with open(file_path, 'wb') as file:
        file.write(response.content)
    print(f"Downloaded file: {document['filename']}")


def download_files(session: requests.Session, email: str, password: str, documents: dict, download_path: str):
    options = Options()
    options.add_argument('--headless')
    options.add_argument("start-minimized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)

    driver.get(f'{URL}/login')
    driver.find_element(By.ID, 'email').send_keys(email)
    driver.find_element(By.ID, 'password').send_keys(password + Keys.RETURN)

    span_element = WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'item')))
    ActionChains(driver).move_to_element(span_element).perform()

    document_items = driver.find_elements(
        By.CSS_SELECTOR, 'div.item.ng-star-inserted')
    print(f"Found {len(document_items)} documents")
    for item in document_items:
        driver.execute_script("arguments[0].scrollIntoView();", item)
        item.click()
        WebDriverWait(driver, 100).until(
            EC.number_of_windows_to_be(2))
        driver.switch_to.window(driver.window_handles[1])
        WebDriverWait(driver, 100).until(
            lambda d: d.current_url.startswith(f'{URL}/rest/employee/document/'))

        document_id = driver.current_url.split('/')[-1].split('?')[0]
        token = driver.current_url.split('=')[-1]
        documents[document_id].update({'token': token})

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        download_file(session, documents[document_id], download_path)

    driver.quit()


def create_path_structure(download_path: str):
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    for value in BESCHEINIGUNGS_TYP.values():
        if not os.path.exists(f'{download_path}/{value}'):
            os.makedirs(f'{download_path}/{value}')


if __name__ == '__main__':
    email, password, download_path = load_environment()
    print(f"Download path: {download_path}")
    create_path_structure(download_path)
    try:
        session = authenticate(email, password)
        set_referrer(session)

        documents = {}
        for key, value in BESCHEINIGUNGS_TYP.items():
            documents_of_type = get_documents_of_type(session, key)
            for document in documents_of_type:
                documents[document['id']] = document
                documents[document['id']].update({'besch_typ': value})
        download_files(session, email, password, documents, download_path)
    except Exception as e:
        print(f"Error: {e}")
        shutil.rmtree(download_path, ignore_errors=True)
    print("Download completed")
