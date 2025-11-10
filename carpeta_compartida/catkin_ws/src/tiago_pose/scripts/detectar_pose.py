#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import os
import numpy as np
OUT_PATH = "/tmp/tiago_pose_latest.jpg"

class TiagoPoseNode:
    def __init__(self):
        rospy.init_node('tiago_pose_estimation')
        self.bridge = CvBridge()
        self.model = YOLO("yolov8n-pose.pt")
        rospy.Subscriber("/xtion/rgb/image_raw", Image, self.callback, queue_size=1, buff_size=2**24)
        rospy.loginfo("Nodo YOLO Pose Estimation para Tiago iniciado.")
        # Crea el directorio si no existe (debería existir /tmp, pero por si acaso)
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        rospy.spin()

    def callback(self, img_msg):
        try:
            # Convertir ROS Image a OpenCV
            frame = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')

            if frame is None or frame.size == 0:
                rospy.logwarn("Frame vacío recibido")
                return

            frame = frame.copy()

            # Inferencia segura
            results = self.model.predict(frame, imgsz=640, conf=0.5, verbose=False)

            # results es una lista: si está vacía, YOLO no ha detectado nada
            if len(results) == 0:
                rospy.logwarn("YOLO no detectó personas en este frame")
                return

            res = results[0]

            # Dibujar anotaciones
            annotated = res.plot()

            # Guardar imagen
            ok = cv2.imwrite(OUT_PATH, annotated)
            if not ok:
                rospy.logerr(f"No se pudo guardar la imagen en {OUT_PATH}")
            else:
                rospy.loginfo(f"Imagen guardada en {OUT_PATH}")

        except Exception as e:
            rospy.logerr(f"Error procesando imagen: {e}")





if __name__ == '__main__':
    TiagoPoseNode()
