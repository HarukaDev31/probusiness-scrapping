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
        let attrContainer = document.querySelector('div[data-testid="module-attribute"]');
        if (!attrContainer) {
            attrContainer = document.querySelector('div[data-module-name="module_attribute"]');
        }
        
        details.attributes = {};
        if (attrContainer) {
            // Buscar TODAS las filas de atributos en cualquier nivel del contenedor
            const allAttrRows = attrContainer.querySelectorAll('div.id-grid');
            
            allAttrRows.forEach(row => {
                // Verificar que esta fila no esté en la sección de embalaje
                const isInPackagingSection = row.closest('div').querySelector('h3') && 
                                           row.closest('div').querySelector('h3').textContent.includes('Embalaje y entrega');
                
                if (!isInPackagingSection) {
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
        if (attrContainer) {
            // Buscar el h3 que contenga "Embalaje y entrega"
            const h3Elements = attrContainer.querySelectorAll('h3');
            let packagingSection = null;
            for (const h3 of h3Elements) {
                if (h3.textContent.includes('Embalaje y entrega')) {
                    packagingSection = h3;
                    break;
                }
            }
            
            // Si no se encuentra en h3, buscar en cualquier elemento que contenga el texto
            if (!packagingSection) {
                const allElements = attrContainer.querySelectorAll('*');
                for (const element of allElements) {
                    if (element.textContent && element.textContent.includes('Embalaje y entrega')) {
                        packagingSection = element;
                        break;
                    }
                }
            }
            
            if (packagingSection) {
                // Buscar el contenedor de embalaje - puede estar en diferentes estructuras
                let packagingContainer = packagingSection.closest('div').querySelector('.id-grid');
                if (!packagingContainer) {
                    // Buscar en la estructura alternativa
                    const nextDiv = packagingSection.closest('div').nextElementSibling;
                    if (nextDiv) {
                        packagingContainer = nextDiv.querySelector('.id-grid');
                    }
                }
                
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
        
        // URL del detalle de Alibaba
        details.alibaba_detail_url = window.location.href;
        
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
        
        // Extraer videos del carrusel principal
        const carouselVideos = document.querySelectorAll([
            'div[data-module="MainImage"] video',
            'div.main-index video',
            '.detail-video-container video',
            'div[data-submodule="ProductImageMain"] video'
        ].join(','));
        
        carouselVideos.forEach(video => {
            const videoSrc = video.src || video.getAttribute('src');
            if (videoSrc && !videoSrc.includes('data:') && !details.images.includes(videoSrc)) {
                details.images.push(videoSrc);
            }
        });
        
        // Extraer videos de elementos source dentro de video
        const videoSources = document.querySelectorAll([
            'div[data-module="MainImage"] video source',
            'div.main-index video source',
            '.detail-video-container video source',
            'div[data-submodule="ProductImageMain"] video source'
        ].join(','));
        
        videoSources.forEach(source => {
            const sourceSrc = source.src || source.getAttribute('data-src');
            if (sourceSrc && !sourceSrc.includes('data:') && !details.images.includes(sourceSrc)) {
                details.images.push(sourceSrc);
            }
        });
        
        details.images = [...new Set(details.images)].map(url => {
            if (url.startsWith('//')) {
                return 'https:' + url;
            }
            return url;
        });
        
        // LIMITAR A MÁXIMO 15 IMÁGENES
        if (details.images.length > 15) {
            details.images = details.images.slice(0, 15);
        }
        
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
                    print("Iframe encontrado pero sin src válido")
                    return {'html': '', 'text': '', 'images': [], 'reconstructed_html': ''}
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
        
        // Crear una copia del body para trabajar sin modificar el original
        const bodyClone = document.body.cloneNode(true);
        
        // Remover divs específicos que no queremos incluir
        const divsToRemove = [
            'div.detailProductNavigation',
            'div.detailTextContent'
        ];
        
        divsToRemove.forEach(selector => {
            const element = bodyClone.querySelector(selector);
            if (element) {
                element.remove();
            }
        });
        
        // Remover elementos module-title específicos que no queremos
        const moduleTitlesToRemove = [
            'detailSellerRecommend'
        ];
        
        moduleTitlesToRemove.forEach(moduleTitle => {
            const elements = bodyClone.querySelectorAll(`div[module-title="${moduleTitle}"]`);
            elements.forEach(element => {
                element.remove();
            });
        });
        
        content.html = bodyClone.innerHTML;
        content.text = bodyClone.innerText;
        
        content.images = [];
        
        // Extraer imágenes
        const imgs = bodyClone.querySelectorAll('img');
        imgs.forEach(img => {
            const src = img.src || img.getAttribute('data-src');
            if (src && !src.includes('data:') && !src.includes('.gif')) {
                content.images.push(src.startsWith('//') ? 'https:' + src : src);
            }
        });
        
        // Extraer videos
        const videos = bodyClone.querySelectorAll('video');
        videos.forEach(video => {
            const src = video.src || video.getAttribute('data-src');
            if (src && !src.includes('data:')) {
                content.images.push(src.startsWith('//') ? 'https:' + src : src);
            }
        });
        
        // Extraer videos de elementos iframe (videos embebidos)
        const videoIframes = bodyClone.querySelectorAll('iframe[src*="video"], iframe[src*="youtube"], iframe[src*="vimeo"]');
        videoIframes.forEach(iframe => {
            const src = iframe.src;
            if (src && !src.includes('data:')) {
                content.images.push(src.startsWith('//') ? 'https:' + src : src);
            }
        });
        
        // Extraer videos de elementos source dentro de video
        const videoSources = bodyClone.querySelectorAll('video source');
        videoSources.forEach(source => {
            const src = source.src || source.getAttribute('data-src');
            if (src && !src.includes('data:')) {
                content.images.push(src.startsWith('//') ? 'https:' + src : src);
            }
        });
        
        // LIMITAR A MÁXIMO 15 IMÁGENES
        if (content.images.length > 15) {
            content.images = content.images.slice(0, 15);
        }

        // GENERAR HTML RECONSTRUIDO
        content.reconstructed_html = '';

        const tables = bodyClone.querySelectorAll('table');
        const sections = bodyClone.querySelectorAll('.magic-0');

        let reconstructedHTML = '';
        reconstructedHTML += '<body class="font-sans mx-5">';

        const mainTitle = bodyClone.querySelector('.magic-9');
        if (mainTitle) {
            reconstructedHTML += '<h1 class="text-3xl font-bold my-6">' + mainTitle.textContent.trim() + '</h1>';
        }

        sections.forEach(section => {
            reconstructedHTML += '<div class="section my-8">';
            reconstructedHTML += '<h2 class="text-2xl font-semibold border-b-2 border-gray-800 pb-3 mb-4">' + section.textContent.trim() + '</h2>';
            
            let nextElement = section.closest('.J_module')?.nextElementSibling;
            
            while (nextElement && !nextElement.querySelector('.magic-0')) {
                // Procesar imágenes
                const images = nextElement.querySelectorAll('img');
                images.forEach(img => {
                    const src = img.src || img.getAttribute('data-src');
                    if (src && !src.includes('data:')) {
                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                        reconstructedHTML += '<img class="product-image w-full my-5" src="' + fullSrc + '" alt="Product Image">';
                    }
                });
                
                // Procesar videos
                const videos = nextElement.querySelectorAll('video');
                videos.forEach(video => {
                    const src = video.src || video.getAttribute('data-src');
                    if (src && !src.includes('data:')) {
                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                        reconstructedHTML += '<video class="product-video w-full my-5" controls><source src="' + fullSrc + '" type="video/mp4">Tu navegador no soporta el elemento video.</video>';
                    }
                });
                
                // Procesar videos embebidos
                const videoIframes = nextElement.querySelectorAll('iframe[src*="video"], iframe[src*="youtube"], iframe[src*="vimeo"]');
                videoIframes.forEach(iframe => {
                    const src = iframe.src;
                    if (src && !src.includes('data:')) {
                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                        reconstructedHTML += '<iframe class="product-video w-full my-5" src="' + fullSrc + '" frameborder="0" allowfullscreen></iframe>';
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

        const allImages = bodyClone.querySelectorAll('img');
        const allVideos = bodyClone.querySelectorAll('video');
        const allVideoIframes = bodyClone.querySelectorAll('iframe[src*="video"], iframe[src*="youtube"], iframe[src*="vimeo"]');
        
        // Crear arrays para limitar a máximo 15 elementos
        let limitedImages = Array.from(allImages).slice(0, 15);
        let limitedVideos = Array.from(allVideos).slice(0, 15);
        let limitedVideoIframes = Array.from(allVideoIframes).slice(0, 15);
        
        // Combinar todos los elementos multimedia y limitar a 15 total
        let allMediaElements = [...limitedImages, ...limitedVideos, ...limitedVideoIframes];
        if (allMediaElements.length > 15) {
            allMediaElements = allMediaElements.slice(0, 15);
        }
        
        if (allMediaElements.length > 0) {
            reconstructedHTML += '<div class="section my-8"><h2 class="text-2xl font-semibold border-b-2 border-gray-800 pb-3 mb-4">Imágenes y Videos del Producto</h2>';
            
            // Agregar elementos multimedia limitados
            allMediaElements.forEach(element => {
                if (element.tagName === 'IMG') {
                    const src = element.src || element.getAttribute('data-src');
                    if (src && !src.includes('data:') && !src.includes('.gif')) {
                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                        reconstructedHTML += '<img class="product-image w-full my-5" src="' + fullSrc + '" alt="Product Image">';
                    }
                } else if (element.tagName === 'VIDEO') {
                    const src = element.src || element.getAttribute('data-src');
                    if (src && !src.includes('data:')) {
                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                        reconstructedHTML += '<video class="product-video w-full my-5" controls><source src="' + fullSrc + '" type="video/mp4">Tu navegador no soporta el elemento video.</video>';
                    }
                } else if (element.tagName === 'IFRAME') {
                    const src = element.src;
                    if (src && !src.includes('data:')) {
                        const fullSrc = src.startsWith('//') ? 'https:' + src : src;
                        reconstructedHTML += '<iframe class="product-video w-full my-5" src="' + fullSrc + '" frameborder="0" allowfullscreen></iframe>';
                    }
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
        """Método de respaldo para extraer imágenes y videos usando Selenium"""
        images = []
        
        try:
            thumbnails = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'div[data-submodule="ProductImageThumbsList"] div[role="group"]'
            )
            
            for i, thumb in enumerate(thumbnails[:15]):  # Cambiar de 10 a 15
                try:
                    self.driver.execute_script("arguments[0].click();", thumb)
                    time.sleep(0.5)
                    
                    # Intentar extraer imagen principal
                    try:
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
                        pass
                    
                    # Intentar extraer video principal
                    try:
                        main_video = self.driver.find_element(
                            By.CSS_SELECTOR, 
                            'div[data-submodule="ProductImageMain"] video'
                        )
                        
                        video_src = main_video.get_attribute('src')
                        if video_src and video_src not in images:
                            if video_src.startswith('//'):
                                video_src = 'https:' + video_src
                            images.append(video_src)
                    except:
                        pass
                    
                    # Intentar extraer video de elementos source
                    try:
                        video_sources = self.driver.find_elements(
                            By.CSS_SELECTOR, 
                            'div[data-submodule="ProductImageMain"] video source'
                        )
                        
                        for source in video_sources:
                            source_src = source.get_attribute('src') or source.get_attribute('data-src')
                            if source_src and source_src not in images:
                                if source_src.startswith('//'):
                                    source_src = 'https:' + source_src
                                images.append(source_src)
                    except:
                        pass
                        
                except:
                    continue
            
        except Exception as e:
            print(f"Error extrayendo imágenes y videos con Selenium: {e}")
        
        # LIMITAR A MÁXIMO 15 IMÁGENES/VIDEOS
        if len(images) > 15:
            images = images[:15]
        
        return images 