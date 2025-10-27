#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import os

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
            frame = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')
            results = self.model(frame)
            annotated = results[0].plot()
            # Guarda el último frame en /tmp (Django lo servirá)
            cv2.imwrite(OUT_PATH, annotated)
        except Exception as e:
            rospy.logerr(f"Error procesando imagen: {e}")

if __name__ == '__main__':
    TiagoPoseNode()
