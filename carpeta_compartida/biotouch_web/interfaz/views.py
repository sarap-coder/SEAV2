import subprocess
from django.http import FileResponse, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.views.decorators.clickjacking import xframe_options_exempt
import os


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



def analisis_reflejos_live(request):
    """
    Vista para ejecutar el test de reflejos SIN mostrar cámara.
    """
    return render(request, 'interfaz/analisis_reflejos_live.html')


def analisis_postura_live(request):
    """
    Vista dedicada solo a la cámara (fondo oscuro, tamaño medio).
    """
    return render(request, 'interfaz/analisis_postura_live.html')


def _is_pose_node_running():
    # Revisa si ya hay un rosrun de ese script/nodo
    try:
        out = subprocess.check_output(["bash", "-lc", "pgrep -af 'rosrun tiago_pose detectar_pose\\.py' || true"])
        return bool(out.strip())
    except Exception:
        return False

def iniciar_postura(request):
    print(">>> CLIC EN INICIAR POSTURA (Django lo recibió correctamente)")
    if not _is_pose_node_running():
        launch_cmd = _ros_env_cmd("nohup rosrun tiago_pose detectar_pose.py >/tmp/tiago_pose.log 2>&1 &")
        subprocess.Popen(launch_cmd, shell=True)
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
