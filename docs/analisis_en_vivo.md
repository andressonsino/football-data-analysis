# Guía de Análisis de Fútbol en Vivo
**Repositorio:** football-analytics  
**Autor:** Andrés  
**Versión:** 1.0  
**Última actualización:** 2025

> Guía práctica para extraer, procesar y publicar análisis durante un partido en tiempo real.  
> Complementa `docs/metodologia-futbol.md` para el enfoque estadístico.

---

## Índice

1. [Configuración de importaciones](#1-configuración-de-importaciones)
2. [Árbol de decisión — qué fuente usar](#2-árbol-de-decisión--qué-fuente-usar)
3. [Flujo de trabajo para un partido](#3-flujo-de-trabajo-para-un-partido)
4. [Fuente principal — SofaScore API](#4-fuente-principal--sofascore-api)
5. [Fuente alternativa — football-data.org](#5-fuente-alternativa--football-dataorg)
6. [Procesamiento de datos en vivo](#6-procesamiento-de-datos-en-vivo)
7. [Visualizaciones para publicar](#7-visualizaciones-para-publicar)
8. [Análisis post-partido con FBref](#8-análisis-post-partido-con-fbref)
9. [Estructura de publicación](#9-estructura-de-publicación)
10. [Errores comunes y soluciones](#10-errores-comunes-y-soluciones)
11. [Checklist de partido](#11-checklist-de-partido)

---

## 1. Configuración de importaciones

Ejecutar una sola vez al inicio del notebook de análisis en vivo.

```python
# Librerías estándar
import os
import json
import time
from datetime import datetime

# Datos
import pandas as pd
import numpy as np

# HTTP
import requests

# Visualización
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# Configuración de pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', '{:.2f}'.format)

# Configuración de gráficos
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 11
sns.set_theme(style='whitegrid')

# Headers base para todas las requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "es-AR,es;q=0.9",
}

print("Configuración lista")
```

---

## 2. Árbol de decisión — qué fuente usar

```
¿Qué tipo de análisis querés hacer?
│
├── Durante el partido (tiempo real)
│   ├── Liga Argentina o Premier → SofaScore API     [Sección 4]
│   └── Necesitás xG en vivo    → SofaScore API     [Sección 4]
│
├── Al descanso o final del partido
│   ├── Estadísticas generales  → SofaScore API     [Sección 4]
│   └── Resultados y fixture    → football-data.org [Sección 5]
│
└── Post-partido (1-2hs después del pitazo)
    └── Análisis profundo       → FBref             [Sección 8]
```

**Regla general:**
```
Tiempo real y semi-real  → SofaScore API (gratuito, sin registro)
Resultados y fixture     → football-data.org (gratuito con registro)
Análisis táctico profundo → FBref (post-partido, gratuito)
Datos de eventos         → StatsBomb Open Data (histórico, gratuito)
```

---

## 3. Flujo de trabajo para un partido

> Seguir este orden en cada partido que analices.

```
ANTES DEL PARTIDO (30 min antes)
    Buscar el match_id del partido en SofaScore
    Preparar el notebook con la configuración
    Publicar lineup y contexto pre-partido

PRIMER TIEMPO
    Correr el script de datos cuando querás actualizar
    Guardar snapshot al minuto 45

AL DESCANSO
    Procesar datos del 1T
    Publicar análisis de primer tiempo

SEGUNDO TIEMPO
    Actualizar datos en los minutos clave (60', 75', 90')

AL FINAL
    Guardar snapshot final
    Publicar análisis completo del partido

POST-PARTIDO (1-2hs después)
    Bajar datos de FBref cuando estén disponibles
    Publicar análisis táctico profundo
```

---

## 4. Fuente principal — SofaScore API

SofaScore actualiza sus datos cada 2-3 minutos durante el partido.  
No requiere registro ni API key — usa la API interna del sitio.

### 4.1 Encontrar el match_id

```python
# El match_id está en la URL del partido en SofaScore
# Ejemplo: https://www.sofascore.com/huracan-boca-juniors/abc#id:12345678
#                                                                  ^^^^^^^^
# Ese número al final es el match_id

MATCH_ID = "12345678"    # ← CAMBIAR: match_id del partido a analizar
EQUIPO_LOCAL = "Huracán"   # ← CAMBIAR
EQUIPO_VISITANTE = "Boca Juniors"  # ← CAMBIAR
```

### 4.2 Función base de extracción

```python
def traer_datos_partido(match_id: str, endpoint: str = "statistics") -> dict:
    """
    Extrae datos de un partido desde SofaScore.

    Endpoints disponibles:
        'statistics'  → estadísticas generales (posesión, tiros, pases, etc.)
        'lineups'     → formaciones y jugadores titulares
        'incidents'   → goles, tarjetas, cambios con minuto exacto
        'best-player' → mejor jugador del partido según SofaScore
    """
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/{endpoint}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP {response.status_code}: {e}")
    except requests.exceptions.Timeout:
        print("Timeout — SofaScore tardó demasiado")
    except Exception as e:
        print(f"Error: {e}")

    return {}
```

### 4.3 Estadísticas generales del partido

```python
def estadisticas_partido(match_id: str) -> pd.DataFrame:
    """
    Devuelve un DataFrame con las estadísticas del partido por equipo.
    Incluye posesión, tiros, pases, corners, faltas, tarjetas y más.
    """
    datos = traer_datos_partido(match_id, "statistics")

    if not datos or 'statistics' not in datos:
        print("Sin datos disponibles aún")
        return pd.DataFrame()

    registros = []
    for grupo in datos['statistics']:
        for stat in grupo['statisticsItems']:
            registros.append({
                'categoria': grupo['groupName'],
                'metrica': stat['name'],
                'local': stat.get('home', None),
                'visitante': stat.get('away', None),
                'tipo': stat.get('type', None)
            })

    df = pd.DataFrame(registros)
    print(f"Estadísticas disponibles: {len(df)} métricas")
    return df

# Uso — correr cuando querés actualizar los datos
df_stats = estadisticas_partido(MATCH_ID)
display(df_stats)
```

### 4.4 Guardar snapshot por momento del partido

```python
def guardar_snapshot(df: pd.DataFrame, momento: str, carpeta: str = 'data/live') -> str:
    """
    Guarda un snapshot de las estadísticas en un momento específico del partido.

    Parámetros:
        momento : descripción del momento ('descanso', 'min60', 'final', etc.)
    """
    os.makedirs(carpeta, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    nombre = f"{EQUIPO_LOCAL.lower().replace(' ', '_')}_vs_"  \
             f"{EQUIPO_VISITANTE.lower().replace(' ', '_')}_{momento}_{timestamp}.csv"
    ruta = f"{carpeta}/{nombre}"
    df.to_csv(ruta, index=False)
    print(f"Snapshot guardado: {ruta}")
    return ruta

# Uso — al descanso
guardar_snapshot(df_stats, 'descanso')

# Uso — al final
guardar_snapshot(df_stats, 'final')
```

### 4.5 Extraer métricas clave

```python
def metrica(df: pd.DataFrame, nombre: str, equipo: str = 'local'):
    """
    Extrae el valor de una métrica específica para un equipo.

    Parámetros:
        nombre : nombre de la métrica en inglés (como aparece en SofaScore)
                 Ejemplos: 'Ball possession', 'Total shots', 'Shots on target',
                           'Big chances', 'Expected goals', 'Passes', 'Corners'
        equipo : 'local' o 'visitante'
    """
    fila = df[df['metrica'].str.lower() == nombre.lower()]

    if fila.empty:
        print(f"Métrica '{nombre}' no encontrada")
        return None

    valor = fila[equipo].values[0]

    # Limpiar porcentajes y convertir a float
    if isinstance(valor, str) and '%' in valor:
        return float(valor.replace('%', ''))

    return valor

# Ejemplos de uso
posesion_local = metrica(df_stats, 'Ball possession', 'local')
xg_local = metrica(df_stats, 'Expected goals', 'local')
xg_visitante = metrica(df_stats, 'Expected goals', 'visitante')
tiros_arco_local = metrica(df_stats, 'Shots on target', 'local')

print(f"Posesión {EQUIPO_LOCAL}: {posesion_local}%")
print(f"xG {EQUIPO_LOCAL}: {xg_local}")
print(f"xG {EQUIPO_VISITANTE}: {xg_visitante}")
```

### 4.6 Incidentes del partido (goles, tarjetas, cambios)

```python
def incidentes_partido(match_id: str) -> pd.DataFrame:
    """
    Devuelve todos los eventos del partido con su minuto exacto.
    Incluye goles, tarjetas amarillas y rojas, y cambios.
    """
    datos = traer_datos_partido(match_id, "incidents")

    if not datos or 'incidents' not in datos:
        print("Sin incidentes disponibles aún")
        return pd.DataFrame()

    registros = []
    for inc in datos['incidents']:
        registros.append({
            'minuto': inc.get('time', None),
            'tipo': inc.get('incidentType', None),
            'equipo': inc.get('isHome', None),
            'jugador': inc.get('player', {}).get('name', None) if 'player' in inc else None,
            'descripcion': inc.get('incidentClass', None)
        })

    df = pd.DataFrame(registros)
    df['equipo'] = df['equipo'].map({True: EQUIPO_LOCAL, False: EQUIPO_VISITANTE})
    df = df.sort_values('minuto').reset_index(drop=True)

    return df

# Uso
df_incidentes = incidentes_partido(MATCH_ID)
display(df_incidentes)
```

### 4.7 Lineup y formación

```python
def lineup_partido(match_id: str) -> tuple:
    """
    Devuelve dos DataFrames: titulares local y visitante.
    Incluye nombre, posición y número de camiseta.
    """
    datos = traer_datos_partido(match_id, "lineups")

    if not datos:
        return pd.DataFrame(), pd.DataFrame()

    def parsear_equipo(jugadores_raw):
        return pd.DataFrame([{
            'nombre': j['player']['name'],
            'posicion': j.get('position', None),
            'numero': j.get('shirtNumber', None),
            'capitan': j.get('captain', False)
        } for j in jugadores_raw])

    local = parsear_equipo(datos.get('home', {}).get('players', []))
    visitante = parsear_equipo(datos.get('away', {}).get('players', []))

    return local, visitante

# Uso
df_local, df_visitante = lineup_partido(MATCH_ID)
print(f"Lineup {EQUIPO_LOCAL}:")
display(df_local)
```

---

## 5. Fuente alternativa — football-data.org

API gratuita con registro. Útil para resultados, fixtures y standings.  
Requiere API key gratuita en `https://www.football-data.org/client/register`

```python
API_KEY = "TU_API_KEY"    # ← CAMBIAR: tu key gratuita de football-data.org

HEADERS_FD = {
    "X-Auth-Token": API_KEY
}

def traer_partidos_jornada(competicion: str, jornada: int) -> pd.DataFrame:
    """
    Trae los partidos de una jornada específica.

    Códigos de competición:
        'PL'   → Premier League
        'PD'   → La Liga
        'SA'   → Serie A
        'BL1'  → Bundesliga
        'FL1'  → Ligue 1
        'WC'   → Copa del Mundo
    """
    url = f"https://api.football-data.org/v4/competitions/{competicion}/matches"
    params = {"matchday": jornada}

    response = requests.get(url, headers=HEADERS_FD, params=params, timeout=10)
    response.raise_for_status()

    partidos = response.json()['matches']
    return pd.DataFrame([{
        'fecha': p['utcDate'],
        'local': p['homeTeam']['name'],
        'visitante': p['awayTeam']['name'],
        'goles_local': p['score']['fullTime']['home'],
        'goles_visitante': p['score']['fullTime']['away'],
        'estado': p['status']
    } for p in partidos])

# Uso
df_jornada = traer_partidos_jornada('PL', jornada=32)
display(df_jornada)
```

---

## 6. Procesamiento de datos en vivo

### 6.1 Tabla resumen del partido

```python
def resumen_partido(df_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Genera una tabla resumen con las métricas más relevantes para publicar.
    """
    metricas_clave = [
        'Ball possession',
        'Total shots',
        'Shots on target',
        'Big chances',
        'Expected goals',
        'Passes',
        'Accurate passes',
        'Corners',
        'Fouls',
        'Yellow cards',
        'Red cards'
    ]

    resumen = []
    for m in metricas_clave:
        fila = df_stats[df_stats['metrica'].str.lower() == m.lower()]
        if not fila.empty:
            resumen.append({
                'Métrica': m,
                EQUIPO_LOCAL: fila['local'].values[0],
                EQUIPO_VISITANTE: fila['visitante'].values[0]
            })

    return pd.DataFrame(resumen)

# Uso
df_resumen = resumen_partido(df_stats)
display(df_resumen)
```

### 6.2 Calcular diferencial de xG

```python
def analisis_xg(df_stats: pd.DataFrame) -> dict:
    """
    Calcula el diferencial de xG y determina quién merece ganar según el juego.
    """
    xg_local = float(metrica(df_stats, 'Expected goals', 'local') or 0)
    xg_visit = float(metrica(df_stats, 'Expected goals', 'visitante') or 0)
    diferencial = xg_local - xg_visit

    if diferencial > 0.5:
        merecimiento = f"{EQUIPO_LOCAL} merece ganar según el juego"
    elif diferencial < -0.5:
        merecimiento = f"{EQUIPO_VISITANTE} merece ganar según el juego"
    else:
        merecimiento = "Partido parejo según el xG"

    return {
        'xg_local': xg_local,
        'xg_visitante': xg_visit,
        'diferencial': round(diferencial, 2),
        'merecimiento': merecimiento
    }

# Uso
analisis = analisis_xg(df_stats)
for clave, valor in analisis.items():
    print(f"{clave}: {valor}")
```

---

## 7. Visualizaciones para publicar

### 7.1 Comparación de estadísticas — gráfico de barras horizontales

```python
def grafico_comparacion(df_resumen: pd.DataFrame, titulo: str = None) -> None:
    """
    Gráfico de barras horizontales enfrentadas para comparar estadísticas.
    Diseñado para exportar y publicar en redes sociales.
    """
    metricas = df_resumen['Métrica'].tolist()
    valores_local = pd.to_numeric(df_resumen[EQUIPO_LOCAL]
                    .astype(str).str.replace('%', ''), errors='coerce').fillna(0).tolist()
    valores_visit = pd.to_numeric(df_resumen[EQUIPO_VISITANTE]
                    .astype(str).str.replace('%', ''), errors='coerce').fillna(0).tolist()

    fig, ax = plt.subplots(figsize=(12, 8))

    y = range(len(metricas))
    ax.barh(y, [-v for v in valores_local], color='#1a73e8', alpha=0.8, label=EQUIPO_LOCAL)
    ax.barh(y, valores_visit, color='#e8341a', alpha=0.8, label=EQUIPO_VISITANTE)

    ax.set_yticks(y)
    ax.set_yticklabels(metricas, fontsize=11)
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_title(titulo or f'{EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}', fontsize=14, pad=15)

    # Etiquetas de valores
    for i, (vl, vv) in enumerate(zip(valores_local, valores_visit)):
        ax.text(-vl - 0.5, i, str(vl), ha='right', va='center', fontsize=9)
        ax.text(vv + 0.5, i, str(vv), ha='left', va='center', fontsize=9)

    ax.legend(loc='lower right')
    ax.set_xlabel('')
    ax.xaxis.set_visible(False)
    plt.tight_layout()
    plt.savefig('outputs/comparacion_stats.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("Guardado en outputs/comparacion_stats.png")

# Uso
os.makedirs('outputs', exist_ok=True)
grafico_comparacion(df_resumen, titulo=f'{EQUIPO_LOCAL} vs {EQUIPO_VISITANTE} — Estadísticas')
```

### 7.2 Evolución de xG durante el partido

```python
def grafico_xg_timeline(df_incidentes: pd.DataFrame) -> None:
    """
    Gráfico de línea con la evolución del xG acumulado durante el partido.
    Requiere que los incidentes incluyan el xG de cada tiro.
    """
    goles_local = df_incidentes[
        (df_incidentes['tipo'] == 'goal') &
        (df_incidentes['equipo'] == EQUIPO_LOCAL)
    ][['minuto']].copy()

    goles_visit = df_incidentes[
        (df_incidentes['tipo'] == 'goal') &
        (df_incidentes['equipo'] == EQUIPO_VISITANTE)
    ][['minuto']].copy()

    fig, ax = plt.subplots(figsize=(14, 5))

    # Línea vertical en el descanso
    ax.axvline(45, color='gray', linestyle='--', alpha=0.5, label='Descanso')

    # Marcar goles
    for _, gol in goles_local.iterrows():
        ax.axvline(gol['minuto'], color='#1a73e8', alpha=0.6, linewidth=2)
        ax.text(gol['minuto'], ax.get_ylim()[1] * 0.9, f"⚽ {gol['minuto']}'",
                color='#1a73e8', fontsize=9, ha='center')

    for _, gol in goles_visit.iterrows():
        ax.axvline(gol['minuto'], color='#e8341a', alpha=0.6, linewidth=2)
        ax.text(gol['minuto'], ax.get_ylim()[1] * 0.7, f"⚽ {gol['minuto']}'",
                color='#e8341a', fontsize=9, ha='center')

    ax.set_xlabel('Minuto')
    ax.set_title(f'Timeline de goles — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
    ax.legend()
    plt.tight_layout()
    plt.savefig('outputs/timeline_goles.png', dpi=150, bbox_inches='tight')
    plt.show()
```

---

## 8. Análisis post-partido con FBref

FBref publica estadísticas completas 1-2 horas después del pitazo final.  
Es el análisis más profundo y usa las mismas funciones de la guía de scraping.

```python
def traer_stats_fbref_partido(url_partido: str) -> dict:
    """
    Extrae estadísticas de un partido específico desde FBref.
    La URL se obtiene desde la página del partido en FBref.

    Retorna un diccionario con DataFrames por categoría.
    """
    response = requests.get(url_partido, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    response.raise_for_status()

    tablas = pd.read_html(response.text)
    print(f"Tablas disponibles: {len(tablas)}")

    return {
        'stats_local': tablas[0] if len(tablas) > 0 else pd.DataFrame(),
        'stats_visitante': tablas[1] if len(tablas) > 1 else pd.DataFrame(),
    }

# Uso — después del partido
url_fbref = "https://fbref.com/en/matches/..."    # ← CAMBIAR: URL del partido en FBref
datos_fbref = traer_stats_fbref_partido(url_fbref)
display(datos_fbref['stats_local'])
```

---

## 9. Estructura de publicación

### 9.1 Momentos clave para publicar

```
PRE-PARTIDO (30 min antes)
→ Lineup confirmado + formación
→ Contexto: últimos 5 partidos, historial entre ambos

DESCANSO
→ Resumen estadístico del 1T
→ xG diferencial + quién merece ganar
→ Una visualización de comparación

FINAL DEL PARTIDO
→ Estadísticas completas
→ Análisis de incidentes clave
→ Quién mereció ganar según los datos

POST-PARTIDO (1-2hs después)
→ Análisis táctico profundo con FBref
→ Métricas avanzadas: pases progresivos, presiones, zonas de juego
```

### 9.2 Plantilla de texto para publicar al descanso

```python
def generar_texto_descanso(df_stats: pd.DataFrame, resultado: str) -> str:
    """
    Genera un texto base para publicar al descanso.
    Resultado en formato '1-0', '0-0', etc.
    """
    analisis = analisis_xg(df_stats)
    posesion = metrica(df_stats, 'Ball possession', 'local')
    tiros_local = metrica(df_stats, 'Total shots', 'local')
    tiros_visit = metrica(df_stats, 'Total shots', 'visitante')

    texto = f"""
📊 Análisis de primer tiempo — {EQUIPO_LOCAL} {resultado} {EQUIPO_VISITANTE}

⚽ xG: {EQUIPO_LOCAL} {analisis['xg_local']} — {analisis['xg_visitante']} {EQUIPO_VISITANTE}
🎯 Tiros: {tiros_local} vs {tiros_visit}
🔵 Posesión {EQUIPO_LOCAL}: {posesion}%

📌 {analisis['merecimiento']}

#Fútbol #{EQUIPO_LOCAL.replace(' ', '')} #{EQUIPO_VISITANTE.replace(' ', '')}
    """.strip()

    return texto

# Uso
resultado_1t = "1-0"    # ← CAMBIAR: resultado al descanso
print(generar_texto_descanso(df_stats, resultado_1t))
```

---

## 10. Errores comunes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `404 Not Found` en SofaScore | match_id incorrecto | Verificar el ID en la URL del partido |
| Datos vacíos antes del partido | El partido no empezó | Esperar al pitazo inicial |
| `KeyError` en estadísticas | SofaScore cambió la estructura | Imprimir `datos.keys()` para inspeccionar |
| Métrica devuelve `None` | El nombre no coincide exactamente | Imprimir `df_stats['metrica'].unique()` para ver los nombres reales |
| xG no disponible | Partido sin datos de xG (ligas menores) | Usar tiros al arco como proxy |
| FBref sin datos del partido | Muy reciente, aún no publicado | Esperar 1-2hs post-partido |
| Timeout frecuente | Servidor saturado durante el partido | Aumentar `timeout=` o espaciar las requests |

---

## 11. Checklist de partido

### Antes del partido
- [ ] Buscar y configurar `MATCH_ID` en SofaScore
- [ ] Configurar `EQUIPO_LOCAL` y `EQUIPO_VISITANTE`
- [ ] Verificar que la API responde con `traer_datos_partido(MATCH_ID, 'lineups')`
- [ ] Preparar carpeta `outputs/` y `data/live/`

### Durante el partido
- [ ] Guardar snapshot al minuto 45 (descanso)
- [ ] Guardar snapshot al final del partido
- [ ] Publicar análisis al descanso con `generar_texto_descanso()`

### Post-partido
- [ ] Guardar snapshot final en `data/live/`
- [ ] Esperar 1-2hs y bajar datos de FBref
- [ ] Publicar análisis profundo post-partido
- [ ] Documentar URL de FBref del partido para referencia futura

---

*Para metodología estadística aplicada al análisis → `docs/metodologia-futbol.md`*  
*Para scraping avanzado de fuentes → `docs/guia-scraping-web.md`*
