#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
import cv2
import time
from sensor_msgs.msg import Image
from control_msgs.msg import FollowJointTrajectoryAction, FollowJointTrajectoryGoal
from trajectory_msgs.msg import JointTrajectoryPoint
from cv_bridge import CvBridge
from ultralytics import YOLO

class MoverBrazoYOLOCam:
    def __init__(self):
        rospy.init_node("mover_brazo_yolo_cam")

        self.arm_joint_names = [
            "arm_1_joint", "arm_2_joint", "arm_3_joint",
            "arm_4_joint", "arm_5_joint", "arm_6_joint", "arm_7_joint"
        ]
        self.gripper_joint_names = ["gripper_left_finger_joint", "gripper_right_finger_joint"]

        self.arm_client = actionlib.SimpleActionClient(
            "/arm_controller/follow_joint_trajectory", FollowJointTrajectoryAction)
        self.gripper_client = actionlib.SimpleActionClient(
            "/gripper_controller/follow_joint_trajectory", FollowJointTrajectoryAction)

        rospy.loginfo("⏳ Esperando a servidores...")
        self.arm_client.wait_for_server()
        self.gripper_client.wait_for_server()
        rospy.loginfo("✅ Conectado a brazo y gripper.")

        self.bridge = CvBridge()
        self.last_frame = None
        rospy.Subscriber("/xtion/rgb/image_raw", Image, self.image_cb)

        self.yolo = YOLO("yolov8n.pt")

    def image_cb(self, msg):
        self.last_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

    def mover_gripper(self, pos):
        goal = FollowJointTrajectoryGoal()
        goal.trajectory.joint_names = self.gripper_joint_names
        p = JointTrajectoryPoint()
        p.positions = [pos, pos]
        p.time_from_start = rospy.Duration(1.0)
        goal.trajectory.points = [p]
        self.gripper_client.send_goal(goal)
        self.gripper_client.wait_for_result(rospy.Duration(3.0))

    def mover_brazo(self):
        q_goal = [0.558, 0.628, -1.448, 1.274, -1.448, 0.070, -0.995]
        goal = FollowJointTrajectoryGoal()
        goal.trajectory.joint_names = self.arm_joint_names
        p = JointTrajectoryPoint()
        p.positions = q_goal
        p.time_from_start = rospy.Duration(3.0)
        goal.trajectory.points = [p]
        self.arm_client.send_goal(goal)
        self.arm_client.wait_for_result(rospy.Duration(6.0))

    def detectar_mouse(self):
        rospy.loginfo("🎯 MOSTRANDO CÁMARA Y DETECTANDO")
        t_end = time.time() + 1.2

        while time.time() < t_end and not rospy.is_shutdown():
            if self.last_frame is None:
                rospy.sleep(0.05)
                continue

            frame = self.last_frame.copy()
            cv2.imshow("CAMARA TIAGO", frame)
            cv2.waitKey(1)

            results = self.yolo(frame, verbose=False)
            for r in results:
                for b in r.boxes:
                    if r.names[int(b.cls[0])] == "cell phone":
                        cv2.destroyAllWindows()
                        rospy.loginfo("✅ DETECTADO")
                        return

            rospy.sleep(0.1)

        cv2.destroyAllWindows()
        rospy.loginfo("❌ NO DETECTADO")

    def run(self):
        self.mover_gripper(0.008)
        self.mover_brazo()
        self.mover_gripper(0.033)
        self.detectar_mouse()

if __name__ == "__main__":
    node = MoverBrazoYOLOCam()
    rospy.sleep(1.0)
    node.run()
