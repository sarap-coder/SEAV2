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

class ImageHandler(FileSystemEventHandler):
    def __init__(self, temperature_node):
        self.temperature_node = temperature_node
        self.processing_files = set()  # Evitar procesar duplicados
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename = os.path.basename(event.src_path)
            
            # Evitar procesar el mismo archivo múltiples veces
            if filename in self.processing_files:
                return
                
            self.processing_files.add(filename)
            rospy.loginfo(f"📸 Nueva imagen detectada: {filename}")
            
            # Esperar a que el archivo esté completamente escrito
            self.wait_for_file_ready(event.src_path)
            
            # Procesar la imagen
            self.temperature_node.process_single_image(event.src_path)
            
            # Remover de la lista de procesamiento después de un tiempo
            rospy.Timer(rospy.Duration(5), lambda e: self.processing_files.discard(filename), oneshot=True)
    
    def wait_for_file_ready(self, file_path, timeout=10):
        """Espera a que el archivo esté completamente escrito"""
        start_time = time.time()
        last_size = -1
        
        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    # El tamaño se estabilizó, el archivo está listo
                    rospy.loginfo(f"✅ Archivo listo, tamaño: {current_size} bytes")
                    return True
                
                last_size = current_size
                rospy.sleep(0.5)  # Esperar medio segundo entre verificaciones
                
            except OSError:
                # El archivo puede no existir momentáneamente
                rospy.sleep(0.2)
        
        rospy.logwarn(f"⚠️ Timeout esperando por archivo: {file_path}")
        return False

class TemperatureNode:
    def __init__(self):
        rospy.init_node('temperature_node')
        
        self.temp_pub = rospy.Publisher('/temperature_result', Float32, queue_size=10)
        self.ruta_carpeta = "/home/tiago/carpeta_compartida/imagenes_recibidas"
        self.archivos_vistos = set()

        # 🔥 MODIFICADO: Variables para calcular la media por lotes independientes
        self.temperaturas_lote_actual = []  # Solo las 10 temperaturas actuales
        self.contador_fotos = 0  # Contador de fotos procesadas en el lote actual
        self.numero_lote = 1  # Número del lote actual
        
        # Asegurar que la carpeta existe
        os.makedirs(self.ruta_carpeta, exist_ok=True)

        # Configurar watchdog
        self.event_handler = ImageHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.ruta_carpeta, recursive=False)
        
        rospy.Subscriber('/clinical_instructions', String, self.instruction_callback)
        
        # Iniciar monitoreo
        self.observer.start()
        rospy.loginfo("🔍 Monitoreo de carpeta activado - Esperando nuevas imágenes...")
        rospy.loginfo("📊 Modo media por lotes: cada 10 fotos → media independiente")
        
        # Procesar imágenes existentes al inicio
        self.process_existing_images()
        
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
            # Procesar cualquier imagen pendiente
            self.process_existing_images()
    
    def calcular_media_lote(self):
        """Calcula y publica la media del lote actual de 10 fotos"""
        if len(self.temperaturas_lote_actual) == 0:
            rospy.logwarn("📭 No hay temperaturas en el lote actual para calcular la media")
            return
            
        media_lote = sum(self.temperaturas_lote_actual) / len(self.temperaturas_lote_actual)
        
        rospy.loginfo("=" * 60)
        rospy.loginfo(f"📊 LOTES {self.numero_lote} - RESUMEN DE {len(self.temperaturas_lote_actual)} FOTOS:")
        rospy.loginfo(f"📈 Temperaturas individuales: {self.temperaturas_lote_actual}")
        rospy.loginfo(f"🧮 Media del lote: {media_lote:.2f}°C")
        rospy.loginfo(f"🔢 Rango: {min(self.temperaturas_lote_actual):.1f}°C - {max(self.temperaturas_lote_actual):.1f}°C")
        rospy.loginfo("=" * 60)
        
        # Publicar la media del lote
        self.publish_temperature(media_lote, is_media=True, numero_lote=self.numero_lote)
        
        # 🔥 MODIFICADO: Reiniciar para el siguiente lote
        self.temperaturas_lote_actual = []  # Limpiar el lote actual
        self.contador_fotos = 0  # Reiniciar contador
        self.numero_lote += 1  # Incrementar número de lote
        
        rospy.loginfo(f"🔄 Lote {self.numero_lote-1} completado. Iniciando lote {self.numero_lote}...")
        
    def process_single_image(self, image_path):
        """Procesa una sola imagen"""
        custom_config = r'--oem 3 --psm 6 outputbase digits'
        filename = os.path.basename(image_path)
        
        rospy.loginfo(f"🔄 Iniciando procesamiento de: {filename}")
        
        if filename in self.archivos_vistos:
            rospy.loginfo(f"⏭️ Imagen ya procesada: {filename}")
            return
            
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
                    
                    # 🔥 MODIFICADO: Guardar en el lote actual y verificar si es hora de calcular media
                    self.temperaturas_lote_actual.append(val_temp)
                    self.contador_fotos += 1
                    
                    # Publicar temperatura individual
                    self.publish_temperature(val_temp, is_individual=True)
                    
                    # Verificar si hemos llegado a 10 fotos en el lote actual
                    if self.contador_fotos == 10:
                        rospy.loginfo(f"🎯 Lote {self.numero_lote} completado ({self.contador_fotos} fotos) - Calculando media...")
                        self.calcular_media_lote()
                    else:
                        rospy.loginfo(f"📈 Progreso lote {self.numero_lote}: {self.contador_fotos}/10 fotos")
                    
                else:
                    rospy.logwarn(f"❌ No se pudieron detectar dígitos. Texto: '{texto}'")
                    # Publicar temperatura simulada para esta imagen
                    self.publish_temperature(36.5, simulated=True)
                    
            except Exception as e:
                rospy.logerr(f"❌ Error procesando imagen {filename}: {e}")
                self.publish_temperature(36.5, simulated=True)
            
            # Marcar como procesado
            self.archivos_vistos.add(filename)
            
            # Esperar antes de eliminar
            rospy.sleep(0.5)
            
            # Eliminar archivo
            try:
                os.remove(image_path)
                rospy.loginfo(f"🗑️ Imagen eliminada: {filename}")
            except Exception as e:
                rospy.logwarn(f"⚠️ No se pudo eliminar {filename}: {e}")
        else:
            rospy.logwarn(f"❌ No se pudo leer la imagen: {filename}")
            self.archivos_vistos.add(filename)  # Marcar igual para no reintentar
    
    def publish_temperature(self, temperatura, simulated=False, is_individual=False, is_media=False, numero_lote=1):
        """Publica la temperatura en ROS"""
        temp_msg = Float32()
        temp_msg.data = temperatura
        self.temp_pub.publish(temp_msg)
        
        if simulated:
            rospy.loginfo(f"🌡️ Temperatura simulada publicada: {temperatura}°C")
        elif is_media:
            rospy.loginfo(f"📊 [LOTE {numero_lote}] TEMPERATURA MEDIA PUBLICADA: {temperatura:.2f}°C")
        elif is_individual:
            rospy.loginfo(f"✅ Temperatura individual publicada: {temperatura}°C")
        else:
            rospy.loginfo(f"✅ Temperatura publicada: {temperatura}°C")
    
    def shutdown(self):
        """Cierra el observer correctamente"""
        # 🔥 MODIFICADO: Calcular media final del lote actual si hay temperaturas pendientes
        if self.temperaturas_lote_actual and len(self.temperaturas_lote_actual) > 0:
            rospy.loginfo(f"🔚 Calculando media final del lote {self.numero_lote} con {len(self.temperaturas_lote_actual)} temperaturas...")
            media_final = sum(self.temperaturas_lote_actual) / len(self.temperaturas_lote_actual)
            rospy.loginfo(f"📊 MEDIA FINAL LOTE {self.numero_lote}: {media_final:.2f}°C (con {len(self.temperaturas_lote_actual)} fotos)")
            self.publish_temperature(media_final, is_media=True, numero_lote=self.numero_lote)
            
        self.observer.stop()
        self.observer.join()

if __name__ == '__main__':
    node = TemperatureNode()
    try:
        rospy.loginfo("🚀 Nodo temperatura iniciado - Watchdog activo")
        rospy.loginfo("📊 Modo lotes independientes: cada 10 fotos → media independiente")
        rospy.spin()
    except KeyboardInterrupt:
        rospy.loginfo("⏹️ Interrupción por teclado")
    finally:
        node.shutdown()
        rospy.loginfo("🔚 Nodo terminado correctamente")