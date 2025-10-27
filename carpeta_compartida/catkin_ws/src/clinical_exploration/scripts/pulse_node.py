#!/usr/bin/env python3
import rospy
import socket
import threading
import time
from std_msgs.msg import String, Int32

class PulseNode:
    def __init__(self):
        # Inicializar nodo ROS
        rospy.init_node('pulse_node', anonymous=True)
        
        # Publishers para los datos recibidos
        self.pulse_pub = rospy.Publisher('/pulse_rate', Int32, queue_size=10)
        self.raw_data_pub = rospy.Publisher('/pulse_raw_data', String, queue_size=10)
        self.status_pub = rospy.Publisher('/pulse_status', String, queue_size=10)
        
        # Configuración del servidor
        self.host = '0.0.0.0'
        self.port = 8888
        self.connected = False
        self.server = None
        self.conn = None
        
        # Registrar shutdown hook para liberar recursos
        rospy.on_shutdown(self.cleanup)
        
        rospy.loginfo(" Nodo Pulse iniciado")
        
    def start_server(self):
        """Inicia el servidor socket en un hilo separado"""
        try:
            # Crear socket del servidor
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(1)
            self.server.settimeout(2.0)  # Timeout para poder verificar shutdown
            
            rospy.loginfo(f" Servidor escuchando en {self.host}:{self.port}")
            self.status_pub.publish("Servidor iniciado - Esperando Raspberry Pi")
            
            while not rospy.is_shutdown():
                try:
                    # Esperar conexión
                    rospy.loginfo(" Esperando conexión de Raspberry Pi...")
                    self.conn, addr = self.server.accept()
                    
                    rospy.loginfo(f" Raspberry Pi conectada: {addr}")
                    self.status_pub.publish(f"Conectado: {addr}")
                    self.connected = True
                    
                    # Manejar la conexión
                    self.handle_connection(self.conn, addr)
                    
                except socket.timeout:
                    # Timeout normal, continuar esperando
                    continue
                except Exception as e:
                    if not rospy.is_shutdown():
                        rospy.logerr(f" Error en servidor: {e}")
                        self.status_pub.publish(f"Error: {e}")
                    
        except Exception as e:
            if not rospy.is_shutdown():
                rospy.logerr(f" Error iniciando servidor: {e}")
                self.status_pub.publish(f"Error servidor: {e}")
    
    def handle_connection(self, conn, addr):
        """Maneja una conexión entrante"""
        try:
            rospy.loginfo(" Recibiendo datos...")
            
            while not rospy.is_shutdown():
                # Recibir datos
                data = conn.recv(1024).decode('utf-8')
                
                if not data:
                    rospy.loginfo("🔌 Conexión cerrada por el cliente")
                    break
                
                # Publicar datos crudos
                self.raw_data_pub.publish(data.strip())
                rospy.loginfo(f" Dato recibido: {data.strip()}")
                
                # Intentar extraer valor numérico del pulso
                pulse_value = self.extract_pulse_value(data)
                if pulse_value is not None:
                    self.pulse_pub.publish(pulse_value)
                    rospy.loginfo(f"  Pulso publicado: {pulse_value} BPM")
                
        except socket.timeout:
            rospy.logwarn(" Timeout en recepción de datos")
        except Exception as e:
            if not rospy.is_shutdown():
                rospy.logwarn(f"  Error en conexión: {e}")
        finally:
            self.close_connection()
    
    def extract_pulse_value(self, data):
        """Extrae el valor numérico del pulso del texto recibido"""
        try:
            # Buscar patrones comunes en los datos
            if "BPM" in data or "ritmo" in data.lower() or "pulso" in data.lower():
                # Buscar números en el texto
                import re
                numbers = re.findall(r'\d+', data)
                if numbers:
                    pulse = int(numbers[0])
                    # Validar que sea un valor razonable de pulso
                    if 40 <= pulse <= 200:
                        return pulse
            return None
        except:
            return None
    
    def close_connection(self):
        """Cierra la conexión actual"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
        except:
            pass
        self.connected = False
        self.status_pub.publish("Desconectado")
        rospy.loginfo(" Conexión cerrada")
    
    def cleanup(self):
        """Limpia recursos al cerrar - LIBERA EL PUERTO"""
        rospy.loginfo(" Cerrando nodo y liberando puerto...")
        
        # Cerrar conexión si existe
        self.close_connection()
        
        # Cerrar servidor y liberar puerto
        try:
            if self.server:
                self.server.close()
                rospy.loginfo(" Socket del servidor cerrado")
        except Exception as e:
            rospy.logwarn(f"  Error cerrando servidor: {e}")
        
        # Pequeña pausa para asegurar liberación
        time.sleep(0.5)
        
        # Verificar que el puerto se liberó
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.bind((self.host, self.port))
            test_socket.close()
            rospy.loginfo(f" Puerto {self.port} liberado correctamente")
        except socket.error as e:
            rospy.logwarn(f"  El puerto {self.port} aún podría estar ocupado: {e}")
        
        rospy.loginfo(" Nodo Pulse terminado. Puerto listo para reuso.")
    
    def run(self):
        """Función principal del nodo"""
        # Iniciar servidor en un hilo separado
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()
        
        rospy.loginfo(" Nodo Pulse listo. Usa Ctrl+C para detener.")
        rospy.loginfo(f" Puerto {self.port} se liberará automáticamente al cerrar")
        
        # Mantener el nodo activo
        rate = rospy.Rate(1)  # 1 Hz
        while not rospy.is_shutdown():
            # Publicar estado periódicamente
            if self.connected:
                self.status_pub.publish("Conectado - Recibiendo datos")
            else:
                self.status_pub.publish("Esperando conexión")
            rate.sleep()
        
        # Limpieza final (por si acaso)
        self.cleanup()

if __name__ == '__main__':
    try:
        node = PulseNode()
        node.run()
    except rospy.ROSInterruptException:
        rospy.loginfo(" Nodo interrumpido por usuario")
    except Exception as e:
        rospy.logerr(f" Error fatal: {e}")
    finally:
        rospy.loginfo(" Ejecución finalizada")