"""
Script principal refactorizado para scraping de Alibaba optimizado y modular
Versión 3.0 - Estructura completamente modular
"""
import time
import random
import threading
from typing import List, Dict, Any
from driver_manager import DriverManager
from product_extractor import ProductExtractor
from captcha_handler import CaptchaHandler
from api_utils import (
    get_products_to_scrap_from_api,
    mark_products_completed_batch,
    mark_single_product_completed,
    save_to_csv,
    save_images_report,
    send_products_to_api,
    send_single_product_to_api
)
from config import API_URLS, RETRY_CONFIG, TIMEOUTS
from notification_handler import notification_handler


class AlibabaScraperOrchestrator:
    """Orquestador principal del scraping de Alibaba"""
    
    def __init__(self, headless=False):
        self.headless = headless
        self.driver_manager = None
        self.product_extractor = None
        self.captcha_handler = None
        self.products = []
        self.lock = threading.Lock()
        self.page_retry_count = 0
    
    def initialize(self):
        """Inicializa todos los componentes necesarios"""
        print("Inicializando componentes del scraper...")
        self.driver_manager = DriverManager(headless=self.headless)
        self.driver_manager.setup_driver()
        self.product_extractor = ProductExtractor(self.driver_manager)
        self.captcha_handler = CaptchaHandler(self.driver_manager.driver)
        print("✓ Componentes inicializados correctamente")
    
    def search_products_optimized(self, search_term: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Búsqueda optimizada con manejo de errores mejorado"""
        if not self.driver_manager or not self.product_extractor:
            print("Componentes no inicializados")
            return []
            
        base_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&keywords={search_term.replace(' ', '+')}"
        
        # Intentar cargar la página con reintentos
        if not self.driver_manager.reload_page_with_retry(base_url):
            print(f"No se pudo cargar la página de búsqueda para '{search_term}'")
            return []
        
        # Esperar a que se carguen los productos
        self.driver_manager.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=10)
        
        page_products = []
        
        for page in range(1, max_pages + 1):
            print(f"Scrapeando página {page} para '{search_term}'...")
            
            try:
                # Scroll inteligente
                self.driver_manager.smart_scroll()
                
                # Extraer productos
                current_page_products = self.product_extractor.extract_products_optimized()
                page_products.extend(current_page_products)
                
                print(f"Página {page}: {len(current_page_products)} productos encontrados")
                
                # Navegación a siguiente página
                if page < max_pages:
                    next_button = self.driver_manager.wait_for_element_clickable(
                        f'a[href*="page={page + 1}"] button.pagination-item',
                        timeout=3
                    )
                    
                    if next_button and self.driver_manager.driver and self.captcha_handler:
                        self.driver_manager.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(2)
                        
                        # Verificar CAPTCHA después de cambio de página
                        if not self.captcha_handler.handle_slider_captcha_advanced():
                            print("No se pudo resolver CAPTCHA en cambio de página")
                            break
                        
                        self.driver_manager.wait_for_elements_presence(".m-gallery-product-item-v2", timeout=5)
                    else:
                        print("No se encontró botón de siguiente página")
                        break
                
                time.sleep(random.uniform(*TIMEOUTS["between_requests"]))
                
            except Exception as e:
                print(f"Error en página {page}: {e}")
                continue
        
        return page_products
    
    def process_products_batch(self, products_to_scrap: List[Dict]) -> tuple:
        """Procesa un lote de productos en fases"""
        all_found_products = []
        products_with_details = []
        successfully_processed_ids = []
        failed_products = []
        completed_original_ids = set()  # Para trackear qué productos originales se completaron
        
        # FASE 1: Buscar todos los productos primero
        print("\n=== FASE 1: BÚSQUEDA DE PRODUCTOS ===")
        for idx, product in enumerate(products_to_scrap):
            print(f"\n--- Buscando producto {idx + 1}/{len(products_to_scrap)} ---")
            print(f"Producto: {product['name']} (ID: {product['id']})")
            
            search_retry_count = 0
            max_search_retries = RETRY_CONFIG["max_search_retries"]
            search_success = False
            current_product_found_products = []  # Productos encontrados para este producto específico
            
            while search_retry_count < max_search_retries and not search_success:
                try:
                    search_retry_count += 1
                    print(f"Intento de búsqueda {search_retry_count}/{max_search_retries}")
                    
                    # Buscar productos
                    search_term = product['name']
                    found_products = self.search_products_optimized(search_term, max_pages=1)
                    
                    if found_products:
                        print(f"✓ Encontrados {len(found_products)} productos para '{search_term}'")
                        # Tomar el primer producto (más relevante)
                        for p in found_products:
                            p['original_product_id'] = product['id']
                            p['category_id'] = product.get('category_id', 'N/A')
                        current_product_found_products.extend(found_products)
                        all_found_products.extend(found_products)
                        search_success = True
                    else:
                        print(f"✗ No se encontraron productos para '{search_term}'")
                        if search_retry_count >= max_search_retries:
                            failed_products.append(product)
                    
                    # Pausa entre búsquedas
                    time.sleep(random.uniform(*TIMEOUTS["between_requests"]))
                    
                except Exception as e:
                    print(f"✗ Error en búsqueda (intento {search_retry_count}): {e}")
                    if search_retry_count >= max_search_retries:
                        failed_products.append(product)
                    time.sleep(random.uniform(*TIMEOUTS["retry_wait"]))
            
            if not search_success:
                print(f"✗ Producto ID {product['id']} falló en la búsqueda")
            
            # FASE 2: Procesar detalles de los productos encontrados para este producto específico
            if current_product_found_products:
                print(f"\n=== PROCESANDO DETALLES PARA PRODUCTO ORIGINAL ID {product['id']} ===")
                print(f"Obteniendo detalles de {len(current_product_found_products)} productos encontrados...")
                
                products_processed_for_this_original = 0
                
                for idx, alibaba_product in enumerate(current_product_found_products):
                    print(f"\n--- Detallando producto Alibaba {idx + 1}/{len(current_product_found_products)} ---")
                    print(f"Producto: {alibaba_product.get('description', '')[:80]}...")
                    
                    if alibaba_product.get('product_url', 'N/A') == 'N/A':
                        print("✗ Producto sin URL válida, saltando...")
                        continue
                    
                    detail_retry_count = 0
                    max_detail_retries = RETRY_CONFIG["max_detail_retries"]
                    details_success = False
                    
                    while detail_retry_count < max_detail_retries and not details_success:
                        try:
                            detail_retry_count += 1
                            print(f"Intento de detalles {detail_retry_count}/{max_detail_retries}")
                            
                            if self.product_extractor:
                                details = self.product_extractor.get_detailed_product_info_fast(alibaba_product['product_url'])
                            else:
                                details = {}
                            
                            # Verificar que los detalles sean válidos
                            if details and (
                                details.get('attributes') or 
                                details.get('detailed_description_text', 'N/A') != 'N/A' or
                                details.get('images', [])
                            ):
                                alibaba_product.update(details)
                                products_with_details.append(alibaba_product)
                                successfully_processed_ids.append(alibaba_product['original_product_id'])
                                products_processed_for_this_original += 1
                                details_success = True
                                print(f"✓ Detalles obtenidos exitosamente")
                                print(f"  - Atributos: {len(details.get('attributes', {}))}")
                                print(f"  - Imágenes: {len(details.get('images', []))}")
                                print(f"  - Precios: {len(details.get('prices', []))}")
                                
                                # Enviar producto individualmente a la API inmediatamente
                                print(f"📤 Enviando producto a la API...")
                                send_success = send_single_product_to_api(alibaba_product)
                                if send_success:
                                    print(f"✅ Producto enviado y guardado localmente")
                                else:
                                    print(f"⚠️ Producto guardado localmente pero no enviado a la API")
                            else:
                                print(f"✗ Detalles incompletos, reintentando...")
                                time.sleep(random.uniform(*TIMEOUTS["retry_wait"]))
                                
                        except Exception as e:
                            print(f"✗ Error obteniendo detalles (intento {detail_retry_count}): {e}")
                            time.sleep(random.uniform(*TIMEOUTS["retry_wait"]))
                    
                    if not details_success:
                        print(f"✗ No se pudieron obtener detalles después de {max_detail_retries} intentos")
                    
                    # Pausa entre productos para evitar bloqueos
                    time.sleep(random.uniform(*TIMEOUTS["between_products"]))
                
                # Marcar el producto original como completado si se procesó al menos un producto
                if products_processed_for_this_original > 0:
                    print(f"\n🎯 PRODUCTO ORIGINAL ID {product['id']} COMPLETADO")
                    print(f"Se procesaron {products_processed_for_this_original} productos de Alibaba")
                    
                    # Marcar como completado
                    if mark_single_product_completed(product['id']):
                        completed_original_ids.add(product['id'])
                        print(f"✅ Producto original ID {product['id']} marcado como completado")
                    else:
                        print(f"❌ Error marcando producto original ID {product['id']} como completado")
                else:
                    print(f"\n⚠️ Producto original ID {product['id']} no se pudo procesar completamente")
        
        print(f"\n=== RESUMEN FASE 1 ===")
        print(f"Productos encontrados: {len(all_found_products)}")
        print(f"Productos no encontrados: {len(failed_products)}")
        print(f"Productos originales completados: {len(completed_original_ids)}")
        
        return all_found_products, products_with_details, list(completed_original_ids), failed_products
    
    def save_results(self, products_with_details: List[Dict]):
        """Guarda los resultados en archivos"""
        if products_with_details:
            print(f"\n=== FASE 3: GUARDADO DE DATOS ===")
            print(f"Productos con detalles completos: {len(products_with_details)}")
            
            # Asignar solo los productos con detalles al scraper
            self.products = products_with_details
            
            # Guardar datos
            save_to_csv(products_with_details)
            save_images_report(products_with_details)
            print("✓ Datos guardados exitosamente")
            
            # Mostrar resumen de productos guardados
            print("\n=== RESUMEN DE PRODUCTOS GUARDADOS ===")
            for i, product in enumerate(products_with_details[:5]):
                print(f"\n{i+1}. {product.get('description', '')[:80]}...")
                print(f"   Precio: {product.get('price', 'N/A')}")
                print(f"   Empresa: {product.get('company', 'N/A')}")
                print(f"   ID Original: {product.get('original_product_id', 'N/A')}")
                print(f"   Category ID: {product.get('category_id', 'N/A')}")
                print(f"   Atributos: {len(product.get('attributes', {}))}")
                print(f"   Imágenes: {len(product.get('images', []))}")
        else:
            print("\n✗ No se obtuvieron productos con detalles completos")
    
    def mark_completed_and_send(self, successfully_processed_ids: List[int], products_with_details: List[Dict]):
        """Resumen de productos marcados como completados (ya se marcaron durante el procesamiento)"""
        if successfully_processed_ids:
            print(f"\n=== RESUMEN DE PRODUCTOS COMPLETADOS ===")
            print(f"Productos marcados como completados durante el procesamiento: {len(successfully_processed_ids)}")
            
            # Notificación final de resumen
            notification_handler.send_success_notification(
                f"Proceso completado: {len(successfully_processed_ids)} productos procesados y marcados como completados"
            )
        else:
            print("No se completó ningún producto")
    
    def run(self) -> bool:
        """Ejecuta el proceso completo de scraping"""
        start_time = time.time()
        print("Iniciando Alibaba Scraper Optimizado v3.0...")
        print(f"Tiempo de inicio: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        
        max_execution_retries = RETRY_CONFIG["max_execution_retries"]
        execution_attempt = 0
        
        while execution_attempt < max_execution_retries:
            try:
                execution_attempt += 1
                print(f"\n=== INTENTO DE EJECUCIÓN {execution_attempt}/{max_execution_retries} ===")
                
                # Inicializar componentes
                self.initialize()
                
                # Obtener productos desde la API
                products_to_scrap = get_products_to_scrap_from_api(API_URLS['get_products'])
                
                if not products_to_scrap:
                    print("No hay productos para scrapear. Saliendo...")
                    self.close()
                    return True
                
                print(f"Productos a scrapear: {len(products_to_scrap)}")
                
                # Procesar productos
                all_found_products, products_with_details, successfully_processed_ids, failed_products = \
                    self.process_products_batch(products_to_scrap)
                
                # Guardar resultados
                self.save_results(products_with_details)
                
                # Marcar como completados y enviar a API
                self.mark_completed_and_send(successfully_processed_ids, products_with_details)
                
                # Resumen final
                print(f"\n=== RESUMEN FINAL DE EJECUCIÓN ===")
                print(f"Total productos solicitados: {len(products_to_scrap)}")
                print(f"Productos encontrados en búsqueda: {len(all_found_products)}")
                print(f"Productos con detalles completos: {len(products_with_details)}")
                print(f"Productos enviados a la API: {len(products_with_details)}")
                print(f"Productos originales marcados como completados: {len(successfully_processed_ids)}")
                print(f"Productos originales fallidos: {len(failed_products)}")
                
                self.close()
                
                # Si llegamos aquí, la ejecución fue exitosa
                elapsed_time = time.time() - start_time
                print(f"\n✓ Scraping completado exitosamente!")
                print(f"Tiempo total: {elapsed_time:.2f} segundos ({elapsed_time/60:.2f} minutos)")
                if products_with_details:
                    print(f"Velocidad promedio: {len(products_with_details)/elapsed_time:.2f} productos/segundo")
                
                # Enviar notificación de éxito
                notification_handler.send_success_notification(
                    f"Scraping completado. {len(products_with_details)} productos procesados en {elapsed_time/60:.1f} minutos."
                )
                
                return True  # Salir del bucle de reintentos
                
            except KeyboardInterrupt:
                print("\nScraping interrumpido por el usuario")
                self.close()
                return False
                
            except Exception as e:
                print(f"\n✗ Error crítico en ejecución {execution_attempt}: {e}")
                print("Detalles del error:")
                import traceback
                traceback.print_exc()
                
                # Enviar notificación de error
                notification_handler.send_error_notification(
                    f"Error en ejecución {execution_attempt}: {str(e)[:100]}..."
                )
                
                self.close()
                
                if execution_attempt < max_execution_retries:
                    wait_time = random.uniform(10, 20)
                    print(f"Esperando {wait_time:.1f} segundos antes del siguiente intento...")
                    time.sleep(wait_time)
                else:
                    print("Se agotaron todos los intentos de ejecución")
                    notification_handler.send_error_notification(
                        "Se agotaron todos los intentos de ejecución. El scraper se ha detenido."
                    )
                    break
        
        print("Programa terminado")
        return False
    
    def close(self):
        """Cierra todos los recursos"""
        if self.driver_manager:
            self.driver_manager.close()


def main():
    """Función principal"""
    orchestrator = AlibabaScraperOrchestrator(headless=False)
    success = orchestrator.run()
    
    if success:
        print("\n🎉 Proceso completado exitosamente!")
    else:
        print("\n❌ Proceso terminado con errores")


if __name__ == "__main__":
    main() 