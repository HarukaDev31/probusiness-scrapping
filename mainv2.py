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
import json
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import requests
from typing import List, Dict
import re

class AlibabaOptimizedScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.products = []
        self.lock = threading.Lock()
        self.page_retry_count = 0
        self.max_page_retries = 3
    
    def setup_driver(self, headless=False):
        """Configuración segura del driver que no afecta otras instancias de Chrome"""
        import tempfile
        import os
        import random
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.support.ui import WebDriverWait

        try:
            # Configuración de opciones de Chrome
            chrome_options = Options()
            
            # Configuración de directorio de usuario único y aislado
            user_data_dir = tempfile.mkdtemp(prefix='chrome_scraper_')
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            
            # Configuración para evitar conflictos con otras instancias
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-service-autorun")
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_argument("--disable-background-networking")
            
            # Configuración de headless (usando la nueva sintaxis si está disponible)
            if headless:
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--disable-gpu")
            
            # Configuraciones de privacidad y rendimiento
            chrome_options.add_argument("--incognito")
            chrome_options.add_argument("--disable-application-cache")
            chrome_options.add_argument("--disable-cache")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Configuraciones anti-detección
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Rotación de user agents
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
            
            # Configuración de preferencias
            prefs = {
                "profile.managed_default_content_settings.images": 1,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.geolocation": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Configuración del servicio con manejo de logs
            service = ChromeService(
                log_path=os.path.devnull,
                service_args=['--verbose']
            )
            
            # Creación del driver con manejo de errores
            try:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                # Intento alternativo sin service_args si falla
                service = ChromeService(log_path=os.path.devnull)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Scripts anti-detección mejorados
            stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
                configurable: true
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });
            window.chrome = {
                runtime: {},
                app: {
                    isInstalled: false
                }
            };
            """
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": stealth_js
            })
            
            # Configuración de tiempos de espera
            self.wait = WebDriverWait(self.driver, 5)
            self.long_wait = WebDriverWait(self.driver, 15)
            
            return True
            
        except Exception as e:
            print(f"Error al configurar el driver: {str(e)}")
            # Limpieza del directorio temporal si falla
            try:
                import shutil
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except:
                pass
            raise

    def reload_page_with_retry(self, url, max_retries=3):
        """Recarga la página con reintentos si hay problemas"""
        for attempt in range(max_retries):
            try:
                print(f"Cargando página... Intento {attempt + 1}/{max_retries}")
                self.driver.get(url)
                time.sleep(2)
                
                # Verificar si la página cargó correctamente
                if self.driver.current_url and not "error" in self.driver.current_url.lower():
                    # Verificar CAPTCHA inmediatamente
                    captcha_solved = self.handle_slider_captcha_advanced()
                    if captcha_solved or not self.is_captcha_present():
                        print("Página cargada correctamente")
                        return True
                
                print(f"Página no cargó correctamente, reintentando...")
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"Error en intento {attempt + 1}: {e}")
                time.sleep(random.uniform(2, 4))
        
        print(f"No se pudo cargar la página después de {max_retries} intentos")
        return False

    def is_captcha_present(self):
        """Detecta si hay un CAPTCHA presente en la página"""
        captcha_selectors = [
            "div.nc_wrapper",
            "div#nc_1_wrapper", 
            "div.nc-lang-cnt",
            "div[id*='nocaptcha']",
            "span.nc_iconfont.btn_slide",
            "div.geetest_slider_button",
            "div.slider-btn",
            "iframe[src*='captcha']"
        ]
        
        for selector in captcha_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        return True
            except:
                continue
        return False

    def handle_slider_captcha_advanced(self):
        """Manejo avanzado de CAPTCHA con múltiples estrategias"""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                print(f"Buscando CAPTCHA... Intento {attempt + 1}/{max_attempts}")
                
                if not self.is_captcha_present():
                    print("No se detectó CAPTCHA")
                    return True
                
                # Esperar un momento para que el CAPTCHA se cargue completamente
                time.sleep(2)
                
                # Detectar tipo de CAPTCHA
                slider_element = self.find_slider_element()
                
                if slider_element:
                    print(f"CAPTCHA detectado, resolviendo... (Intento {attempt + 1})")
                    
                    # Estrategia múltiple de resolución
                    if attempt < 2:
                        success = self.solve_slider_v1(slider_element)
                    elif attempt < 4:
                        success = self.solve_slider_v2(slider_element)
                    else:
                        success = self.solve_slider_v3(slider_element)
                    
                    if success:
                        print("¡CAPTCHA resuelto exitosamente!")
                        time.sleep(2)
                        return True
                    else:
                        print(f"Intento {attempt + 1} fallido, reintentando...")
                        time.sleep(random.uniform(2, 4))
                        # Refrescar página si falla
                        if attempt >= 2:
                            self.driver.refresh()
                            time.sleep(3)
                else:
                    print("No se encontró elemento deslizante")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error en intento {attempt + 1}: {e}")
                time.sleep(random.uniform(1, 3))
        
        print("No se pudo resolver el CAPTCHA después de todos los intentos")
        return False

    def find_slider_element(self):
        """Encuentra el elemento slider del CAPTCHA"""
        slider_selectors = [
            "span.nc_iconfont.btn_slide",
            "span.btn_slide", 
            "div.geetest_slider_button",
            "div.slider-btn",
            "span[class*='btn_slide']",
            "div[class*='slider']",
            ".nc_iconfont",
            "[class*='slide']"
        ]
        
        for selector in slider_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        return element
            except:
                continue
        return None

    def solve_slider_v1(self, slider_element):
        """Estrategia 1: Movimiento lineal rápido"""
        try:
            action = ActionChains(self.driver)
            
            # Obtener dimensiones
            slider_rect = slider_element.rect
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            container_width = container.size['width']
            
            distance = container_width - slider_rect['width']
            
            # Movimiento rápido y directo
            action.move_to_element(slider_element).perform()
            time.sleep(0.5)
            
            action.click_and_hold(slider_element).perform()
            time.sleep(0.2)
            
            action.move_by_offset(distance, 0).perform()
            time.sleep(0.5)
            
            action.release().perform()
            
            return self.check_captcha_success()
            
        except Exception as e:
            print(f"Error en estrategia 1: {e}")
            return False

    def solve_slider_v2(self, slider_element):
        """Estrategia 2: Movimiento con aceleración humana"""
        try:
            action = ActionChains(self.driver)
            
            slider_rect = slider_element.rect
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            container_width = container.size['width']
            
            distance = container_width - slider_rect['width'] 
            
            action.move_to_element(slider_element).perform()
            time.sleep(random.uniform(0.5, 1))
            
            action.click_and_hold(slider_element).perform()
            time.sleep(random.uniform(0.1, 0.3))
            
            # Movimiento en etapas con aceleración
            steps = 8
            for i in range(steps):
                step_distance = distance / steps
                if i < 3:  # Aceleración
                    step_distance *= 0.7
                elif i > 5:  # Desaceleración
                    step_distance *= 1.3
                    
                action.move_by_offset(step_distance, random.uniform(-1, 1)).perform()
                time.sleep(random.uniform(0.02, 0.05))
            
            time.sleep(random.uniform(0.3, 0.7))
            action.release().perform()
            
            return self.check_captcha_success()
            
        except Exception as e:
            print(f"Error en estrategia 2: {e}")
            return False

    def solve_slider_v3(self, slider_element):
        """Estrategia 3: Movimiento con JavaScript"""
        try:
            # Usar JavaScript para mover directamente
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            
            js_solve = """
            const slider = arguments[0];
            const container = arguments[1];
            
            const containerWidth = container.offsetWidth;
            const sliderWidth = slider.offsetWidth;
            const distance = containerWidth - sliderWidth ;
            
            // Simular eventos de mouse
            const mouseDown = new MouseEvent('mousedown', {
                bubbles: true,
                cancelable: true,
                clientX: slider.getBoundingClientRect().left + sliderWidth/2,
                clientY: slider.getBoundingClientRect().top + slider.offsetHeight/2
            });
            slider.dispatchEvent(mouseDown);
            
            setTimeout(() => {
                const mouseMove = new MouseEvent('mousemove', {
                    bubbles: true,
                    cancelable: true,
                    clientX: slider.getBoundingClientRect().left + distance,
                    clientY: slider.getBoundingClientRect().top + slider.offsetHeight/2
                });
                document.dispatchEvent(mouseMove);
                
                setTimeout(() => {
                    const mouseUp = new MouseEvent('mouseup', {
                        bubbles: true,
                        cancelable: true,
                        clientX: slider.getBoundingClientRect().left + distance,
                        clientY: slider.getBoundingClientRect().top + slider.offsetHeight/2
                    });
                    document.dispatchEvent(mouseUp);
                }, 500);
            }, 200);
            """
            
            self.driver.execute_script(js_solve, slider_element, container)
            time.sleep(2)
            
            return self.check_captcha_success()
            
        except Exception as e:
            print(f"Error en estrategia 3: {e}")
            return False

    def check_captcha_success(self):
        """Verifica si el CAPTCHA fue resuelto exitosamente"""
        success_indicators = [
            "div.nc-lang-cnt[data-nc-lang='_yesTEXT']",
            "span[class*='success']",
            "div[class*='success']",
            "div[class*='verified']",
            ".nc-lang-cnt:contains('成功')",
            "[class*='pass']"
        ]
        
        time.sleep(2)  # Esperar respuesta del servidor
        
        for indicator in success_indicators:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                for element in elements:
                    if element.is_displayed():
                        return True
            except:
                continue
        
        # Verificar si el CAPTCHA desapareció
        if not self.is_captcha_present():
            return True
            
        return False

    def search_products_optimized(self, search_term, max_pages=5):
        """Búsqueda optimizada con manejo de errores mejorado"""
        base_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&keywords={search_term.replace(' ', '+')}"
        
        # Intentar cargar la página con reintentos
        if not self.reload_page_with_retry(base_url):
            print(f"No se pudo cargar la página de búsqueda para '{search_term}'")
            return []
        
        # Esperar a que se carguen los productos
        self.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=10)
        
        page_products = []
        
        for page in range(1, max_pages + 1):
            print(f"Scrapeando página {page} para '{search_term}'...")
            
            try:
                # Scroll inteligente
                self.smart_scroll()
                
                # Extraer productos
                current_page_products = self.extract_products_optimized()
                page_products.extend(current_page_products)
                
                print(f"Página {page}: {len(current_page_products)} productos encontrados")
                
                # Navegación a siguiente página
                if page < max_pages:
                    next_button = self.wait_for_element_clickable(
                        f'a[href*="page={page + 1}"] button.pagination-item',
                        timeout=3
                    )
                    
                    if next_button:
                        self.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(2)
                        
                        # Verificar CAPTCHA después de cambio de página
                        if not self.handle_slider_captcha_advanced():
                            print("No se pudo resolver CAPTCHA en cambio de página")
                            break
                        
                        self.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=5)
                    else:
                        print("No se encontró botón de siguiente página")
                        break
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"Error en página {page}: {e}")
                continue
        
        return page_products

    def wait_for_element_clickable(self, selector, timeout=5):
        """Espera dinámica para que un elemento sea clickeable"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            return None

    def wait_for_elements_presence(self, selector, timeout=5):
        """Espera dinámica para la presencia de elementos"""
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return elements
        except TimeoutException:
            return []

    def smart_scroll(self):
        """Scroll inteligente que detecta cuando ya no hay más contenido"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        no_change_count = 0
        
        while no_change_count < 3:
            scroll_distance = random.randint(500, 1000)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(0.5, 1))
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                no_change_count += 1
            else:
                no_change_count = 0
                last_height = new_height
        
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def extract_products_optimized(self):
        """Extracción optimizada de productos"""
        page_products = []
        
        product_elements = self.wait_for_elements_presence(".m-gallery-product-item-v2")
        
        js_extract = """
        return Array.from(arguments[0]).map(el => {
            const data = {};
            
            const img = el.querySelector('.search-card-e-slider__img');
            data.img = img ? (img.src || img.dataset.src || 'N/A') : 'N/A';
            
            const title = el.querySelector('.search-card-e-title');
            data.description = title ? title.textContent.trim() : 'N/A';
            
            const price = el.querySelector('.search-card-e-price-main');
            data.price = price ? price.textContent.trim() : 'N/A';
            
            const company = el.querySelector('.search-card-e-company');
            data.company = company ? company.textContent.trim() : 'N/A';
            
            const link = el.querySelector('a[href*="/product-detail/"]') || 
                        el.querySelector('.search-card-e-title a');
            data.product_url = link ? link.href : 'N/A';
            
            const moq = el.querySelector('.search-card-e-moq');
            data.min_order = moq ? moq.textContent.trim() : 'N/A';
            
            return data;
        });
        """
        
        try:
            products_data = self.driver.execute_script(js_extract, product_elements)
            for product in products_data:
                if product['description'] != 'N/A' or product['price'] != 'N/A':
                    page_products.append(product)
        except Exception as e:
            print(f"Error en extracción: {e}")
        
        return page_products

    def get_detailed_product_info_fast(self, product_url):
        """Obtiene información detallada del producto con manejo de errores mejorado"""
        try:
            if not self.reload_page_with_retry(product_url):
                print(f"No se pudo cargar la página del producto: {product_url}")
                return {}
            self.wait_for_element_clickable('div[data-testid="ladder-price"]', timeout=5)
            
            # Extracción con JavaScript
            details_js = """
            const details = {};
            
            // Precios
            const priceContainer = document.querySelector('div[data-testid="ladder-price"]');
            details.prices = [];
            if (priceContainer) {
                const priceItems = priceContainer.querySelectorAll('.price-item');
                priceItems.forEach(item => {
                    const allDivs = item.querySelectorAll('div');
                    let quantityText = '';
                    let priceText = '';
                    
                    allDivs.forEach(div => {
                        const classes = div.className || '';
                        if (classes.includes('text-sm') && classes.includes('666') && !quantityText) {
                            quantityText = div.textContent.trim();
                        }
                    });
                    
                    const priceSpans = item.querySelectorAll('span');
                    if (priceSpans.length > 0) {
                        priceText = priceSpans[0].textContent.trim();
                    }
                    
                    if (!quantityText && allDivs.length > 0) {
                        quantityText = allDivs[0].textContent.trim();
                    }
                    
                    if (quantityText && priceText) {
                        details.prices.push({
                            quantity: quantityText,
                            price: priceText
                        });
                    }
                });
            }
            
            // Atributos
            const attrContainer = document.querySelector('div[data-testid="module-attribute"]');
            details.attributes = {};
            if (attrContainer) {
                const overflowContainer = attrContainer.querySelector('.id-overflow-hidden');
                if (overflowContainer) {
                    const attrRows = overflowContainer.querySelectorAll('div.id-grid[class*="id-grid-cols"]');
                    attrRows.forEach(row => {
                        if (!row.classList.contains('id-hidden')) {
                            const keyDiv = row.querySelector('div[class*="id-bg-"][class*="f8f8f8"]');
                            const valueDiv = row.querySelector('div[class*="id-font-medium"]');
                            
                            if (keyDiv && valueDiv) {
                                const keyElement = keyDiv.querySelector('.id-line-clamp-2') || keyDiv;
                                const valueElement = valueDiv.querySelector('.id-line-clamp-2') || valueDiv;
                                
                                const keyText = keyElement.textContent.trim();
                                const valueText = valueElement.textContent.trim();
                                
                                if (keyText && valueText) {
                                    details.attributes[keyText] = valueText;
                                }
                            }
                        }
                    });
                }
            }
            
            // Descripción
            const descLayout = document.getElementById('description-layout') || 
                                document.querySelector('.description-layout');
            details.detailed_description_html = descLayout ? descLayout.outerHTML : 'N/A';
            details.detailed_description_text = descLayout ? descLayout.textContent.trim() : 'N/A';
            
            // Imágenes
            details.images = [];
            
            
            // Imágenes principales
            const mainImages = document.querySelectorAll('img[data-testid="media-image"], div[data-testid="media-image"] img');
            mainImages.forEach(img => {
                const src = img.src || img.getAttribute('src');
                if (src && !src.includes('data:') && !details.images.includes(src)) {
                    details.images.push(src);
                }
            });
            
            // Imágenes del carrusel
            const carouselImages = document.querySelectorAll([
                'div[data-module="MainImage"] img[src*="alicdn.com"]',
                'div.main-index img[src*="alicdn.com"]',
                'img[alt*="producto"]',
                'img[alt*="product"]',
                'video[poster]'
            ].join(','));
            
            carouselImages.forEach(element => {
                let imgUrl = '';
                if (element.tagName === 'VIDEO') {
                    imgUrl = element.getAttribute('poster');
                } else {
                    imgUrl = element.src || element.getAttribute('src');
                }
                
                if (imgUrl && !imgUrl.includes('data:') && !imgUrl.includes('.gif')) {
                    imgUrl = imgUrl.replace(/_\\d+x\\d+.*\\.jpg/, '_720x720q50.jpg');
                    if (!details.images.includes(imgUrl)) {
                        details.images.push(imgUrl);
                    }
                }
            });
            
           
            
            details.images = [...new Set(details.images)].map(url => {
                if (url.startsWith('//')) {
                    return 'https:' + url;
                }
                return url;
            });
            
            return details;
            """
            
            details = self.driver.execute_script(details_js)
            
            # Información del proveedor
            try:
                supplier_section = self.driver.find_element(
                    By.CSS_SELECTOR, 'div[data-module-name="module_unifed_company_card"]'
                )
                supplier_info = self.extract_supplier_info(supplier_section)
                details['supplier_info'] = supplier_info
            except:
                details['supplier_info'] = {}
            
            # Obtener contenido del iframe
            try:
                time.sleep(2)
                
                iframe = None
                iframe_selectors = [
                    'iframe[src*="descIframe.html"]',
                    'iframe[src*="description"]',
                    'iframe#description-iframe',
                    'div.description-layout iframe',
                    'div[id="description-layout"] iframe'
                ]
                
                for selector in iframe_selectors:
                    try:
                        iframe = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if iframe:
                            break
                    except:
                        continue
                
                if iframe:
                    iframe_src = iframe.get_attribute('src')
                    
                    if iframe_src:
                        current_url = self.driver.current_url
                        
                        if iframe_src.startswith('/'):
                            base_url = self.driver.current_url.split('/product-detail/')[0]
                            iframe_url = base_url + iframe_src
                        else:
                            iframe_url = iframe_src
                        
                        self.driver.get(iframe_url)
                        time.sleep(1)
                        
                        iframe_content_js = """
                        const content = {};
                        
                        content.html = document.body ? document.body.innerHTML : '';
                        content.text = document.body ? document.body.innerText : '';
                        
                        content.images = [];
                        const imgs = document.querySelectorAll('img');
                        imgs.forEach(img => {
                            const src = img.src || img.getAttribute('data-src');
                            if (src && !src.includes('data:') && !src.includes('.gif')) {
                                content.images.push(src.startsWith('//') ? 'https:' + src : src);
                            }
                        });

                        // GENERAR HTML RECONSTRUIDO
                        content.reconstructed_html = '';

                        const tables = document.querySelectorAll('table');
                        const sections = document.querySelectorAll('.magic-0');

                        let reconstructedHTML = '';
                        reconstructedHTML += '<body class="font-sans mx-5">';

                        const mainTitle = document.querySelector('.magic-9');
                        if (mainTitle) {
                            reconstructedHTML += '<h1 class="text-3xl font-bold my-6">' + mainTitle.textContent.trim() + '</h1>';
                        }

                        sections.forEach(section => {
                            reconstructedHTML += '<div class="section my-8">';
                            reconstructedHTML += '<h2 class="text-2xl font-semibold border-b-2 border-gray-800 pb-3 mb-4">' + section.textContent.trim() + '</h2>';
                            
                            let nextElement = section.closest('.J_module')?.nextElementSibling;
                            
                            while (nextElement && !nextElement.querySelector('.magic-0')) {
                                const images = nextElement.querySelectorAll('img');
                                images.forEach(img => {
                                    const src = img.src || img.getAttribute('data-src');
                                    if (src && !src.includes('data:')) {
                                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                                        reconstructedHTML += '<img class="product-image w-full my-5" src="' + fullSrc + '" alt="Product Image">';
                                    }
                                });
                                
                                const table = nextElement.querySelector('table');
                                if (table) {
                                    reconstructedHTML += '<div class="w-full my-5">';
                                    const rows = table.querySelectorAll('tr');
                                    rows.forEach(row => {
                                        reconstructedHTML += '<div class="flex border-b">';
                                        const cells = row.querySelectorAll('td');
                                        cells.forEach(cell => {
                                            const cellContent = cell.querySelector('div');
                                            if (cellContent && !cell.classList.contains('magic-10')) {
                                                reconstructedHTML += '<div class="flex-1 p-3 border-r">' + cellContent.textContent.trim() + '</div>';
                                            }
                                        });
                                        reconstructedHTML += '</div>';
                                    });
                                    reconstructedHTML += '</div>';
                                }
                                
                                nextElement = nextElement.nextElementSibling;
                            }
                            
                            reconstructedHTML += '</div>';
                        });

                        if (sections.length === 0 && tables.length > 0) {
                            tables.forEach(table => {
                                reconstructedHTML += '<div class="w-full my-5">';
                                const rows = table.querySelectorAll('tr');
                                rows.forEach(row => {
                                    reconstructedHTML += '<div class="flex border-b">';
                                    const cells = row.querySelectorAll('td');
                                    cells.forEach(cell => {
                                        const cellContent = cell.querySelector('div');
                                        if (cellContent && !cell.classList.contains('magic-10')) {
                                            reconstructedHTML += '<div class="flex-1 p-3 border-r">' + cellContent.textContent.trim() + '</div>';
                                        }
                                    });
                                    reconstructedHTML += '</div>';
                                });
                                reconstructedHTML += '</div>';
                            });
                        }

                        const allImages = document.querySelectorAll('img');
                        if (allImages.length > 0) {
                            reconstructedHTML += '<div class="section my-8"><h2 class="text-2xl font-semibold border-b-2 border-gray-800 pb-3 mb-4">Imágenes del Producto</h2>';
                            allImages.forEach(img => {
                                const src = img.src || img.getAttribute('data-src');
                                if (src && !src.includes('data:') && !src.includes('.gif')) {
                                    const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                                    reconstructedHTML += '<img class="product-image w-full my-5" src="' + fullSrc + '" alt="Product Image">';
                                }
                            });
                            reconstructedHTML += '</div>';
                        }

                        reconstructedHTML += '</body>';
                        content.reconstructed_html = reconstructedHTML;

                        return content;
                        """
                        
                        iframe_content = self.driver.execute_script(iframe_content_js)
                        details['iframe_content'] = iframe_content
                        
                        if iframe_content.get('images'):
                            if 'images' not in details:
                                details['images'] = []
                            details['images'].extend(iframe_content['images'])
                            details['images'] = list(set(details['images']))
                        
                        self.driver.get(current_url)
                        time.sleep(1)
                else:
                    print("No se encontró iframe de descripción")
                    details['iframe_content'] = {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}
                    
            except Exception as e:
                print(f"Error con iframe: {e}")
                details['iframe_content'] = {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}
            
            if not details.get('images') or len(details['images']) == 0:
                details['images'] = self.extract_images_selenium()
            
            print(f"Imágenes encontradas: {len(details.get('images', []))}")
            
            return details
            
        except Exception as e:
            print(f"Error obteniendo detalles del producto: {e}")
            return {}

    def extract_supplier_info(self, supplier_section):
        """Extrae información del proveedor"""
        supplier_info = {}
        
        try:
            supplier_js = """
            const section = arguments[0];
            const info = {};
            
            const nameLink = section.querySelector('a[target="_blank"]');
            info.name = nameLink ? nameLink.textContent.trim() : 'N/A';
            
            const typeEl = section.querySelector('.id-text-xs');
            if (typeEl) {
                const spans = typeEl.querySelectorAll('span');
                info.type = spans[0] ? spans[0].textContent.trim() : 'N/A';
                info.years_on_alibaba = spans[1] ? spans[1].textContent.trim() : 'N/A';
            }
            
            const locEl = section.querySelector('.id-text-xs > img + span');
            info.location = locEl ? locEl.textContent.trim() : 'N/A';
            
            const perfButtons = section.querySelectorAll('button[id*="trigger-"]');
            info.performance = {};
            perfButtons.forEach(btn => {
                const key = btn.querySelector('div:first-child')?.textContent.trim();
                const value = btn.querySelector('div:last-child')?.textContent.trim();
                if (key && value) info.performance[key] = value;
            });
            
            return info;
            """
            
            supplier_info = self.driver.execute_script(supplier_js, supplier_section)
        except:
            supplier_info = {"name": "N/A", "type": "N/A", "years_on_alibaba": "N/A", "location": "N/A"}
        
        return supplier_info

    def extract_images_selenium(self):
        """Método de respaldo para extraer imágenes usando Selenium"""
        images = []
        
        try:
            thumbnails = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'div[data-submodule="ProductImageThumbsList"] div[role="group"]'
            )
            
            for i, thumb in enumerate(thumbnails[:10]):
                try:
                    self.driver.execute_script("arguments[0].click();", thumb)
                    time.sleep(0.5)
                    
                    main_img = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        'div[data-submodule="ProductImageMain"] img[src*="alicdn.com"]:not([src*=".gif"])'
                    )
                    
                    img_src = main_img.get_attribute('src')
                    if img_src and img_src not in images:
                        img_src = re.sub(r'_\d+x\d+.*\.jpg', '_720x720q50.jpg', img_src)
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        images.append(img_src)
                except:
                    continue
            
        except Exception as e:
            print(f"Error extrayendo imágenes con Selenium: {e}")
        
        return images

    def save_to_csv(self, filename="alibaba_products_optimized.csv"):
        """Guardado en CSV"""
        if not self.products:
            print("No hay productos para guardar")
            return
        
        fieldnames = [
            "img", "description", "price", "company", "product_url", "min_order",
            "detailed_description_text", "detailed_description_html", 
            "iframe_content_text", "iframe_content_html", "iframe_content_images",
            "prices", "attributes", "images", "original_product_id",
            "supplier_name", "supplier_type", "supplier_years", "supplier_location",
            "supplier_performance"
        ]
        
        with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in self.products:
                row = {k: v for k, v in product.items() if k in fieldnames}
                
                if "prices" in product:
                    row["prices"] = json.dumps(product.get("prices", []))
                if "attributes" in product:
                    row["attributes"] = json.dumps(product.get("attributes", {}))
                if "images" in product:
                    row["images"] = json.dumps(product.get("images", []))
                
                if "iframe_content" in product:
                    row["iframe_content_text"] = product['iframe_content'].get('text', '')[:1000]
                    row["iframe_content_html"] = product['iframe_content'].get('reconstructed_html', '')
                    row["iframe_content_images"] = json.dumps(product['iframe_content'].get('images', []))
                else:
                    row["iframe_content_text"] = ""
                    row["iframe_content_html"] = ""
                    row["iframe_content_images"] = "[]"
                
                if "supplier_info" in product:
                    supplier = product["supplier_info"]
                    row.update({
                        "supplier_name": supplier.get("name", "N/A"),
                        "supplier_type": supplier.get("type", "N/A"),
                        "supplier_years": supplier.get("years_on_alibaba", "N/A"),
                        "supplier_location": supplier.get("location", "N/A"),
                        "supplier_performance": json.dumps(supplier.get("performance", {}))
                    })
                
                writer.writerow(row)
        
        print(f"Datos guardados en {filename}")
        
        json_filename = filename.replace('.csv', '.json')
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump(self.products, json_file, ensure_ascii=False, indent=2)
        print(f"Datos también guardados en {json_filename}")

    def save_images_report(self, filename="alibaba_images_report.txt"):
        """Genera un reporte detallado de todas las imágenes encontradas"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("REPORTE DE IMÁGENES DE PRODUCTOS\n")
            f.write("=" * 50 + "\n\n")
            
            for i, product in enumerate(self.products):
                if 'images' in product and product['images']:
                    f.write(f"Producto {i+1}: {product.get('description', 'Sin descripción')[:100]}...\n")
                    f.write(f"URL del producto: {product.get('product_url', 'N/A')}\n")
                    f.write(f"Total de imágenes: {len(product['images'])}\n")
                    f.write("Imágenes:\n")
                    
                    for j, img_url in enumerate(product['images']):
                        f.write(f"  {j+1}. {img_url}\n")
                    
                    f.write("\n" + "-" * 50 + "\n\n")
        
        print(f"Reporte de imágenes guardado en {filename}")

    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()


def get_products_to_scrap_from_api(api_url: str) -> Dict:
    """Obtiene productos para scrapear desde la API"""
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error al obtener productos de la API: {e}")
        return None


def mark_product_completed(product_id: int):
    """Marca un producto como completado en la API"""
    api_url = "https://tiendaback.probusiness.pe/api/markProductsCompleted"
    try:
        response = requests.post(api_url, json={'product_ids': [product_id]})
        response.raise_for_status()
        print(f"Producto ID {product_id} marcado como completado")
        return True
    except requests.RequestException as e:
        print(f"Error al marcar producto {product_id} como completado: {e}")
        return False


def main():
    start_time = time.time()
    print("Iniciando Alibaba Scraper Optimizado...")
    print(f"Tiempo de inicio: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    
    max_execution_retries = 3
    execution_attempt = 0
    
    while execution_attempt < max_execution_retries:
        try:
            execution_attempt += 1
            print(f"\n=== INTENTO DE EJECUCIÓN {execution_attempt}/{max_execution_retries} ===")
            
            scraper = AlibabaOptimizedScraper(headless=False)
            
            # Obtener productos desde la API
            api_response = get_products_to_scrap_from_api("https://tiendaback.probusiness.pe/api/getProductsToScrapping")
            
            if not api_response or not api_response.get('products'):
                print("No hay productos para scrapear. Saliendo...")
                scraper.close()
                return
            
            products_to_scrap = api_response['products']
            print(f"Productos a scrapear: {len(products_to_scrap)}")
            
            # Listas para tracking
            all_found_products = []
            products_with_details = []
            successfully_processed_ids = []
            failed_products = []
            
            # FASE 1: Buscar todos los productos primero
            print("\n=== FASE 1: BÚSQUEDA DE PRODUCTOS ===")
            for idx, product in enumerate(products_to_scrap):
                print(f"\n--- Buscando producto {idx + 1}/{len(products_to_scrap)} ---")
                print(f"Producto: {product['name']} (ID: {product['id']})")
                
                search_retry_count = 0
                max_search_retries = 3
                search_success = False
                
                while search_retry_count < max_search_retries and not search_success:
                    try:
                        search_retry_count += 1
                        print(f"Intento de búsqueda {search_retry_count}/{max_search_retries}")
                        
                        # Buscar productos
                        search_term = product['name']
                        found_products = scraper.search_products_optimized(search_term, max_pages=1)
                        
                        if found_products:
                            print(f"✓ Encontrados {len(found_products)} productos para '{search_term}'")
                            # Tomar el primer producto (más relevante)
                            
                            for p in found_products:
                                p['original_product_id'] = product['id']
                            all_found_products=found_products
                            search_success = True
                        else:
                            print(f"✗ No se encontraron productos para '{search_term}'")
                            if search_retry_count >= max_search_retries:
                                failed_products.append(product)
                        
                        # Pausa entre búsquedas
                        time.sleep(random.uniform(1, 2))
                        
                    except Exception as e:
                        print(f"✗ Error en búsqueda (intento {search_retry_count}): {e}")
                        if search_retry_count >= max_search_retries:
                            failed_products.append(product)
                        time.sleep(random.uniform(2, 4))
                
                if not search_success:
                    print(f"✗ Producto ID {product['id']} falló en la búsqueda")
            
            print(f"\n=== RESUMEN FASE 1 ===")
            print(f"Productos encontrados: {len(all_found_products)}")
            print(f"Productos no encontrados: {len(failed_products)}")
            
            # FASE 2: Obtener detalles de todos los productos encontrados
            if all_found_products:
                print("\n=== FASE 2: OBTENCIÓN DE DETALLES ===")
                print(f"Obteniendo detalles de {len(all_found_products)} productos...")
                
                for idx, product in enumerate(all_found_products):
                    print(f"\n--- Detallando producto {idx + 1}/{len(all_found_products)} ---")
                    print(f"Producto: {product.get('description', '')[:80]}...")
                    
                    if product.get('product_url', 'N/A') == 'N/A':
                        print("✗ Producto sin URL válida, saltando...")
                        continue
                    
                    detail_retry_count = 0
                    max_detail_retries = 3
                    details_success = False
                    
                    while detail_retry_count < max_detail_retries and not details_success:
                        try:
                            detail_retry_count += 1
                            print(f"Intento de detalles {detail_retry_count}/{max_detail_retries}")
                            
                            details = scraper.get_detailed_product_info_fast(product['product_url'])
                            
                            # Verificar que los detalles sean válidos
                            if details and (
                                details.get('attributes') or 
                                details.get('detailed_description_text', 'N/A') != 'N/A' or
                                details.get('images', [])
                            ):
                                product.update(details)
                                products_with_details.append(product)
                                successfully_processed_ids.append(product['original_product_id'])
                                details_success = True
                                print(f"✓ Detalles obtenidos exitosamente")
                                print(f"  - Atributos: {len(details.get('attributes', {}))}")
                                print(f"  - Imágenes: {len(details.get('images', []))}")
                                print(f"  - Precios: {len(details.get('prices', []))}")
                            else:
                                print(f"✗ Detalles incompletos, reintentando...")
                                time.sleep(random.uniform(2, 4))
                                
                        except Exception as e:
                            print(f"✗ Error obteniendo detalles (intento {detail_retry_count}): {e}")
                            time.sleep(random.uniform(2, 4))
                    
                    if not details_success:
                        print(f"✗ No se pudieron obtener detalles después de {max_detail_retries} intentos")
                    
                    # Pausa entre productos para evitar bloqueos
                    time.sleep(random.uniform(2, 3))
            
            # FASE 3: Guardar solo productos con detalles completos
            if products_with_details:
                print(f"\n=== FASE 3: GUARDADO DE DATOS ===")
                print(f"Productos con detalles completos: {len(products_with_details)}")
                
                # Asignar solo los productos con detalles al scraper
                scraper.products = products_with_details
                
                # Guardar datos
                scraper.save_to_csv()
                scraper.save_images_report()
                print("✓ Datos guardados exitosamente")
                
                # FASE 4: Marcar como completados solo los exitosos
                if successfully_processed_ids:
                    print(f"\n=== FASE 4: MARCANDO PRODUCTOS COMPLETADOS ===")
                    print(f"Marcando {len(successfully_processed_ids)} productos como completados...")
                    
                    # Marcar todos los IDs exitosos de una vez
                    mark_products_completed_batch(successfully_processed_ids)
                
                # Mostrar resumen de productos guardados
                print("\n=== RESUMEN DE PRODUCTOS GUARDADOS ===")
                for i, product in enumerate(products_with_details[:5]):
                    print(f"\n{i+1}. {product.get('description', '')[:80]}...")
                    print(f"   Precio: {product.get('price', 'N/A')}")
                    print(f"   Empresa: {product.get('company', 'N/A')}")
                    print(f"   ID Original: {product.get('original_product_id', 'N/A')}")
                    print(f"   Atributos: {len(product.get('attributes', {}))}")
                    print(f"   Imágenes: {len(product.get('images', []))}")
            else:
                print("\n✗ No se obtuvieron productos con detalles completos")
            
            # Resumen final
            print(f"\n=== RESUMEN FINAL DE EJECUCIÓN ===")
            print(f"Total productos solicitados: {len(products_to_scrap)}")
            print(f"Productos encontrados en búsqueda: {len(all_found_products)}")
            print(f"Productos con detalles completos: {len(products_with_details)}")
            print(f"Productos marcados como completados: {len(successfully_processed_ids)}")
            print(f"Productos fallidos: {len(failed_products) + (len(all_found_products) - len(products_with_details))}")
            
            scraper.close()
            
            # Si llegamos aquí, la ejecución fue exitosa
            elapsed_time = time.time() - start_time
            print(f"\n✓ Scraping completado exitosamente!")
            print(f"Tiempo total: {elapsed_time:.2f} segundos ({elapsed_time/60:.2f} minutos)")
            if products_with_details:
                print(f"Velocidad promedio: {len(products_with_details)/elapsed_time:.2f} productos/segundo")
            send_products_to_api("https://tiendaback.probusiness.pe/api/products")
            return  # Salir del bucle de reintentos
            
        except KeyboardInterrupt:
            print("\nScraping interrumpido por el usuario")
            try:
                scraper.close()
            except:
                pass
            return
            
        except Exception as e:
            print(f"\n✗ Error crítico en ejecución {execution_attempt}: {e}")
            print("Detalles del error:")
            import traceback
            traceback.print_exc()
            
            try:
                scraper.close()
            except:
                pass
            
            if execution_attempt < max_execution_retries:
                wait_time = random.uniform(10, 20)
                print(f"Esperando {wait_time:.1f} segundos antes del siguiente intento...")
                time.sleep(wait_time)
            else:
                print("Se agotaron todos los intentos de ejecución")
                break
    
    print("Programa terminado")

   
def mark_products_completed_batch(product_ids: List[int]):
    """Marca múltiples productos como completados en la API"""
    api_url = "https://tiendaback.probusiness.pe/api/markProductsCompleted"
    try:
        response = requests.post(api_url, json={'product_ids': product_ids})
        response.raise_for_status()
        print(f"✓ {len(product_ids)} productos marcados como completados")
        return True
    except requests.RequestException as e:
        print(f"✗ Error al marcar productos como completados: {e}")
        # Intentar marcar uno por uno si falla el batch
        success_count = 0
        for pid in product_ids:
            if mark_product_completed(pid):
                success_count += 1
        print(f"✓ {success_count}/{len(product_ids)} productos marcados individualmente")
        return success_count > 0

def send_products_to_api( api_url):
        """Envía los productos a una API si tienen atributos"""
        import requests
        products = []
        """get json from alibaba_products_optimized.json and send to api_url/products"""
        try:
            with open("alibaba_products_optimized.json", "r", encoding="utf-8") as f:
                products = json.load(f)
        except FileNotFoundError:
            print("Archivo JSON no encontrado. Asegúrate de haber ejecutado el scraping primero.")
            return
        except json.JSONDecodeError:
            print("Error al decodificar el archivo JSON. Asegúrate de que el formato sea correcto.")
            return
        
        if not products:
            print("No hay productos para enviar")
            return
        
        headers = {'Content-Type': 'application/json'}
        
        for product in products:
            if 'detailed_description_text' in product and product['detailed_description_text']:
                try:
                    response = requests.post(api_url, json=product, headers=headers)
                    if response.status_code == 200:
                        print(f"Producto enviado exitosamente: {product['description'][:50]}...")
                    else:
                        print(f"Error al enviar producto: {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"Error al enviar producto: {e}")
    
if __name__ == "__main__":
    main()
