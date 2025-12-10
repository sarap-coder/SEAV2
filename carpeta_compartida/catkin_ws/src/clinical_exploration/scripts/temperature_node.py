#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32, String
import cv2
import os
import time
import pytesseract
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import paramiko  # Para SSH a Raspberry
import threading

class ImageHandler(FileSystemEventHandler):
    def __init__(self, temperature_node):
        self.temperature_node = temperature_node
        self.processing_files = set()
   
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename = os.path.basename(event.src_path)
           
            if filename in self.processing_files:
                return
               
            self.processing_files.add(filename)
            rospy.loginfo(f"📸 Nueva imagen detectada: {filename}")
           
            self.wait_for_file_ready(event.src_path)
            self.temperature_node.process_single_image(event.src_path)
           
            rospy.Timer(rospy.Duration(5), lambda e: self.processing_files.discard(filename), oneshot=True)
   
    def wait_for_file_ready(self, file_path, timeout=10):
        """Espera a que el archivo esté completamente escrito"""
        start_time = time.time()
        last_size = -1
       
        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    rospy.loginfo(f"✅ Archivo listo, tamaño: {current_size} bytes")
                    return True
               
                last_size = current_size
                rospy.sleep(0.5)
               
            except OSError:
                rospy.sleep(0.2)
       
        rospy.logwarn(f"⚠️ Timeout esperando por archivo: {file_path}")
        return False

class TemperatureNode:
    def __init__(self):
        rospy.init_node('temperature_node')
       
        # ============================================
        # CONFIGURACIÓN RASPBERRY (AJUSTAR ESTOS VALORES!)
        # ============================================
        self.raspberry_ip = "10.172.209.145"          # IP de tu Raspberry
        self.raspberry_user = "pi"                   # Usuario Raspberry
        self.raspberry_password = "pi"        # Contraseña
        self.raspberry_script = "v4mandar_imagen.py" # Script a ejecutar
        self.raspberry_script_path = f"/home/pi/{self.raspberry_script}"
       
        # SSH client para Raspberry
        self.ssh_client = None
        self.image_sender_pid = None
        self.raspberry_connected = False
       
        # ============================================
        # CONFIGURACIÓN TEMPERATURA
        # ============================================
        self.temp_pub = rospy.Publisher('/temperature_result', Float32, queue_size=10)
        self.status_pub = rospy.Publisher('/temperature_status', String, queue_size=10)
        self.ruta_carpeta = "/home/tiago/carpeta_compartida/imagenes_recibidas"
        self.archivos_vistos = set()

        # Variables para media por lotes
        self.temperaturas_lote_actual = []
        self.contador_imagenes_procesadas = 0
        self.numero_lote = 1
       
        # Asegurar que la carpeta existe
        os.makedirs(self.ruta_carpeta, exist_ok=True)

        # Configurar watchdog
        self.event_handler = ImageHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.ruta_carpeta, recursive=False)
       
        rospy.Subscriber('/clinical_instructions', String, self.instruction_callback)
       
        # ============================================
        # PASO 1: CONECTAR Y PREPARAR RASPBERRY
        # ============================================
        rospy.loginfo("🚀 Iniciando nodo de temperatura...")
        self.connect_to_raspberry()
       
        # ============================================
        # PASO 2: INICIAR ENVÍO DE IMÁGENES
        # ============================================
        self.start_image_sender()
       
        # ============================================
        # PASO 3: INICIAR MONITOREO DE CARPETA
        # ============================================
        self.observer.start()
        rospy.loginfo("🔍 Monitoreo de carpeta activado - Esperando imágenes...")
        rospy.loginfo("📊 Modo media por lotes: cada 10 imágenes → media independiente")
       
        # Procesar imágenes existentes al inicio
        self.process_existing_images()
       
        # Verificar estado periódicamente
        self.check_timer = rospy.Timer(rospy.Duration(10), self.check_system_status)
       
    def connect_to_raspberry(self):
        """Conecta a Raspberry Pi vía SSH"""
        try:
            rospy.loginfo(f"🔌 Conectando a Raspberry Pi ({self.raspberry_ip})...")
           
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.raspberry_ip,
                username=self.raspberry_user,
                password=self.raspberry_password,
                timeout=15
            )
           
            # Probar conexión
            stdin, stdout, stderr = self.ssh_client.exec_command('hostname')
            hostname = stdout.read().decode().strip()
           
            self.raspberry_connected = True
            rospy.loginfo(f"✅ Conectado a Raspberry: {hostname}")
            self.status_pub.publish(f"Conectado a Raspberry: {hostname}")
           
            # Verificar que el script existe
            check_cmd = f'[ -f "{self.raspberry_script_path}" ] && echo "EXISTS" || echo "NOT_FOUND"'
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            if "EXISTS" in stdout.read().decode():
                rospy.loginfo(f"✅ Script encontrado: {self.raspberry_script}")
            else:
                rospy.logerr(f"❌ Script no encontrado: {self.raspberry_script_path}")
                self.status_pub.publish(f"Error: Script no encontrado")
                return False
           
            return True
               
        except Exception as e:
            rospy.logerr(f"❌ Error conectando a Raspberry: {e}")
            self.status_pub.publish(f"Error conexión: {str(e)}")
            self.raspberry_connected = False
            return False
   
    def start_image_sender(self):
        """Ejecuta el script v4mandar_imagen.py en Raspberry"""
        if not self.raspberry_connected:
            rospy.logwarn("⚠️ Raspberry no conectada. Intentando reconectar...")
            if not self.connect_to_raspberry():
                rospy.logerr("❌ No se pudo conectar a Raspberry")
                return
       
        try:
            rospy.loginfo("📤 Iniciando envío de imágenes desde Raspberry...")
           
            # 1. Matar procesos anteriores si existen
            kill_cmds = [
                "pkill -f 'v4mandar_imagen.py'",
                "pkill -f 'python.*mandar_imagen'",
                "sleep 1"
            ]
           
            for cmd in kill_cmds:
                self.ssh_client.exec_command(cmd)
           
            # 2. Ejecutar el script en background
            # NOTA: Ajusta el comando según cómo se deba ejecutar tu script
            # Si necesita argumentos o configuración especial, modifica esta línea
            execute_cmd = f"""
            cd /home/pi
            nohup python3 {self.raspberry_script} > /tmp/image_sender.log 2>&1 &
            echo $!
            """
           
            stdin, stdout, stderr = self.ssh_client.exec_command(execute_cmd)
            pid = stdout.read().decode().strip()
           
            if pid and pid.isdigit():
                self.image_sender_pid = pid
                rospy.loginfo(f"✅ Envío de imágenes iniciado (PID: {pid})")
                self.status_pub.publish(f"Envío imágenes activo - PID: {pid}")
               
                # Verificar que arrancó correctamente
                threading.Timer(3.0, self.verify_image_sender).start()
               
                return True
            else:
                rospy.logerr("❌ No se pudo obtener PID del proceso")
                self.check_raspberry_logs()
                return False
               
        except Exception as e:
            rospy.logerr(f"❌ Error iniciando envío de imágenes: {e}")
            self.status_pub.publish(f"Error inicio: {str(e)}")
            return False
   
    def verify_image_sender(self):
        """Verifica que el envío de imágenes esté funcionando"""
        if not self.ssh_client or not self.image_sender_pid:
            return
       
        try:
            # Verificar que el proceso sigue activo
            check_cmd = f"ps -p {self.image_sender_pid} > /dev/null && echo 'RUNNING' || echo 'STOPPED'"
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            status = stdout.read().decode().strip()
           
            if status == 'RUNNING':
                rospy.loginfo(f"✅ Envío de imágenes activo (PID: {self.image_sender_pid})")
               
                # Mostrar logs recientes
                self.check_raspberry_logs()
            else:
                rospy.logwarn("⚠️ Envío de imágenes no está corriendo")
                self.status_pub.publish("Error: Envío detenido")
               
        except Exception as e:
            rospy.logwarn(f"⚠️ Error verificando envío: {e}")
   
    def check_raspberry_logs(self):
        """Muestra logs del script en Raspberry"""
        if not self.ssh_client:
            return
       
        try:
            log_cmd = "tail -10 /tmp/image_sender.log 2>/dev/null || echo 'No hay logs aún'"
            stdin, stdout, stderr = self.ssh_client.exec_command(log_cmd)
            logs = stdout.read().decode()
           
            if logs and "No hay logs" not in logs:
                rospy.loginfo(f"📄 Logs Raspberry:\n{logs}")
        except:
            pass
   
    def stop_image_sender(self):
        """Detiene el envío de imágenes en Raspberry"""
        if not self.ssh_client or not self.image_sender_pid:
            return
       
        try:
            rospy.loginfo(f"⏹️ Deteniendo envío de imágenes (PID: {self.image_sender_pid})...")
           
            kill_cmds = [
                f"kill -TERM {self.image_sender_pid}",
                "sleep 1",
                f"kill -KILL {self.image_sender_pid} 2>/dev/null || true",
                "pkill -f 'v4mandar_imagen.py'"
            ]
           
            for cmd in kill_cmds:
                self.ssh_client.exec_command(cmd)
           
            rospy.loginfo("✅ Envío de imágenes detenido")
            self.image_sender_pid = None
            self.status_pub.publish("Envío detenido")
           
        except Exception as e:
            rospy.logerr(f"❌ Error deteniendo envío: {e}")
   
    def check_system_status(self, event):
        """Verifica periódicamente el estado del sistema"""
        if not self.raspberry_connected:
            rospy.logwarn("⚠️ Raspberry desconectada. Reintentando...")
            self.connect_to_raspberry()
       
        # Contar imágenes en carpeta
        if os.path.exists(self.ruta_carpeta):
            images_count = len([f for f in os.listdir(self.ruta_carpeta)
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
           
            if images_count > 0:
                rospy.loginfo(f"📂 Imágenes en carpeta: {images_count}")
       
    # ============================================
    # MÉTODOS EXISTENTES (se mantienen igual)
    # ============================================
   
    def process_existing_images(self):
        """Procesa imágenes que ya estaban en la carpeta al iniciar"""
        if os.path.exists(self.ruta_carpeta):
            archivos = [f for f in os.listdir(self.ruta_carpeta)
                       if f.lower().endswith((".jpeg", ".jpg", ".png"))]
           
            if archivos:
                rospy.loginfo(f"📁 Procesando {len(archivos)} imágenes existentes")
                for archivo in archivos:
                    if archivo not in self.archivos_vistos:
                        image_path = os.path.join(self.ruta_carpeta, archivo)
                        self.process_single_image(image_path)
       
    def instruction_callback(self, msg):
        if "temperature" in msg.data.lower():
            rospy.loginfo("🔍 Instrucción de temperatura recibida")
            self.process_existing_images()
   
    def calcular_media_lote(self):
        """Calcula y publica la media del lote actual de 10 imágenes"""
        if len(self.temperaturas_lote_actual) == 0:
            rospy.logwarn("📭 No hay temperaturas válidas en el lote actual")
            self.publish_temperature(36.5, simulated=True, is_media=True, numero_lote=self.numero_lote)
        else:
            media_lote = sum(self.temperaturas_lote_actual) / len(self.temperaturas_lote_actual)
           
            rospy.loginfo("=" * 60)
            rospy.loginfo(f"📊 LOTE {self.numero_lote} - RESUMEN:")
            rospy.loginfo(f"📈 Imágenes procesadas: {10}")
            rospy.loginfo(f"✅ Lecturas exitosas: {len(self.temperaturas_lote_actual)}")
            rospy.loginfo(f"🌡️ Temperaturas válidas: {self.temperaturas_lote_actual}")
            rospy.loginfo(f"🧮 Media del lote: {media_lote:.2f}°C")
            if len(self.temperaturas_lote_actual) > 1:
                rospy.loginfo(f"🔢 Rango: {min(self.temperaturas_lote_actual):.1f}°C - {max(self.temperaturas_lote_actual):.1f}°C")
            rospy.loginfo("=" * 60)
           
            self.publish_temperature(media_lote, is_media=True, numero_lote=self.numero_lote)
       
        self.temperaturas_lote_actual = []
        self.contador_imagenes_procesadas = 0
        self.numero_lote += 1
       
        rospy.loginfo(f"🔄 Lote {self.numero_lote-1} completado. Iniciando lote {self.numero_lote}...")
       
    def process_single_image(self, image_path):
        """Procesa una sola imagen"""
        custom_config = r'--oem 3 --psm 6 outputbase digits'
        filename = os.path.basename(image_path)
       
        rospy.loginfo(f"🔄 Iniciando procesamiento de: {filename}")
       
        self.contador_imagenes_procesadas += 1
        rospy.loginfo(f"📊 Imágenes procesadas totales: {self.contador_imagenes_procesadas}")
       
        img = cv2.imread(image_path)
        if img is not None:
            try:
                rospy.loginfo("🎯 Procesando ROI...")
               
                # Recortar región de interés (ROI)
                roi = img[1:51, 1:101]

                # Convertir a un canal
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

                # Reducir ruido
                gray = cv2.GaussianBlur(gray, (3, 3), 0)  

                # Binarizar
                _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
                thresh = 255 - thresh
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

                # Reconocer dígitos
                rospy.loginfo("🔍 Reconociendo dígitos con Tesseract...")
                texto = pytesseract.image_to_string(roi, config=custom_config)
                rospy.loginfo(f"📝 Texto reconocido: '{texto}'")

                # Tomar solo los primeros 3 dígitos reconocidos
                digitos = ''.join([c for c in texto if c.isdigit()])[:3]

                # Calcular valor de temperatura
                if len(digitos) == 3:
                    val_temp = int(digitos[0])*10 + int(digitos[1]) + int(digitos[2])*0.1
                    rospy.loginfo(f"🔢 Dígitos detectados: {digitos}, Temperatura: {val_temp}°C")
                   
                    self.temperaturas_lote_actual.append(val_temp)
                    self.publish_temperature(val_temp, is_individual=True)
                   
                else:
                    rospy.logwarn(f"❌ No se pudieron detectar dígitos. Texto: '{texto}'")
                   
            except Exception as e:
                rospy.logerr(f"❌ Error procesando imagen {filename}: {e}")
           
            if self.contador_imagenes_procesadas >= 10:
                rospy.loginfo(f"🎯 Lote {self.numero_lote} completado ({self.contador_imagenes_procesadas} imágenes) - Calculando media...")
                self.calcular_media_lote()
            else:
                rospy.loginfo(f"📈 Progreso lote {self.numero_lote}: {self.contador_imagenes_procesadas}/10 imágenes")
           
            self.archivos_vistos.add(filename)
           
            rospy.sleep(0.5)
           
            try:
                os.remove(image_path)
                rospy.loginfo(f"🗑️ Imagen eliminada: {filename}")
            except Exception as e:
                rospy.logwarn(f"⚠️ No se pudo eliminar {filename}: {e}")
        else:
            rospy.logwarn(f"❌ No se pudo leer la imagen: {filename}")
            self.archivos_vistos.add(filename)
           
            if self.contador_imagenes_procesadas >= 10:
                rospy.loginfo(f"🎯 Lote {self.numero_lote} completado ({self.contador_imagenes_procesadas} imágenes) - Calculando media...")
                self.calcular_media_lote()
   
    def publish_temperature(self, temperatura, simulated=False, is_individual=False, is_media=False, numero_lote=1):
        """Publica la temperatura en ROS"""
        temp_msg = Float32()
        temp_msg.data = temperatura
        self.temp_pub.publish(temp_msg)
       
        if is_media:
            rospy.loginfo(f"📊 [LOTE {numero_lote}] TEMPERATURA MEDIA: {temperatura:.2f}°C")
            self.status_pub.publish(f"Temperatura media: {temperatura:.2f}°C")
        elif is_individual:
            rospy.loginfo(f"✅ Temperatura individual: {temperatura}°C")
        else:
            rospy.loginfo(f"✅ Temperatura: {temperatura}°C")
   
    def shutdown(self):
        """Cierra el nodo correctamente"""
        rospy.loginfo("🧹 Cerrando nodo de temperatura...")
       
        # Detener envío de imágenes en Raspberry
        self.stop_image_sender()
       
        # Cerrar conexión SSH
        if self.ssh_client:
            try:
                self.ssh_client.close()
                rospy.loginfo("🔌 Conexión SSH cerrada")
            except:
                pass
       
        # Calcular media final si hay imágenes procesadas
        if self.contador_imagenes_procesadas > 0:
            rospy.loginfo(f"🔚 Calculando media final del lote {self.numero_lote}...")
            if self.temperaturas_lote_actual:
                media_final = sum(self.temperaturas_lote_actual) / len(self.temperaturas_lote_actual)
                rospy.loginfo(f"📊 MEDIA FINAL: {media_final:.2f}°C")
                self.publish_temperature(media_final, is_media=True, numero_lote=self.numero_lote)
            else:
                rospy.logwarn(f"📭 Lote sin lecturas válidas")
               
        # Detener observer
        self.observer.stop()
        self.observer.join()
       
        rospy.loginfo("✅ Nodo de temperatura terminado")

if __name__ == '__main__':
    node = TemperatureNode()
    try:
        rospy.loginfo("🚀 Nodo temperatura iniciado - Control automático de Raspberry")
        rospy.spin()
    except KeyboardInterrupt:
        rospy.loginfo("⏹️ Interrupción por teclado")
    finally:
        node.shutdown()
        rospy.loginfo("🔚 Nodo terminado correctamente")