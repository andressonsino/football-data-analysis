# Carga de archivos FBref (Excel Workbook / .xls)

Plantilla para cargar y concatenar archivos descargados desde FBref en formato
**Get as Excel Workbook** (`.xls`). Cubre el problema del doble encabezado y la
fusión inteligente de columnas.

---

## ¿Por qué este código y no los otros?

FBref ofrece dos formatos de descarga:

| Opción en FBref | Extensión real | Cómo leerlo |
|---|---|---|
| **Get as Excel Workbook** | `.xls` (HTML disfrazado) | `pd.read_html(archivo)[0]` |
| **Get table as CSV (for Excel)** | `.csv` con encoding roto | `pd.read_csv()` — encoding problemático |

El archivo `.xls` que descarga FBref **no es un Excel real**. Es una página HTML
guardada con extensión `.xls`. Por eso:

- `pd.read_excel()` **falla** → espera un binario Excel real
- `pd.read_html()` **funciona** → lee la tabla HTML que hay adentro
- `pd.read_csv()` **falla** → el encoding de FBref rompe tildes y ñ

---

## ¿Cuándo funciona esta plantilla?

| Contexto | ¿Funciona? |
|---|---|
| Archivos descargados con "Get as Excel Workbook" de FBref | ✅ Sí |
| Múltiples archivos de la misma tabla (distintas temporadas o ligas) | ✅ Sí |
| Tablas con doble encabezado (Performance, Per 90, etc.) | ✅ Sí — el código lo resuelve |
| Tablas sin doble encabezado (Player, Age, Nation) | ✅ Sí — el código lo maneja igual |
| Archivos CSV descargados de FBref | ❌ No — usar Bloc de Notas + guardar como UTF-8 |
| Archivos `.xlsx` reales (no de FBref) | ❌ No — usar `pd.read_excel()` |

---

## ¿Qué es el doble encabezado de FBref?

FBref agrupa columnas bajo categorías. Por ejemplo, la tabla de estadísticas
estándar tiene esta estructura:

```
               |     Performance      |      Per 90       |
Player  | Age  | Gls | Ast | xG | xAG | Gls | Ast | xG  |
```

Pandas lee eso como un `MultiIndex` con dos niveles:
- Nivel superior: `"Performance"`, `"Per 90"`, o `"Unnamed: 0"` para las columnas sin grupo
- Nivel inferior: `"Gls"`, `"Ast"`, `"xG"`, etc.

Sin resolver esto, las columnas quedan como tuplas ilegibles:
`('Performance', 'Gls')`, `('Unnamed: 2', 'Player')`, etc.

---

## Código de la plantilla

```python
import pandas as pd
import glob

# ── Configuración ──────────────────────────────────────────
DATA_PATH_LOCAL = r"ruta/a/tu/carpeta/raw/"  # ← CAMBIAR: ruta donde están los .xls
# ───────────────────────────────────────────────────────────

# 1. Buscar todos los archivos .xls en la carpeta
archivos = glob.glob(DATA_PATH_LOCAL + "*.xls")
print(f"Archivos encontrados: {len(archivos)}")

# 2. Cargar y concatenar
lista_dfs = []

for archivo in archivos:
    # read_html lee la tabla HTML dentro del .xls de FBref
    # [0] porque FBref siempre tiene una sola tabla por archivo
    df = pd.read_html(archivo)[0]

    # 3. Resolver el doble encabezado si existe
    if isinstance(df.columns, pd.MultiIndex):
        nuevas_columnas = []
        for nivel_sup, nivel_inf in df.columns:
            if 'Unnamed' in str(nivel_sup):
                # Columnas sin grupo (Player, Age, Nation, Pos, etc.)
                # Solo nos quedamos con el nombre del nivel inferior
                nuevas_columnas.append(nivel_inf)
            else:
                # Columnas con grupo (Performance_Gls, Per 90_Ast, etc.)
                # Unimos los dos niveles con guion bajo
                nuevas_columnas.append(f"{nivel_sup}_{nivel_inf}")

        df.columns = nuevas_columnas

    lista_dfs.append(df)

# 4. Concatenar todos los DataFrames
df_total = pd.concat(lista_dfs, ignore_index=True)
# ignore_index=True: resetea el índice para que sea continuo (0, 1, 2...)
# sin esto, el índice se repetiría para cada archivo concatenado

print(f"✅ Dataset cargado — Filas: {df_total.shape[0]} | Columnas: {df_total.shape[1]}")
print(f"Columnas: {df_total.columns.tolist()}")
df_total.head()
```

---

## Explicación línea por línea

### `glob.glob(DATA_PATH_LOCAL + "*.xls")`
Busca todos los archivos que terminen en `.xls` dentro de la carpeta.
El `*` es un comodín: coincide con cualquier nombre de archivo.
Devuelve una lista de rutas completas.

### `pd.read_html(archivo)[0]`
Lee la tabla HTML del archivo y devuelve una lista de DataFrames
(uno por tabla encontrada). FBref siempre tiene una sola tabla,
entonces `[0]` toma la primera y única.

### `isinstance(df.columns, pd.MultiIndex)`
Verifica si las columnas son de doble nivel. Si FBref no tiene
grupos de columnas (algunas tablas simples no los tienen), las
columnas son normales y esta condición es `False`: el código
las deja tal cual.

### `'Unnamed' in str(nivel_sup)`
FBref nombra el nivel superior como `Unnamed: 0`, `Unnamed: 1`,
etc. para las columnas que no pertenecen a ningún grupo.
Detectar "Unnamed" en el texto es la forma de identificarlas.

### `pd.concat(lista_dfs, ignore_index=True)`
Une todos los DataFrames apilados verticalmente (uno abajo del otro).
`ignore_index=True` reinicia el índice de 0 a N para que no haya
índices duplicados entre archivos.

---

## Paso siguiente recomendado después de cargar

FBref agrega una fila de totales al final y filas de encabezado
repetidas cuando concatenás múltiples archivos. Siempre limpiar:

```python
# Eliminar filas donde Player es NaN o contiene "Player" (encabezados repetidos)
df_raw = df_total[
    df_total['Player'].notna() &
    (df_total['Player'] != 'Player')
].reset_index(drop=True)

print(f"Filas después de limpieza: {df_raw.shape[0]}")
```

---

## Estructura de carpetas recomendada para proyectos FBref

```
proyecto/
├── data/
│   ├── raw/
│   │   └── standard-stats-temporada/   ← los .xls van acá
│   └── processed/
│       └── standard-stats-clean.csv    ← el resultado limpio
└── notebooks/
    └── 01-carga-y-limpieza.ipynb
```

---

*Plantilla FBref — ds-toolkit by andressonsino*
*Posición en el flujo: `02-integracion-de-datos/`*
