"""
Manejador de notificaciones para diferentes sistemas operativos
"""
import platform
import os
import time
from typing import Optional


class NotificationHandler:
    """Manejador de notificaciones multiplataforma"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.notification_sound = None
        self._setup_notification_system()
    
    def _setup_notification_system(self):
        """Configura el sistema de notificaciones según el SO"""
        if self.system == "windows":
            try:
                from win10toast import ToastNotifier
                self.toaster = ToastNotifier()
                self.windows_available = True
            except ImportError:
                print("⚠️  win10toast no está instalado. Instala con: pip install win10toast")
                self.windows_available = False
                self._setup_fallback_notification()
        elif self.system == "darwin":  # macOS
            self.macos_available = True
        elif self.system == "linux":
            self.linux_available = True
        else:
            self._setup_fallback_notification()
    
    def _setup_fallback_notification(self):
        """Configura notificación de respaldo usando beep"""
        self.fallback_available = True
    
    def send_captcha_alert(self, message: str = "¡CAPTCHA detectado!", 
                          title: str = "Alibaba Scraper", 
                          duration: int = 10) -> bool:
        """
        Envía una alerta de CAPTCHA detectado
        
        Args:
            message: Mensaje de la notificación
            title: Título de la notificación
            duration: Duración en segundos (Windows)
            
        Returns:
            bool: True si la notificación se envió exitosamente
        """
        try:
            if self.system == "windows" and hasattr(self, 'windows_available') and self.windows_available:
                return self._send_windows_notification(title, message, duration)
            elif self.system == "darwin" and hasattr(self, 'macos_available') and self.macos_available:
                return self._send_macos_notification(title, message)
            elif self.system == "linux" and hasattr(self, 'linux_available') and self.linux_available:
                return self._send_linux_notification(title, message)
            else:
                return self._send_fallback_notification(message)
        except Exception as e:
            print(f"Error enviando notificación: {e}")
            return self._send_fallback_notification(message)
    
    def _send_windows_notification(self, title: str, message: str, duration: int) -> bool:
        """Envía notificación en Windows usando win10toast"""
        try:
            self.toaster.show_toast(
                title,
                message,
                duration=duration,
                threaded=True,
                icon_path=None
            )
            print(f"🔔 Notificación Windows enviada: {title} - {message}")
            return True
        except Exception as e:
            print(f"Error en notificación Windows: {e}")
            return False
    
    def _send_macos_notification(self, title: str, message: str) -> bool:
        """Envía notificación en macOS usando osascript"""
        try:
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            os.system(f"osascript -e '{script}'")
            print(f"🔔 Notificación macOS enviada: {title} - {message}")
            return True
        except Exception as e:
            print(f"Error en notificación macOS: {e}")
            return False
    
    def _send_linux_notification(self, title: str, message: str) -> bool:
        """Envía notificación en Linux usando notify-send"""
        try:
            os.system(f'notify-send "{title}" "{message}" --urgency=critical')
            print(f"🔔 Notificación Linux enviada: {title} - {message}")
            return True
        except Exception as e:
            print(f"Error en notificación Linux: {e}")
            return False
    
    def _send_fallback_notification(self, message: str) -> bool:
        """Notificación de respaldo usando beep y print"""
        try:
            # Hacer beep múltiples veces para llamar la atención
            for _ in range(5):
                print('\a', end='', flush=True)  # Beep
                time.sleep(0.2)
            
            print(f"\n🚨 ALERTA CAPTCHA: {message}")
            print("=" * 50)
            print("¡INTERVENCIÓN MANUAL REQUERIDA!")
            print("El scraper ha detectado un CAPTCHA y necesita tu ayuda.")
            print("=" * 50)
            return True
        except Exception as e:
            print(f"Error en notificación de respaldo: {e}")
            return False
    
    def send_success_notification(self, message: str = "Scraping completado exitosamente") -> bool:
        """Envía notificación de éxito"""
        return self.send_captcha_alert(
            message=message,
            title="Alibaba Scraper - Éxito",
            duration=5
        )
    
    def send_error_notification(self, message: str = "Error en el scraping") -> bool:
        """Envía notificación de error"""
        return self.send_captcha_alert(
            message=message,
            title="Alibaba Scraper - Error",
            duration=8
        )


# Instancia global para usar en otros módulos
notification_handler = NotificationHandler() 