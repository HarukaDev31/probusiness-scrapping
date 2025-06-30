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

class AlibabaOptimizedScraper:
    def __init__(self, headless=False):
        self.setup_driver(headless)
        self.products = []
        self.lock = threading.Lock()
    
    def setup_driver(self, headless=False):
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Configuraciones anti-detección mejoradas
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
        
        # Configuraciones para eliminar warnings de WebGL
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-webgl")
        chrome_options.add_argument("--disable-threaded-animation")
        chrome_options.add_argument("--disable-threaded-scrolling")
        chrome_options.add_argument("--disable-in-process-stack-traces")
        chrome_options.add_argument("--disable-histogram-customizer")
        chrome_options.add_argument("--disable-gl-extensions")
        chrome_options.add_argument("--disable-composited-antialiasing")
        chrome_options.add_argument("--disable-canvas-aa")
        chrome_options.add_argument("--disable-3d-apis")
        chrome_options.add_argument("--disable-accelerated-2d-canvas")
        chrome_options.add_argument("--disable-accelerated-jpeg-decoding")
        chrome_options.add_argument("--disable-accelerated-mjpeg-decode")
        chrome_options.add_argument("--disable-app-list-dismiss-on-blur")
        chrome_options.add_argument("--disable-accelerated-video-decode")
        chrome_options.add_argument("--num-raster-threads=1")
        
        # Configuraciones adicionales de rendimiento
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Suprimir logs de Chrome
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Cargar imágenes solo si es necesario
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Configurar el servicio de Chrome para suprimir logs
        from selenium.webdriver.chrome.service import Service as ChromeService
        service = ChromeService(log_path='NUL' if os.name == 'nt' else '/dev/null')
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Scripts anti-detección
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({
                query: () => Promise.resolve({state: 'granted'})
            })
        });
        """
        self.driver.execute_script(stealth_js)
        
        # Wait más corto por defecto
        self.wait = WebDriverWait(self.driver, 5)
        self.long_wait = WebDriverWait(self.driver, 10)

    def handle_slider_captcha(self):
        """Maneja específicamente los CAPTCHAs tipo slider de Alibaba"""
        try:
            # Detectar el slider CAPTCHA
            slider_detected = False
            
            # Buscar diferentes tipos de sliders
            slider_selectors = [
                "div.nc_wrapper",
                "div#nc_1_wrapper", 
                "div.nc-lang-cnt",
                "div[id*='nocaptcha']",
                "span.nc_iconfont.btn_slide",
                "div.geetest_slider_button",
                "div.slider-btn"
            ]
            
            for selector in slider_selectors:
                try:
                    slider_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if slider_element.is_displayed():
                        slider_detected = True
                        print(f"Slider CAPTCHA detectado: {selector}")
                        
                        # Obtener el botón deslizante
                        slider_button = None
                        button_selectors = [
                            "span.nc_iconfont.btn_slide",
                            "span.btn_slide",
                            "div.geetest_slider_button",
                            "div.slider-btn",
                            "span[class*='btn_slide']"
                        ]
                        
                        for btn_selector in button_selectors:
                            try:
                                slider_button = self.driver.find_element(By.CSS_SELECTOR, btn_selector)
                                if slider_button.is_displayed():
                                    break
                            except:
                                continue
                        
                        if slider_button:
                            # Simular movimiento humano para el slider
                            self.solve_slider_captcha(slider_button)
                            return True
                        break
                except:
                    continue
            
            # Verificar si hay iframe de captcha
            try:
                captcha_iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id*='captcha'], iframe[src*='captcha']")
                for iframe in captcha_iframes:
                    if iframe.is_displayed():
                        self.driver.switch_to.frame(iframe)
                        # Intentar resolver dentro del iframe
                        result = self.handle_slider_captcha()
                        self.driver.switch_to.default_content()
                        return result
            except:
                pass
            
            return slider_detected
            
        except Exception as e:
            print(f"Error manejando slider CAPTCHA: {e}")
            return False

    def solve_slider_captcha(self, slider_button):
        """Resuelve el CAPTCHA tipo slider con movimiento humano"""
        try:
            action = ActionChains(self.driver)
            
            # Obtener dimensiones del slider
            slider_width = slider_button.size['width']
            slider_container = slider_button.find_element(By.XPATH, "./..")
            container_width = slider_container.size['width']
            
            # Calcular distancia a mover (usualmente es el ancho completo menos el botón)
            distance = container_width - slider_width - 10
            
            # Generar trayectoria humana
            trajectory = self.generate_human_trajectory(distance)
            
            # Mover a la posición del slider
            action.move_to_element(slider_button).perform()
            time.sleep(random.uniform(0.5, 1))
            
            # Click y mantener
            action.click_and_hold(slider_button).perform()
            time.sleep(random.uniform(0.2, 0.5))
            
            # Mover siguiendo la trayectoria
            for x, y in trajectory:
                action.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.001, 0.003))
            
            # Pequeña pausa antes de soltar
            time.sleep(random.uniform(0.5, 1))
            
            # Soltar
            action.release().perform()
            
            # Esperar resultado
            time.sleep(2)
            
            # Verificar si se resolvió
            try:
                success_indicators = [
                    "div.nc-lang-cnt[data-nc-lang='_yesTEXT']",
                    "span.nc-lang-cnt[data-nc-lang='_yesTEXT']",
                    "div[class*='success']",
                    "div[class*='verified']"
                ]
                
                for indicator in success_indicators:
                    try:
                        if self.driver.find_element(By.CSS_SELECTOR, indicator):
                            print("¡Slider CAPTCHA resuelto con éxito!")
                            return True
                    except:
                        continue
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"Error resolviendo slider: {e}")
            return False

    def generate_human_trajectory(self, distance):
        """Genera una trayectoria de movimiento humana para el slider"""
        points = []
        current = 0
        
        # Acelerar al principio, desacelerar al final
        while current < distance:
            if current < distance * 0.6:
                # Aceleración
                step = random.uniform(5, 10)
            elif current < distance * 0.8:
                # Velocidad constante
                step = random.uniform(4, 8)
            else:
                # Desaceleración
                step = random.uniform(0.5, 1)
            
            # Agregar algo de ruido vertical (movimiento no perfectamente horizontal)
            y_noise = random.uniform(-0.5, 0.5)
            
            current += step
            if current > distance:
                step = distance - (current - step)
                current = distance
            
            points.append((step, y_noise))
        
        # Agregar un pequeño sobrepaso y corrección (más humano)
        if random.random() > 0.5:
            overshoot = random.uniform(5, 10)
            points.append((overshoot, 0))
            points.append((-overshoot, 0))
        
        return points

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
            # Scroll más natural
            scroll_distance = random.randint(500, 1000)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            
            # Espera dinámica corta
            time.sleep(random.uniform(0.5, 1))
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                no_change_count += 1
            else:
                no_change_count = 0
                last_height = new_height
        
        # Scroll final al bottom
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def search_products_optimized(self, search_term, max_pages=5):
        """Búsqueda optimizada con tiempos de espera dinámicos"""
        base_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&keywords={search_term.replace(' ', '+')}"
        
        self.driver.get(base_url)
        
        # Espera dinámica inicial
        self.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=10)
        
        # Verificar y resolver CAPTCHA si aparece
        if self.handle_slider_captcha():
            time.sleep(2)
            # Re-esperar elementos después del captcha
            self.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=10)
        
        for page in range(1, max_pages + 1):
            print(f"Scrapeando página {page} para '{search_term}'...")
            
            try:
                # Scroll inteligente
                self.smart_scroll()
                
                # Extraer productos con espera dinámica
                page_products = self.extract_products_optimized()
                
                with self.lock:
                    self.products.extend(page_products)
                
                print(f"Página {page}: {len(page_products)} productos encontrados")
                
                # Navegación a siguiente página
                if page < max_pages:
                    next_button = self.wait_for_element_clickable(
                        f'a[href*="page={page + 1}"] button.pagination-item',
                        timeout=3
                    )
                    
                    if next_button:
                        # Click con JavaScript para evitar interceptación
                        self.driver.execute_script("arguments[0].click();", next_button)
                        
                        # Esperar carga de nueva página
                        self.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=5)
                        
                        # Verificar CAPTCHA después de cambio de página
                        if self.handle_slider_captcha():
                            time.sleep(2)
                    else:
                        print("No se encontró botón de siguiente página")
                        break
                
                # Pausa aleatoria corta entre páginas
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"Error en página {page}: {e}")
                continue
        
        return self.products

    def extract_products_optimized(self):
        """Extracción optimizada de productos"""
        page_products = []
        
        # Esperar a que los productos estén presentes
        product_elements = self.wait_for_elements_presence(".m-gallery-product-item-v2")
        
        # Extracción paralela de productos usando JavaScript
        js_extract = """
        return Array.from(arguments[0]).map(el => {
            const data = {};
            
            // Imagen
            const img = el.querySelector('.search-card-e-slider__img');
            data.img = img ? (img.src || img.dataset.src || 'N/A') : 'N/A';
            
            // Título
            const title = el.querySelector('.search-card-e-title');
            data.description = title ? title.textContent.trim() : 'N/A';
            
            // Precio
            const price = el.querySelector('.search-card-e-price-main');
            data.price = price ? price.textContent.trim() : 'N/A';
            
            // Empresa
            const company = el.querySelector('.search-card-e-company');
            data.company = company ? company.textContent.trim() : 'N/A';
            
            // URL
            const link = el.querySelector('a[href*="/product-detail/"]') || 
                        el.querySelector('.search-card-e-title a');
            data.product_url = link ? link.href : 'N/A';
            
            // MOQ
            const moq = el.querySelector('.search-card-e-moq');
            data.min_order = moq ? moq.textContent.trim() : 'N/A';
            
            return data;
        });
        """
        
        try:
            # Ejecutar extracción en batch con JavaScript
            products_data = self.driver.execute_script(js_extract, product_elements)
            
            # Filtrar productos válidos
            for product in products_data:
                if product['description'] != 'N/A' or product['price'] != 'N/A':
                    page_products.append(product)
        except Exception as e:
            print(f"Error en extracción batch: {e}")
            # Fallback a extracción individual
            for element in product_elements[:10]:  # Limitar para evitar timeout
                try:
                    product = self.extract_single_product(element)
                    if product:
                        page_products.append(product)
                except:
                    continue
        
        return page_products


    def get_detailed_product_info_fast(self, product_url):
        try:
            self.driver.get(product_url)
            
            # Espera dinámica para elementos clave
            self.wait_for_element_clickable('div[data-testid="ladder-price"]', timeout=3)
            
            # Extracción con JavaScript para mayor velocidad
            details_js = """
            const details = {};
            
            // Precios - versión corregida sin corchetes problemáticos
            const priceContainer = document.querySelector('div[data-testid="ladder-price"]');
            details.prices = [];

            if (priceContainer) {
                const priceItems = priceContainer.querySelectorAll('.price-item');
                priceItems.forEach(item => {
                    // Buscar elementos por sus clases parciales sin usar corchetes
                    const allDivs = item.querySelectorAll('div');
                    let quantityText = '';
                    let priceText = '';
                    
                    // Buscar el div de cantidad (generalmente el primero con texto pequeño)
                    allDivs.forEach(div => {
                        const classes = div.className || '';
                        if (classes.includes('text-sm') && classes.includes('666') && !quantityText) {
                            quantityText = div.textContent.trim();
                        }
                    });
                    
                    // Buscar el precio en spans
                    const priceSpans = item.querySelectorAll('span');
                    if (priceSpans.length > 0) {
                        priceText = priceSpans[0].textContent.trim();
                    }
                    
                    // Si no encontramos con el método anterior, usar índices
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
                            
                            // Atributos - versión corregida
                        const attrContainer = document.querySelector('div[data-testid="module-attribute"]');
                details.attributes = {};

                if (attrContainer) {
                // Buscar el contenedor con overflow-hidden que contiene todos los atributos
                const overflowContainer = attrContainer.querySelector('.id-overflow-hidden');
                
                if (overflowContainer) {
                    // Buscar todas las filas de grid dentro del contenedor
                    const attrRows = overflowContainer.querySelectorAll('div.id-grid[class*="id-grid-cols"]');
                    
                    attrRows.forEach(row => {
                        // Verificar que no sea una fila oculta
                        if (!row.classList.contains('id-hidden')) {
                            // Buscar el div con fondo gris (key) y el div con font-medium (value)
                            const keyDiv = row.querySelector('div[class*="id-bg-"][class*="f8f8f8"]');
                            const valueDiv = row.querySelector('div[class*="id-font-medium"]');
                            
                            if (keyDiv && valueDiv) {
                                // Buscar el texto dentro de id-line-clamp-2 o usar el texto directo
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
                    
                    // También buscar atributos ocultos si el usuario expandió la vista
                    const hiddenRows = overflowContainer.querySelectorAll('div.id-grid.id-hidden[class*="id-grid-cols"]');
                    hiddenRows.forEach(row => {
                        const keyDiv = row.querySelector('div[class*="id-bg-"][class*="f8f8f8"]');
                        const valueDiv = row.querySelector('div[class*="id-font-medium"]');
                        
                        if (keyDiv && valueDiv) {
                            const keyElement = keyDiv.querySelector('.id-line-clamp-2') || keyDiv;
                            const valueElement = valueDiv.querySelector('.id-line-clamp-2') || valueDiv;
                            
                            const keyText = keyElement.textContent.trim();
                            const valueText = valueElement.textContent.trim();
                            
                            if (keyText && valueText) {
                                // Marcar como atributo oculto
                                details.attributes[keyText + ' (oculto)'] = valueText;
                            }
                        }
                    });
                }
                }

                // Si no se encontraron atributos con el método anterior, intentar método alternativo
                if (Object.keys(details.attributes).length === 0) {
                const allGridRows = document.querySelectorAll('div[data-testid="module-attribute"] div.id-grid');
                
                allGridRows.forEach(row => {
                    // Buscar divs que parecen contener pares key-value
                    const divs = row.querySelectorAll('div.id-text-sm');
                    
                    if (divs.length >= 2) {
                        // El primer div con p-4 suele ser el key, el segundo el value
                        let keyText = '';
                        let valueText = '';
                        
                        divs.forEach(div => {
                            if (div.classList.contains('id-p-4')) {
                                const text = div.textContent.trim();
                                if (!keyText && div.parentElement.className.includes('bg-')) {
                                    keyText = text;
                                } else if (!valueText && keyText) {
                                    valueText = text;
                                }
                            }
                        });
                        
                        if (keyText && valueText) {
                            details.attributes[keyText] = valueText;
                        }
                    }
                });
                }
            // Descripción - obtener HTML completo
            const descLayout = document.getElementById('description-layout') || 
                                document.querySelector('.description-layout');
            details.detailed_description_html = descLayout ? descLayout.outerHTML : 'N/A';
            details.detailed_description_text = descLayout ? descLayout.textContent.trim() : 'N/A';
            
            // EXTRAER TODAS LAS IMÁGENES DEL PRODUCTO
            details.images = [];
            
            // 1. Imágenes del carrusel principal (thumbnails)
            const thumbnails = document.querySelectorAll('div[data-submodule="ProductImageThumbsList"] div[style*="background-image"]');
            thumbnails.forEach(thumb => {
                const style = thumb.getAttribute('style');
                const match = style?.match(/url\\("?([^"]+)"?\\)/);
                if (match && match[1]) {
                    // Convertir thumbnail a imagen de alta calidad
                    let imgUrl = match[1];
                    imgUrl = imgUrl.replace('_80x80.jpg', '_720x720q50.jpg')
                                    .replace('_100x100.jpg', '_720x720q50.jpg')
                                    .replace('_250x250.jpg', '_720x720q50.jpg');
                    details.images.push(imgUrl);
                }
            });
            
            // 2. Imágenes principales del visor
            const mainImages = document.querySelectorAll('img[data-testid="media-image"], div[data-testid="media-image"] img');
            mainImages.forEach(img => {
                const src = img.src || img.getAttribute('src');
                if (src && !src.includes('data:') && !details.images.includes(src)) {
                    details.images.push(src);
                }
            });
            
            // 3. Buscar imágenes en el carrusel principal con diferentes selectores
            const carouselImages = document.querySelectorAll([
                'div[data-module="MainImage"] img[src*="alicdn.com"]',
                'div.main-index img[src*="alicdn.com"]',
                'img[alt*="producto"]',
                'img[alt*="product"]',
                'video[poster]' // También obtener posters de videos
            ].join(','));
            
            carouselImages.forEach(element => {
                let imgUrl = '';
                if (element.tagName === 'VIDEO') {
                    imgUrl = element.getAttribute('poster');
                } else {
                    imgUrl = element.src || element.getAttribute('src');
                }
                
                if (imgUrl && !imgUrl.includes('data:') && !imgUrl.includes('.gif')) {
                    // Mejorar calidad de imagen
                    imgUrl = imgUrl.replace(/_\\d+x\\d+.*\\.jpg/, '_720x720q50.jpg');
                    if (!details.images.includes(imgUrl)) {
                        details.images.push(imgUrl);
                    }
                }
            });
            
            // 4. Buscar imágenes en la descripción del producto
            const descImages = document.querySelectorAll([
                'div[id*="description"] img',
                'div[data-module-name*="description"] img',
                '#description-layout img'
            ].join(','));
            
            descImages.forEach(img => {
                const src = img.src || img.getAttribute('src') || img.getAttribute('data-src');
                if (src && !src.includes('data:') && !src.includes('.gif') && !details.images.includes(src)) {
                    details.images.push(src);
                }
            });
            
            // Limpiar URLs duplicadas y formatear
            details.images = [...new Set(details.images)].map(url => {
                // Asegurar protocolo HTTPS
                if (url.startsWith('//')) {
                    return 'https:' + url;
                }
                return url;
            });
            
            // También obtener el contenido del iframe si existe
            const iframeEl = document.querySelector('iframe[src*="descIframe.html"]');
            details.iframe_src = iframeEl ? iframeEl.src : null;
            
            return details;
            """
            
            details = self.driver.execute_script(details_js)
            
            # Información del proveedor (más compleja, mantener con Selenium)
            try:
                supplier_section = self.driver.find_element(
                    By.CSS_SELECTOR, 'div[data-module-name="module_unifed_company_card"]'
                )
                supplier_info = self.extract_supplier_info(supplier_section)
                details['supplier_info'] = supplier_info
            except:
                details['supplier_info'] = {}
            
            # Obtener contenido del iframe de descripción
            try:
                # Esperar un momento para que se cargue la página
                time.sleep(2)
                
                # Buscar el iframe con diferentes selectores
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
                        # Guardar URL actual
                        current_url = self.driver.current_url
                        
                        # Construir URL completa del iframe
                        if iframe_src.startswith('/'):
                            base_url = self.driver.current_url.split('/product-detail/')[0]
                            iframe_url = base_url + iframe_src
                        else:
                            iframe_url = iframe_src
                        
                        # Navegar al iframe
                        self.driver.get(iframe_url)
                        time.sleep(1)
                        
                        # Extraer contenido del iframe
                        iframe_content_js = """
                        const content = {};
                        
                        // Obtener todo el HTML
                        content.html = document.body ? document.body.innerHTML : '';
                        
                        // Obtener texto limpio
                        content.text = document.body ? document.body.innerText : '';
                        
                        // Buscar imágenes adicionales en el iframe
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

// Extraer información de las tablas
const tables = document.querySelectorAll('table');
const sections = document.querySelectorAll('.magic-0');

let reconstructedHTML = '';
reconstructedHTML += '<body class="font-sans mx-5">';

// Título principal
const mainTitle = document.querySelector('.magic-9');
if (mainTitle) {
    reconstructedHTML += '<h1 class="text-3xl font-bold my-6">' + mainTitle.textContent.trim() + '</h1>';
}

// Secciones con títulos
sections.forEach(section => {
    reconstructedHTML += '<div class="section my-8">';
    reconstructedHTML += '<h2 class="text-2xl font-semibold border-b-2 border-gray-800 pb-3 mb-4">' + section.textContent.trim() + '</h2>';
    
    // Buscar el contenido después de esta sección
    let nextElement = section.closest('.J_module')?.nextElementSibling;
    
    while (nextElement && !nextElement.querySelector('.magic-0')) {
        // Si es una imagen
        const images = nextElement.querySelectorAll('img');
        images.forEach(img => {
            const src = img.src || img.getAttribute('data-src');
            if (src && !src.includes('data:')) {
                const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                reconstructedHTML += '<img class="product-image w-full my-5" src="' + fullSrc + '" alt="Product Image">';
            }
        });
        
        // Si es una tabla (convertir a divs con Tailwind)
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

// Agregar todas las imágenes encontradas
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
                        
                        # Agregar imágenes del iframe a la lista principal
                        if iframe_content.get('images'):
                            if 'images' not in details:
                                details['images'] = []
                            details['images'].extend(iframe_content['images'])
                            details['images'] = list(set(details['images']))  # Eliminar duplicados
                        
                        # Volver a la página del producto
                        self.driver.get(current_url)
                        time.sleep(1)
                else:
                    print("No se encontró iframe de descripción")
                    details['iframe_content'] = {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}            
            except Exception as e:
                    print(f"Error con iframe: {e}")
                    details['iframe_content'] = {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}
                
                # Si no se encontraron imágenes con JavaScript, intentar con Selenium
            if not details.get('images') or len(details['images']) == 0:
                details['images'] = self.extract_images_selenium()
                
            print(f"Imágenes encontradas: {len(details.get('images', []))}")
                
            return details
       
        except Exception as e:
            print(f"Error obteniendo detalles: {e}")
            return {}

    def extract_supplier_info(self, supplier_section):
        """Extrae información del proveedor de manera eficiente"""
        supplier_info = {}
        
        try:
            # Usar JavaScript para extracción más rápida
            supplier_js = """
            const section = arguments[0];
            const info = {};
            
            // Nombre
            const nameLink = section.querySelector('a[target="_blank"]');
            info.name = nameLink ? nameLink.textContent.trim() : 'N/A';
            
            // Tipo y años
            const typeEl = section.querySelector('.id-text-xs');
            if (typeEl) {
                const spans = typeEl.querySelectorAll('span');
                info.type = spans[0] ? spans[0].textContent.trim() : 'N/A';
                info.years_on_alibaba = spans[1] ? spans[1].textContent.trim() : 'N/A';
            }
            
            // Ubicación
            const locEl = section.querySelector('.id-text-xs > img + span');
            info.location = locEl ? locEl.textContent.trim() : 'N/A';
            
            // Performance
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
            # Hacer clic en las miniaturas para cargar todas las imágenes
            thumbnails = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'div[data-submodule="ProductImageThumbsList"] div[role="group"]'
            )
            
            for i, thumb in enumerate(thumbnails[:10]):  # Limitar a 10 para evitar timeout
                try:
                    # Click en miniatura
                    self.driver.execute_script("arguments[0].click();", thumb)
                    time.sleep(0.5)
                    
                    # Buscar imagen principal actual
                    main_img = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        'div[data-submodule="ProductImageMain"] img[src*="alicdn.com"]:not([src*=".gif"])'
                    )
                    
                    img_src = main_img.get_attribute('src')
                    if img_src and img_src not in images:
                        # Mejorar calidad
                        img_src = re.sub(r'_\d+x\d+.*\.jpg', '_720x720q50.jpg', img_src)
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        images.append(img_src)
                except:
                    continue
            
        except Exception as e:
            print(f"Error extrayendo imágenes con Selenium: {e}")
        
        return images

    def parallel_search(self, search_terms, max_pages=3, max_workers=3):
        """Búsqueda paralela de múltiples términos"""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for term in search_terms:
                future = executor.submit(self.search_products_optimized, term, max_pages)
                futures.append(future)
            
            for future in futures:
                future.result()
        
        return self.products
    def get_iframe_content(self, iframe_url):
        try:
            if iframe_url and iframe_url != 'null':
                # Si es URL relativa, construir URL completa
                if iframe_url.startswith('/'):
                    iframe_url = 'https://www.alibaba.com' + iframe_url
                
                self.driver.get(iframe_url)
                time.sleep(1)
                
                # Obtener todo el HTML del iframe
                iframe_html = self.driver.execute_script("return document.documentElement.outerHTML;")
                return iframe_html
        except Exception as e:
            print(f"Error obteniendo contenido del iframe: {e}")
        
        return None
    
    def save_to_csv(self, filename="alibaba_products_optimized.csv"):
        """Guardado eficiente en CSV incluyendo URLs de imágenes"""
        if not self.products:
            print("No hay productos para guardar")
            return
        
        # En save_to_csv, actualizar fieldnames para incluir los campos del iframe:

        fieldnames = [
            "img", "description", "price", "company", "product_url", "min_order",
            "detailed_description_text", "detailed_description_html", 
            "iframe_content_text", "iframe_content_images",  # Agregar estos campos
            "prices", "attributes", "images",
            "supplier_name", "supplier_type", "supplier_years", "supplier_location",
            "supplier_performance"
        ]
        with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in self.products:
                row = {k: v for k, v in product.items() if k in fieldnames}
                
                # Convertir objetos complejos a JSON
                if "prices" in product:
                    row["prices"] = json.dumps(product.get("prices", []))
                if "attributes" in product:
                    row["attributes"] = json.dumps(product.get("attributes", {}))
                if "images" in product:
                    row["images"] = json.dumps(product.get("images", []))
                if "iframe_content" in product:
                    row["iframe_content_text"] = product['iframe_content'].get('text', '')[:1000]
                    row["iframe_content_images"] = json.dumps(product['iframe_content'].get('images', []))
                else:
                    row["iframe_content_text"] = ""
                    row["iframe_content_images"] = "[]"
                # Extraer info del proveedor
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
        
        # Guardar también un archivo JSON para mejor manejo de imágenes
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
    
def main():
    start_time = time.time()
    print("Iniciando Alibaba Scraper Optimizado...")
    print(f"Tiempo de inicio: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    
    scraper = AlibabaOptimizedScraper(headless=False)
    
    try:
        # Opción de búsqueda simple o múltiple
        search_mode = input("¿Búsqueda simple (s) o múltiple (m)? [s/m]: ").strip().lower() or "s"
        
        if search_mode == "m":
            # Búsqueda múltiple paralela
            search_terms = []
            print("Ingresa los términos de búsqueda (línea vacía para terminar):")
            while True:
                term = input().strip()
                if not term:
                    break
                search_terms.append(term)
            
            if search_terms:
                max_pages = int(input("¿Cuántas páginas por término? (1-5): ") or "2")
                max_pages = min(max_pages, 5)
                
                products = scraper.parallel_search(search_terms, max_pages)
        else:
            # Búsqueda simple
            search_term = input("Ingresa el término de búsqueda: ").strip() or "inspection camera"
            max_pages = int(input("¿Cuántas páginas quieres scrapear? (1-10): ") or "3")
            max_pages = min(max_pages, 10)
            
            products = scraper.search_products_optimized(search_term, max_pages)
        
        if scraper.products:
            print(f"\n¡Se encontraron {len(scraper.products)} productos en total!")
            
            # Mostrar resumen
            for i, product in enumerate(scraper.products[:5]):
                print(f"\n{i+1}. {product['description'][:80]}...")
                print(f"   Precio: {product['price']}")
                print(f"   Empresa: {product['company']}")
            
            # Obtener detalles rápidamente
            get_details = input("\n¿Obtener detalles de productos? [s/n]: ").strip().lower() == "s"
            
            if get_details:
                num_details = int(input(f"¿Cuántos productos detallar? (0 para todos, max {len(scraper.products)}): ") or "10")
                products_to_detail = scraper.products if num_details == 0 else scraper.products[:num_details]
                
                print(f"\nObteniendo detalles de {len(products_to_detail)} productos...")
                for i, product in enumerate(products_to_detail):
                    if product['product_url'] != 'N/A':
                        print(f"Procesando {i+1}/{len(products_to_detail)}...", end='\r')
                        details = scraper.get_detailed_product_info_fast(product['product_url'])
                        product.update(details)
                        
                        # Manejo de CAPTCHA si aparece
                        if scraper.handle_slider_captcha():
                            time.sleep(1)
            
            # Guardar resultados
            scraper.save_to_csv()
            
            # Preguntar si guardar reporte de imágenes
            save_images = input("\n¿Guardar reporte detallado de imágenes? [s/n]: ").strip().lower() == "s"
            if save_images:
                scraper.save_images_report()
            
            print("\n¡Scraping completado exitosamente!")
            
        else:
            print("No se encontraron productos")
    
    except KeyboardInterrupt:
        print("\nScraping interrumpido por el usuario")
    except Exception as e:
        print(f"Error durante el scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        elapsed_time = time.time() - start_time
        print(f"\nTiempo total de ejecución: {elapsed_time:.2f} segundos ({elapsed_time/60:.2f} minutos)")
        print(f"Velocidad promedio: {len(scraper.products)/elapsed_time:.2f} productos/segundo" if scraper.products else "")
        send_products_to_api("http://localhost:8000/api/products")

    """def send  products in post to apiurl/products only if in json a row has key attributes and send all object"""
    

if __name__ == "__main__":
    # Crear una instancia del scraper
    # Aquí deberías llenar scraper.products antes de enviar, por ejemplo:
    # scraper.search_products_optimized("inspection camera", 1)
    # scraper.get_detailed_product_info_fast(product_url)
    # Luego enviar los productos a la API
    #send_products_to_api("http://localhost:8000/api/products")
    # main()