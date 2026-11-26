# Simulación de tráfico con sistemas multiagentes

Simulación 3D de la ciudad diseñada en la actividad M4 (circuito exterior, calles interiores de doble
sentido y glorieta central). Los vehículos, semáforos e intersecciones son agentes de **AgentPy**; la
ciudad se dibuja con **Pygame + PyOpenGL** con estilo de maqueta urbana. El notebook
`Simulacion.ipynb` ejecuta el mismo modelo sin ventana para comparar dos políticas de semáforos
(fija y adaptativa).

- 8 intersecciones con semáforo: 4 en T (calle interior con el circuito) y 4 accesos a la glorieta.
- Vehículos autónomos: siguen su ruta, mantienen distancia de seguridad, piden permiso para cruzar,
  giran y cambian de carril en el circuito exterior (dos carriles del mismo sentido).
- Las calaveras se encienden cuando el coche frena o espera y las direccionales parpadean al girar o
  cambiar de carril (muestran la máquina de estados).

## Requisitos

- Windows 10/11.
- **Python 3.13** (versión probada). Descárgalo de https://www.python.org/downloads/ y marca
  "Add python.exe to PATH". Comprueba con:

  ```powershell
  py -3.13 --version
  ```

- Librerías (versiones exactas en `requirements.txt`): AgentPy 0.1.5, NumPy, SciPy, SALib, NetworkX,
  Joblib, Pandas, Matplotlib, Pygame, PyOpenGL, Jupyter Notebook, ipykernel y nbconvert.

## Instalación desde cero

1. Descomprime `Simulacion_Trafico.zip` y abre PowerShell dentro de la carpeta `Simulacion_Trafico`
   (en el Explorador: clic derecho dentro de la carpeta → "Abrir en Terminal").

2. Crea el entorno virtual:

   ```powershell
   py -3.13 -m venv .venv
   ```

3. Actívalo:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   Si PowerShell no permite ejecutar scripts, ejecuta esto (solo afecta a esa ventana) y vuelve a activar:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

4. Instala las dependencias:

   ```powershell
   python -m pip install --upgrade pip
   ```

   ```powershell
   python -m pip install -r requirements.txt
   ```

## Ejecutar la simulación gráfica

```powershell
python main.py
```

Empieza sola con 20 vehículos y control adaptativo. El título de la ventana muestra el tiempo
simulado, vehículos, política, velocidad media, detenidos, cruces y choques detectados.

| Tecla | Acción |
|---|---|
| ← / → , H / L, ↑ | Girar la cámara |
| K / J o rueda del ratón | Acercar / alejar |
| W / S | Subir / bajar la cámara |
| V | Vista superior / orbital |
| ESPACIO | Pausar / continuar |
| R | Reiniciar (misma semilla) |
| + / - | Agregar / quitar 4 vehículos (reinicia) |
| 1 / 2 / 3 | Tráfico ligero (8) / moderado (20) / elevado (40) |
| P | Cambiar la política de semáforos en vivo |
| F12 | Guardar captura en `capturas/` |
| ESC o cerrar la ventana | Salir |

## Ejecutar el notebook

```powershell
python -m notebook Simulacion.ipynb
```

En el navegador usa **Kernel → Restart Kernel and Run All Cells**. Los experimentos (3 escenarios ×
2 políticas × 5 repeticiones de 300 s) tardan entre medio minuto y unos minutos según la computadora.
Los resultados se guardan en `results/`. Sin navegador:

```powershell
python -m nbconvert --to notebook --execute --inplace Simulacion.ipynb
```

Usa `python -m notebook` (y no solo `jupyter notebook`) para que Jupyter sea el del entorno `.venv`,
sobre todo si también tienes Anaconda.

## Visual Studio Code

1. Crea el entorno e instala las dependencias (pasos anteriores).
2. **Archivo → Abrir carpeta** → `Simulacion_Trafico`.
3. `Ctrl+Shift+P` → **Python: Select Interpreter** → el que dice `.venv`.
4. Abre `main.py` y presiona **F5** (elige "Python Debugger: Python File" si lo pregunta) o el botón ▶.
5. Para el notebook: abre `Simulacion.ipynb`, **Select Kernel → Python Environments → .venv** y **Run All**.

Extensiones necesarias: Python, Pylance, Python Debugger y Jupyter (de Microsoft).

## Archivos

| Archivo | Qué hace |
|---|---|
| `main.py` | Ventana, cámara, controles, iluminación y bucle con paso lógico fijo. Solo dibuja lo que dicen los agentes. |
| `modelo_multiagentes.py` | Modelo AgentPy: `ModeloTrafico`, `AgenteVehiculo`, `AgenteSemaforo`, `AgenteInterseccion`, métricas y experimentos. |
| `red_vial.py` | Red lógica de carriles medida sobre `piso.png`: segmentos, giros, glorieta, intersecciones y postes. |
| `Carro.py` | Carro jerárquico (carrocería, llantas, luces, sombra) sincronizado con su agente. |
| `Semaforo.py` | Poste de semáforo con el color de su agente. |
| `Edificio.py` | Edificio con el modelo OBJ original y edificio urbano hecho con cajas (ventanas, puerta, azotea). |
| `Decoracion.py` | Árboles, arbustos, jardineras, bancas y farolas. |
| `Escenario.py` | Dónde va cada edificio y elemento decorativo (solo en áreas verdes y banquetas). |
| `Fuente.py` | Fuente original con isleta y agua. |
| `figuras.py` | Figuras básicas de OpenGL (caja, cilindro, esfera). |
| `objloader.py` | Cargador de modelos OBJ/MTL. |
| `models/`, `piso.png` | Modelos 3D, materiales y texturas. |
| `Simulacion.ipynb` | Experimentos sin ventana, tablas y gráficas. |
| `results/` | Resultados reales: CSV por corrida, resumen y gráficas. |

## Parámetros principales

| Qué cambiar | Dónde |
|---|---|
| Velocidad máxima, aceleración, frenado, distancia de seguridad | `modelo_multiagentes.py`: `V_MAX`, `A_MAX`, `B_COMODO`, `S0`, `T_SEGURIDAD` |
| Tiempos de semáforo (fijo y adaptativo) | `modelo_multiagentes.py`: `VERDE_FIJO`, `VERDE_MIN`, `VERDE_MAX`, `T_AMARILLO`, `T_TODO_ROJO`, `ESPERA_TOLERADA` |
| Capacidad y hueco de la glorieta | `modelo_multiagentes.py`: `CAPACIDAD_GLORIETA`, `T_HUECO_GLORIETA` |
| Probabilidad de girar, salir de la glorieta o cambiar de carril | `modelo_multiagentes.py`: `AgenteVehiculo._opciones` |
| Escenarios (8 / 20 / 40) | `modelo_multiagentes.py`: `ESCENARIOS` |
| Vehículos, política y semilla al abrir la ventana | `main.py`: `n_vehiculos`, `politica`, `semilla` |
| Cámara inicial y colores de los carros | `main.py`: `theta`, `radius`, `altura_camara`, `COLORES_CARRO` |
| Edificios, árboles, bancas y farolas | `Escenario.py` |
| Duración, repeticiones y semilla de los experimentos | `Simulacion.ipynb`, sección 2 |

Unidades: internamente se usan unidades del mundo OpenGL (15 unidades = 1 m); las métricas se
reportan en metros, segundos y vehículos. El paso lógico es de 0.1 s y no depende de los FPS.

## Solución de errores comunes

| Problema | Solución |
|---|---|
| `py` no se reconoce | Instala Python 3.13 con "Add python.exe to PATH" o usa la ruta completa de `python.exe`. |
| No se puede ejecutar `Activate.ps1` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, o ejecuta `.\.venv\Scripts\python.exe main.py` sin activar. |
| `ModuleNotFoundError` (agentpy, pygame, OpenGL) | El entorno no está activado o VS Code usa otro intérprete. Selecciona `.venv`. |
| El notebook no encuentra `agentpy` | Jupyter usa otro Python (por ejemplo Anaconda). Ábrelo con `python -m notebook` o elige el kernel `.venv` en VS Code. |
| Falla la instalación de `pygame` | Usa Python 3.13; en versiones más nuevas puede no haber paquetes precompilados. |
| Ventana negra o errores de OpenGL | Actualiza los controladores de video. |
| La simulación se ve lenta | Reduce los vehículos con `-` o la tecla `1`. La lógica no cambia: el paso es fijo. |
| `FileNotFoundError` de modelos o texturas | No muevas `main.py` fuera de su carpeta; las rutas se calculan desde ese archivo. |

## Créditos

- Diseño de la ciudad (M4) y proyecto: Belsy Aislinn Rueda Santiago y Juan José Moreno Arenas.
- Clase `Carro` original: Ivan Olmos Pineda.
- Modelación de sistemas multiagentes con gráficas computacionales — Tecnológico de Monterrey.
