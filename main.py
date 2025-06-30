from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import csv
import time
import random

class AlibabaSeleniumScraper:
    def __init__(self, headless=False):

        self.setup_driver(headless)
        self.products = []
    
    def setup_driver(self, headless=False):

        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Opciones para evitar detección
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Otras opciones útiles
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(service=Service(), options=chrome_options)
        
        # Ejecutar script para ocultar que es selenium
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 10)
    
    def search_products_multiple_pages(self, search_term, max_pages=5):
        """
        Busca productos en múltiples páginas
        """
        base_url = f"https://www.alibaba.com/trade/search?spm=a2700.product_home_newuser.home_new_user_first_screen_fy23_pc_search_bar.keydown__Enter&tab=all&SearchText={search_term}"
        
        for page in range(1, max_pages + 1):
            print(f"Scrapeando página {page} para '{search_term}'...")
            
            # URL con número de página
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}&page={page}"
            
            try:
                # Navegar a la página
                self.driver.get(url)
                
                # Esperar a que los productos se carguen
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".m-gallery-product-item-v2")))
                
                # Scroll hacia abajo para cargar productos con lazy loading
                self.scroll_page()
                
                # Esperar un poco más después del scroll
                time.sleep(2)
                
                # Extraer productos de la página actual
                page_products = self.extract_products_from_page()
                self.products.extend(page_products)
                
                print(f"Página {page}: {len(page_products)} productos encontrados")
                
                # Pausa entre páginas para evitar ser detectado
                time.sleep(random.uniform(2, 4))
                
            except TimeoutException:
                print(f"Timeout en página {page}. Puede que no haya más productos.")
                break
            except Exception as e:
                print(f"Error en página {page}: {e}")
                continue
        
        print(f"Total de productos recolectados: {len(self.products)}")
        return self.products
    
    def scroll_page(self):
        """
        Hace scroll en la página para cargar todos los productos
        """
        # Scroll gradual hacia abajo
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll hacia abajo
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Esperar a que se cargue el contenido
            time.sleep(2)
            
            # Calcular nueva altura
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def extract_products_from_page(self):
        """
        Extrae todos los productos de la página actual
        """
        page_products = []
        
        try:
            # Buscar todos los elementos de productos
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, ".m-gallery-product-item-v2")
            
            for product_element in product_elements:
                try:
                    product_data = self.extract_single_product(product_element)
                    if product_data:
                        page_products.append(product_data)
                except Exception as e:
                    print(f"Error extrayendo producto individual: {e}")
                    continue
            
        except NoSuchElementException:
            print("No se encontraron productos en esta página")
        
        return page_products
    
    def extract_single_product(self, product_element):
        """
        Extrae información de un solo producto
        """
        product = {}
        
        try:
            # Imagen del producto
            try:
                img_element = product_element.find_element(By.CSS_SELECTOR, ".search-card-e-slider__img")
                product["img"] = img_element.get_attribute("src") or img_element.get_attribute("data-src")
            except NoSuchElementException:
                product["img"] = "N/A"
            
            # Descripción/Título
            try:
                description_element = product_element.find_element(By.CSS_SELECTOR, ".search-card-e-title")
                product["description"] = description_element.text.strip()
            except NoSuchElementException:
                product["description"] = "N/A"
            
            # Precio
            try:
                price_element = product_element.find_element(By.CSS_SELECTOR, ".search-card-e-price-main")
                product["price"] = price_element.text.strip()
            except NoSuchElementException:
                product["price"] = "N/A"
            
            # Empresa/Proveedor
            try:
                company_element = product_element.find_element(By.CSS_SELECTOR, ".search-card-e-company")
                product["company"] = company_element.text.strip()
            except NoSuchElementException:
                product["company"] = "N/A"
            
            # URL del producto - NUEVA FUNCIONALIDAD
            try:
                # Buscar el enlace principal del producto
                link_element = product_element.find_element(By.CSS_SELECTOR, "a[href*='/product-detail/']")
                product_url = link_element.get_attribute("href")
                product["product_url"] = product_url
            except NoSuchElementException:
                try:
                    # Selector alternativo
                    link_element = product_element.find_element(By.CSS_SELECTOR, ".search-card-e-title a")
                    product_url = link_element.get_attribute("href")
                    product["product_url"] = product_url
                except NoSuchElementException:
                    product["product_url"] = "N/A"
            
            # Cantidad mínima de pedido
            try:
                moq_element = product_element.find_element(By.CSS_SELECTOR, ".search-card-e-moq")
                product["min_order"] = moq_element.text.strip()
            except NoSuchElementException:
                product["min_order"] = "N/A"
            
            # Solo devolver si tiene al menos título o precio
            if product["description"] != "N/A" or product["price"] != "N/A":
                return product
            
        except Exception as e:
            print(f"Error procesando producto: {e}")
        
        return None
    
    def get_detailed_product_info(self, product_url):
        """
        Obtiene información detallada de un producto específico
        """
        try:
            print(f"Obteniendo detalles de: {product_url}")
            self.driver.get(product_url)
            
            # Esperar a que la página se cargue
            time.sleep(3)
            
            details = {}
            
            # Descripción detallada
            try:
                desc_element = self.driver.find_element(By.CSS_SELECTOR, ".do-entry-item")
                details["detailed_description"] = desc_element.text.strip()
            except NoSuchElementException:
                details["detailed_description"] = "N/A"
            
            # Especificaciones
            try:
                spec_elements = self.driver.find_elements(By.CSS_SELECTOR, ".do-entry-list .do-entry-item")
                specifications = {}
                for spec in spec_elements:
                    try:
                        key_elem = spec.find_element(By.CSS_SELECTOR, ".do-entry-item__label")
                        value_elem = spec.find_element(By.CSS_SELECTOR, ".do-entry-item__value")
                        specifications[key_elem.text.strip()] = value_elem.text.strip()
                    except NoSuchElementException:
                        continue
                details["specifications"] = specifications
            except NoSuchElementException:
                details["specifications"] = {}
            
            # Información del proveedor
            try:
                supplier_element = self.driver.find_element(By.CSS_SELECTOR, ".supplier-base-info")
                details["supplier_info"] = supplier_element.text.strip()
            except NoSuchElementException:
                details["supplier_info"] = "N/A"
            
            # Imágenes adicionales
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, ".detail-gallery-img img")
                details["additional_images"] = [img.get_attribute("src") for img in img_elements[:5]]  # Máximo 5 imágenes
            except NoSuchElementException:
                details["additional_images"] = []
            
            time.sleep(random.uniform(1, 2))
            return details
            
        except Exception as e:
            print(f"Error obteniendo detalles del producto: {e}")
            return {}
    
    def save_to_csv(self, filename="alibaba_products_complete.csv"):
        """
        Guarda los productos en CSV
        """
        if not self.products:
            print("No hay productos para guardar")
            return
        
        # Definir todas las posibles columnas
        fieldnames = ["img", "description", "price", "company", "product_url", "min_order"]
        
        with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in self.products:
                writer.writerow(product)
        
        print(f"Datos guardados en {filename}")
    
    def close(self):
        """
        Cierra el navegador
        """
        if self.driver:
            self.driver.quit()

def main():
    # Crear scraper
    scraper = AlibabaSeleniumScraper(headless=False)  # Cambiar a True para modo sin ventana
    
    try:
        # Parámetros de búsqueda
        search_term = input("Ingresa el término de búsqueda: ").strip() or "laptop"
        max_pages = int(input("¿Cuántas páginas quieres scrapear? (1-10): ") or "3")
        max_pages = min(max_pages, 10)
        
        # Buscar productos en múltiples páginas
        products = scraper.search_products_multiple_pages(search_term, max_pages)
        
        if products:
            print(f"\n¡Se encontraron {len(products)} productos!")
            
            # Mostrar algunos ejemplos
            print("\nPrimeros 3 productos:")
            for i, product in enumerate(products[:3]):
                print(f"\n{i+1}. {product['description']}")
                print(f"   Precio: {product['price']}")
                print(f"   Empresa: {product['company']}")
                print(f"   URL: {product['product_url']}")
            
            # Preguntar si quiere obtener detalles de algunos productos
            get_details = input("\n¿Quieres obtener información detallada de los primeros 3 productos? (y/n): ").lower()
            
            if get_details == 'y':
                for i, product in enumerate(products[:3]):
                    if product['product_url'] != 'N/A':
                        print(f"\nObteniendo detalles del producto {i+1}...")
                        details = scraper.get_detailed_product_info(product['product_url'])
                        
                        # Agregar detalles al producto
                        product.update(details)
                        
                        print(f"Detalles obtenidos para: {product['description'][:50]}...")
            
            # Guardar datos
            scraper.save_to_csv()
            print("\n¡Scraping completado exitosamente!")
            
        else:
            print("No se encontraron productos")
    
    except KeyboardInterrupt:
        print("\nScraping interrumpido por el usuario")
    except Exception as e:
        print(f"Error durante el scraping: {e}")
    finally:
        # Siempre cerrar el navegador
        scraper.close()

if __name__ == "__main__":
    main()