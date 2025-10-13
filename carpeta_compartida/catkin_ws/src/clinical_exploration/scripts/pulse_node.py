#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32, String

class PulseNode:
    def __init__(self):
        rospy.init_node('pulse_node')
        
        # Publicar resultados
        self.pulse_pub = rospy.Publisher('/pulse_result', Float32, queue_size=10)
        
        # Escuchar instrucciones del maestro
        rospy.Subscriber('/clinical_instructions', String, self.instruction_callback)
        
        rospy.loginfo("Nodo pulso listo")
    
    def instruction_callback(self, msg):
        """Cuando el maestro dice 'medir pulso'"""
        if "pulse" in msg.data:
            rospy.loginfo("Midiendo pulso...")
            
            # 1. Medir pulso (SIMULADO)
            pulso = self.medir_pulso()
            
            # 2. Publicar resultado
            pulse_msg = Float32()
            pulse_msg.data = pulso
            self.pulse_pub.publish(pulse_msg)
            
            rospy.loginfo(f"✅ Pulso: {pulso} BPM")
    
    def medir_pulso(self):
        """Aquí va la lectura real del Polar"""
        # ⚠️ TU COMPAÑERO IMPLEMENTA ESTO
        return 72.0  # Simulado por ahora

if __name__ == '__main__':
    try:
        node = PulseNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass