# NVDAMacroManager (IDE moderno de macros y motor de automatización)

**Desarrollador:** Muhammet Enes Şenovalı
**Versión:** 1.2.6

NVDA Macro Manager es un grabador, editor y motor de reproducción accesible de macros de teclado integrado con el lector de pantalla NVDA. Está pensado para flujos de trabajo repetibles en los que se conocen la aplicación de destino y la secuencia de teclas grabada.

## 🚀 Funciones principales

* **Dos modos de grabación (en directo y seguro):** En el modo en directo, las teclas llegan a las aplicaciones mientras se graban. El modo seguro bloquea las pulsaciones físicas hasta que se detiene con `NVDA + Windows + Mayús + R`.
* **Atajos dinámicos de NVDA:** Las macros guardadas se integran en NVDA. Puede asignar un atajo propio a cada macro desde `Preferencias → Gestos de entrada → Administrador de macros`.
* **IDE profesional de macros (editor de eventos):**
  * **Flujo lineal:** Las teclas y los retrasos son pasos independientes (Esperar, Pulsar, Pulsar tecla, Soltar tecla).
  * **Portapapeles de eventos:** `Ctrl + C`, `Ctrl + X` y `Ctrl + V` copian o mueven pasos de la macro.
  * **Deshacer/Rehacer:** `Ctrl + Z` y `Ctrl + Y` deshacen o restauran cambios.
  * **Inserción de eventos:** Añada nuevos retrasos o teclas en cualquier punto.
* **Captura inteligente de teclas:** Capture una tecla física o selecciónela en una lista localizada generada por el sistema operativo.
* **Reproducción de entrada de Windows:** La reproducción utiliza la API `SendInput` de Windows. Algunas aplicaciones protegidas, elevadas, remotas o juegos pueden rechazar la entrada simulada; no se garantiza la compatibilidad con sistemas anti-trampas.
* **Velocidad, retardo inicial y repeticiones:** Ajuste libremente la velocidad, elija un retardo independiente de la velocidad antes del primer evento, use reproducción instantánea o configure un bucle infinito.
* **Bloqueo de aplicación:** Restrinja una macro a una aplicación. La reproducción no comienza si no puede comprobarse la aplicación y se detiene si cambia el foco.
* **Multilingüe:** Catálogos de interfaz completos en inglés, turco, español, alemán y portugués (Portugal).

## ⌨️ Atajos predeterminados

* **`NVDA + Windows + R`:** Inicia o detiene la grabación en directo.
* **`NVDA + Windows + Mayús + R`:** Inicia o detiene la grabación segura. Las pulsaciones físicas se bloquean durante la grabación.
* **`NVDA + Windows + P`:** Reproduce la última macro temporal grabada o cancela una reproducción en curso.
* **`NVDA + Mayús + M`:** Abre el Administrador de macros.

## 📦 Instalación

1. Descargue el último archivo `.nvda-addon` desde [GitHub Releases](https://github.com/m-enes-senovali/nvdaMacroManager/releases).
2. Abra el archivo mientras NVDA está en ejecución y confirme la instalación.
3. Reinicie NVDA cuando se le solicite y compruebe el complemento en **Menú NVDA → Herramientas → Tienda de complementos → Complementos instalados**.

Se requiere NVDA 2023.1 o posterior. Solo se admite Windows porque la grabación y la reproducción utilizan las API de teclado de Windows.

## 🛠️ Uso

### 1. Grabar rápidamente una macro

* Use `NVDA + Windows + R` para una grabación normal.
* Use `NVDA + Windows + Mayús + R` cuando no quiera que las teclas actúen sobre el sistema durante la grabación.
* Detenga la grabación con el mismo atajo y pruebe la macro temporal con `NVDA + Windows + P`.

### 2. Guardar y editar macros

Abra el administrador con `NVDA + Mayús + M`, indique un nombre, configure la velocidad, el retardo inicial y el número de repeticiones y guarde la macro. El retardo inicial se aplica una sola vez antes del primer evento y no cambia con la velocidad de reproducción.

Seleccione una macro guardada y elija **Editar**:

* Use `Mayús` para seleccionar varios eventos.
* Copie o mueva eventos con `Ctrl + C`, `Ctrl + X` y `Ctrl + V`.
* Modifique retrasos o teclas capturadas.
* Inserte nuevos pasos con **Añadir evento**.

### 3. Asignar atajos personalizados

Abra `Preferencias → Gestos de entrada` en NVDA, expanda **Administrador de macros**, seleccione la macro y asígnele un atajo.

## 🔒 Datos y seguridad

Las macros guardadas se almacenan como `nvda_macros.json` en el directorio de configuración activo de NVDA. Las actualizaciones se escriben de forma atómica y el archivo anterior se conserva como `nvda_macros.json.bak`. Las importaciones desde archivos y el portapapeles se validan y limitan por tamaño antes de utilizarse.

La grabación segura bloquea las pulsaciones físicas, pero la reproducción realiza acciones reales de teclado. Revise las macros importadas, pruébelas primero en una aplicación no crítica y utilice bloqueos de aplicación siempre que sea posible. El complemento no puede eludir los niveles de integridad de Windows, las aplicaciones protegidas, las restricciones de sesiones remotas ni los controles de seguridad de los juegos.
