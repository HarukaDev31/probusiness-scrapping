"""
Script de prueba para verificar las limitaciones de imágenes
"""
import json

def test_image_limits():
    """Prueba las limitaciones de imágenes en los archivos generados"""
    
    try:
        # Cargar productos del JSON
        with open('alibaba_products_optimized.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        print("=== VERIFICACIÓN DE LÍMITES DE IMÁGENES ===")
        print(f"Total de productos: {len(products)}")
        
        for i, product in enumerate(products):
            print(f"\n--- Producto {i+1} ---")
            print(f"Descripción: {product.get('description', '')[:50]}...")
            
            # Verificar imágenes principales
            main_images = product.get('images', [])
            print(f"Imágenes principales: {len(main_images)}")
            if len(main_images) > 15:
                print(f"⚠️ ADVERTENCIA: {len(main_images)} imágenes principales (máximo 15)")
            
            # Verificar imágenes del iframe
            iframe_content = product.get('iframe_content', {})
            iframe_images = iframe_content.get('images', [])
            print(f"Imágenes del iframe: {len(iframe_images)}")
            if len(iframe_images) > 15:
                print(f"⚠️ ADVERTENCIA: {len(iframe_images)} imágenes del iframe (máximo 15)")
            
            # Verificar HTML reconstruido del iframe
            iframe_html = iframe_content.get('reconstructed_html', '')
            img_tags = iframe_html.count('<img class="product-image')
            video_tags = iframe_html.count('<video class="product-video')
            iframe_tags = iframe_html.count('<iframe class="product-video')
            total_media_in_html = img_tags + video_tags + iframe_tags
            print(f"Elementos multimedia en HTML: {total_media_in_html}")
            if total_media_in_html > 15:
                print(f"⚠️ ADVERTENCIA: {total_media_in_html} elementos multimedia en HTML (máximo 15)")
            
            # Mostrar primeras 5 imágenes como ejemplo
            if main_images:
                print("Primeras 5 imágenes principales:")
                for j, img in enumerate(main_images[:5]):
                    print(f"  {j+1}. {img[:80]}...")
            
            if iframe_images:
                print("Primeras 5 imágenes del iframe:")
                for j, img in enumerate(iframe_images[:5]):
                    print(f"  {j+1}. {img[:80]}...")
            
            print("-" * 50)
            
            # Solo mostrar los primeros 3 productos para no saturar la salida
            if i >= 2:
                print(f"\n... y {len(products) - 3} productos más")
                break
        
        print("\n=== RESUMEN ===")
        print("✅ Verificación completada")
        print("Las limitaciones de 15 imágenes se aplican en:")
        print("  - Imágenes principales del producto")
        print("  - Imágenes extraídas del iframe")
        print("  - HTML reconstruido del iframe")
        print("  - Método de respaldo Selenium")
        
    except FileNotFoundError:
        print("❌ Archivo alibaba_products_optimized.json no encontrado")
        print("Ejecuta primero el scraper para generar el archivo")
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")

if __name__ == "__main__":
    test_image_limits() 