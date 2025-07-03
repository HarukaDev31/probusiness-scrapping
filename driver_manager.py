"""
Manejador del driver de Chrome para el scraper
"""
import tempfile
import os
import random
import shutil
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from config import CHROME_OPTIONS, TIMEOUTS


class DriverManager:
    def __init__(self, headless=False):
        self.driver = None
        self.user_data_dir = None
        self.headless = headless
    
    def setup_driver(self) -> bool:
        """Configuración segura del driver que no afecta otras instancias de Chrome"""
        try:
            # Configuración de opciones de Chrome
            chrome_options = Options()
            
            # Configuración de directorio de usuario único y aislado
            self.user_data_dir = tempfile.mkdtemp(prefix='chrome_scraper_')
            chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
            
            # Configuración para evitar conflictos con otras instancias
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-service-autorun")
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_argument("--disable-background-networking")
            
            # Configuración de headless (usando la nueva sintaxis si está disponible)
            if self.headless:
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
            chrome_options.add_argument(f"--window-size={CHROME_OPTIONS['window_size']}")
            
            # Configuraciones anti-detección
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Rotación de user agents
            user_agent = random.choice(CHROME_OPTIONS["user_agents"])
            chrome_options.add_argument(f"--user-agent={user_agent}")
            
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
            self._apply_stealth_scripts()
            
            # Configuración de tiempos de espera
            self.wait = WebDriverWait(self.driver, TIMEOUTS["short"])
            self.long_wait = WebDriverWait(self.driver, TIMEOUTS["long"])
            
            return True
            
        except Exception as e:
            print(f"Error al configurar el driver: {str(e)}")
            self._cleanup_temp_dir()
            raise
    
    def _apply_stealth_scripts(self):
        """Aplica scripts anti-detección al driver"""
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
    
    def reload_page_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """Recarga la página con reintentos si hay problemas"""
        from captcha_handler import CaptchaHandler
        
        captcha_handler = CaptchaHandler(self.driver)
        
        for attempt in range(max_retries):
            try:
                print(f"Cargando página... Intento {attempt + 1}/{max_retries}")
                self.driver.get(url)
                time.sleep(TIMEOUTS["page_load"])
                
                # Verificar si la página cargó correctamente
                if self.driver.current_url and not "error" in self.driver.current_url.lower():
                    # Verificar CAPTCHA inmediatamente
                    captcha_solved = captcha_handler.handle_slider_captcha_advanced()
                    if captcha_solved or not captcha_handler.is_captcha_present():
                        print("Página cargada correctamente")
                        return True
                
                print(f"Página no cargó correctamente, reintentando...")
                time.sleep(random.uniform(*TIMEOUTS["retry_wait"]))
                
            except Exception as e:
                print(f"Error en intento {attempt + 1}: {e}")
                time.sleep(random.uniform(*TIMEOUTS["retry_wait"]))
        
        print(f"No se pudo cargar la página después de {max_retries} intentos")
        return False
    
    def wait_for_element_clickable(self, selector: str, timeout: int = 5):
        """Espera dinámica para que un elemento sea clickeable"""
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            return None
    
    def wait_for_elements_presence(self, selector: str, timeout: int = 5):
        """Espera dinámica para la presencia de elementos"""
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException
        
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return elements
        except TimeoutException:
            return []
    
    def smart_scroll(self):
        """Scroll inteligente que detecta cuando ya no hay más contenido"""
        import random
        
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
    
    def _cleanup_temp_dir(self):
        """Limpia el directorio temporal si falla"""
        if self.user_data_dir:
            try:
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
            except:
                pass
    
    def close(self):
        """Cierra el navegador y limpia recursos"""
        if self.driver:
            self.driver.quit()
        self._cleanup_temp_dir() 