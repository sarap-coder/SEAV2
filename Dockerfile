FROM ros:noetic

RUN apt update && apt install -y rviz \
         ros-noetic-moveit \
         curl \
         apt-utils \
         python3-pip \
         python-is-python3 \
         ssh \
         net-tools \
         sudo \
         iputils-ping \
         nmap \
         xauth \
         ros-noetic-robot-state-publisher \
         ros-noetic-joint-state-publisher \
         git \
         ros-noetic-usb-cam \
         htop \
         sudo \
         libxmlrpc-core-c3-dev

RUN pip install catkin_tools \
                tensorboard \
                opencv-python \
                ultralytics \
                django
                
RUN rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1000 tiago && \
    useradd -ms /bin/bash tiago -u 1000 -g 1000 && \
    echo "tiago ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    echo "source /home/tiago/carpeta_compartida/setup_env.sh" >> /home/tiago/.bashrc && \
    RUN echo 'tiago:tiago' | chpasswd && \
    chown tiago:tiago /home/tiago && \
    mkdir -p /var/run/tiago/1000 && \
    chown tiago:tiago /var/run/tiago/1000

USER tiago

ENTRYPOINT [ "sleep", "infinity"]