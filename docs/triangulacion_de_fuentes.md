# Triangulación de Fuentes — Construcción de una Tabla Maestra

Plantilla reutilizable para armar una tabla de datos **cuando no existe una fuente única ya extraída**.
La tabla se construye cruzando varias fuentes independientes, y cada dato queda con su origen,
su fecha de consulta y su nivel de confianza.

**Posición en el flujo:** `02-integracion-de-datos/`

---

## ¿Qué es la triangulación de fuentes?

Es un método de integración donde **ninguna fuente se toma por buena de forma aislada**. Cada registro se
construye en capas y cada capa audita a la anterior:

| Capa | Rol | Pregunta que responde |
|---|---|---|
| **Capa 1 — Esqueleto** | Define el universo: quién entra en la tabla | ¿Tengo a todos los registros que debería tener? |
| **Capa 2 — Validación** | Audita los datos "duros" contra la fuente oficial | ¿Lo que dice la capa 1 es correcto? |
| **Capa 3 — Métricas** | Agrega mediciones objetivas | ¿Qué hizo realmente cada registro? |

### ¿Cuándo usarla?

- No hay una tabla ya armada y tenés que construirla desde cero
- Las fuentes disponibles tienen errores conocidos (portales agregadores, planillas manuales)
- El resultado va a ser cuestionado y necesitás poder respaldar cada dato
- Los datos viven repartidos en sistemas o archivos que no se hablan entre sí

### ¿Cuándo NO usarla?

- Existe una fuente única, oficial y exportable (con un `read_csv` alcanza)
- El análisis es exploratorio y no requiere auditoría

### Qué garantiza y qué no

La triangulación **no vuelve infalible a la tabla**: reduce el error y, sobre todo, lo vuelve **visible y
trazable**. Dos fuentes pueden coincidir y estar equivocadas las dos. Por eso el objetivo real no es
"datos perfectos" sino **datos auditables**: que ante una objeción puedas mostrar de dónde salió cada
valor, cuándo se consultó y qué pasó cuando las fuentes discreparon.

---

## Principios del método

1. **Las reglas de inclusión se fijan antes de cargar datos.** Si las definís después, el resultado se
   sesga hacia lo que querías encontrar.
2. **Una fuente de verdad por campo.** Para cada columna se define de antemano qué fuente gana en caso de conflicto.
3. **Toda discrepancia se registra.** No se corrige en silencio: se guarda en un log.
4. **Cada valor tiene trazabilidad.** Fuente, URL y fecha de consulta (las fuentes web cambian).
5. **Las métricas se calculan sobre una base comparable.** Ej: minutos reales sobre minutos *posibles*, no sobre el total del torneo.

---

## Estructura de la tabla maestra

Campos del dominio (ejemplo con un análisis de refuerzos de un club de fútbol):

| Campo | Descripción | Capa / fuente de validación |
|---|---|---|
| `jugador` | Nombre completo | Capa 1 — censo |
| `posicion` | Posición principal | Capa 1 — censo |
| `mercado` | Período de llegada (ej. Invierno 2023) | Capa 1 — fecha de firma |
| `fecha_alta` | Fecha exacta de alta | Capa 1 — censo |
| `categoria_ingreso` | Refuerzo / retorno de cesión / juvenil | Capa 1 — reglas de inclusión |
| `dt_receptor` | Entrenador al momento de llegar | Cronología deportiva |
| `condicion_contractual` | Compra (% adquirido) / Préstamo / Libre | **Capa 2 — comunicado oficial** |
| `costo_inicial` | Monto por pase o cargo de préstamo | **Capa 2 — balance / oficial** |
| `minutos_posibles` | Minutos del equipo mientras el jugador estuvo habilitado | Capa 3 — cálculo |
| `minutos_jugados` | Minutos reales en cancha | Capa 3 — estadísticas |
| `pct_presencia` | `minutos_jugados / minutos_posibles × 100` | Cálculo |
| `aporte_directo` | G+A, vallas invictas, etc. según puesto | Capa 3 — estadísticas |
| `destino_estado` | En el club / préstamo / venta / rescisión | Situación registral |

Columnas de **metadatos de trazabilidad** (agregarlas siempre, sin importar el dominio):

| Campo | Para qué sirve |
|---|---|
| `fuente_*` | De qué fuente salió cada dato crítico |
| `url_fuente` | Dónde volver a verificarlo |
| `fecha_consulta` | Cuándo se consultó (las fuentes web cambian) |
| `validado_capa2` | Si el registro fue confirmado por la fuente oficial |
| `tiene_discrepancia` | Si las fuentes no coincidieron en algún campo |
| `nivel_confianza` | Alto / Medio / Bajo (regla en el Bloque 8) |

---

## BLOQUE 0 — Imports y configuración

```python
import re
import unicodedata

import numpy as np
import pandas as pd

# ── Configuración ──────────────────────────────────────────
CLAVE            = "jugador"                       # ← CAMBIAR: columna que identifica al registro
CLAVE_NORM       = "clave_norm"                    # columna normalizada (se crea sola)
MERCADO_NORM     = "mercado_norm"                  # idem para el período
CLAVE_UNICA      = [CLAVE_NORM, MERCADO_NORM]      # ← CAMBIAR si la clave única es otra

FECHA_CORTE_INI  = "2023-07-01"                    # ← CAMBIAR: desde cuándo entra el universo
FECHA_CONSULTA   = pd.Timestamp.today().strftime("%Y-%m-%d")

RUTA_CAPA1       = r"data/raw/capa1_censo.csv"     # ← CAMBIAR
RUTA_CAPA2       = r"data/raw/capa2_oficial.csv"   # ← CAMBIAR
RUTA_CAPA3       = r"data/raw/capa3_metricas.csv"  # ← CAMBIAR
RUTA_PARTIDOS    = r"data/raw/partidos_equipo.csv" # ← CAMBIAR: calendario del equipo
RUTA_SALIDA      = r"data/processed/tabla_maestra.csv"
RUTA_LOG         = r"data/processed/log_discrepancias.csv"
# ───────────────────────────────────────────────────────────
```

---

## BLOQUE 1 — Reglas de inclusión y exclusión (definir ANTES de cargar)

Este bloque no ejecuta nada pesado: es la **declaración escrita** de qué entra y qué no.
Se define primero para evitar sesgo.

| Categoría | Criterio | Tratamiento |
|---|---|---|
| **Entra (genuino)** | Incorporación externa: compra, préstamo o libre | Se incluye |
| **Se separa en columna aparte** | Retorno de cesión que se queda a jugar | Se incluye con `categoria_ingreso = "retorno_cesion"` para poder filtrarlo |
| **No se computa** | Primer contrato a juveniles de inferiores | Se excluye (responde a política formativa, no a scouting) |

```python
# ── Configuración ──────────────────────────────────────────
CATEGORIAS_INCLUIR  = ["refuerzo", "retorno_cesion"]  # ← CAMBIAR
CATEGORIAS_EXCLUIR  = ["juvenil_inferiores"]          # ← CAMBIAR
# ───────────────────────────────────────────────────────────
```

> **Regla:** si una regla cambia a mitad del trabajo, se documenta el cambio y se vuelve a correr
> todo el notebook. Nunca se retocan filas a mano.

---

## BLOQUE 2 — Funciones auxiliares

### `normalizar_texto`: el mismo registro escrito de tres formas

Fuentes distintas escriben distinto: `"Cristian Mamani"`, `"CRISTIAN  MAMANI"`, `"Cristián Mamaní"`.
Sin normalizar, el `merge` no los empareja y el registro "desaparece" de la capa 2.

### `sufijar`: evitar choques de columnas

Si dos capas tienen una columna `club_origen`, el `merge` pisa o renombra de forma confusa.
Agregar un sufijo por capa (`_c1`, `_c2`, `_c3`) conserva el valor de cada fuente por separado,
que es justamente lo que necesitás para compararlas.

```python
def normalizar_texto(texto):
    """Minúsculas, sin tildes, sin signos, espacios simples."""
    if pd.isna(texto):
        return texto
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip().lower()
    return texto


def agregar_claves(df):
    """Crea las columnas normalizadas que se usan como clave de cruce."""
    df = df.copy()
    df[CLAVE_NORM]   = df[CLAVE].apply(normalizar_texto)
    df[MERCADO_NORM] = df["mercado"].apply(normalizar_texto)
    return df


def sufijar(df, sufijo):
    """Agrega un sufijo a todas las columnas que no son clave."""
    return df.rename(columns={
        c: f"{c}_{sufijo}" for c in df.columns if c not in CLAVE_UNICA
    })
```

---

## BLOQUE 3 — Capa 1: el esqueleto del censo

**Objetivo:** no omitir a ningún registro del universo, incluso los de poca relevancia
(los que llegaron y casi no jugaron son justamente los que más se olvidan).

**Columnas esperadas en el archivo de capa 1:**

`jugador | mercado | fecha_alta | posicion | edad_al_llegar | club_origen | condicion_contractual | categoria_ingreso`

```python
df_capa1 = pd.read_csv(RUTA_CAPA1)
df_capa1["fecha_alta"] = pd.to_datetime(df_capa1["fecha_alta"], errors="coerce")
df_capa1 = agregar_claves(df_capa1)

# Aplicar el corte temporal y las reglas del Bloque 1
df_capa1 = df_capa1[df_capa1["fecha_alta"] >= pd.Timestamp(FECHA_CORTE_INI)]
df_capa1 = df_capa1[~df_capa1["categoria_ingreso"].isin(CATEGORIAS_EXCLUIR)]
df_capa1 = df_capa1[df_capa1["categoria_ingreso"].isin(CATEGORIAS_INCLUIR)]

# Control de integridad del esqueleto
print(f"Registros en el censo:          {len(df_capa1)}")
print(f"Fechas de alta no interpretadas: {df_capa1['fecha_alta'].isna().sum()}")
print(f"Duplicados en clave única:       {df_capa1.duplicated(subset=CLAVE_UNICA).sum()}")

df_capa1_s = sufijar(df_capa1, "c1")
```

> Un duplicado en la clave única puede ser un error de carga **o** un jugador que llegó dos veces
> (ej. un retorno). Revisá cada caso antes de eliminarlo.

---

## BLOQUE 4 — Capa 2: validación contra la fuente oficial

**Objetivo:** auditar cada fila del censo contra comunicados oficiales y balances. Los portales
agregadores suelen confundir préstamos con compras o no detallar cláusulas.

**Columnas esperadas en el archivo de capa 2:**

`jugador | mercado | condicion_contractual | costo_inicial | club_origen | url_fuente | fecha_comunicado`

```python
df_capa2 = pd.read_csv(RUTA_CAPA2)
df_capa2 = agregar_claves(df_capa2)
df_capa2_s = sufijar(df_capa2, "c2")

# 1. Cruce completo para ver quién está en una capa y no en la otra
df_cmp = df_capa1_s.merge(df_capa2_s, on=CLAVE_UNICA, how="outer", indicator=True)
print(df_cmp["_merge"].value_counts())

sin_validar  = df_cmp[df_cmp["_merge"] == "left_only"]    # están en el censo, no en la fuente oficial
solo_oficial = df_cmp[df_cmp["_merge"] == "right_only"]   # están en la fuente oficial, faltan en el censo

print(f"\nSin validar (revisar a mano):        {len(sin_validar)}")
print(f"Solo en fuente oficial (agregar a capa 1): {len(solo_oficial)}")
```

### Registro de discrepancias

```python
# ── Configuración ──────────────────────────────────────────
CAMPOS_A_COMPARAR = ["condicion_contractual", "club_origen"]  # ← CAMBIAR: campos presentes en ambas capas
# ───────────────────────────────────────────────────────────

ambos = df_cmp[df_cmp["_merge"] == "both"]
registros = []

for campo in CAMPOS_A_COMPARAR:
    valor_c1 = ambos[f"{campo}_c1"].apply(normalizar_texto)
    valor_c2 = ambos[f"{campo}_c2"].apply(normalizar_texto)

    # Hay discrepancia si difieren y no son ambos nulos
    hay_dif = (valor_c1 != valor_c2) & ~(valor_c1.isna() & valor_c2.isna())

    for _, fila in ambos[hay_dif].iterrows():
        registros.append({
            CLAVE_NORM:   fila[CLAVE_NORM],
            MERCADO_NORM: fila[MERCADO_NORM],
            "campo":      campo,
            "valor_c1":   fila[f"{campo}_c1"],
            "valor_c2":   fila[f"{campo}_c2"],
            "resolucion": "pendiente",
        })

df_discrepancias = pd.DataFrame(
    registros,
    columns=[CLAVE_NORM, MERCADO_NORM, "campo", "valor_c1", "valor_c2", "resolucion"]
)

print(f"Discrepancias detectadas: {len(df_discrepancias)}")
display(df_discrepancias)
```

**Cómo leer el resultado:** cada fila es un dato en el que las dos fuentes no coinciden. No se corrige
a mano: se resuelve aplicando la fuente de verdad definida (Bloque 8) y queda guardado en el log.

---

## BLOQUE 5 — Capa 3: métricas objetivas

**Objetivo:** reemplazar la opinión ("rindió / no rindió") por mediciones.

**Columnas esperadas en el archivo de capa 3:**

`jugador | mercado | fecha_baja | minutos_jugados | goles | asistencias | destino_estado`

**Columnas esperadas en el calendario del equipo (`partidos_equipo.csv`):**

`fecha | minutos_equipo` (una fila por partido; normalmente 90, más si hubo tiempo extra)

```python
df_capa3 = pd.read_csv(RUTA_CAPA3)
df_capa3["fecha_baja"] = pd.to_datetime(df_capa3["fecha_baja"], errors="coerce")
df_capa3 = agregar_claves(df_capa3)
df_capa3_s = sufijar(df_capa3, "c3")

df_partidos = pd.read_csv(RUTA_PARTIDOS)
df_partidos["fecha"] = pd.to_datetime(df_partidos["fecha"], errors="coerce")

print(f"Registros con métricas: {len(df_capa3)}")
print(f"Partidos del equipo cargados: {len(df_partidos)}")
```

---

## BLOQUE 6 — Consolidación en `df_raw`

Se parte del esqueleto (capa 1) y se le agregan las otras capas con `how="left"`: así **nunca se pierde
un registro del censo** aunque falte en otra capa.

```python
df_raw = (
    df_capa1_s
    .merge(df_capa2_s, on=CLAVE_UNICA, how="left", indicator="merge_c2")
    .merge(df_capa3_s, on=CLAVE_UNICA, how="left")
)

df_raw["validado_capa2"] = df_raw["merge_c2"] == "both"
df_raw = df_raw.drop(columns="merge_c2")

# Trazabilidad
df_raw["fecha_consulta"] = FECHA_CONSULTA

print(f"Registros consolidados: {len(df_raw)}")
print(f"Validados contra fuente oficial: {df_raw['validado_capa2'].sum()} "
      f"({df_raw['validado_capa2'].mean()*100:.1f}%)")
```

---

## BLOQUE 7 — Métricas derivadas (minutos posibles, % presencia, por 90)

### Por qué "minutos posibles" y no "minutos totales del torneo"

Si un jugador llegó en la fecha 5 de un torneo de 14, solo pudo jugar las 9 fechas restantes.
Compararlo contra las 14 lo penaliza por partidos en los que **ni siquiera estaba**. La métrica justa es:

```
% Presencia = Minutos jugados ÷ Minutos que jugó el equipo con el jugador habilitado × 100
```

```python
def minutos_posibles(fecha_alta, fecha_baja, df_partidos):
    """Suma los minutos del equipo entre el alta y la baja (o hoy, si sigue)."""
    if pd.isna(fecha_alta):
        return np.nan
    fin = fecha_baja if pd.notna(fecha_baja) else pd.Timestamp.today()
    mascara = (df_partidos["fecha"] >= fecha_alta) & (df_partidos["fecha"] <= fin)
    return df_partidos.loc[mascara, "minutos_equipo"].sum()


df_raw["minutos_posibles"] = df_raw.apply(
    lambda f: minutos_posibles(f["fecha_alta_c1"], f["fecha_baja_c3"], df_partidos),
    axis=1
)

# % de presencia (el replace evita dividir por cero)
df_raw["pct_presencia"] = (
    df_raw["minutos_jugados_c3"] / df_raw["minutos_posibles"].replace(0, np.nan) * 100
).round(1)

# Producción por 90 minutos
# ── Configuración ──────────────────────────────────────────
COLS_APORTE      = ["goles_c3", "asistencias_c3"]  # ← CAMBIAR según el puesto/métrica
MIN_MINUTOS_P90  = 270                             # ← CAMBIAR: umbral de muestra mínima
# ───────────────────────────────────────────────────────────

df_raw["aporte_directo"] = df_raw[COLS_APORTE].sum(axis=1)
df_raw["aporte_por_90"] = (
    df_raw["aporte_directo"] / df_raw["minutos_jugados_c3"].replace(0, np.nan) * 90
).round(2)

# Con pocos minutos el "por 90" es engañoso: se marca la muestra insuficiente
df_raw["muestra_suficiente"] = df_raw["minutos_jugados_c3"] >= MIN_MINUTOS_P90
```

> **Advertencia estadística:** un jugador con 1 gol en 30 minutos tiene un promedio de 3 goles por 90.
> Ese número no significa nada. Por eso se agrega `muestra_suficiente` y se filtra por ella al comparar.

---

## BLOQUE 8 — Resolución de discrepancias y nivel de confianza

### Fuente de verdad por campo

Se define **una vez** qué fuente gana en cada campo. El primer elemento de la lista es la fuente
principal; los siguientes son respaldo si la principal viene vacía.

```python
# ── Configuración ──────────────────────────────────────────
FUENTE_DE_VERDAD = {                                  # ← CAMBIAR según tu dominio
    "condicion_contractual": ["c2", "c1"],  # oficial gana sobre el agregador
    "club_origen":           ["c2", "c1"],
    "fecha_alta":            ["c1"],
}
# ───────────────────────────────────────────────────────────

for campo, orden in FUENTE_DE_VERDAD.items():
    columnas = [f"{campo}_{s}" for s in orden if f"{campo}_{s}" in df_raw.columns]
    resultado = df_raw[columnas[0]]
    for col in columnas[1:]:
        resultado = resultado.fillna(df_raw[col])
    df_raw[campo] = resultado

# Cerrar el log: toda discrepancia queda resuelta por jerarquía de fuentes
df_discrepancias["resolucion"] = df_discrepancias["campo"].map(
    lambda c: f"gana {FUENTE_DE_VERDAD[c][0]}" if c in FUENTE_DE_VERDAD else "pendiente"
)
```

### Nivel de confianza por registro

| Nivel | Criterio |
|---|---|
| **Alto** | Validado contra fuente oficial y sin discrepancias |
| **Medio** | Validado, pero hubo discrepancia resuelta por jerarquía de fuentes |
| **Bajo** | Sin validación contra fuente oficial |

```python
claves_disc = (
    df_discrepancias[CLAVE_UNICA]
    .drop_duplicates()
    .assign(tiene_discrepancia=True)
)

df_raw = df_raw.merge(claves_disc, on=CLAVE_UNICA, how="left")
df_raw["tiene_discrepancia"] = df_raw["tiene_discrepancia"].fillna(False).astype(bool)

df_raw["nivel_confianza"] = np.select(
    [
        df_raw["validado_capa2"] & ~df_raw["tiene_discrepancia"],
        df_raw["validado_capa2"] &  df_raw["tiene_discrepancia"],
    ],
    ["Alto", "Medio"],
    default="Bajo"
)

print(df_raw["nivel_confianza"].value_counts())
```

---

## BLOQUE 9 — Enriquecimiento con cronología (ej. DT receptor)

Algunos campos no vienen de ninguna fuente: se **derivan** de otra tabla con fechas.
`pd.merge_asof` asigna a cada fecha el período vigente más reciente, sin hacer un `if` por cada caso.

```python
# ── Configuración ──────────────────────────────────────────
df_cronologia = pd.DataFrame({
    "dt":    ["DT_1", "DT_2", "DT_3"],                                        # ← CAMBIAR
    "desde": pd.to_datetime(["2023-01-01", "2024-03-01", "2025-06-01"]),      # ← CAMBIAR
}).sort_values("desde")
# ───────────────────────────────────────────────────────────

df_raw = df_raw.sort_values("fecha_alta")

df_raw = pd.merge_asof(
    df_raw,
    df_cronologia,
    left_on="fecha_alta",
    right_on="desde",
    direction="backward"      # toma el período que empezó antes de la fecha de alta
).rename(columns={"dt": "dt_receptor"}).drop(columns="desde")
```

> Los dos DataFrames deben estar **ordenados por la columna de fecha** o `merge_asof` falla.

---

## BLOQUE 10 — Validaciones de integridad → `df_clean`

Antes de dar por terminada la tabla, comprobá que no viole reglas que **no pueden** violarse.

```python
# ── Configuración ──────────────────────────────────────────
COLUMNAS_CRITICAS = [CLAVE, "fecha_alta", "condicion_contractual"]  # ← CAMBIAR
# ───────────────────────────────────────────────────────────

df_clean = df_raw.copy()

chequeos = {
    "Sin duplicados en la clave única":
        df_clean.duplicated(subset=CLAVE_UNICA).sum() == 0,
    "Minutos jugados ≤ minutos posibles":
        (df_clean["minutos_jugados_c3"].fillna(0) <= df_clean["minutos_posibles"].fillna(np.inf)).all(),
    "% de presencia entre 0 y 100":
        df_clean["pct_presencia"].dropna().between(0, 100).all(),
    "Sin nulos en columnas críticas":
        df_clean[COLUMNAS_CRITICAS].notna().all().all(),
    "Todas las altas posteriores al corte":
        (df_clean["fecha_alta"] >= pd.Timestamp(FECHA_CORTE_INI)).all(),
}

for nombre, ok in chequeos.items():
    print(("✅" if ok else "❌"), nombre)
```

Si un chequeo falla, **no se arregla la fila a mano**: se investiga la causa en la capa que corresponda
y se vuelve a correr el notebook completo.

---

## BLOQUE 11 — Exportar tabla maestra y log

```python
df_clean.to_csv(RUTA_SALIDA, index=False, encoding="utf-8")
df_discrepancias.to_csv(RUTA_LOG, index=False, encoding="utf-8")

print(f"✅ Tabla maestra exportada: {RUTA_SALIDA} ({df_clean.shape[0]} filas)")
print(f"✅ Log de discrepancias exportado: {RUTA_LOG} ({len(df_discrepancias)} registros)")
```

> Si el archivo va a abrirse en Excel y ves tildes rotas, exportá con `encoding="utf-8-sig"`.

---

## Checklist de cierre

- [ ] Las reglas de inclusión/exclusión están escritas **antes** de cargar datos
- [ ] La capa 1 cubre todo el universo (incluidos los registros "menores")
- [ ] Cada registro de capa 1 fue buscado en la fuente oficial
- [ ] Los registros "solo en la fuente oficial" se revisaron y agregaron a capa 1
- [ ] Toda discrepancia está en el log con su resolución
- [ ] Cada campo crítico tiene una fuente de verdad definida
- [ ] Las métricas se calculan sobre minutos/períodos **posibles**, no totales
- [ ] Se marcó la muestra insuficiente en las métricas por 90
- [ ] Todos los chequeos del Bloque 10 pasan
- [ ] Cada fuente tiene URL y fecha de consulta registradas

---

## Referencia rápida — problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| Muchos registros "sin validar" en capa 2 | Nombres escritos distinto entre fuentes | Revisar `normalizar_texto`; considerar emparejamiento por similitud (`difflib`, `rapidfuzz`) |
| `merge` duplica filas | La clave de cruce no es única en una de las capas | Verificar `duplicated(subset=CLAVE_UNICA)` en cada capa antes de cruzar |
| `pct_presencia` mayor a 100 | Fechas de alta/baja mal cargadas o calendario incompleto | Revisar `fecha_alta`, `fecha_baja` y que `partidos_equipo.csv` cubra el período |
| `merge_asof` lanza error | DataFrames sin ordenar por fecha | `sort_values` por la columna de fecha en ambos |
| Todas las filas con confianza "Bajo" | La capa 2 no está matcheando | Revisar claves normalizadas y que `mercado` se escriba igual en ambas |
| Valores por 90 absurdos | Muestra de pocos minutos | Filtrar por `muestra_suficiente` |

---

## Notas de buenas prácticas

- **Guardá una copia cruda de cada capa** en `data/raw/`. Nunca sobrescribas el archivo original.
- **Cada fuente web cambia con el tiempo.** Por eso se registra `fecha_consulta`: es parte del dato.
- **Verificá qué métricas publica hoy cada fuente** antes de diseñar la capa 3. Los proveedores a veces
  dejan de publicar ciertos indicadores y el diseño de la tabla se rompe a mitad del proyecto.
- **Antes de extraer datos automáticamente de un sitio**, revisá sus términos de uso. La extracción
  manual o por exportación oficial es siempre la opción más segura (ver `scraping.md`).
- **Este método escala a otros dominios**: reemplazá "jugador/mercado/minutos" por
  "alumno/cohorte/asistencia" o "cliente/campaña/compras" y la lógica de las tres capas se mantiene.

---

*Template de Triangulación de Fuentes — ds-toolkit by andressonsino*
*Posición en el flujo: `02-integracion-de-datos/`*
