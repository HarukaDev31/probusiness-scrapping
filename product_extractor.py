"""
Extractor de productos de Alibaba
"""
import time
import random
import re
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from config import SELECTORS, TIMEOUTS


class ProductExtractor:
    def __init__(self, driver_manager):
        self.driver_manager = driver_manager
        self.driver = driver_manager.driver
    
    def extract_products_optimized(self) -> List[Dict[str, Any]]:
        """Extracción optimizada de productos"""
        page_products = []
        
        product_elements = self.driver_manager.wait_for_elements_presence(SELECTORS["product_items"])
        
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
    
    def get_detailed_product_info_fast(self, product_url: str) -> Dict[str, Any]:
        """Obtiene información detallada del producto con manejo de errores mejorado"""
        try:
            if not self.driver_manager.reload_page_with_retry(product_url):
                print(f"No se pudo cargar la página del producto: {product_url}")
                return {}
            
            self.driver_manager.wait_for_element_clickable(SELECTORS["price_container"], timeout=5)
            
            # Extracción con JavaScript
            details = self._extract_product_details_js()
            
            # Información del proveedor
            try:
                supplier_section = self.driver.find_element(
                    By.CSS_SELECTOR, SELECTORS["supplier_section"]
                )
                supplier_info = self._extract_supplier_info(supplier_section)
                details['supplier_info'] = supplier_info
            except:
                details['supplier_info'] = {}
            
            # Obtener contenido del iframe
            details['iframe_content'] = self._extract_iframe_content()
            
            if not details.get('images') or len(details['images']) == 0:
                details['images'] = self._extract_images_selenium()
            
            print(f"Imágenes encontradas: {len(details.get('images', []))}")
            
            return details
            
        except Exception as e:
            print(f"Error obteniendo detalles del producto: {e}")
            return {}
    
    def _extract_product_details_js(self) -> Dict[str, Any]:
        """Extrae detalles del producto usando JavaScript"""
        details_js = """
        const details = {};
        
        // Precios
        details.prices = [];
        
        // Intentar extraer precios con estructura de escalera (múltiples rangos)
        const priceContainer = document.querySelector('div[data-testid="ladder-price"]');
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
        
        // Si no hay precios con estructura de escalera, intentar con estructura de rango único
        if (details.prices.length === 0) {
            const singlePriceContainer = document.querySelector('div[data-testid="range-price"]');
            if (singlePriceContainer) {
                // Extraer cantidad mínima de pedido - tomar el primer div
                const firstDiv = singlePriceContainer.querySelector('div');
                const moqText = firstDiv ? firstDiv.textContent.trim() : '';
                
                // Extraer rango de precios - tomar el primer span
                const firstSpan = singlePriceContainer.querySelector('span');
                const priceText = firstSpan ? firstSpan.textContent.trim() : '';
                
                if (moqText && priceText) {
                    details.prices.push({
                        quantity: moqText,
                        price: priceText
                    });
                } else if (priceText) {
                    details.prices.push({
                        quantity: 'Cantidad mínima no especificada',
                        price: priceText
                    });
                }
            }
        }
        
        // Atributos
        const attrContainer = document.querySelector('div[data-testid="module-attribute"]');
        details.attributes = {};
        if (attrContainer) {
            // Buscar TODAS las filas de atributos en cualquier nivel del contenedor
            const allAttrRows = attrContainer.querySelectorAll('div.id-grid');
            
            allAttrRows.forEach(row => {
                // Buscar todos los divs dentro de la fila que tengan las clases específicas
                const keyDiv = row.querySelector('div[class*="id-bg-[#f8f8f8]"]');
                const valueDiv = row.querySelector('div[class*="id-font-medium"]');
                
                if (keyDiv && valueDiv) {
                    // Extraer texto de los elementos internos o del div mismo
                    const keyElement = keyDiv.querySelector('.id-line-clamp-2') || keyDiv;
                    const valueElement = valueDiv.querySelector('.id-line-clamp-2') || valueDiv;
                    
                    const keyText = keyElement.textContent.trim();
                    const valueText = valueElement.textContent.trim();
                    
                    if (keyText && valueText) {
                        details.attributes[keyText] = valueText;
                    }
                }
            });
        }
        
        // Información del proveedor
        details.supplier_name = 'N/A';
        const companyContainer = document.querySelector('.product-company');
        if (companyContainer) {
            const companyNameElement = companyContainer.querySelector('.company-name a');
            if (companyNameElement) {
                details.supplier_name = companyNameElement.textContent.trim();
            } else {
                // Fallback: buscar cualquier enlace con el nombre de la empresa
                const companyLink = companyContainer.querySelector('a[title]');
                if (companyLink) {
                    details.supplier_name = companyLink.getAttribute('title') || companyLink.textContent.trim();
                }
            }
        }
        
        // Información de embalaje (separar de atributos generales)
        details.packaging_info = {};
        const packagingSection = attrContainer ? attrContainer.querySelector('h3:contains("Embalaje y entrega")') : null;
        if (packagingSection) {
            const packagingContainer = packagingSection.closest('div').querySelector('.id-grid');
            if (packagingContainer) {
                const packagingRows = packagingContainer.querySelectorAll('div.id-grid');
                packagingRows.forEach(row => {
                    const keyDiv = row.querySelector('div[class*="id-bg-[#f8f8f8]"]');
                    const valueDiv = row.querySelector('div[class*="id-font-medium"]');
                    
                    if (keyDiv && valueDiv) {
                        const keyElement = keyDiv.querySelector('.id-line-clamp-2') || keyDiv;
                        const valueElement = valueDiv.querySelector('.id-line-clamp-2') || valueDiv;
                        
                        const keyText = keyElement.textContent.trim();
                        const valueText = valueElement.textContent.trim();
                        
                        if (keyText && valueText) {
                            details.packaging_info[keyText] = valueText;
                        }
                    }
                });
            }
        }
        
        // Plazos de entrega
        details.delivery_lead_times = {};
        const leadTimeContainer = document.querySelector('div[data-module-name="module_lead"]');
        if (leadTimeContainer) {
            const table = leadTimeContainer.querySelector('table');
            if (table) {
                const rows = table.querySelectorAll('tr');
                if (rows.length >= 2) {
                    const headerRow = rows[0];
                    const dataRow = rows[1];
                    
                    const headers = headerRow.querySelectorAll('td');
                    const values = dataRow.querySelectorAll('td');
                    
                    if (headers.length > 1 && values.length > 1) {
                        // El primer td es el título, los demás son los rangos
                        for (let i = 1; i < headers.length && i < values.length; i++) {
                            const range = headers[i].textContent.trim();
                            const time = values[i].textContent.trim();
                            if (range && time) {
                                details.delivery_lead_times[range] = time;
                            }
                        }
                    }
                }
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
        
        return self.driver.execute_script(details_js)
    
    def _extract_supplier_info(self, supplier_section) -> Dict[str, Any]:
        """Extrae información del proveedor"""
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
        
        try:
            supplier_info = self.driver.execute_script(supplier_js, supplier_section)
        except:
            supplier_info = {"name": "N/A", "type": "N/A", "years_on_alibaba": "N/A", "location": "N/A"}
        
        return supplier_info
    
    def _extract_iframe_content(self) -> Dict[str, Any]:
        """Extrae contenido del iframe de descripción"""
        try:
            time.sleep(2)
            
            iframe = None
            for selector in SELECTORS["iframe_description"]:
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
                    
                    iframe_content = self._extract_iframe_content_js()
                    
                    self.driver.get(current_url)
                    time.sleep(1)
                    
                    return iframe_content
            else:
                print("No se encontró iframe de descripción")
                return {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}
                
        except Exception as e:
            print(f"Error con iframe: {e}")
            return {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}
    
    def _extract_iframe_content_js(self) -> Dict[str, Any]:
        """Extrae contenido del iframe usando JavaScript"""
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
        
        return self.driver.execute_script(iframe_content_js)
    
    def _extract_images_selenium(self) -> List[str]:
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