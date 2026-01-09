#!/usr/bin/env python3
import rospy
import socket
import threading
import time
import signal
import sys
import subprocess
import paramiko
from std_msgs.msg import String, Int32

class PulseNode:
    def __init__(self):
        # Inicializar nodo ROS
        rospy.init_node('pulse_node', anonymous=True)
       
        # Configuración SSH para Raspberry
        self.raspberry_ip = rospy.get_param('~raspberry_ip', '10.172.209.145')
        self.raspberry_user = rospy.get_param('~raspberry_user', 'pi')
        self.raspberry_password = rospy.get_param('~raspberry_password', 'pi')
       
        # Path del script en Raspberry
        self.polar_script_path = rospy.get_param('~polar_script', '/home/pi/pulse_node.py')
       
        # Publishers para los datos recibidos
        self.pulse_pub = rospy.Publisher('/pulse_rate', Int32, queue_size=10)
        self.raw_data_pub = rospy.Publisher('/pulse_raw_data', String, queue_size=10)
        self.status_pub = rospy.Publisher('/pulse_status', String, queue_size=10)
       
        # Configuración del servidor socket
        self.host = '0.0.0.0'
        self.port = 8888
        self.connected = False
        self.server = None
        self.conn = None
       
        # SSH client para Raspberry
        self.ssh_client = None
        self.polar_process_pid = None
       
        # Registrar shutdown hook
        rospy.on_shutdown(self.cleanup)
        signal.signal(signal.SIGINT, self.signal_handler)
       
        rospy.loginfo("🫀 Nodo Pulse iniciado - Control automático de Raspberry")
       
        # ============================================
        # PASO 1: Preparar Raspberry automáticamente
        # ============================================
        self.prepare_raspberry()
       
        # ============================================
        # PASO 2: Iniciar servidor socket para recibir datos
        # ============================================
        self.start_server()
   
    def prepare_raspberry(self):
        """Prepara Raspberry automáticamente vía SSH"""
        rospy.loginfo(f"🔌 Conectando a Raspberry Pi ({self.raspberry_ip})...")
       
        try:
            # 1. Conectar vía SSH
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.raspberry_ip,
                username=self.raspberry_user,
                password=self.raspberry_password,
                timeout=15
            )
           
            rospy.loginfo("✅ Conectado a Raspberry Pi")
           
            # 2. Opcional: Resetear Bluetooth USB si es necesario
            rospy.loginfo("🔄 Preparando Bluetooth USB...")
            reset_commands = [
                "echo '1-1.3' | sudo tee /sys/bus/usb/drivers/usb/unbind",
                "sleep 2",
                "echo '1-1.3' | sudo tee /sys/bus/usb/drivers/usb/bind",
                "sleep 3",
                "sudo hciconfig hci0 up"
            ]
           
            for cmd in reset_commands:
                try:
                    stdin, stdout, stderr = self.ssh_client.exec_command(cmd, timeout=5)
                    stdout.read()  # Esperar a que termine
                    rospy.logdebug(f"Comando ejecutado: {cmd}")
                except:
                    pass  # Ignorar errores en comandos opcionales
           
            # 3. Verificar que el script existe
            check_cmd = f'[ -f "{self.polar_script_path}" ] && echo "EXISTS" || echo "NOT_FOUND"'
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            if "EXISTS" in stdout.read().decode():
                rospy.loginfo(f"✅ Script encontrado: {self.polar_script_path}")
            else:
                rospy.logerr(f"❌ Script no encontrado: {self.polar_script_path}")
                return False
           
            # 4. Matar procesos previos del Polar si existen
            rospy.loginfo("🧹 Limpiando procesos anteriores...")
            kill_cmds = [
                "pkill -f 'pulse_raspberry.py'",
                "pkill -f 'python.*polar'",
                "sleep 1"
            ]
           
            for cmd in kill_cmds:
                self.ssh_client.exec_command(cmd)
           
            # 5. Ejecutar el script de Polar EN SEGUNDO PLANO
            rospy.loginfo("🚀 Iniciando monitor Polar en Raspberry...")
           
            # Comando para ejecutar en background y capturar PID
            execute_cmd = f"""
            cd /home/pi
            nohup python3 {self.polar_script_path} > /tmp/polar_monitor.log 2>&1 &
            echo $!
            """
           
            stdin, stdout, stderr = self.ssh_client.exec_command(execute_cmd)
            pid = stdout.read().decode().strip()
           
            if pid and pid.isdigit():
                self.polar_process_pid = pid
                rospy.loginfo(f"✅ Monitor Polar iniciado (PID: {pid})")
                self.status_pub.publish(f"Raspberry: Polar activo (PID: {pid})")
               
                # Verificar que arrancó correctamente después de 3 segundos
                threading.Timer(3.0, self.verify_polar_startup).start()
               
                return True
            else:
                rospy.logerr("❌ No se pudo obtener PID del proceso Polar")
                # Mostrar logs de error
                self.check_raspberry_logs()
                return False
               
        except Exception as e:
            rospy.logerr(f"❌ Error preparando Raspberry: {e}")
            self.status_pub.publish(f"Error Raspberry: {str(e)}")
            return False
   
    def verify_polar_startup(self):
        """Verifica que el script Polar se inició correctamente"""
        if not self.ssh_client:
            return
       
        try:
            # Verificar que el proceso sigue activo
            check_cmd = f"ps -p {self.polar_process_pid} > /dev/null && echo 'RUNNING' || echo 'STOPPED'"
            stdin, stdout, stderr = self.ssh_client.exec_command(check_cmd)
            status = stdout.read().decode().strip()
           
            if status == 'RUNNING':
                rospy.loginfo(f"✅ Polar correctamente en ejecución (PID: {self.polar_process_pid})")
               
                # Mostrar primeras líneas del log
                log_cmd = "tail -5 /tmp/polar_monitor.log"
                stdin, stdout, stderr = self.ssh_client.exec_command(log_cmd)
                logs = stdout.read().decode()
                if logs:
                    rospy.loginfo(f"📄 Logs iniciales:\n{logs}")
            else:
                rospy.logwarn(f"⚠️ Polar no está corriendo. Revisar logs...")
                self.check_raspberry_logs()
               
        except Exception as e:
            rospy.logwarn(f"⚠️ Error verificando Polar: {e}")
   
    def check_raspberry_logs(self):
        """Muestra logs de error de Raspberry"""
        if not self.ssh_client:
            return
       
        try:
            log_cmd = "tail -20 /tmp/polar_monitor.log 2>/dev/null || echo 'No hay logs'"
            stdin, stdout, stderr = self.ssh_client.exec_command(log_cmd)
            logs = stdout.read().decode()
            rospy.loginfo(f"📄 Logs Raspberry:\n{logs}")
        except:
            pass
   
    def stop_polar_monitor(self):
        """Detiene el monitor Polar en Raspberry"""
        if not self.ssh_client or not self.polar_process_pid:
            return
       
        try:
            rospy.loginfo(f"⏹️ Deteniendo Polar en Raspberry (PID: {self.polar_process_pid})...")
           
            kill_cmds = [
                f"kill -TERM {self.polar_process_pid}",
                "sleep 1",
                f"kill -KILL {self.polar_process_pid} 2>/dev/null || true",
                "pkill -f 'pulse_raspberry.py'"
            ]
           
            for cmd in kill_cmds:
                self.ssh_client.exec_command(cmd)
           
            rospy.loginfo("✅ Polar detenido")
            self.polar_process_pid = None
           
        except Exception as e:
            rospy.logerr(f"❌ Error deteniendo Polar: {e}")
   
    # ============================================
    # EL RESTO DEL CÓDIGO SE MANTIENE IGUAL
    # (métodos start_server, handle_connection, etc.)
    # ============================================
   
    def start_server(self):
        """Inicia el servidor socket (código existente)"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(1)
            self.server.settimeout(2.0)
           
            rospy.loginfo(f"🌐 Servidor escuchando en {self.host}:{self.port}")
            rospy.loginfo("📡 Esperando datos de Raspberry...")
            self.status_pub.publish("Esperando Raspberry Pi")
           
            # Iniciar hilo para aceptar conexiones
            server_thread = threading.Thread(target=self.accept_connections, daemon=True)
            server_thread.start()
           
        except Exception as e:
            rospy.logerr(f"❌ Error iniciando servidor: {e}")
            self.status_pub.publish(f"Error servidor: {e}")
   
    def accept_connections(self):
        """Acepta conexiones entrantes (en hilo separado)"""
        while not rospy.is_shutdown():
            try:
                self.conn, addr = self.server.accept()
                self.conn.settimeout(2.0)
               
                rospy.loginfo(f"✅ Raspberry conectada: {addr}")
                self.status_pub.publish(f"Conectado: {addr}")
                self.connected = True
               
                # Manejar la conexión
                self.handle_connection(self.conn, addr)
               
            except socket.timeout:
                continue
            except Exception as e:
                if not rospy.is_shutdown():
                    rospy.logwarn(f"⚠️ Error en servidor: {e}")
   
    def handle_connection(self, conn, addr):
        """Maneja una conexión entrante (código existente)"""
        try:
            rospy.loginfo("📊 Recibiendo datos de pulso...")
           
            while not rospy.is_shutdown() and self.connected:
                try:
                    data = conn.recv(1024).decode('utf-8')
                   
                    if not data:
                        rospy.loginfo("🔌 Conexión cerrada por Raspberry")
                        break
                   
                    # Publicar datos crudos
                    self.raw_data_pub.publish(data.strip())
                    rospy.loginfo(f"📨 Dato recibido: {data.strip()}")
                   
                    # Extraer valor numérico del pulso
                    pulse_value = self.extract_pulse_value(data)
                    if pulse_value is not None:
                        self.pulse_pub.publish(pulse_value)
                        rospy.loginfo(f"🫀 Pulso publicado: {pulse_value} BPM")
                   
                except socket.timeout:
                    continue
                except socket.error as e:
                    if not rospy.is_shutdown():
                        rospy.logwarn(f"⚠️ Error de socket: {e}")
                    break
               
        except Exception as e:
            rospy.logwarn(f"⚠️ Error en conexión: {e}")
        finally:
            self.close_connection()
   
    def extract_pulse_value(self, data):
        """Extrae el valor numérico del pulso"""
        try:
            if "Pulso:" in data or "BPM" in data.upper():
                import re
                numbers = re.findall(r'\d+', data)
                if numbers:
                    pulse = int(numbers[0])
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
                rospy.loginfo("🔌 Conexión cliente cerrada")
        except Exception as e:
            rospy.logwarn(f"⚠️ Error cerrando conexión: {e}")
       
        self.connected = False
        self.status_pub.publish("Desconectado")
   
    def cleanup(self):
        """Limpia recursos al cerrar"""
        rospy.loginfo("🧹 Cerrando nodo y liberando recursos...")
       
        # 1. Detener Polar en Raspberry
        self.stop_polar_monitor()
       
        # 2. Cerrar conexión SSH
        if self.ssh_client:
            try:
                self.ssh_client.close()
                rospy.loginfo("🔌 Conexión SSH cerrada")
            except:
                pass
       
        # 3. Cerrar conexión socket
        self.close_connection()
       
        # 4. Cerrar servidor socket
        try:
            if self.server:
                self.server.close()
                rospy.loginfo("🌐 Socket del servidor cerrado")
        except Exception as e:
            rospy.logwarn(f"⚠️ Error cerrando servidor: {e}")
       
        time.sleep(0.1)
        rospy.loginfo("✅ Nodo Pulse terminado")
   
    def verify_port_release(self):
        """Verifica que el puerto se haya liberado"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind((self.host, self.port))
            test_socket.close()
            rospy.loginfo(f"✅ Puerto {self.port} liberado")
            return True
        except socket.error as e:
            rospy.logwarn(f"⚠️ Puerto {self.port} aún ocupado: {e}")
            return False
   
    def signal_handler(self, signum, frame):
        """Manejador para Ctrl+C"""
        rospy.loginfo("\n🛑 Señal Ctrl+C recibida")
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Función principal del nodo (opcional - para compatibilidad)"""
        rospy.loginfo("🫀 Nodo Pulse listo. Ctrl+C para detener.")
        rospy.spin()

if __name__ == '__main__':
    try:
        node = PulseNode()
        node.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("🔚 Nodo interrumpido")
    except Exception as e:
        rospy.logerr(f"❌ Error fatal: {e}")
    finally:
        rospy.loginfo("🏁 Ejecución finalizada")