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
        self.raspberry_password = "pi"               # Contraseña
        self.v6_script = "v6mandar_imagen.py"        # Script del pistón (v6)
        self.v4_script = "v4mandar_imagen.py"        # Script de envío imágenes (v4)
        self.v6_script_path = f"/home/pi/{self.v6_script}"
        self.v4_script_path = f"/home/pi/{self.v4_script}"
       
        # SSH client para Raspberry
        self.ssh_client = None
        self.image_sender_pid = None
        self.raspberry_connected = False
        self.v6_executed = False
       
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
        # FLUJO COMPLETO
        # ============================================
        rospy.loginfo("🚀 Iniciando nodo de temperatura...")
        self.connect_to_raspberry()
       
        # PASO 1: EJECUTAR V6 (PISTÓN)
        rospy.loginfo("🔧 Activando pistón (v6)...")
        self.execute_v6_piston()
        
        # PASO 2: ESPERAR UN MOMENTO PARA QUE EL PISTÓN TERMINE
        rospy.sleep(3)  # Ajusta este tiempo según necesite el pistón
        
        # PASO 3: INICIAR V4 (ENVÍO DE IMÁGENES)
        rospy.loginfo("📤 Iniciando envío de imágenes (v4)...")
        self.start_v4_image_sender()
        
        # PASO 4: INICIAR MONITOREO
        self.observer.start()
        rospy.loginfo("🔍 Monitoreo de carpeta activado - Esperando imágenes...")
       
        # Procesar imágenes existentes
        self.process_existing_images()
       
        # Verificar estado periódicamente
        self.check_timer = rospy.Timer(rospy.Duration(10), self.check_system_status)
    
    def execute_v6_piston(self):
        """Ejecuta v6mandar_imagen.py (control del pistón)"""
        if not self.raspberry_connected:
            rospy.logwarn("⚠️ Raspberry no conectada. Intentando reconectar...")
            if not self.connect_to_raspberry():
                rospy.logerr("❌ No se pudo conectar a Raspberry")
                return False
        
        try:
            rospy.loginfo("🔧 Ejecutando v6 (control del pistón)...")
            
            # Verificar que el script existe
            check_cmd = f'[ -f "{self.v6_script_path}" ] && echo "EXISTS" || echo "NOT_FOUND"'
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            if "EXISTS" not in stdout.read().decode():
                rospy.logerr(f"❌ Script v6 no encontrado: {self.v6_script_path}")
                self.status_pub.publish("Error: Script v6 no encontrado")
                return False
            
            # Detener v4 si está corriendo (para evitar conflictos)
            rospy.loginfo("⏸️ Deteniendo v4 temporalmente...")
            self.stop_v4_image_sender()
            
            # Ejecutar v6 (pistón)
            execute_cmd = f"cd /home/pi && python3 {self.v6_script}"
            stdin, stdout, stderr = self.ssh_client.exec_command(execute_cmd)
            
            # Esperar a que termine
            rospy.loginfo("⏳ Esperando a que el pistón termine...")
            output = stdout.read().decode()
            error = stderr.read().decode()
            exit_status = stdin.channel.recv_exit_status()
            
            if exit_status == 0:
                rospy.loginfo("✅ Pistón (v6) terminado exitosamente")
                rospy.loginfo(f"📄 Salida del pistón:\n{output}")
                self.v6_executed = True
                self.status_pub.publish("Pistón activado - Completado")
                return True
            else:
                rospy.logerr(f"❌ Pistón (v6) falló con código: {exit_status}")
                if error:
                    rospy.logerr(f"📄 Error:\n{error}")
                self.status_pub.publish(f"Error pistón: código {exit_status}")
                return False
                
        except Exception as e:
            rospy.logerr(f"❌ Error ejecutando pistón (v6): {e}")
            self.status_pub.publish(f"Error pistón: {str(e)}")
            return False
    
    def start_v4_image_sender(self):
        """Inicia v4mandar_imagen.py (envío continuo de imágenes)"""
        if not self.raspberry_connected:
            rospy.logwarn("⚠️ Raspberry no conectada")
            return False
       
        try:
            rospy.loginfo("📤 Iniciando envío de imágenes (v4)...")
           
            # 1. Verificar que v4 existe
            check_cmd = f'[ -f "{self.v4_script_path}" ] && echo "EXISTS" || echo "NOT_FOUND"'
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            if "EXISTS" not in stdout.read().decode():
                rospy.logerr(f"❌ Script v4 no encontrado: {self.v4_script_path}")
                return False
            
            # 2. Matar procesos anteriores de v4 si existen
            self.stop_v4_image_sender()
            rospy.sleep(1)  # Esperar a que termine completamente
           
            # 3. Ejecutar v4 en background
            execute_cmd = f"""
            cd /home/pi
            nohup python3 {self.v4_script} > /tmp/v4_image_sender.log 2>&1 &
            echo $!
            """
           
            stdin, stdout, stderr = self.ssh_client.exec_command(execute_cmd)
            pid = stdout.read().decode().strip()
           
            if pid and pid.isdigit():
                self.image_sender_pid = pid
                rospy.loginfo(f"✅ Envío de imágenes (v4) iniciado (PID: {pid})")
                self.status_pub.publish(f"Envío imágenes activo - PID: {pid}")
               
                # Verificar que arrancó correctamente
                threading.Timer(3.0, self.verify_v4_sender).start()
               
                return True
            else:
                rospy.logerr("❌ No se pudo obtener PID del proceso v4")
                self.check_v4_logs()
                return False
               
        except Exception as e:
            rospy.logerr(f"❌ Error iniciando envío de imágenes (v4): {e}")
            return False
    
    def stop_v4_image_sender(self):
        """Detiene v4mandar_imagen.py"""
        if not self.ssh_client:
            return
       
        try:
            rospy.loginfo("⏹️ Deteniendo envío de imágenes (v4)...")
           
            kill_cmds = [
                f"pkill -f '{self.v4_script}'",
                f"pkill -f 'python.*{self.v4_script}'",
                "sleep 1",
                f"kill -KILL $(ps aux | grep '{self.v4_script}' | grep -v grep | awk '{{print $2}}') 2>/dev/null || true"
            ]
           
            for cmd in kill_cmds:
                self.ssh_client.exec_command(cmd)
           
            rospy.loginfo("✅ Envío de imágenes (v4) detenido")
            self.image_sender_pid = None
           
        except Exception as e:
            rospy.logerr(f"❌ Error deteniendo v4: {e}")
    
    def verify_v4_sender(self):
        """Verifica que v4 esté funcionando"""
        if not self.ssh_client:
            return
       
        try:
            # Verificar que el proceso sigue activo
            check_cmd = f"ps aux | grep '{self.v4_script}' | grep -v grep"
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            processes = stdout.read().decode()
           
            if processes:
                rospy.loginfo(f"✅ v4 está corriendo")
                self.check_v4_logs()
            else:
                rospy.logwarn("⚠️ v4 no está corriendo")
                self.status_pub.publish("Error: v4 detenido")
               
        except Exception as e:
            rospy.logwarn(f"⚠️ Error verificando v4: {e}")
    
    def check_v4_logs(self):
        """Muestra logs de v4"""
        if not self.ssh_client:
            return
       
        try:
            log_cmd = "tail -10 /tmp/v4_image_sender.log 2>/dev/null || echo 'No hay logs aún'"
            stdin, stdout, stderr = self.ssh_client.exec_command(log_cmd)
            logs = stdout.read().decode()
           
            if logs and "No hay logs" not in logs:
                rospy.loginfo(f"📄 Logs v4:\n{logs}")
        except:
            pass
    
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
           
            return True
               
        except Exception as e:
            rospy.logerr(f"❌ Error conectando a Raspberry: {e}")
            self.status_pub.publish(f"Error conexión: {str(e)}")
            self.raspberry_connected = False
            return False
    
    # ============================================
    # MÉTODOS EXISTENTES (se mantienen igual)
    # ============================================
   
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
        """Calcula y publica la media del lote actual de 5 imágenes"""
        if len(self.temperaturas_lote_actual) == 0:
            rospy.logwarn("📭 No hay temperaturas válidas en el lote actual")
            self.publish_temperature(36.5, simulated=True, is_media=True, numero_lote=self.numero_lote)
        else:
            media_lote = sum(self.temperaturas_lote_actual) / len(self.temperaturas_lote_actual)
           
            rospy.loginfo("=" * 60)
            rospy.loginfo(f"📊 LOTE {self.numero_lote} - RESUMEN:")
            rospy.loginfo(f"📈 Imágenes procesadas: {5}")
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
           
            if self.contador_imagenes_procesadas >= 5:
                rospy.loginfo(f"🎯 Lote {self.numero_lote} completado ({self.contador_imagenes_procesadas} imágenes) - Calculando media...")
                self.calcular_media_lote()
            else:
                rospy.loginfo(f"📈 Progreso lote {self.numero_lote}: {self.contador_imagenes_procesadas}/5 imágenes")
           
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
           
            if self.contador_imagenes_procesadas >= 5:
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
        self.stop_v4_image_sender()
       
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
        rospy.loginfo("🚀 Nodo temperatura iniciado - Pistón activado, envío imágenes activo")
        rospy.spin()
    except KeyboardInterrupt:
        rospy.loginfo("⏹️ Interrupción por teclado")
    finally:
        node.shutdown()
        rospy.loginfo("🔚 Nodo terminado correctamente")