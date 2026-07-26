# EDA de Fútbol — Análisis de Partido
**Repositorio:** football-analytics  
**Autor:** Andrés  
**Versión:** 1.0  
**Última actualización:** 2025

> Guía de análisis exploratorio específica para datos de partido de fútbol (FBref).  
> A diferencia del EDA genérico, cada gráfico responde una pregunta táctica concreta.  
> Para fundamentos estadísticos → `docs/metodologia-futbol.md`  
> Para EDA genérico → `ds-toolkit/eda.md`

---

## Índice

1. [Setup](#1-setup)
2. [Carga y preparación](#2-carga-y-preparación)
3. [Diagnóstico estructural](#3-diagnóstico-estructural)
4. [Análisis ofensivo](#4-análisis-ofensivo)
5. [Análisis defensivo](#5-análisis-defensivo)
6. [Análisis de participación](#6-análisis-de-participación)
7. [Análisis por posición](#7-análisis-por-posición)
8. [Análisis de disciplina](#8-análisis-de-disciplina)
9. [Perfil individual de jugador](#9-perfil-individual-de-jugador)
10. [Comparación entre equipos](#10-comparación-entre-equipos)
11. [Qué gráfico usar según la pregunta táctica](#11-qué-gráfico-usar-según-la-pregunta-táctica)

---

## 1. Setup

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', '{:.2f}'.format)

# Configuración de gráficos
sns.set_theme(style='whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 11

# Configuración del partido
EQUIPO_LOCAL    = 'Huracán'       # ← reemplazar
EQUIPO_VISITANTE = 'Banfield'     # ← reemplazar
TEMPORADA       = '2026'          # ← reemplazar
```

---

## 2. Carga y preparación

```python
# Carga del dataset limpio
df_clean = pd.read_csv('../data/clean/NOMBRE_ARCHIVO_clean.csv')  # ← reemplazar
print(f'Dataset cargado: {df_clean.shape[0]} jugadores x {df_clean.shape[1]} columnas')
```

```python
# Separar por equipo si el dataset tiene los dos juntos
df_local     = df_clean[df_clean['Equipo'] == EQUIPO_LOCAL].copy()     # ← reemplazar columna si es distinta
df_visitante = df_clean[df_clean['Equipo'] == EQUIPO_VISITANTE].copy()

print(f'{EQUIPO_LOCAL}: {len(df_local)} jugadores')
print(f'{EQUIPO_VISITANTE}: {len(df_visitante)} jugadores')
```

```python
# Filtrar solo jugadores que participaron (más de 0 minutos)
df_activos = df_clean[df_clean['Minutos'] > 0].copy()
print(f'Jugadores con minutos jugados: {len(df_activos)}')
```

---

## 3. Diagnóstico estructural

**Ejecutar siempre antes de cualquier análisis.**

```python
df_clean.info()
```

```python
display(df_clean.describe())
```

```python
# Nulos por columna
nulos = pd.DataFrame({
    'Nulos': df_clean.isnull().sum(),
    'Porcentaje': (df_clean.isnull().sum() / len(df_clean) * 100).round(2)
})
display(nulos[nulos['Nulos'] > 0])
```

```python
# Distribución de minutos jugados — entender quiénes participaron
print(df_clean['Minutos'].value_counts().sort_index(ascending=False))
```

---

## 4. Análisis ofensivo

### Pregunta: ¿Quiénes generaron más peligro?

```python
# Top jugadores por tiros totales
df_ofensivo = df_activos[['Jugador', 'Posición', 'Minutos',
                            'Tiros totales', 'Tiros al arco',
                            'Goles', 'Asistencias']].copy()

df_ofensivo = df_ofensivo.sort_values('Tiros totales', ascending=False)

plt.figure(figsize=(12, 6))
p = sns.barplot(
    data=df_ofensivo.head(10),
    x='Jugador',
    y='Tiros totales',
    hue='Posición',
    dodge=False,
    palette='Blues_r'
)
for container in p.containers:
    p.bar_label(container, label_type='edge', padding=3)
plt.title(f'Top 10 por tiros totales — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('../outputs/top_tiros.png', dpi=150, bbox_inches='tight')
plt.show()
```

### Pregunta: ¿Qué tan certeros fueron los tiros?

```python
# Efectividad: tiros al arco sobre tiros totales
# Solo jugadores con al menos 1 tiro
df_tiros = df_activos[df_activos['Tiros totales'] > 0].copy()
df_tiros['efectividad_tiro'] = (
    df_tiros['Tiros al arco'] / df_tiros['Tiros totales'] * 100
).round(1)

df_tiros = df_tiros.sort_values('efectividad_tiro', ascending=False)

plt.figure(figsize=(12, 6))
p = sns.barplot(
    data=df_tiros,
    x='Jugador',
    y='efectividad_tiro',
    hue='Posición',
    dodge=False,
    palette='Greens_r'
)
for container in p.containers:
    p.bar_label(container, fmt='%.0f%%', label_type='edge', padding=3)
plt.title(f'Efectividad de tiro (% al arco) — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.ylabel('Tiros al arco (%)')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('../outputs/efectividad_tiro.png', dpi=150, bbox_inches='tight')
plt.show()
```

### Pregunta: ¿Quiénes contribuyeron directamente al juego ofensivo?

```python
# Contribuciones directas: goles + asistencias
df_activos['contribucion_ofensiva'] = df_activos['Goles'] + df_activos['Asistencias']
df_contrib = df_activos[df_activos['contribucion_ofensiva'] > 0].sort_values(
    'contribucion_ofensiva', ascending=False
)

if len(df_contrib) == 0:
    print("Sin goles ni asistencias en este partido")
else:
    plt.figure(figsize=(10, 5))
    p = sns.barplot(
        data=df_contrib,
        x='Jugador',
        y='contribucion_ofensiva',
        hue='Posición',
        dodge=False,
        palette='Oranges_r'
    )
    for container in p.containers:
        p.bar_label(container, label_type='edge', padding=3)
    plt.title(f'Contribuciones ofensivas (G+A) — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('../outputs/contribucion_ofensiva.png', dpi=150, bbox_inches='tight')
    plt.show()
```

---

## 5. Análisis defensivo

### Pregunta: ¿Quiénes trabajaron más defensivamente?

```python
# Acciones defensivas: entradas ganadas + intercepciones
df_activos['acciones_defensivas'] = (
    df_activos['Entradas ganadas'] + df_activos['Intercepciones']
)

df_def = df_activos[['Jugador', 'Posición', 'Minutos',
                       'Entradas ganadas', 'Intercepciones',
                       'acciones_defensivas']].sort_values(
    'acciones_defensivas', ascending=False
)

plt.figure(figsize=(12, 6))
p = sns.barplot(
    data=df_def.head(10),
    x='Jugador',
    y='acciones_defensivas',
    hue='Posición',
    dodge=False,
    palette='Reds_r'
)
for container in p.containers:
    p.bar_label(container, label_type='edge', padding=3)
plt.title(f'Top 10 acciones defensivas — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('../outputs/acciones_defensivas.png', dpi=150, bbox_inches='tight')
plt.show()
```

### Pregunta: ¿Cómo se distribuyen las acciones defensivas por posición?

```python
df_def_pos = df_activos.groupby('Posición')[
    ['Entradas ganadas', 'Intercepciones']
].sum().reset_index()

df_def_pos_melt = df_def_pos.melt(
    id_vars='Posición',
    value_vars=['Entradas ganadas', 'Intercepciones'],
    var_name='Acción',
    value_name='Total'
)

plt.figure(figsize=(12, 6))
sns.barplot(
    data=df_def_pos_melt,
    x='Posición',
    y='Total',
    hue='Acción',
    palette='Set2'
)
plt.title(f'Acciones defensivas por posición — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.savefig('../outputs/defensiva_por_posicion.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 6. Análisis de participación

### Pregunta: ¿Cuánto jugó cada uno?

```python
df_min = df_activos.sort_values('Minutos', ascending=True)

plt.figure(figsize=(10, 8))
p = sns.barplot(
    data=df_min,
    x='Minutos',
    y='Jugador',
    hue='Posición',
    dodge=False,
    palette='husl'
)
plt.axvline(45, color='gray', linestyle='--', alpha=0.7, label='Entretiempo')
plt.axvline(90, color='black', linestyle='--', alpha=0.7, label='Tiempo reglamentario')
plt.title(f'Minutos jugados por jugador — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.legend()
plt.tight_layout()
plt.savefig('../outputs/minutos_jugados.png', dpi=150, bbox_inches='tight')
plt.show()
```

### Pregunta: ¿Qué tan activo fue cada jugador respecto a sus minutos?

```python
# Normalizar acciones por 90 minutos para comparar titulares y suplentes
df_activos = df_activos[df_activos['Minutos'] >= 10].copy()  # mínimo 10 min

df_activos['tiros_per90']    = df_activos['Tiros totales'] / df_activos['Minutos'] * 90
df_activos['def_per90']      = df_activos['acciones_defensivas'] / df_activos['Minutos'] * 90
df_activos['centros_per90']  = df_activos['Centros'] / df_activos['Minutos'] * 90

print("Métricas per90 calculadas")
display(df_activos[['Jugador', 'Posición', 'Minutos',
                     'tiros_per90', 'def_per90', 'centros_per90']].sort_values(
    'tiros_per90', ascending=False
))
```

---

## 7. Análisis por posición

### Pregunta: ¿Qué aportó cada línea del equipo?

```python
# Resumen de métricas clave agrupadas por posición
metricas_por_pos = df_activos.groupby('Posición').agg(
    jugadores=('Jugador', 'count'),
    minutos_prom=('Minutos', 'mean'),
    tiros_total=('Tiros totales', 'sum'),
    tiros_arco_total=('Tiros al arco', 'sum'),
    goles_total=('Goles', 'sum'),
    def_total=('acciones_defensivas', 'sum'),
    faltas_com=('Faltas cometidas', 'sum'),
    faltas_rec=('Faltas recibidas', 'sum'),
).round(1).reset_index()

display(metricas_por_pos)
```

```python
# Visualización — aporte ofensivo vs defensivo por posición
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Ofensivo
sns.barplot(
    data=metricas_por_pos,
    x='Posición',
    y='tiros_total',
    ax=axes[0],
    palette='Blues_r',
    hue='Posición',
    legend=False
)
axes[0].set_title('Tiros totales por posición')
axes[0].set_xlabel('')
axes[0].tick_params(axis='x', rotation=30)

# Defensivo
sns.barplot(
    data=metricas_por_pos,
    x='Posición',
    y='def_total',
    ax=axes[1],
    palette='Reds_r',
    hue='Posición',
    legend=False
)
axes[1].set_title('Acciones defensivas por posición')
axes[1].set_xlabel('')
axes[1].tick_params(axis='x', rotation=30)

plt.suptitle(f'Aporte por posición — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}', fontsize=14)
plt.tight_layout()
plt.savefig('../outputs/aporte_por_posicion.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 8. Análisis de disciplina

### Pregunta: ¿Hubo jugadores problemáticos o muy fouleados?

```python
df_disciplina = df_activos[
    (df_activos['Faltas cometidas'] > 0) |
    (df_activos['Faltas recibidas'] > 0) |
    (df_activos['Tarjetas amarillas'] > 0) |
    (df_activos['Tarjetas rojas'] > 0)
].copy()

df_disciplina = df_disciplina.sort_values('Faltas cometidas', ascending=False)

# Faltas cometidas vs recibidas
df_disc_melt = df_disciplina[['Jugador', 'Faltas cometidas', 'Faltas recibidas']].melt(
    id_vars='Jugador',
    var_name='Tipo',
    value_name='Faltas'
)

plt.figure(figsize=(12, 6))
sns.barplot(
    data=df_disc_melt,
    x='Jugador',
    y='Faltas',
    hue='Tipo',
    palette={'Faltas cometidas': '#e8341a', 'Faltas recibidas': '#1a73e8'}
)
plt.title(f'Faltas cometidas vs recibidas — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('../outputs/disciplina.png', dpi=150, bbox_inches='tight')
plt.show()
```

```python
# Tarjetas
tarjetas = df_activos[
    (df_activos['Tarjetas amarillas'] > 0) | (df_activos['Tarjetas rojas'] > 0)
][['Jugador', 'Posición', 'Tarjetas amarillas', 'Tarjetas rojas']]

if len(tarjetas) == 0:
    print("Sin tarjetas en este partido")
else:
    display(tarjetas)
```

---

## 9. Perfil individual de jugador

### Pregunta: ¿Cómo fue el partido de un jugador específico?

```python
def perfil_jugador(df: pd.DataFrame, nombre: str) -> None:
    """
    Muestra el perfil completo de un jugador en el partido.
    Compara sus métricas con el promedio de su posición.
    """
    jugador = df[df['Jugador'].str.contains(nombre, case=False, na=False)]

    if jugador.empty:
        print(f"Jugador '{nombre}' no encontrado")
        return

    jugador = jugador.iloc[0]
    posicion = jugador['Posición']
    promedio_pos = df[df['Posición'] == posicion].select_dtypes(include='number').mean()

    metricas = ['Minutos', 'Tiros totales', 'Tiros al arco', 'Goles',
                'Asistencias', 'Entradas ganadas', 'Intercepciones',
                'Faltas cometidas', 'Faltas recibidas', 'Centros']

    metricas_presentes = [m for m in metricas if m in df.columns]

    print(f"\n{'='*50}")
    print(f"PERFIL: {jugador['Jugador']} | {posicion} | {jugador['Minutos']} min")
    print(f"{'='*50}")
    print(f"{'Métrica':<25} {'Valor':>8} {'Prom. posición':>15}")
    print(f"{'-'*50}")
    for m in metricas_presentes:
        if m in jugador.index and m in promedio_pos.index:
            print(f"{m:<25} {jugador[m]:>8.0f} {promedio_pos[m]:>15.1f}")

# Uso
perfil_jugador(df_activos, 'Messi')       # ← reemplazar con el jugador que querés analizar
```

---

## 10. Comparación entre equipos

### Pregunta: ¿Qué diferencias hubo entre ambos equipos?

```python
# Requiere columna 'Equipo' en el dataset
# Si no la tenés, separar manualmente df_local y df_visitante

def comparar_equipos(df: pd.DataFrame,
                     col_equipo: str = 'Equipo') -> pd.DataFrame:
    """
    Compara las métricas totales entre los dos equipos del partido.
    """
    metricas = ['Tiros totales', 'Tiros al arco', 'Goles', 'Asistencias',
                'Entradas ganadas', 'Intercepciones', 'Faltas cometidas',
                'Faltas recibidas', 'Centros', 'Fueras de juego',
                'Tarjetas amarillas', 'Tarjetas rojas']

    metricas_presentes = [m for m in metricas if m in df.columns]

    resumen = df.groupby(col_equipo)[metricas_presentes].sum().T
    resumen.columns.name = None
    return resumen

# Uso
df_comparacion = comparar_equipos(df_activos)
display(df_comparacion)
```

```python
# Visualización de comparación
df_comp_melt = df_comparacion.reset_index().melt(
    id_vars='index',
    var_name='Equipo',
    value_name='Total'
).rename(columns={'index': 'Métrica'})

# Filtrar métricas con al menos un valor > 0
metricas_con_datos = df_comparacion[df_comparacion.sum(axis=1) > 0].index.tolist()
df_comp_filtrado = df_comp_melt[df_comp_melt['Métrica'].isin(metricas_con_datos)]

plt.figure(figsize=(14, 7))
sns.barplot(
    data=df_comp_filtrado,
    x='Métrica',
    y='Total',
    hue='Equipo',
    palette=[('#1a73e8'), ('#e8341a')]
)
plt.title(f'Comparación de métricas — {EQUIPO_LOCAL} vs {EQUIPO_VISITANTE}')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('../outputs/comparacion_equipos.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 11. Qué gráfico usar según la pregunta táctica

| Pregunta táctica | Tipo de gráfico | Métricas clave |
|-----------------|-----------------|----------------|
| ¿Quién generó más peligro? | Barplot horizontal | Tiros totales, Tiros al arco |
| ¿Qué tan certero fue el ataque? | Barplot con % | Tiros al arco / Tiros totales |
| ¿Quién trabajó más defensivamente? | Barplot ordenado | Entradas + Intercepciones |
| ¿Cómo se distribuyó el trabajo por línea? | Barplot agrupado por posición | Todas las métricas |
| ¿Quién fue el más foulero o el más foulleado? | Barplot doble (cometidas vs recibidas) | Faltas cometidas, Faltas recibidas |
| ¿Cuánto participó cada jugador? | Barplot horizontal ordenado | Minutos |
| ¿Cómo fue el partido de X jugador? | Tabla comparativa vs promedio posición | Todas |
| ¿Qué diferencias hubo entre equipos? | Barplot agrupado por equipo | Totales por equipo |
| ¿Quién fue más activo por minuto jugado? | Barplot de métricas per90 | Cualquier métrica / Minutos * 90 |

> **Regla de oro para fútbol:** nunca graficar una métrica sin una pregunta táctica detrás.  
> Un histograma de "Distribución de Goles" en un partido no dice nada — todos tienen 0 o 1.  
> La misma métrica con una pregunta ("¿quién tiró más?") se convierte en análisis real.

---

*Para análisis de temporada completa con múltiples partidos → adaptar agrupando por fecha*  
*Para análisis en vivo → `docs/analisis-en-vivo.md`*  
*Para metodología estadística → `docs/metodologia-futbol.md`*
