"""
Manejador de CAPTCHAs para Alibaba
"""
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import CAPTCHA_SELECTORS, SLIDER_SELECTORS, RETRY_CONFIG
from notification_handler import notification_handler


class CaptchaHandler:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 5)
    
    def is_captcha_present(self) -> bool:
        """Detecta si hay un CAPTCHA presente en la página"""
        for selector in CAPTCHA_SELECTORS:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        return True
            except:
                continue
        return False
    
    def find_slider_element(self):
        """Encuentra el elemento slider del CAPTCHA"""
        for selector in SLIDER_SELECTORS:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        return element
            except:
                continue
        return None
    
    def handle_slider_captcha_advanced(self) -> bool:
        """Manejo avanzado de CAPTCHA con múltiples estrategias"""
        max_attempts = RETRY_CONFIG["max_captcha_attempts"]
        captcha_detected = False
        
        for attempt in range(max_attempts):
            try:
                print(f"Buscando CAPTCHA... Intento {attempt + 1}/{max_attempts}")
                
                if not self.is_captcha_present():
                    print("No se detectó CAPTCHA")
                    return True
                
                # Si es la primera vez que detectamos CAPTCHA, enviar notificación
                if not captcha_detected:
                    captcha_detected = True
                    notification_handler.send_captcha_alert(
                        message="CAPTCHA detectado en Alibaba. El scraper intentará resolverlo automáticamente.",
                        title="Alibaba Scraper - CAPTCHA Detectado"
                    )
                
                time.sleep(2)
                
                # Detectar tipo de CAPTCHA
                slider_element = self.find_slider_element()
                
                if slider_element:
                    print(f"CAPTCHA detectado, resolviendo... (Intento {attempt + 1})")
                    
                    # Estrategia múltiple de resolución
                    if attempt < 2:
                        success = self._solve_slider_v1(slider_element)
                    elif attempt < 4:
                        success = self._solve_slider_v2(slider_element)
                    elif attempt < 5:
                        success = self._solve_slider_v3(slider_element)
                    else:
                        success = self._solve_slider_v4(slider_element)
                    
                    if success:
                        print("¡CAPTCHA resuelto exitosamente!")
                        notification_handler.send_success_notification(
                            "CAPTCHA resuelto automáticamente. El scraping continúa."
                        )
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
        
        # Si llegamos aquí, no se pudo resolver el CAPTCHA
        print("No se pudo resolver el CAPTCHA después de todos los intentos")
        notification_handler.send_error_notification(
            "CAPTCHA no pudo ser resuelto automáticamente. Se requiere intervención manual."
        )
        return False
    
    def _solve_slider_v1(self, slider_element) -> bool:
        """Estrategia 1: Movimiento lineal rápido con distancia garantizada"""
        try:
            action = ActionChains(self.driver)
            
            # Obtener dimensiones del contenedor
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            container_width = container.size['width']
            
            # Calcular distancia exacta hasta el final
            slider_rect = slider_element.rect
            slider_width = slider_rect['width']
            
            # Asegurar que llegue hasta el final (agregar un pequeño margen)
            distance = container_width - slider_width + 5
            
            print(f"Distancia calculada: {distance}px (container: {container_width}px, slider: {slider_width}px)")
            
            # Movimiento rápido y directo
            action.move_to_element(slider_element).perform()
            time.sleep(0.5)
            
            action.click_and_hold(slider_element).perform()
            time.sleep(0.2)
            
            # Mover hasta el final
            action.move_by_offset(distance, 0).perform()
            time.sleep(0.5)
            
            action.release().perform()
            
            return self._check_captcha_success()
            
        except Exception as e:
            print(f"Error en estrategia 1: {e}")
            return False
    
    def _solve_slider_v2(self, slider_element) -> bool:
        """Estrategia 2: Movimiento con aceleración humana y distancia garantizada"""
        try:
            action = ActionChains(self.driver)
            
            # Obtener dimensiones del contenedor
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            container_width = container.size['width']
            
            # Calcular distancia exacta hasta el final
            slider_rect = slider_element.rect
            slider_width = slider_rect['width']
            
            # Asegurar que llegue hasta el final (agregar un pequeño margen)
            distance = container_width - slider_width + 5
            
            print(f"Estrategia 2 - Distancia calculada: {distance}px")
            
            action.move_to_element(slider_element).perform()
            time.sleep(random.uniform(0.5, 1))
            
            action.click_and_hold(slider_element).perform()
            time.sleep(random.uniform(0.1, 0.3))
            
            # Movimiento en etapas con aceleración y distancia garantizada
            steps = 10
            total_moved = 0
            
            for i in range(steps):
                step_distance = distance / steps
                
                # Ajustar velocidad según la etapa
                if i < 3:  # Aceleración
                    step_distance *= 0.8
                elif i > 7:  # Desaceleración
                    step_distance *= 1.2
                
                # Asegurar que el último paso llegue exactamente al final
                if i == steps - 1:
                    remaining_distance = distance - total_moved
                    step_distance = remaining_distance
                
                action.move_by_offset(step_distance, int(random.uniform(-1, 1))).perform()
                total_moved += step_distance
                time.sleep(random.uniform(0.02, 0.05))
            
            time.sleep(random.uniform(0.3, 0.7))
            action.release().perform()
            
            return self._check_captcha_success()
            
        except Exception as e:
            print(f"Error en estrategia 2: {e}")
            return False
    
    def _solve_slider_v3(self, slider_element) -> bool:
        """Estrategia 3: Movimiento con JavaScript mejorado y distancia garantizada"""
        try:
            # Usar JavaScript para mover directamente
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            
            js_solve = """
            const slider = arguments[0];
            const container = arguments[1];
            
            const containerWidth = container.offsetWidth;
            const sliderWidth = slider.offsetWidth;
            const distance = containerWidth - sliderWidth + 5; // Agregar margen
            
            console.log('Distancia calculada:', distance, 'px');
            
            // Simular eventos de mouse con movimiento gradual
            const mouseDown = new MouseEvent('mousedown', {
                bubbles: true,
                cancelable: true,
                clientX: slider.getBoundingClientRect().left + sliderWidth/2,
                clientY: slider.getBoundingClientRect().top + slider.offsetHeight/2
            });
            slider.dispatchEvent(mouseDown);
            
            // Movimiento gradual en JavaScript
            let currentX = slider.getBoundingClientRect().left;
            const targetX = currentX + distance;
            const steps = 20;
            const stepDistance = distance / steps;
            
            for (let i = 0; i < steps; i++) {
                setTimeout(() => {
                    currentX += stepDistance;
                    const mouseMove = new MouseEvent('mousemove', {
                        bubbles: true,
                        cancelable: true,
                        clientX: currentX,
                        clientY: slider.getBoundingClientRect().top + slider.offsetHeight/2
                    });
                    document.dispatchEvent(mouseMove);
                    
                    // En el último paso, soltar el mouse
                    if (i === steps - 1) {
                        setTimeout(() => {
                            const mouseUp = new MouseEvent('mouseup', {
                                bubbles: true,
                                cancelable: true,
                                clientX: currentX,
                                clientY: slider.getBoundingClientRect().top + slider.offsetHeight/2
                            });
                            document.dispatchEvent(mouseUp);
                        }, 100);
                    }
                }, i * 20);
            }
            """
            
            self.driver.execute_script(js_solve, slider_element, container)
            time.sleep(3)  # Dar más tiempo para que complete el movimiento
            
            return self._check_captcha_success()
            
        except Exception as e:
            print(f"Error en estrategia 3: {e}")
            return False
    
    def _solve_slider_v4(self, slider_element) -> bool:
        """Estrategia 4: Movimiento agresivo con múltiples intentos"""
        try:
            action = ActionChains(self.driver)
            
            # Obtener dimensiones del contenedor
            container = slider_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'nc_wrapper') or contains(@class, 'slider')]")
            container_width = container.size['width']
            
            # Calcular distancia con margen extra
            slider_rect = slider_element.rect
            slider_width = slider_rect['width']
            distance = container_width - slider_width + 10  # Margen extra
            
            print(f"Estrategia 4 - Distancia agresiva: {distance}px")
            
            # Múltiples intentos con diferentes velocidades
            for attempt in range(3):
                try:
                    action.move_to_element(slider_element).perform()
                    time.sleep(0.3)
                    
                    action.click_and_hold(slider_element).perform()
                    time.sleep(0.1)
                    
                    # Movimiento muy rápido al final
                    action.move_by_offset(distance, 0).perform()
                    time.sleep(0.2)
                    
                    action.release().perform()
                    time.sleep(1)
                    
                    if self._check_captcha_success():
                        return True
                        
                except Exception as e:
                    print(f"Intento {attempt + 1} de estrategia 4 falló: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"Error en estrategia 4: {e}")
            return False
    
    def _check_captcha_success(self) -> bool:
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