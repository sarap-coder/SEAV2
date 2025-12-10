import subprocess
from django.shortcuts import render, redirect
import os
import rospy
from django.contrib.auth.models import User
from django.http import StreamingHttpResponse, FileResponse, HttpResponseNotFound
from django.views.decorators.clickjacking import xframe_options_exempt
from std_msgs.msg import String
import threading
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .models import AnalisisMedico, ResultadoSesion
from std_msgs.msg import Int32
from django.http import HttpResponse, FileResponse, HttpResponseNotFound
from django.http import JsonResponse
import csv


ultimo_resultado_reflejos = "Sin evaluar"
reflejos_subscriber_initialized = False

def reflejos_callback(msg):
    global ultimo_resultado_reflejos
    ultimo_resultado_reflejos = msg.data

def init_reflejos_listener():
    global reflejos_subscriber_initialized
    if reflejos_subscriber_initialized:
        return
    reflejos_subscriber_initialized = True

    # 🔧 Inicializar ROS solo una vez
    init_ros_once()

    def listener():
        rospy.Subscriber("/reflejos_resultado", String, reflejos_callback)
        rospy.spin()  # mantenemos el hilo vivo escuchando

    threading.Thread(target=listener, daemon=True).start()

def reflejos_feed(request):
    init_reflejos_listener()
    return JsonResponse({"resultado": ultimo_resultado_reflejos})


@login_required
def analisis(request):
    obj, created = AnalisisMedico.objects.get_or_create(user=request.user)
    return render(request, 'interfaz/analisis.html', {"analisis": obj})


last_pulse = "Sin datos"
pulse_subscriber_initialized = False


ros_initialized = False

def init_ros_once():
    global ros_initialized
    if ros_initialized:
        return

    try:
        rospy.init_node("django_bridge", anonymous=True, disable_signals=True)
        ros_initialized = True
        print("✅ ROS inicializado desde Django")
    except rospy.exceptions.ROSException:
        # Si el nodo ya existe, no pasa nada
        pass



def init_pulse_listener():
    global pulse_subscriber_initialized
    if pulse_subscriber_initialized:
        return

    pulse_subscriber_initialized = True

    # Inicializar ROS (solo la primera vez)
    init_ros_once()

    def listener():
        rospy.Subscriber("/pulse_rate", Int32, pulse_callback)
        rospy.spin()

    threading.Thread(target=listener, daemon=True).start()



def pulse_feed(request):
    init_pulse_listener()
    return JsonResponse({"data": last_pulse})


def pulse_callback(msg):
    global last_pulse
    last_pulse = str(msg.data)  # Convertimos a string para enviar por JSON


# Ruta donde el nodo ROS deja la imagen
POSE_IMG_PATH = "/tmp/tiago_pose_latest.jpg"

def home(request):
    return render(request, 'interfaz/home.html')


def _ros_env_cmd(cmd):
    return f"""
        bash -lc '
            set -e
            source /opt/ros/noetic/setup.bash
            source ~/carpeta_compartida/catkin_ws/devel/setup.bash   # <<< ESTA ES LA QUE NECESITAMOS
            export ROS_MASTER_URI=http://tiago-222c:11311
            export ROS_IP=10.68.0.137
            {cmd}
        '
    """

def iniciar_evaluacion_reflejos(request):
    launch_cmd = _ros_env_cmd("nohup rosrun test_reflejos evaluar_reflejos.py >/tmp/evaluar_reflejos.log 2>&1 &")
    subprocess.Popen(launch_cmd, shell=True)
    return redirect('analisis_reflejos_live')

def analisis_pulso_live(request):
    obj, _ = AnalisisMedico.objects.get_or_create(user=request.user)
    obj.completado_pulso = True
    obj.save()
    return render(request, 'interfaz/analisis_pulso_live.html')


def iniciar_pulso(request):
    launch_cmd = _ros_env_cmd("nohup rosrun clinical_exploration pulse_node.py >/tmp/pulse_node.log 2>&1 &")
    subprocess.Popen(launch_cmd, shell=True)
    return redirect('analisis_pulso_live')


def analisis_reflejos_live(request):
    obj, _ = AnalisisMedico.objects.get_or_create(user=request.user)
    obj.completado_reflejos = True
    obj.save()
    return render(request, 'interfaz/analisis_reflejos_live.html')

@login_required
def analisis_otros(request):
    obj, _ = AnalisisMedico.objects.get_or_create(user=request.user)
    obj.completado_otros = True
    obj.save()
    return redirect('analisis')


def analisis_postura_live(request):
    obj, _ = AnalisisMedico.objects.get_or_create(user=request.user)
    obj.completado_postura = True
    obj.save()
    return render(request, 'interfaz/analisis_postura_live.html')


def _is_pose_node_running():
    nodes = subprocess.getoutput("rosnode list")
    return "/tiago_pose_estimation" in nodes

def iniciar_postura(request):
    """
    Lanza el nodo de postura con rosrun en background (si no está ya corriendo).
    """
    if not _is_pose_node_running():
        cmd = _ros_env_cmd(
            "nohup rosrun tiago_pose detectar_pose.py >/tmp/tiago_pose.log 2>&1 &"
        )
        subprocess.Popen(cmd, shell=True)

    return redirect('analisis')

@xframe_options_exempt
def video_feed(request):
    if not os.path.exists("/tmp/tiago_pose_latest.jpg"):
        return HttpResponseNotFound("Aún no hay imagen procesada")
    try:
        with open("/tmp/tiago_pose_latest.jpg", "rb") as f:
            data = f.read()
        return HttpResponse(data, content_type="image/jpeg")
    except:
        return HttpResponseNotFound("No se pudo leer la imagen")


def traducir_postura(valor):
    v = str(valor).strip()

    if v in ["✅", "correcto", "ok", "1", "true", "True"]:
        return "Postura correcta"
    elif v in ["❌", "incorrecto", "0", "false", "False"]:
        return "Postura incorrecta"
    else:
        return "Sin evaluar"
    
def evaluar_pulso(bpm):
    try:
        bpm = int(bpm)

        if bpm < 60:
            return f"{bpm} bpm | Pulso bajo"

        elif 60 <= bpm <= 100:
            return f"{bpm} bpm | Pulso normal"

        else:
            return f"{bpm} bpm | Pulso acelerado"

    except:
        return "Pulso no válido"


@login_required
def analisis_final(request):

    estado, created = AnalisisMedico.objects.get_or_create(user=request.user)

    if not estado.completado_todo():
        return redirect("analisis")

    hombros_raw = ultimo_resultado_postura.get("hombros", "Sin evaluar")
    cadera_raw = ultimo_resultado_postura.get("cadera", "Sin evaluar")
    torso_raw = ultimo_resultado_postura.get("torso", "Sin evaluar")

    hombros = traducir_postura(hombros_raw)
    cadera = traducir_postura(cadera_raw)
    torso = traducir_postura(torso_raw)


    # TEMPERATURA
    temp_raw = temperature_bridge.get_temperature().replace("°C","")
    try:
        temperatura = float(temp_raw)
    except:
        temperatura = 0.0

    # PULSO
    try:
        pulso_valor = int(last_pulse)
    except:
        pulso_valor = 0

    pulso = evaluar_pulso(pulso_valor)


    raw_reflejos = ultimo_resultado_reflejos.lower().strip()

    if raw_reflejos in ["detectado", "true", "1", "si", "sí"]:
        reflejos = "Reflejos correctos"
    else:
        reflejos = "Reflejos incorrectos"


    ResultadoSesion.objects.create(
        user=request.user,
        postura_hombros=hombros,
        postura_cadera=cadera,
        postura_torso=torso,
        temperatura=temperatura,
        pulso=pulso,
        reflejos=reflejos,
    )

    estado.delete()

    return render(request, 'interfaz/analisis_final.html', {
        "postura_hombros": hombros,
        "postura_cadera": cadera,
        "postura_torso": torso,
        "temperatura": temperatura,
        "pulso": pulso,
        "reflejos": reflejos,
    })




def salir(request):
    logout(request)
    return redirect('login')


def login_view(request):
    # ✅ Crear usuario automático si no existen usuarios
    if User.objects.count() == 0:
        User.objects.create_superuser(
            username="sara",
            email="",
            password="sara"
        )
        print("✅ Usuario automático creado: admin / admin")

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST["username"],
            password=request.POST["password"],
        )
        if user:
            login(request, user)
            return redirect('analisis')
        return render(request, "interfaz/login.html", {"error": "Credenciales inválidas"})

    return render(request, "interfaz/login.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")

        if password != confirm:
            return render(request, "interfaz/register.html", {"error": "Las contraseñas no coinciden"})

        if User.objects.filter(username=username).exists():
            return render(request, "interfaz/register.html", {"error": "Ese usuario ya existe"})

        User.objects.create_user(username=username, password=password)
        return redirect("login")

    return render(request, "interfaz/register.html")



class TemperatureBridge:
    def __init__(self):
        self.ultima_temperatura = "Sin datos"
        self.initialized = False
        self._lock = threading.Lock()

    def start(self):
        if self.initialized:
            return

        # Usar exactamente la misma inicialización ROS que los otros listeners
        init_ros_once()

        thread = threading.Thread(target=self._ros_listener, daemon=True)
        thread.start()

        self.initialized = True
        print("🚀 Bridge de temperatura iniciado correctamente")

    def _ros_listener(self):
        import rospy
        from std_msgs.msg import Float32

        try:
            def callback(msg):
                with self._lock:
                    self.ultima_temperatura = f"{msg.data:.2f}°C"

            rospy.Subscriber("/temperature_result", Float32, callback)
            print("🌡️ Suscrito a /temperature_result")

            rospy.spin()

        except Exception as e:
            print(f"❌ Error en listener ROS: {e}")

    def get_temperature(self):
        with self._lock:
            return self.ultima_temperatura

# Instancia global
temperature_bridge = TemperatureBridge()

@login_required
def temperature_feed(request):
    temperature_bridge.start()
    return JsonResponse({
        "temperature": temperature_bridge.get_temperature(), 
        "status": "success"
    })
    
    
@login_required  
def iniciar_temperatura(request):
    launch_cmd = _ros_env_cmd(
        "nohup rosrun clinical_exploration temperature_node.py >/tmp/temperature_node.log 2>&1 &"
    )
    subprocess.Popen(launch_cmd, shell=True)

    temperature_bridge.start()

    return redirect('analisis_temperatura_live')


@login_required
def analisis_temperatura_live(request):
    obj, _ = AnalisisMedico.objects.get_or_create(user=request.user)
    obj.completado_temperatura = True
    obj.save()
    return render(request, 'interfaz/analisis_temperatura_live.html')


@login_required
def temperature_debug(request):
    import subprocess
    result = {}
    
    try:
        topics = subprocess.check_output(["rostopic", "list"]).decode().splitlines()
        result['topics'] = [t for t in topics if 'temperature' in t]
    except:
        result['topics'] = ['Error al obtener topics']
    
    try:
        nodes = subprocess.check_output(["rosnode", "list"]).decode().splitlines()
        result['nodes'] = nodes
    except:
        result['nodes'] = ['Error al obtener nodos']
    
    result['ultima_temperatura'] = temperature_bridge.get_temperature()
    result['temperature_bridge_initialized'] = temperature_bridge.initialized
    
    return JsonResponse(result)

# ---------------- POSTURA ----------------

ultimo_resultado_postura = {
    "hombros": "Sin evaluar",
    "cadera": "Sin evaluar",
    "torso": "Sin evaluar"
}

postura_subscriber_initialized = False


import ast

def postura_callback(msg):
    global ultimo_resultado_postura

    try:
        # Convertimos string → dict
        data = ast.literal_eval(msg.data)
        ultimo_resultado_postura = data
    except:
        print("❌ Error leyendo resultado postura:", msg.data)


def init_postura_listener():
    global postura_subscriber_initialized

    if postura_subscriber_initialized:
        return

    postura_subscriber_initialized = True

    init_ros_once()

    def listener():
        rospy.Subscriber("/postura_resultado", String, postura_callback)
        rospy.spin()

    threading.Thread(target=listener, daemon=True).start()



@login_required
def postura_feed(request):
    init_postura_listener()
    return JsonResponse(ultimo_resultado_postura)

@login_required
def historial(request):
    historial = ResultadoSesion.objects.filter(
        user=request.user
    ).order_by("-fecha")

    return render(request, "interfaz/historial.html", {
        "historial": historial
    })

@login_required
def export_historial(request):

    sesiones = ResultadoSesion.objects.filter(user=request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=historial.csv"

    writer = csv.writer(response)
    writer.writerow([
        "Fecha",
        "Hombros",
        "Cadera",
        "Torso",
        "Temp",
        "Pulso",
        "Reflejos",
    ])

    for s in sesiones:
        writer.writerow([
            s.fecha,
            s.postura_hombros,
            s.postura_cadera,
            s.postura_torso,
            s.temperatura,
            s.pulso,
            s.reflejos,
        ])

    return response
