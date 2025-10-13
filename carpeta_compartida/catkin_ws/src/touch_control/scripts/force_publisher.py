#!/usr/bin/env python3
import rospy
from control_msgs.msg import FollowJointTrajectoryFeedback
from std_msgs.msg import Float32

def callback(msg):
    if len(msg.actual.effort) > 0:
        force_value = msg.actual.effort[0]
        pub.publish(force_value)
        rospy.loginfo(f"Fuerza actual: {force_value:.2f} N")

def listener():
    rospy.init_node('force_publisher')
    rospy.Subscriber('/gripper_controller/state', FollowJointTrajectoryFeedback, callback)
    rospy.spin()

if __name__ == '__main__':
    pub = rospy.Publisher('/biotouch/force', Float32, queue_size=10)
    listener()
