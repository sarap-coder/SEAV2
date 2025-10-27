#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
from sensor_msgs.msg import JointState
from control_msgs.msg import FollowJointTrajectoryAction, FollowJointTrajectoryGoal
from trajectory_msgs.msg import JointTrajectoryPoint

class MoverBrazoSeguro:
    def __init__(self):
        rospy.init_node("mover_brazo_seguro")
        rospy.loginfo("✅ Nodo iniciado correctamente.")

        # 1) Nombres CONFIRMADOS del brazo real
        self.arm_joint_names = [
            "arm_1_joint", "arm_2_joint", "arm_3_joint",
            "arm_4_joint", "arm_5_joint", "arm_6_joint", "arm_7_joint"
        ]

        # 2) Seleccionar AUTOMÁTICAMENTE el controlador correcto
        self.ctrl_topic = "/arm_controller/follow_joint_trajectory"
        rospy.loginfo(f"🔍 Usando controlador: {self.ctrl_topic}")

        self.arm_client = actionlib.SimpleActionClient(
            self.ctrl_topic, FollowJointTrajectoryAction
        )
        rospy.loginfo("⏳ Esperando al servidor de acción...")
        if not self.arm_client.wait_for_server(rospy.Duration(10.0)):
            rospy.logerr(f"❌ No se pudo conectar con {self.ctrl_topic}")
            return

        rospy.loginfo("✅ Conectado correctamente.")

    def mover_minimo_adelante(self):
        rospy.loginfo("⏳ Leyendo /joint_states...")
        try:
            js = rospy.wait_for_message("/joint_states", JointState, timeout=3.0)
        except:
            rospy.logerr("❌ No llega /joint_states. No muevo nada por seguridad.")
            return

        name_to_pos = dict(zip(js.name, js.position))
        if any(j not in name_to_pos for j in self.arm_joint_names):
            rospy.logerr("❌ Alguna articulación no está en /joint_states. Abortando.")
            return

        q_now = [name_to_pos[j] for j in self.arm_joint_names]
        rospy.loginfo(f"🔹 Pose actual: {q_now}")

        # 3) Movimiento mínimo hacia adelante (seguro)
        q_goal = q_now[:]
        q_goal[0] += 0.35   # extender ligeramente
        # q_goal[3] -= 0.25   # empujar hacia adelante

        rospy.loginfo("🦾 Enviando trayectoria mínima hacia adelante...")
        goal = FollowJointTrajectoryGoal()
        goal.trajectory.joint_names = self.arm_joint_names

        p = JointTrajectoryPoint()
        p.positions = q_goal
        p.velocities = [0.0]*7
        p.time_from_start = rospy.Duration(3.0)
        goal.trajectory.points = [p]
        # goal.trajectory.header.stamp = rospy.Time.now()

        self.arm_client.send_goal(goal)
        finished = self.arm_client.wait_for_result(rospy.Duration(6.0))
        state = self.arm_client.get_state()
        rospy.loginfo(f"📡 Resultado: state={state} (3=OK, 5=RECHAZADO, 4=ABORTADO)")

    def run(self):
        self.mover_minimo_adelante()

if __name__ == "__main__":
    node = MoverBrazoSeguro()
    rospy.sleep(1.0)
    node.run()
