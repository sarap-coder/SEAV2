#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32, String
import cv2
import os
import time
from tensorflow.keras.models import load_model
import numpy as np 

class TemperatureNode:
    def __init__(self):
        rospy.init_node('temperature_node')
        
        # Publicar resultados
        self.temp_pub = rospy.Publisher('/temperature_result', Float32, queue_size=10)
        
        # Escuchar instrucciones del maestro
        rospy.Subscriber('/clinical_instructions', String, self.measure_temperature)
        
        rospy.loginfo("🌡️ Nodo temperatura listo")

        # Cargar modelo y ruta
        self.model = load_model("modelo_cnn_digitos.h5")
        # Nombre de ruta mantiene fijo en la camara, puede variar la ubicación
        self.ruta_carpeta = "E:/19700101/" 

        # Registro de archivos vistos
        self.archivos_vistos = set()
    
    def instruction_callback(self, msg):
        if "temperature" in msg.data:
            rospy.loginfo("Midiendo temperatura...")
            temperatura = 36.5  # Simulado
            
            temp_msg = Float32()
            temp_msg.data = temperatura
            self.temp_pub.publish(temp_msg)
            
            rospy.loginfo(f"✅ Temperatura: {temperatura}°C")

    def measure_temperature(self):
        print("Esperando nuevas imágenes en", self.ruta_carpeta)
        while True:
            archivos = [foto for foto in os.listdir(self.ruta_carpeta) if foto.lower().endswith((".jpeg"))]
            nuevos = [foto for foto in archivos if foto not in self.archivos_vistos]
            for foto in nuevos:
                print(f"Nueva imagen detectada: {foto}")
                img = cv2.imread(os.path.join(self.ruta_carpeta, foto))
                if img is not None:

                    # Recortar región de interés (ROI):
                    roi = img[1:51, 1:101]

                    # Convertir a un canal:
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

                    # reducir ruido:
                    gray = cv2.GaussianBlur(gray, (3, 3), 0)  

                    # Binarizar:
                    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
                    thresh = 255 - thresh
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

                    # Segmentar:
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    # Ordenar contornos:
                    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

                    # Sepearar y predecir dígitos:
                    digitos = []
                    for c in contours:
                        x, y, w, h = cv2.boundingRect(c)

                        # filtrar ruido
                        if h > 10 and w > 5:  

                            # Recortar dígito:
                            digit = thresh[y:y+h, x:x+w]

                            # ROI:
                            cv2.rectangle(roi, (x, y), (x+w, y+h), (0, 255, 0), 1)  
                            alto, ancho = digit.shape
                            borde = int(0.2 * max(alto, ancho))

                            # Añadir borde:
                            digit = cv2.copyMakeBorder(
                                digit,
                                top=borde,
                                bottom=borde,
                                left=borde,
                                right=borde,
                                borderType=cv2.BORDER_CONSTANT,
                                value=0  
                            )
                            # Preparar imagen para la CNN:
                            digit = cv2.resize(digit, (28, 28))
                            digit = digit.astype("float32") / 255.0
                            digit = np.expand_dims(digit, axis=(0, -1))

                            # Predecir con modelo:
                            pred = self.model.predict(digit)
                            numero = np.argmax(pred)
                            digitos.append(str(numero))         

                    # Calcular valor de temperatura:
                    val_temp = int(digitos[0])*10 + int(digitos[1]) + int(digitos[2])*0.1
                    print(f"Dígitos detectados: {digitos}, valor de temperatura: {val_temp}")
                self.archivos_vistos.add(foto)
                # Publicar temperatura
                temp_msg = Float32()
                temp_msg.data = val_temp
                self.pub.publish(temp_msg)

                # Eliminar archivo procesado
                if foto in self.archivos_vistos:
                    remove_path = os.path.join(self.ruta_carpeta, foto)
                    os.remove(remove_path)
            time.sleep(1)

if __name__ == '__main__':
    try:
        node = TemperatureNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass