#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32, String

class TemperatureNode:
    def __init__(self):
        rospy.init_node('temperature_node')
        
        # Publicar resultados
        self.temp_pub = rospy.Publisher('/temperature_result', Float32, queue_size=10)
        
        # Escuchar instrucciones del maestro
        rospy.Subscriber('/clinical_instructions', String, self.instruction_callback)
        
        rospy.loginfo("🌡️ Nodo temperatura listo")
    
    def instruction_callback(self, msg):
        if "temperature" in msg.data:
            rospy.loginfo("Midiendo temperatura...")
            temperatura = 36.5  # Simulado
            
            temp_msg = Float32()
            temp_msg.data = temperatura
            self.temp_pub.publish(temp_msg)
            
            rospy.loginfo(f"✅ Temperatura: {temperatura}°C")

if __name__ == '__main__':
    try:
        node = TemperatureNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass