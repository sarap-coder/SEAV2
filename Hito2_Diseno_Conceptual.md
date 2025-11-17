# Hito 2 – Diseño Conceptual  
### Proyecto: **Exploración clínica asistida por robot**  
### Asignatura: Robótica aplicada a servicios biomédicos  
### Equipo: Eva Gómez, Sara Peñas y Ander Díez

---

## 1. Resumen del problema biomédico

En contextos biomédicos como rehabilitación física, geriatría y evaluación funcional de pacientes, resulta fundamental obtener mediciones objetivas, repetibles y no invasivas sobre el estado físico del paciente. Los profesionales requieren datos como la temperatura corporal, la postura, el tiempo de reacción y el ritmo cardíaco para valorar el estado de salud y evolución de cada individuo.

Este proyecto propone utilizar el robot TIAGo de PAL Robotics para realizar una **evaluación biomédica asistida**, enfocándose en la interacción física segura con el paciente. El sistema emplea sensores térmicos, RGB-D y un pulsómetro Bluetooth, junto con el brazo robótico del TIAGo, para medir:

- Temperatura corporal (sensor térmico).
- Ritmo cardíaco (pulsómetro Bluetooth).
- Postura (cámara RGB-D).
- Tiempo de reacción (estimación indirecta mediante la cámara del robot).

Además, el sistema guía al usuario mediante una **interfaz web desarrollada en Django**, registrando resultados y proporcionando retroalimentación clara y accesible.

---

## 2. Arquitectura del sistema

### 2.1 Diagrama general del sistema y módulos funcionales

**Módulos principales:**

1. **Percepción**  
   - Cámara térmica → Obtención de temperatura.  
   - RGB-D integrada (Xtion) → Estimación de postura del paciente.

2. **Interacción física**  
   - Brazo y cámara del robot → Estimación del tiempo de reacción del paciente.
   - Pulsómetro Bluetooth → Lectura del ritmo cardíaco.

3. **Control del robot**  
   - Planificación de trayectorias del brazo.  
   - Control de presión de contacto.  
   - Posicionamiento suave el paciente.

4. **Interfaz Web (Django)**  
   - Flujo guiado para el paciente.  
   - Visualización de mediciones.  
   - Almacenamiento de datos en CSV.

5. **Integración ROS ↔ Django**  
   - Nodo puente ROS que envía datos a Django por REST/WebSockets.
   - Comandos desde Django hacia ROS (start/stop, siguiente paso).

### Diagrama conceptual (descripción)

---

### 2.2 Especificación del hardware

| Componente | Descripción | Comunicación |
|-----------|-------------|--------------|
| **Robot TIAGo** | Base móvil + brazo de 7 DOF + pinza paralela | ROS 1 TCPROS |
| **Sensor térmico tipo pistola** | Temperatura puntual (frente/muñeca) | USB / SD |
| **RGB-D (Asus Xtion)** | Nube de puntos + imagen para postura | /xtion/* topics |
| **Pulsómetro Bluetooth** | Frecuencia cardíaca | BLE nodo ROS |
| **Laptop o servidor** | Ejecuta Django + nodos ROS propios | Ethernet/WiFi |

---

### 2.3 Interfaz de usuario y flujo de interacción

El sistema guía al paciente paso a paso:

1. **Bienvenida** → Introducción y comprobación de conexión.
2. **Inicio de sesión** → Inicio de sesión para guardar datos por paciente.
2. **Postura** → La cámara RGB-D analiza la alineación del torso.  
3. **Temperatura** → El sistema muestra instrucciones para usar la cámara térmica.  
4. **Pulso** → El usuario activa el pulsómetro Bluetooth.  
5. **Reflejos** → El robot posiciona su brazo enfrente del paciente y suelta un objeto, analizando el resultado con la cámara.
6. **Resultados** → Se resumen en pantalla y se guardan en CSV.

**Pantallas previstas:**
- Inicio  
- Elección de análisis
    - Postura  
    - Temperatura  
    - Pulso  
    - Reflejos 
- Resultados finales

---

## 3. Diseño de software y comunicación

### 3.1 Arquitectura de nodos en ROS 1

**Nodos principales:**

- `/biotouch_temp_reader` → Procesa lectura de sensor térmico.  #################################################
- `/biotouch_pose_estimator` → Analiza postura desde RGB-D.  
- `/biotouch_ble_hr` → Pulso desde pulsómetro Bluetooth.  
- `/biotouch_bridge` → Comunicación ROS ↔ Django.

**Topics:**

| Topic | Tipo | Función |
|-------|------|---------|
| `/gripper_controller/state` | JointTrajectoryControllerState | Estado del gripper |
| `/biotouch/temp` | std_msgs/Float32 | Temperatura corporal |
| `/biotouch/posture` | std_msgs/String | “Correcta/Incorrecta” |
| `/biotouch/pulse` | std_msgs/Int32 | BPM |
| `/biotouch/data` | custom_msgs/BioTouchData | Datos agregados |

---

### 3.2 Estructura del repositorio

    carpeta_compartida/
    ├── docs/
    │ └── Hito2_Diseno_Conceptual.md
    ├── catkin_ws/
    │ ├── src/
    │ │ ├── test_reflejos/
    │ │ ├── clinical_exploration/
    │ │ └── tiago_pose
    │ └── CMakeLists.txt
    └── biotouch_web/ 
      ├── biotouch_web/ 
      └──  interfaz/
        └── templates/

---

### 3.3 Contenedores Docker y dependencias del entorno

El proyecto utilizará **un único contenedor Docker** que integra el entorno necesario para la ejecución del sistema, con el objetivo de simplificar el despliegue, garantizar la reproducibilidad y asegurar que todos los miembros del equipo trabajan sobre la misma configuración.

**Contenido del contenedor único:**

- **ROS Noetic**  
  Incluye nodos personalizados del proyecto (lectura de postura, temperatura, tiempo de reacción, ritmo cardíaco del pulsómetro y puente ROS ↔ web).

- **Servidor web Django**  
  Aplicación web que guía al paciente y visualiza los resultados en tiempo real.

- **Dependencias adicionales:**  
  - `rosbridge_server` para comunicación web.  
  - Librerías de Bluetooth (bleak).  
  - OpenCV, NumPy, ultralytics y pytesseract para la analítica de datos.  
  - Django para la interfaz web.

---

## 4. Análisis de viabilidad técnica

### 4.1 Limitaciones técnicas identificadas

- La cámara térmica tipo pistola no recoge datos a tiempo real.
- BLE puede presentar latencias en la lectura del pulso.  
- Coordinación ROS ↔ Web puede requerir control de concurrencia.

### 4.2 Estrategias de mitigación

- Programación individual y creación de entorno para el control automático de la cámara.
- Uso de WebSockets para actualizar datos al navegador en tiempo real.
- Pruebas incrementales:  
  1. Simulación  
  2. Pruebas con objetos  
  3. Usuario real  
  4. Flujo completo

---

## 5. Cronograma de desarrollo

### 5.1 Plan temporal (Hito 3 → Final)

| Semana | Tarea |
|--------|--------|
| 1 | Accionamiento automático de cámara e interpretación de datos |
| 2 | Integración final en la interfaz y parametrizacón de los datos |
| 3 | Pruebas en robot real |
| 4 | Optimización e informe final | 

---

### 5.2 Reparto de responsabilidades actualizado

- **Sara:**  
  - Análisis de postura y reflejos
  - Interfaz gráfica  
  - Interacción física  
  - Experiencia de usuario  

- **Eva:**  
  - Percepción térmica
  - Tratamiento de datos de la cámara térmica
  - Integración de la cámara térmica al entorno

- **Ander:**  
  - Lectura de datos del pulsómetro  
  - Tratamiento de datos del pulsómetro
  - Preparación del modulos de control en la Raspberry Pi

---

**Fin del documento**
