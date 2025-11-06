import subprocess
from django.http import FileResponse, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.views.decorators.clickjacking import xframe_options_exempt
import os
import rospy
import cv2
import os
import cv2
from django.contrib.auth.models import User
from django.http import StreamingHttpResponse, FileResponse, HttpResponseNotFound
from django.views.decorators.clickjacking import xframe_options_exempt
from std_msgs.msg import String
import threading
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .models import AnalisisMedico


@login_required
def analisis(request):
    obj, created = AnalisisMedico.objects.get_or_create(user=request.user)
    return render(request, 'interfaz/analisis.html', {"analisis": obj})


last_pulse = "Sin datos"
pulse_subscriber_initialized = False

def init_pulse_listener():
    global pulse_subscriber_initialized
    if pulse_subscriber_initialized:
        return
    pulse_subscriber_initialized = True

    def listener():
        rospy.Subscriber("/pulse_rate", String, pulse_callback)
        rospy.spin()

    threading.Thread(target=listener, daemon=True).start()


from django.http import JsonResponse

def pulse_feed(request):
    init_pulse_listener()
    return JsonResponse({"data": last_pulse})


def pulse_callback(msg):
    global last_pulse
    last_pulse = msg.data

# Ruta donde el nodo ROS deja la imagen
POSE_IMG_PATH = "/tmp/tiago_pose_latest.jpg"

def home(request):
    return render(request, 'interfaz/home.html')


def analisis(request):
    """
    Pantalla dividida en 4. Primer bloque: Análisis de postura.
    Botón para iniciar el nodo y <img> que se refresca cada 1s.
    Los otros 3 bloques: 'Próximamente...'
    """
    return render(request, 'interfaz/analisis.html')

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
    # Revisa si ya hay un rosrun de ese script/nodo
    try:
        out = subprocess.check_output(["bash", "-lc", "pgrep -af 'rosrun tiago_pose detectar_pose\\.py' || true"])
        return bool(out.strip())
    except Exception:
        return False
def iniciar_postura(request):
    """
    Lanza el nodo de postura con rosrun en background (si no está ya corriendo).
    """
    if not _is_pose_node_running():
        launch_cmd = _ros_env_cmd("nohup rosrun tiago_pose detectar_pose.py >/tmp/tiago_pose.log 2>&1 &")
        subprocess.Popen(launch_cmd, shell=True)

    # Redirige a la pantalla de análisis
    return redirect('analisis')

@xframe_options_exempt
def video_feed(request):
    """
    Sirve el último frame anotado como image/jpeg.
    El <img> del front añade ?t=timestamp para evitar cache.
    """
    if not os.path.exists(POSE_IMG_PATH):
        return HttpResponseNotFound("Aún no hay imagen. ¿Iniciaste el análisis de postura?")
    try:
        # Devuelve el archivo como imagen
        return FileResponse(open(POSE_IMG_PATH, 'rb'), content_type='image/jpeg')
    except Exception:
        return HttpResponseNotFound("No se pudo leer la imagen.")
    

@login_required
def analisis_final(request):
    return render(request, 'interfaz/analisis_final.html')

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
