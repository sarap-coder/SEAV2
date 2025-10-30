#!/usr/bin/env python3
#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32, String
import cv2
import os
import time
import pytesseract
import numpy as np 
import os

class TemperatureNode:
    def __init__(self):
        rospy.init_node('temperature_node')
        
        # Publicar resultados
        self.temp_pub = rospy.Publisher('/temperature_result', Float32, queue_size=10)
        
        # Escuchar instrucciones del maestro
        rospy.Subscriber('/clinical_instructions', String, self.measure_temperature)
        
        rospy.loginfo("🌡️ Nodo temperatura listo")

        # Nombre de ruta mantiene fijo en la camara, puede variar la ubicación
        self.unidades = ["D:/", "E:/", "F:/", "G:/", "H:/"]
        self.ruta_carpeta = str()
        self.encontrar_ruta()

        # Registro de archivos vistos
        self.archivos_vistos = set()
        
    def encontrar_ruta(self):
        for unidad in self.unidades:
            # Verifica si la unidad existe
            if os.path.exists(unidad):
                # Construye la ruta específica que antes tenías fija
                ruta_carpeta = os.path.join(unidad, "19700101")
                
                if os.path.exists(self.ruta_carpeta):
                    self.ruta_carpeta = ruta_carpeta
                    rospy.loginfo(f"Ruta de carpeta encontrada: {self.ruta_carpeta}")
                    return
        rospy.loginfo("Ruta de carpeta no encontrada")
        return

                
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
        if self.ruta_carpeta is not None:
            archivos = [foto for foto in os.listdir(self.ruta_carpeta) if foto.lower().endswith((".jpeg"))]
            custom_config = r'--oem 3 --psm 6 outputbase digits'
        else:
            return
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

                # Reconocer digitos:
                texto = pytesseract.image_to_string(roi, config=custom_config)

                # Tomar solo los primeros 3 dígitos reconocidos (por si detecta más)
                digitos = ''.join([c for c in texto if c.isdigit()])[:3]

                # Calcular valor de temperatura:
                if len(digitos) == 3:
                    val_temp = int(digitos[0])*10 + int(digitos[1]) + int(digitos[2])*0.1
                    print(f"Dígitos detectados: {digitos}, valor de temperatura: {val_temp}")
                else:   
                    val_temp = None
                    print("Lectura de temperatura fallida")
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