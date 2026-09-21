# Docker solo valida la LOGICA pura (parseo del .vil, motor de capas, tap-hold)
# de forma reproducible en cualquier SO. NO prueba la captura/emision real de
# teclas: eso necesita acceso al hardware USB y a las APIs de entrada del SO
# (evdev/uinput en Linux, hook global en Windows), que un contenedor no tiene.
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python3 tests/test_logic.py
CMD ["python3", "tests/test_logic.py"]
