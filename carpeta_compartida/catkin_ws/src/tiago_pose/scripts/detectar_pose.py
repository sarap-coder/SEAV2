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
        try:
            # 1) Convertimos EXACTAMENTE según el encoding del topic
            frame = self.bridge.imgmsg_to_cv2(img_msg, img_msg.encoding)

            # 2) Si es RGB, pasarlo a BGR para que OpenCV + YOLO funcione bien
            if img_msg.encoding == "rgb8":
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            if frame is None or frame.size == 0:
                rospy.logwarn("Frame vacío recibido")
                return

            self.frame_count += 1
            if self.frame_count % self.process_every != 0:
                return

            results = self.model.predict(frame, imgsz=640, conf=0.5, verbose=False)

            if len(results) == 0 or len(results[0].keypoints) == 0:
                return

            res = results[0]
            annotated = frame.copy()

            kps = res.keypoints.xy[0].cpu().numpy()
            for x, y in kps:
                if x > 0 and y > 0:
                    cv2.circle(annotated, (int(x), int(y)), 4, (0, 255, 0), -1)

            skeleton = res.keypoints.skeleton
            for a, b in skeleton:
                x1, y1 = kps[a]
                x2, y2 = kps[b]
                if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
                    cv2.line(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)

            cv2.imwrite(OUT_PATH, annotated)

        except Exception as e:
            rospy.logerr(f"Error procesando imagen: {e}")

