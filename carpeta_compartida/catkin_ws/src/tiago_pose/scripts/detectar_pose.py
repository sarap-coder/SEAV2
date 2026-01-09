#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import os
import numpy as np
from std_msgs.msg import String
import math



OUT_PATH = "/tmp/tiago_pose_latest.jpg"


class TiagoPoseNode:

    
    
    def __init__(self):
        self.postura_pub = rospy.Publisher("/postura_resultado", String, queue_size=1)
        rospy.init_node('tiago_pose_estimation')

        self.bridge = CvBridge()
        self.model = YOLO("yolov8n-pose.pt")

        # procesar 1 de cada 3 frames
        self.frame_count = 0
        self.process_every = 3

        rospy.Subscriber(
            "/xtion/rgb/image_raw",
            Image,
            self.callback,
            queue_size=1,
            buff_size=2**24
        )

        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        rospy.loginfo("Nodo YOLO Pose Estimation iniciado")
        rospy.spin()



    def callback(self, img_msg):
            
        
        def distancia(p1, p2):
            return np.linalg.norm(np.array(p1) - np.array(p2))


        def alineados_y(p1, p2, tolerancia=3):
            return abs(p1[1] - p2[1]) <= tolerancia


        def longitudes_similares(l1, l2, tolerancia=5):
            return abs(l1 - l2) <= tolerancia
        
        try:
            COCO_SKELETON = [
            (0, 1), (0, 2),
            (1, 3), (2, 4),
            (5, 6),
            (5, 7), (7, 9),
            (6, 8), (8, 10),
            (5, 11), (6, 12),
            (11, 12),
            (11, 13), (13, 15),
            (12, 14), (14, 16),
        ]
            frame = self.bridge.imgmsg_to_cv2(img_msg, img_msg.encoding)

            if img_msg.encoding == "rgb8":
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            if frame is None or frame.size == 0:
                rospy.logwarn("Frame vacío recibido")
                return

            self.frame_count += 1
            if self.frame_count % self.process_every != 0:
                return

            annotated = frame.copy()

            results = self.model.predict(frame, imgsz=640, conf=0.5, verbose=False)

            if len(results) > 0 and results[0].keypoints is not None:

                kps_tensor = results[0].keypoints.xy

                if len(kps_tensor) > 0:
                    kps = kps_tensor[0].cpu().numpy()
                    


                    hombro_izq = kps[5]
                        
                    hombro_der = kps[6]
                    cadera_izq = kps[11]
                    cadera_der = kps[12]

                    # Verificar que existen
                    pts = [hombro_izq, hombro_der, cadera_izq, cadera_der]
                    if all(p[0] > 0 and p[1] > 0 for p in pts):

                        # ---- 1. Alineación de hombros ----
                        hombros_alineados = alineados_y(hombro_izq, hombro_der)

                        # ---- 2. Alineación de cintura ----
                        cadera_alineada = alineados_y(cadera_izq, cadera_der)

                        # ---- 3. Longitudes hombro-cadera ----
                        dist_izq = distancia(hombro_izq, cadera_izq)
                        dist_der = distancia(hombro_der, cadera_der)

                        longitudes_ok = longitudes_similares(dist_izq, dist_der)
                        
                        resultado = {
                            "hombros": "✅" if hombros_alineados else "❌",
                            "cadera": "✅" if cadera_alineada else "❌",
                            "torso": "✅" if longitudes_ok else "❌",
                        }

                        msg = str(resultado)
                        self.postura_pub.publish(msg)

                        # ---- RESULTADOS ----
                        print("Hombros alineados:", hombros_alineados)
                        print("Cadera alineada:", cadera_alineada)
                        print("Distancia izquierda:", round(dist_izq,2))
                        print("Distancia derecha:", round(dist_der,2))
                        print("Simetría OK:", longitudes_ok)

                        # ---- Visual feedback ----
                        color = (0,255,0) if hombros_alineados and cadera_alineada and longitudes_ok else (0,0,255)

                        cv2.line(annotated, tuple(hombro_izq.astype(int)), tuple(cadera_izq.astype(int)), color, 3)
                        cv2.line(annotated, tuple(hombro_der.astype(int)), tuple(cadera_der.astype(int)), color, 3)

                    # Dibujar puntos
                    for x, y in kps:
                        if x > 0 and y > 0:
                            cv2.circle(
                                annotated,
                                (int(x), int(y)),
                                4,
                                (0, 255, 0),
                                -1,
                            )

                    # Dibujar esqueleto manual
                    for a, b in COCO_SKELETON:
                        x1, y1 = kps[a]
                        x2, y2 = kps[b]

                        if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
                            cv2.line(
                                annotated,
                                (int(x1), int(y1)),
                                (int(x2), int(y2)),
                                (255, 0, 0),
                                2,
                            )



            # ✅ Guardar SIEMPRE
            cv2.imwrite(OUT_PATH, annotated)

        except Exception as e:
            rospy.logerr(f"Error procesando imagen: {e}")



if __name__ == "__main__":
    TiagoPoseNode()

