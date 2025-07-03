"""
Script principal para scraping de Alibaba optimizado y modular
"""
import time
import random
from driver_manager import DriverManager
from product_extractor import ProductExtractor
from api_utils import (
    get_products_to_scrap_from_api,
    mark_products_completed_batch,
    save_to_csv,
    save_images_report,
    send_products_to_api
)
from config import API_URLS

def main():
    start_time = time.time()
    print("Iniciando Alibaba Scraper Modular...")
    print(f"Tiempo de inicio: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    max_execution_retries = 3
    execution_attempt = 0

    while execution_attempt < max_execution_retries:
        try:
            execution_attempt += 1
            print(f"\n=== INTENTO DE EJECUCIÓN {execution_attempt}/{max_execution_retries} ===")

            driver_manager = DriverManager(headless=False)
            driver_manager.setup_driver()
            extractor = ProductExtractor(driver_manager)

            # Obtener productos desde la API
            products_to_scrap = get_products_to_scrap_from_api(API_URLS['get_products'])
            if not products_to_scrap:
                print("No hay productos para scrapear. Saliendo...")
                driver_manager.close()
                return
            print(f"Productos a scrapear: {len(products_to_scrap)}")

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
                        search_term = product['name']
                        found_products = extractor.extract_products_optimized()
                        if found_products:
                            print(f"✓ Encontrados {len(found_products)} productos para '{search_term}'")
                            for p in found_products:
                                p['original_product_id'] = product['id']
                            all_found_products.extend(found_products)
                            search_success = True
                        else:
                            print(f"✗ No se encontraron productos para '{search_term}'")
                            if search_retry_count >= max_search_retries:
                                failed_products.append(product)
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
                            details = extractor.get_detailed_product_info_fast(product['product_url'])
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
                    time.sleep(random.uniform(2, 3))

            # FASE 3: Guardar solo productos con detalles completos
            if products_with_details:
                print(f"\n=== FASE 3: GUARDADO DE DATOS ===")
                print(f"Productos con detalles completos: {len(products_with_details)}")
                save_to_csv(products_with_details)
                save_images_report(products_with_details)
                print("✓ Datos guardados exitosamente")
                # FASE 4: Marcar como completados solo los exitosos
                if successfully_processed_ids:
                    print(f"\n=== FASE 4: MARCANDO PRODUCTOS COMPLETADOS ===")
                    print(f"Marcando {len(successfully_processed_ids)} productos como completados...")
                    mark_products_completed_batch(successfully_processed_ids)
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

            print(f"\n=== RESUMEN FINAL DE EJECUCIÓN ===")
            print(f"Total productos solicitados: {len(products_to_scrap)}")
            print(f"Productos encontrados en búsqueda: {len(all_found_products)}")
            print(f"Productos con detalles completos: {len(products_with_details)}")
            print(f"Productos marcados como completados: {len(successfully_processed_ids)}")
            print(f"Productos fallidos: {len(failed_products) + (len(all_found_products) - len(products_with_details))}")

            driver_manager.close()

            elapsed_time = time.time() - start_time
            print(f"\n✓ Scraping completado exitosamente!")
            print(f"Tiempo total: {elapsed_time:.2f} segundos ({elapsed_time/60:.2f} minutos)")
            if products_with_details:
                print(f"Velocidad promedio: {len(products_with_details)/elapsed_time:.2f} productos/segundo")
            send_products_to_api(API_URLS['send_products'], products_with_details)
            print("Productos enviados a la API")
            return
        except KeyboardInterrupt:
            print("\nScraping interrumpido por el usuario")
            try:
                driver_manager.close()
            except:
                pass
            return
        except Exception as e:
            print(f"\n✗ Error crítico en ejecución {execution_attempt}: {e}")
            import traceback
            traceback.print_exc()
            try:
                driver_manager.close()
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

if __name__ == "__main__":
    main()