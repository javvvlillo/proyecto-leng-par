from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from .classes import AirbnbHosting
import threading


def airbnb_scrape(city, checkin, checkout, rooms, adults, children, babies):

    while True:
        try:
            list_rows = search(city, checkin, checkout, adults, children, babies)
            break
        except:
            print("busqueda fallida, reintentando...")
            pass

    

    ### FORMA PARALELA ###

    physical_threads = os.cpu_count()
    if physical_threads > 2:
        workers = int(physical_threads/2 + 0.5) - 1
    else:
        workers = 1

    with ThreadPoolExecutor(max_workers = workers) as executor:
        hosting_thread = {executor.submit(refine, row, rooms): row for row in list_rows}

    hosting = []
    for row in as_completed(hosting_thread):
        try:
            item = row.result()
            hosting.append(item)
        except:
            pass
    
    ### FORMA SECUENCIAL ###

    # hosting = []
    # for row in list_rows:
    #     try:
    #         hosting_object = refine(row, rooms)
    #         hosting.append(hosting_object)
    #     except:
    #         pass

    # for i in range(len(hosting)):
    #     print(hosting[i])
    # print("\n"+str(len(hosting))+" resultados de AirBnb obtenidos.")

    return hosting

    
def search(city, checkin, checkout, adults, children, babies):

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--headless')

    chrome_options.add_argument('log-level=3')

    driver = webdriver.Chrome(options = chrome_options)
    wait = WebDriverWait(driver, 5)

    driver.get('https://www.airbnb.cl/')

    # lugar
    sleep(1)

    location_box = wait.until(EC.presence_of_element_located((By.XPATH,"//input[@data-testid='structured-search-input-field-query']")))
    location_box.send_keys(city)

    # fecha de entrada
    checkin_button = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@data-testid='structured-search-input-field-split-dates-0']")))
    checkin_button.click()
    checkin_date = wait.until(EC.presence_of_element_located((By.XPATH,"//div[@data-testid='datepicker-day-"+ checkin +"']")))
    checkin_date.click()

    # fecha de salida
    checkout_date = wait.until(EC.presence_of_element_located((By.XPATH,"//div[@data-testid='datepicker-day-"+ checkout +"']")))
    checkout_date.click()

    # huespedes
    guests_button = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@data-testid='structured-search-input-field-guests-button']")))
    guests_button.click()

    add_adult = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@aria-describedby='searchFlow-title-label-stepper-adults' and @aria-label='aumentar valor']/span")))
    for _ in range(adults):
        add_adult.click()

    add_child = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@aria-describedby='searchFlow-title-label-stepper-children' and @aria-label='aumentar valor']/span")))
    for _ in range(children):
        add_child.click()

    add_babie = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@aria-describedby='searchFlow-title-label-stepper-infants' and @aria-label='aumentar valor']/span")))
    for _ in range(babies):
        add_babie.click()

    # buscar
    search_button = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@data-testid='structured-search-input-search-button']")))
    search_button.click()

    # lista obtenida por la busqueda
    result = wait.until(EC.presence_of_element_located((By.XPATH,"//div[@class='_fhph4u']")))

    # pasar lista de elementos por beautifulsoup
    soup_all_results = BeautifulSoup(result.get_attribute("innerHTML"), "html.parser")
    list_rows = soup_all_results.find_all('div', { 'class': '_8ssblpx' })

    driver.quit()

    return list_rows

  
def refine(row, requested_rooms):

    # habitaciones igual o mayor habitaciones solicitadas
    rooms = row.find_all('div', { 'class': '_kqh46o' })[0].text.split(' · ')[1]
    rooms = int(rooms.replace(" ", "     ")[:3].replace(" ", ''))
    if(rooms < requested_rooms):
        exit()

    # extraer url
    url = "https://www.airbnb.cl" + row.find_all('a', href=True)[0]['href']

    # nombre
    name = row.find_all('div', { 'class': '_1c2n35az' })[0].text

    # categoría
    category = row.find_all('div', { 'class': '_167qordg' })[0].text.split(' en ')[0]

    # precio total
    total_price = row.find_all('button', { 'class': '_ebe4pze' })[0].text.replace("Total: $", '').replace('.', '').replace("Mostrar los detalles", '').replace("CLP", '')
    total_price = int(total_price)

    # superanfitrión
    if(row.find_all('div', { 'class': '_snufp9' })):
        superhost = True
    else:
        superhost = False

    # precio por noche
    nightly_price = row.find_all('span', { 'class': '_1p7iugi' })[0].text.replace("Precio:", '').replace("  CLP por noche", '').replace('.','').replace("CLP", '')
    i = len(nightly_price)-1
    while(nightly_price[i] != '$'):
        i = i-1
    nightly_price = int(nightly_price[i:].replace("$", ''))

    # rating
    if(row.find_all('span', { 'class': '_10fy1f8' })):
        rating = 2*float(row.find_all('span', { 'class': '_10fy1f8' })[0].text.replace(",", "."))
    else:
        rating = None


    ###########################################################################
    # extraer descripción, lugar y servicios (requiere entrar al alojamiento) #
    ###########################################################################

    single_result_chrome_options = webdriver.ChromeOptions()
    single_result_chrome_options.add_argument("--window-size=960,1080")
    single_result_chrome_options.add_argument("--start-maximized")
    single_result_chrome_options.add_argument('--headless')
    single_result_chrome_options.add_argument('log-level=3')
    single_result_driver = webdriver.Chrome(options = single_result_chrome_options)
    wait = WebDriverWait(single_result_driver, 10)

    single_result_driver.get(url)

    location = wait.until(EC.presence_of_element_located((By.XPATH,"//a[@class='_5twioja']"))).text

    description = wait.until(EC.presence_of_element_located((By.XPATH,"//div[@data-section-id='DESCRIPTION_DEFAULT']/div[@class='_siy8gh']")))
    description = description.text.replace(".\n\n", ".\n").replace("\n\n", ".\n").replace(":.", ":")
    
    # servicios
    soup_services_webelement = BeautifulSoup(
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH,"//div[@data-plugin-in-point-id='AMENITIES_DEFAULT']//div[@class='_1byskwn']")
            )
        ).get_attribute("innerHTML"), "html.parser")
    services_webelement_list = soup_services_webelement.find_all('div', { 'class': '_1nlbjeu' })
    services = []
    for webelement in services_webelement_list:
        services.append(webelement.text)

    # cerrar sesión del driver
    single_result_driver.quit()

    ### crear objeto Hosting ###
    new_hosting = AirbnbHosting(name, location, category, rooms, services, nightly_price, total_price, rating, superhost, description, url)

    return new_hosting

