"""
Script de prueba para las notificaciones del scraper
"""
from notification_handler import notification_handler
import time

# Duración de cada notificación (en segundos)
DURACION = 5

notification_handler.send_success_notification("Notificación 1: Éxito")
time.sleep(DURACION + 1)

notification_handler.send_error_notification("Notificación 2: Error")
time.sleep(DURACION + 1)

notification_handler.send_captcha_alert("Notificación 3: Info", title="Alibaba Scraper - Info", duration=DURACION)
time.sleep(DURACION + 1)

def test_notifications():
    """Prueba todas las notificaciones disponibles"""
    print("🧪 Probando sistema de notificaciones...")
    
    # Prueba 1: Notificación de CAPTCHA
    print("\n1. Probando notificación de CAPTCHA...")
    notification_handler.send_captcha_alert(
        message="¡CAPTCHA detectado! El scraper necesita tu ayuda.",
        title="Alibaba Scraper - CAPTCHA Detectado"
    )
    time.sleep(3)
    
    # Prueba 2: Notificación de éxito
    print("\n2. Probando notificación de éxito...")
    notification_handler.send_success_notification(
        "Scraping completado exitosamente. Se procesaron 50 productos."
    )
    time.sleep(3)
    
    # Prueba 3: Notificación de error
    print("\n3. Probando notificación de error...")
    notification_handler.send_error_notification(
        "Error en el scraping: No se pudo conectar con Alibaba."
    )
    
    print("\n✅ Pruebas de notificación completadas!")


if __name__ == "__main__":
    test_notifications() 