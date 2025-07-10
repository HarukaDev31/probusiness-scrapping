"""
Configuración del scraper de Alibaba
"""
import os
from typing import List

# Configuración de Chrome
CHROME_OPTIONS = {
    "headless": False,
    "window_size": "1920,1080",
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
}

# Configuración de tiempos de espera
TIMEOUTS = {
    "short": 5,
    "medium": 10,
    "long": 15,
    "page_load": 2,
    "between_requests": (1, 2),
    "between_products": (2, 3),
    "retry_wait": (2, 4)
}

# Configuración de reintentos
RETRY_CONFIG = {
    "max_page_retries": 3,
    "max_search_retries": 3,
    "max_detail_retries": 3,
    "max_execution_retries": 3,
    "max_captcha_attempts": 5
}
ENV = "prod"
if ENV == "prod":
    BASE_URL = "https://tiendaback.probusiness.pe"
else:
    BASE_URL = "http://localhost:8000"

API_URLS = {
    "get_products": f"{BASE_URL}/api/getProductsToScrapping",
    "mark_completed": f"{BASE_URL}/api/markProductsCompleted",
    "send_products": f"{BASE_URL}/api/products"
}

# Selectores CSS para elementos
SELECTORS = {
    "product_items": ".m-gallery-product-item-v2",
    "product_image": ".search-card-e-slider__img",
    "product_title": ".search-card-e-title",
    "product_price": ".search-card-e-price-main",
    "product_company": ".search-card-e-company",
    "product_link": "a[href*='/product-detail/']",
    "product_moq": ".search-card-e-moq",
    "pagination_next": "a[href*='page='] button.pagination-item",
    "price_container": 'div[data-testid="ladder-price"]',
    "single_price_container": 'div[data-testid="range-price"]',
    "attribute_container": 'div[data-testid="module-attribute"]',
    "supplier_section": 'div[data-module-name="module_unifed_company_card"]',
    "iframe_description": [
        'iframe[src*="descIframe.html"]',
        'iframe[src*="description"]',
        'iframe#description-iframe',
        'div.description-layout iframe',
        'div[id="description-layout"] iframe'
    ]
}

# Selectores para CAPTCHA
CAPTCHA_SELECTORS = [
    "div.nc_wrapper",
    "div#nc_1_wrapper", 
    "div.nc-lang-cnt",
    "div[id*='nocaptcha']",
    "span.nc_iconfont.btn_slide",
    "div.geetest_slider_button",
    "div.slider-btn",
    "iframe[src*='captcha']"
]

SLIDER_SELECTORS = [
    "span.nc_iconfont.btn_slide",
    "span.btn_slide", 
    "div.geetest_slider_button",
    "div.slider-btn",
    "span[class*='btn_slide']",
    "div[class*='slider']",
    ".nc_iconfont",
    "[class*='slide']"
]

# Archivos de salida
OUTPUT_FILES = {
    "csv": "alibaba_products_optimized.csv",
    "json": "alibaba_products_optimized.json",
    "images_report": "alibaba_images_report.txt"
}

# Campos para CSV
CSV_FIELDS = [
    "img", "description", "price", "company", "product_url", "min_order",
    "detailed_description_text", "detailed_description_html", 
    "iframe_content_text", "iframe_content_html", "iframe_content_images",
    "prices", "attributes", "packaging_info", "delivery_lead_times", "images", 
    "original_product_id", "category_id", "alibaba_detail_url", "supplier_name", "supplier_type", 
    "supplier_years", "supplier_location", "supplier_performance"
] 