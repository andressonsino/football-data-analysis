# Metodología de Análisis de Fútbol con Datos
**Repositorio:** football-analytics  
**Autor:** Andrés  
**Versión:** 1.0  
**Última actualización:** 2025

> Guía metodológica específica para análisis de fútbol con datos.  
> Para fundamentos estadísticos generales, ver `ds-toolkit/metodologia/metodologia-analisis-datos.md`

---

## Índice

1. [Principio fundamental](#1-principio-fundamental)
2. [Separar el QUÉ del POR QUÉ en fútbol](#2-separar-el-qué-del-por-qué-en-fútbol)
3. [Fuentes de datos deportivos](#3-fuentes-de-datos-deportivos)
4. [Recolección desde FBref](#4-recolección-desde-fbref)
5. [Limpieza específica de datos de fútbol](#5-limpieza-específica-de-datos-de-fútbol)
6. [Normalización por 90 minutos](#6-normalización-por-90-minutos)
7. [Análisis comparativo entre ligas](#7-análisis-comparativo-entre-ligas)
8. [Modelado aplicado al fútbol](#8-modelado-aplicado-al-fútbol)
9. [Interpretación táctica de resultados](#9-interpretación-táctica-de-resultados)
10. [Comunicación por audiencia](#10-comunicación-por-audiencia)
11. [Errores comunes en análisis de fútbol](#11-errores-comunes-en-análisis-de-fútbol)
12. [Glosario de métricas de fútbol](#12-glosario-de-métricas-de-fútbol)
13. [Checklist de análisis futbolístico](#13-checklist-de-análisis-futbolístico)

---

## 1. Principio fundamental

> **Un número de fútbol sin contexto táctico no es análisis — es una tabla.**

El diferencial de un buen analista deportivo no es calcular bien, sino interpretar bien. Cada métrica debe responder una pregunta táctica concreta.

Flujo correcto:

```
Pregunta táctica concreta
        ↓
¿Qué métricas la responden?
        ↓
¿Están disponibles en las fuentes que tengo?
        ↓
Recolección → Limpieza → EDA → Supuestos estadísticos
        ↓
Hallazgo estadístico
        ↓
Interpretación táctica   ← el paso que más diferencia
        ↓
Comunicación adaptada a la audiencia
```

---

## 2. Separar el QUÉ del POR QUÉ en fútbol

Antes de elegir métricas, clasificarlas explícitamente:

| Pregunta | Tipo | Métricas |
|----------|------|---------|
| ¿La Premier genera más goles? | **QUÉ** (descriptiva) | Goles per 90, xG per 90 |
| ¿Por qué genera más goles? | **POR QUÉ** (explicativa) | PPDA, PrgP, xG por tiro, espacios entre líneas |
| ¿La Argentina es pareja? | **QUÉ** (descriptiva) | Std de puntos, % partidos por 1 gol |
| ¿Por qué es pareja? | **POR QUÉ** (explicativa) | Std de posesión, varianza de xG entre equipos |

**Regla:** nunca publicar solo métricas del QUÉ sin al menos una del POR QUÉ.

---

## 3. Fuentes de datos deportivos

### 3.1 Disponibilidad por liga y fuente

| Liga | FBref básico | FBref StatsBomb | Understat | Sofascore |
|------|:-----------:|:---------------:|:---------:|:---------:|
| Premier League | ✅ | ✅ | ✅ | ✅ |
| La Liga | ✅ | ✅ | ✅ | ✅ |
| Serie A | ✅ | ✅ | ✅ | ✅ |
| Bundesliga | ✅ | ✅ | ✅ | ✅ |
| Ligue 1 | ✅ | ✅ | ✅ | ✅ |
| Liga Argentina | ✅ | ❌ | ❌ | ✅ (parcial) |

> La ausencia de datos granulares para la Liga Argentina no es solo una limitación técnica — es en sí misma un hallazgo relevante sobre el ecosistema del fútbol argentino.

### 3.2 Tablas disponibles en FBref por categoría

| Tabla FBref | Columnas clave | Disponible en Argentina |
|-------------|---------------|------------------------|
| Standard Stats | Gls, Ast, G+A, Poss, CrdY, CrdR | ✅ |
| Shooting | Sh, SoT, SoT%, xG, G/Sh | ✅ (xG parcial) |
| Passing | Cmp%, PrgP, 1/3, KP | ❌ (mayormente vacío) |
| Possession | PrgC, PrgR, Att Pen, 1/3 | ❌ |
| Defensive | Tkl, Int, Blocks, Pressures, PPDA | ❌ |
| Misc | Fls, Fld, OG, Recov | ✅ |

---

## 4. Recolección desde FBref

### 4.1 URLs de tablas principales

```python
# Premier League (comp id = 9)
PREMIER_STATS    = "https://fbref.com/en/comps/9/Premier-League-Stats"
PREMIER_SHOOTING = "https://fbref.com/en/comps/9/shooting/Premier-League-Stats"
PREMIER_PASSING  = "https://fbref.com/en/comps/9/passing/Premier-League-Stats"
PREMIER_POSS     = "https://fbref.com/en/comps/9/possession/Premier-League-Stats"
PREMIER_DEFENSE  = "https://fbref.com/en/comps/9/defense/Premier-League-Stats"
PREMIER_MISC     = "https://fbref.com/en/comps/9/misc/Premier-League-Stats"

# Liga Argentina (comp id = 21)
ARGENTINA_STATS    = "https://fbref.com/en/comps/21/Primera-Division-Stats"
ARGENTINA_SHOOTING = "https://fbref.com/en/comps/21/shooting/Primera-Division-Stats"
ARGENTINA_PASSING  = "https://fbref.com/en/comps/21/passing/Primera-Division-Stats"
ARGENTINA_MISC     = "https://fbref.com/en/comps/21/misc/Primera-Division-Stats"
```

### 4.2 Función base de scraping

```python
import pandas as pd
import requests
import time

def get_fbref_table(url: str, tabla_index: int = 0, espera: float = 3.0) -> pd.DataFrame:
    """
    Descarga una tabla de FBref.
    
    Parámetros:
        url          : URL de la página de estadísticas
        tabla_index  : índice de la tabla en la página (0 = primera)
        espera       : segundos de espera para no saturar el servidor
    
    Retorna:
        DataFrame con los datos crudos
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        time.sleep(espera)  # respetar el servidor
        tablas = pd.read_html(response.text, header=1)
        return tablas[tabla_index]
    
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP {response.status_code}: {e}")
    except requests.exceptions.Timeout:
        print("Timeout — el servidor tardó demasiado")
    except Exception as e:
        print(f"Error inesperado: {e}")
    
    return pd.DataFrame()  # retorna vacío si falla

# Ejemplo de uso
df_premier = get_fbref_table(PREMIER_STATS)
df_argentina = get_fbref_table(ARGENTINA_STATS)

print(f"Premier: {df_premier.shape}")
print(f"Argentina: {df_argentina.shape}")
```

### 4.3 Verificación de disponibilidad de columnas

```python
def verificar_disponibilidad(df: pd.DataFrame, columnas: list, nombre_liga: str) -> None:
    """
    Verifica qué columnas tienen datos reales y cuáles están vacías.
    Útil para detectar si FBref tiene datos StatsBomb para una liga.
    """
    print(f"\n=== Disponibilidad de datos: {nombre_liga} ===")
    for col in columnas:
        if col not in df.columns:
            print(f"  ❌ {col} — columna no existe")
        elif df[col].isnull().all():
            print(f"  ❌ {col} — columna vacía (sin datos StatsBomb)")
        elif df[col].isnull().sum() / len(df) > 0.5:
            print(f"  ⚠️  {col} — más del 50% vacío")
        else:
            pct_nulos = (df[col].isnull().sum() / len(df) * 100).round(1)
            print(f"  ✅ {col} — disponible ({pct_nulos}% nulos)")

# Uso
columnas_avanzadas = ['PrgP', 'PrgC', 'PPDA', 'Att Pen', 'xG']
verificar_disponibilidad(df_premier, columnas_avanzadas, "Premier League")
verificar_disponibilidad(df_argentina, columnas_avanzadas, "Liga Argentina")
```

---

## 5. Limpieza específica de datos de fútbol

### 5.1 Problemas frecuentes en FBref

```python
def limpiar_fbref(df: pd.DataFrame, nombre_liga: str) -> pd.DataFrame:
    """
    Limpieza estándar para tablas descargadas de FBref.
    """
    df = df.copy()
    
    # 1. Eliminar fila de totales o headers repetidos que FBref incluye
    df = df[df['Squad'] != 'Squad'].reset_index(drop=True)
    
    # 2. Eliminar columna "Rk" si existe (ranking, no es útil para análisis)
    if 'Rk' in df.columns:
        df = df.drop(columns=['Rk'])
    
    # 3. Convertir columnas numéricas (FBref a veces las trae como string)
    columnas_numericas = df.columns.drop(['Squad'])
    for col in columnas_numericas:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 4. Limpiar nombres de equipos (strip de espacios)
    df['Squad'] = df['Squad'].str.strip()
    
    # 5. Agregar identificador de liga
    df['liga'] = nombre_liga
    
    return df

# Uso
df_premier_limpio   = limpiar_fbref(df_premier, 'Premier League')
df_argentina_limpio = limpiar_fbref(df_argentina, 'Liga Argentina')

# Combinar en un solo DataFrame
df_combinado = pd.concat([df_premier_limpio, df_argentina_limpio], ignore_index=True)
print(f"Total equipos: {len(df_combinado)}")
print(df_combinado['liga'].value_counts())
```

### 5.2 Manejo de headers multinivel

```python
# FBref a veces usa MultiIndex en columnas — aplanar con:
if isinstance(df.columns, pd.MultiIndex):
    df.columns = ['_'.join(col).strip('_ ') for col in df.columns]
    
# Verificar columnas resultantes
print(df.columns.tolist())
```

---

## 6. Normalización por 90 minutos

> Métrica fundamental en análisis de fútbol. Sin normalizar, comparar equipos con distinta cantidad de partidos es inválido.

### 6.1 Cuándo normalizar

```
✅ Normalizar  → goles, asistencias, tiros, pases, presiones (acumulados)
❌ No normalizar → % (Cmp%, SoT%), promedios ya calculados (xG/Sh), Poss
```

### 6.2 Código de normalización

```python
def normalizar_per90(df: pd.DataFrame, columnas: list, col_minutos: str = '90s') -> pd.DataFrame:
    """
    Normaliza columnas acumuladas por 90 minutos jugados.
    
    FBref usa '90s' como columna de 90-minutos jugados (ej: 11.0 = 990 min).
    """
    df = df.copy()
    
    for col in columnas:
        if col in df.columns:
            nuevo_nombre = f"{col}_per90"
            df[nuevo_nombre] = df[col] / df[col_minutos]
        else:
            print(f"⚠️  Columna '{col}' no encontrada — se omite")
    
    return df

# Ejemplo
columnas_a_normalizar = ['Gls', 'Ast', 'G+A', 'Sh', 'CrdY']
df_combinado = normalizar_per90(df_combinado, columnas_a_normalizar)
```

---

## 7. Análisis comparativo entre ligas

### 7.1 Estadística descriptiva comparativa

```python
from scipy import stats
import numpy as np

def comparar_ligas(df: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """
    Compara una métrica entre todas las ligas presentes en el DataFrame.
    Incluye estadística descriptiva completa y test de normalidad.
    """
    resultado = df.groupby('liga')[metrica].agg(
        n='count',
        media='mean',
        mediana='median',
        std='std',
        minimo='min',
        maximo='max',
        q25=lambda x: x.quantile(0.25),
        q75=lambda x: x.quantile(0.75)
    ).round(3)
    
    # Agregar resultado de test de normalidad
    for liga in df['liga'].unique():
        valores = df[df['liga'] == liga][metrica].dropna()
        if len(valores) >= 3:
            _, p = stats.shapiro(valores)
            resultado.loc[liga, 'shapiro_p'] = round(p, 4)
            resultado.loc[liga, 'normal'] = '✅' if p > 0.05 else '❌'
    
    return resultado

# Uso
print(comparar_ligas(df_combinado, 'Gls_per90'))
```

### 7.2 Test estadístico automático

```python
def test_diferencia_ligas(df: pd.DataFrame, metrica: str,
                           liga1: str, liga2: str) -> dict:
    """
    Elige automáticamente el test correcto según normalidad
    y calcula tamaño del efecto.
    """
    grupo1 = df[df['liga'] == liga1][metrica].dropna()
    grupo2 = df[df['liga'] == liga2][metrica].dropna()
    
    # Verificar normalidad de ambos grupos
    _, p1 = stats.shapiro(grupo1)
    _, p2 = stats.shapiro(grupo2)
    ambos_normales = (p1 > 0.05) and (p2 > 0.05)
    
    # Elegir test
    if ambos_normales:
        stat, p_valor = stats.ttest_ind(grupo1, grupo2)
        test_usado = "t-test (paramétrico)"
    else:
        stat, p_valor = stats.mannwhitneyu(grupo1, grupo2, alternative='two-sided')
        test_usado = "Mann-Whitney U (no paramétrico)"
    
    # Tamaño del efecto — Cohen's d
    diff = grupo1.mean() - grupo2.mean()
    pooled_std = np.sqrt((grupo1.std()**2 + grupo2.std()**2) / 2)
    cohens_d = diff / pooled_std if pooled_std > 0 else 0
    
    return {
        'metrica': metrica,
        'liga1': liga1,
        'media_liga1': round(grupo1.mean(), 3),
        'liga2': liga2,
        'media_liga2': round(grupo2.mean(), 3),
        'test': test_usado,
        'p_valor': round(p_valor, 4),
        'significativo': p_valor < 0.05,
        'cohens_d': round(cohens_d, 3),
        'efecto': 'grande' if abs(cohens_d) > 0.8 else 'mediano' if abs(cohens_d) > 0.5 else 'pequeño'
    }

# Uso
resultado = test_diferencia_ligas(df_combinado, 'Gls_per90', 'Premier League', 'Liga Argentina')
for clave, valor in resultado.items():
    print(f"  {clave}: {valor}")
```

### 7.3 Visualización comparativa

```python
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

def visualizar_comparacion(df: pd.DataFrame, metrica: str, titulo_conclusivo: str) -> None:
    """
    Violin plot comparativo entre ligas.
    El título debe decir la conclusión, no describir el gráfico.
    """
    fig = px.violin(
        df, 
        x='liga', 
        y=metrica,
        box=True, 
        points='all',
        title=f"{titulo_conclusivo} (n={len(df)} equipos)",
        labels={metrica: metrica, 'liga': 'Liga'}
    )
    fig.update_layout(showlegend=False)
    fig.show()

# Ejemplo de uso correcto
visualizar_comparacion(
    df_combinado, 
    'Gls_per90',
    # ✅ Título con conclusión
    'La Premier genera más goles por partido que la Liga Argentina'
    # ❌ Evitar: 'Goles por 90 min por liga'
)
```

---

## 8. Modelado aplicado al fútbol

### 8.1 Radar de perfil de jugador

```python
import numpy as np
import matplotlib.pyplot as plt

def radar_jugador(df_jugadores: pd.DataFrame, nombre: str, 
                  metricas: list, titulo: str = None) -> None:
    """
    Genera un radar chart para un jugador.
    Los valores deben estar normalizados (percentil 0-100).
    """
    jugador = df_jugadores[df_jugadores['Player'] == nombre][metricas].iloc[0]
    
    # Normalizar a percentil
    for m in metricas:
        jugador[m] = df_jugadores[m].rank(pct=True).loc[jugador.name] * 100
    
    valores = jugador.values.tolist()
    valores += valores[:1]  # cerrar el polígono
    
    angulos = [n / float(len(metricas)) * 2 * np.pi for n in range(len(metricas))]
    angulos += angulos[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angulos, valores, linewidth=2)
    ax.fill(angulos, valores, alpha=0.25)
    ax.set_xticks(angulos[:-1])
    ax.set_xticklabels(metricas, size=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['P25', 'P50', 'P75', 'P100'], size=8)
    ax.set_title(titulo or nombre, size=14, pad=20)
    plt.show()
```

### 8.2 Clustering de equipos por estilo de juego

```python
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

def clustering_equipos(df: pd.DataFrame, features: list, n_clusters: int = 4) -> pd.DataFrame:
    """
    Agrupa equipos por estilo de juego usando KMeans.
    Requiere que las features no tengan NaN.
    """
    df_clean = df[['Squad', 'liga'] + features].dropna()
    X = df_clean[features]
    
    # Escalar — obligatorio antes de clustering
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_clean = df_clean.copy()
    df_clean['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Reducción dimensional para visualizar
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X_scaled)
    df_clean['pca1'] = coords[:, 0]
    df_clean['pca2'] = coords[:, 1]
    
    # Varianza explicada
    print(f"Varianza explicada por PCA: {pca.explained_variance_ratio_.sum():.1%}")
    
    return df_clean

# Uso — solo con métricas disponibles para ambas ligas
features_disponibles = ['Gls_per90', 'Ast_per90', 'Poss', 'CrdY_per90']
df_clusters = clustering_equipos(df_combinado, features_disponibles)

# Perfil promedio por cluster
print(df_clusters.groupby('cluster')[features_disponibles].mean().round(2))
```

---

## 9. Interpretación táctica de resultados

### 9.1 El hallazgo estadístico nunca habla solo

Cada resultado necesita traducción táctica:

| Hallazgo estadístico | Interpretación táctica |
|---------------------|------------------------|
| Premier: mayor std en posesión | Hay equipos con identidad ofensiva clara vs equipos reactivos — mayor variedad táctica |
| Argentina: menor std en posesión | Ningún equipo impone su juego — paridad táctica, no solo de resultados |
| Premier: mayor xG por tiro | Las chances no son más frecuentes — son de mayor calidad |
| PPDA bajo en Premier | Presión más agresiva → recuperaciones en zona peligrosa → más transiciones → más goles |
| Correlación alta PrgP-xG | Los equipos que buscan profundidad generan más peligro real |
| Argentina: bajo G/xG | Los equipos generan lo que deberían generar — hay realismo en los resultados |

### 9.2 Cadena causal — cómo construir el argumento

No presentar correlaciones sueltas. Encadenarlas:

```
Ejemplo: ¿Por qué la Premier es más abierta?

PPDA bajo (presión agresiva)
        ↓
Recuperaciones en campo rival
        ↓
Transiciones rápidas en zonas de peligro
        ↓
Tiros de mayor calidad (xG/Sh alto)
        ↓
Más goles por partido
        ↓
Partidos más abiertos
```

### 9.3 Preguntas de validación antes de publicar

- ¿Tiene sentido futbolístico este resultado?
- ¿Hay explicaciones alternativas que no estoy considerando?
- ¿El n es suficiente? (mínimo 15-20 equipos por liga para comparaciones)
- ¿Estoy confundiendo correlación con causalidad?
- ¿La diferencia es significativa en la práctica, no solo estadísticamente?

---

## 10. Comunicación por audiencia

### 10.1 Adaptar el mensaje sin cambiar el dato

```
Fanáticos y seguidores
→ Una imagen clara + conclusión en una oración
→ Ejemplo: "La Premier genera un 34% más de goles por partido"

Periodistas y medios
→ Contexto + comparación + "por qué importa para el seguidor"
→ Ejemplo: "Los datos confirman lo que se ve: la Premier presiona más alto
   y genera chances de mayor calidad que la Liga Argentina"

Cuerpos técnicos y scouts
→ Métricas específicas + percentiles + comparables concretos
→ Ejemplo: "El jugador X está en el percentil 89 en PrgP per90 en Argentina,
   comparable con el percentil 65 en Premier — potencial de adaptación alto"

Académicos / técnicos
→ Metodología completa + supuestos + limitaciones + código disponible
```

### 10.2 Estructura de análisis escrito para publicación

```
1. Pregunta (1 oración)
2. Datos: fuente, liga, temporada, n de equipos
3. Hallazgo principal (conclusión al inicio, no al final)
4. Evidencia estadística (p-value + Cohen's d + visualización)
5. Interpretación táctica encadenada
6. Limitaciones (datos faltantes, tamaño de muestra, etc.)
7. Preguntas derivadas para próximos análisis
```

---

## 11. Errores comunes en análisis de fútbol

| Error | Descripción | Solución |
|-------|-------------|----------|
| **Comparar sin per 90** | Comparar totales entre ligas con distinta cantidad de jornadas | Siempre normalizar por 90 minutos |
| **Confiar en columnas vacías** | Asumir que FBref tiene todos los datos sin verificar | Siempre correr `verificar_disponibilidad()` |
| **Posesión = calidad** | Más posesión no significa mejor juego | Cruzar posesión con xG, PrgP, zonas de dominio |
| **xG como verdad absoluta** | xG es un modelo probabilístico con errores | Reportar siempre junto con goles reales |
| **n pequeño en ligas** | Sacar conclusiones de media temporada (10-12 equipos) | Esperar suficientes jornadas; indicar siempre el n |
| **Comparar ligas sin contexto** | Tratar métricas de distintas ligas como equivalentes | Siempre contextualizar: ritmo, árbitros, reglas de juego local |
| **Ignorar penales** | Los penales inflan métricas ofensivas | Usar G-PK y npxG para métricas de juego real |
| **Asumir normalidad** | Usar z-scores en métricas de fútbol sin verificar | Testear siempre — las métricas de fútbol rara vez son normales |

---

## 12. Glosario de métricas de fútbol

| Métrica | Nombre completo | Qué mide | Fuente |
|---------|----------------|----------|--------|
| **xG** | Expected Goals | Probabilidad de gol de cada tiro según sus características | FBref, Understat |
| **npxG** | Non-Penalty xG | xG sin incluir penales | FBref |
| **xA** | Expected Assists | Probabilidad de asistencia de cada pase | FBref |
| **PPDA** | Passes Allowed Per Defensive Action | Intensidad de presión — menos = más agresivo | FBref (StatsBomb) |
| **PrgP** | Progressive Passes | Pases que avanzan ≥10m hacia el arco rival | FBref (StatsBomb) |
| **PrgC** | Progressive Carries | Conducciones que avanzan ≥10m hacia el arco rival | FBref (StatsBomb) |
| **PrgR** | Progressive Receptions | Recepciones de pases progresivos | FBref (StatsBomb) |
| **Poss** | Possession | % de tiempo en posesión del balón | FBref |
| **G-PK** | Goals minus Penalties | Goles sin penales — más limpio para analizar juego | FBref |
| **npxG/Sh** | Non-Penalty xG per Shot | Calidad promedio de cada tiro (sin penales) | FBref |
| **G+A** | Goals + Assists | Contribuciones ofensivas directas totales | FBref |
| **SCA** | Shot-Creating Actions | Acciones que directa o indirectamente generaron un tiro | FBref (StatsBomb) |
| **GCA** | Goal-Creating Actions | Acciones que directa o indirectamente generaron un gol | FBref (StatsBomb) |
| **Cmp%** | Pass Completion % | Porcentaje de pases completados | FBref |
| **KP** | Key Passes | Pases que resultaron en un tiro del receptor | FBref |
| **1/3** | Final Third | Pases/conducciones que entran al tercio final del campo | FBref (StatsBomb) |
| **Att Pen** | Attacking Penalty Area | Toques dentro del área rival | FBref (StatsBomb) |
| **Sh** | Shots | Tiros totales por partido | FBref |
| **SoT%** | Shots on Target % | Porcentaje de tiros al arco sobre tiros totales | FBref |
| **G/Sh** | Goals per Shot | Goles convertidos por tiro — eficiencia real | FBref |
| **90s** | 90-minute periods | Unidad de tiempo en FBref (11.0 = 990 minutos) | FBref |

---

## 13. Checklist de análisis futbolístico

Usar antes de publicar cualquier análisis:

### Pregunta y métricas
- [ ] La pregunta táctica es específica y medible
- [ ] Se identificaron métricas del QUÉ y del POR QUÉ por separado
- [ ] Se verificó disponibilidad real de columnas (no vacías) para ambas ligas

### Datos
- [ ] Se documentó la fuente (FBref), temporada y fecha de extracción
- [ ] Se guardó el raw data sin modificar
- [ ] Se verificó el n de equipos por liga

### Limpieza
- [ ] Se eliminaron filas basura (headers repetidos, totales)
- [ ] Se convirtieron columnas numéricas correctamente
- [ ] Se normalizaron métricas acumuladas por 90 minutos
- [ ] Se excluyeron penales donde corresponde (usar G-PK, npxG)

### Estadística
- [ ] Se testeó normalidad antes de usar z-scores o t-tests
- [ ] Se calculó estadística descriptiva completa (no solo media)
- [ ] Se calculó tamaño del efecto (Cohen's d) además del p-value
- [ ] Se identificaron y explicaron los outliers

### Interpretación táctica
- [ ] Cada hallazgo tiene interpretación táctica encadenada
- [ ] Se construyó la cadena causal (no solo correlaciones sueltas)
- [ ] Se consideraron explicaciones alternativas
- [ ] Se reportaron las limitaciones (datos faltantes, n, fuente)

### Comunicación
- [ ] Los títulos de gráficos expresan la conclusión, no describen los ejes
- [ ] Se indica el n (equipos, temporada) en cada visualización
- [ ] El lenguaje está adaptado a la audiencia objetivo
- [ ] Se referencia la fuente de datos

---

*Guía viva — actualizar a medida que el proyecto crece, se incorporan nuevas ligas o fuentes de datos.*
