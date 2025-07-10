"""
Utilidades para interacción con la API y guardado de archivos
"""
import requests
import json
import csv
from typing import List, Dict
from config import OUTPUT_FILES, CSV_FIELDS, API_URLS
from notification_handler import notification_handler


def get_products_to_scrap_from_api(api_url: str) -> List[Dict]:
    """Obtiene productos para scrapear desde la API"""
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        return data.get('products', [])
    except requests.RequestException as e:
        print(f"Error al obtener productos de la API: {e}")
        return []

def mark_product_completed(product_id: int) -> bool:
    """Marca un producto como completado en la API"""
    try:
        response = requests.post(API_URLS['mark_completed'], json={'product_ids': [product_id]})
        response.raise_for_status()
        print(f"Producto ID {product_id} marcado como completado")
        return True
    except requests.RequestException as e:
        print(f"Error al marcar producto {product_id} como completado: {e}")
        return False

def mark_products_completed_batch(product_ids: List[int]) -> bool:
    """Marca múltiples productos como completados en la API"""
    try:
        response = requests.post(API_URLS['mark_completed'], json={'product_ids': product_ids})
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

def save_to_csv(products: List[Dict], filename: str = OUTPUT_FILES['csv']):
    """Guardado en CSV y JSON"""
    if not products:
        print("No hay productos para guardar")
        return
    with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for product in products:
            row = {k: v for k, v in product.items() if k in CSV_FIELDS}
            if "prices" in product:
                row["prices"] = json.dumps(product.get("prices", []))
            if "attributes" in product:
                row["attributes"] = json.dumps(product.get("attributes", {}))
            if "packaging_info" in product:
                row["packaging_info"] = json.dumps(product.get("packaging_info", {}))
            if "delivery_lead_times" in product:
                row["delivery_lead_times"] = json.dumps(product.get("delivery_lead_times", {}))
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
            
            # Agregar category_id
            row["category_id"] = product.get("category_id", "N/A")
            
            # Agregar URL del detalle de Alibaba
            row["alibaba_detail_url"] = product.get("alibaba_detail_url", "N/A")
            
            # Manejar información del proveedor
            if "supplier_name" in product:
                row["supplier_name"] = product["supplier_name"]
            elif "supplier_info" in product:
                supplier = product["supplier_info"]
                row["supplier_name"] = supplier.get("name", "N/A")
                row["supplier_type"] = supplier.get("type", "N/A")
                row["supplier_years"] = supplier.get("years_on_alibaba", "N/A")
                row["supplier_location"] = supplier.get("location", "N/A")
                row["supplier_performance"] = json.dumps(supplier.get("performance", {}))
            else:
                row["supplier_name"] = "N/A"
            writer.writerow(row)
    print(f"Datos guardados en {filename}")
    json_filename = filename.replace('.csv', '.json')
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(products, json_file, ensure_ascii=False, indent=2)
    print(f"Datos también guardados en {json_filename}")

def save_images_report(products: List[Dict], filename: str = OUTPUT_FILES['images_report']):
    """Genera un reporte detallado de todas las imágenes encontradas"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE IMÁGENES DE PRODUCTOS\n")
        f.write("=" * 50 + "\n\n")
        for i, product in enumerate(products):
            if 'images' in product and product['images']:
                f.write(f"Producto {i+1}: {product.get('description', 'Sin descripción')[:100]}...\n")
                f.write(f"URL del producto: {product.get('product_url', 'N/A')}\n")
                f.write(f"Total de imágenes: {len(product['images'])}\n")
                f.write("Imágenes:\n")
                for j, img_url in enumerate(product['images']):
                    f.write(f"  {j+1}. {img_url}\n")
                f.write("\n" + "-" * 50 + "\n\n")
    print(f"Reporte de imágenes guardado en {filename}")

def send_single_product_to_api(product: Dict) -> bool:
    """Envía un solo producto a la API y muestra notificación"""
    headers = {'Content-Type': 'application/json'}
    
    if 'detailed_description_text' in product and product['detailed_description_text']:
        try:
            response = requests.post(API_URLS['send_products'], json=product, headers=headers)
            if response.status_code == 200 or response.status_code==201:
                print(f"✓ Producto enviado exitosamente: {product['description'][:50]}...")
                notification_handler.send_success_notification(
                    f"Producto enviado: {product['description'][:30]}..."
                )
                return True
            else:
                print(f"✗ Error al enviar producto: {response.status_code} - {response.text}")
                notification_handler.send_error_notification(
                    f"Error enviando producto: {response.status_code}"
                )
                return False
        except Exception as e:
            print(f"✗ Error al enviar producto: {e}")
            notification_handler.send_error_notification(
                f"Error de conexión enviando producto: {str(e)[:50]}"
            )
            return False
    else:
        print(f"⚠️ Producto sin descripción detallada, saltando envío: {product.get('description', '')[:50]}...")
        return False

def mark_single_product_completed(product_id: int) -> bool:
    """Marca un solo producto como completado y muestra notificación"""
    try:
        response = requests.post(API_URLS['mark_completed'], json={'product_ids': [product_id]})
        response.raise_for_status()
        print(f"✓ Producto ID {product_id} marcado como completado")
        notification_handler.send_success_notification(
            f"Producto ID {product_id} marcado como completado"
        )
        return True
    except requests.RequestException as e:
        print(f"✗ Error al marcar producto {product_id} como completado: {e}")
        notification_handler.send_error_notification(
            f"Error marcando producto {product_id} como completado"
        )
        return False

def send_products_to_api(api_url: str, products: List[Dict]):
    """Envía los productos a una API si tienen atributos (método legacy)"""
    headers = {'Content-Type': 'application/json'}
    for product in products:
        if 'detailed_description_text' in product and product['detailed_description_text']:
            try:
                response = requests.post(api_url, json=product, headers=headers)
                if response.status_code == 200 or response.status_code==201:
                    print(f"Producto enviado exitosamente: {product['description'][:50]}...")
                else:
                    print(f"Error al enviar producto: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error al enviar producto: {e}") 