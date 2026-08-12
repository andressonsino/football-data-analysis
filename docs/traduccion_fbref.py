# ── Diccionarios de traducción FBref ─────────────────────────────────────
# Reutilizable en cualquier análisis de FBref
# Fuente: glosario oficial FBref

COLUMNAS_ES = {
    'Player':     'Jugador',
    '#':          'Camiseta',
    'Pos':        'Posición',
    'Age':        'Edad',
    'Min':        'Minutos',
    'Gls':        'Goles',
    'Ast':        'Asistencias',
    'PK':         'Penales convertidos',
    'PKatt':      'Penales intentados',
    'Sh':         'Tiros totales',
    'SoT':        'Tiros al arco',
    'CrdY':       'Tarjetas amarillas',
    'CrdR':       'Tarjetas rojas',
    'Fls':        'Faltas cometidas',
    'Fld':        'Faltas recibidas',
    'Off':        'Fueras de juego',
    'Crs':        'Centros',
    'TklW':       'Entradas ganadas',
    'Int':        'Intercepciones',
    'OG':         'Goles en contra',
    'PKwon':      'Penales ganados',
    'PKcon':      'Penales concedidos',
    'edad_anios': 'Edad (años)',
    'edad_dias':  'Edad (días de año en curso)'
}

POSICIONES_ES = {
    'GK':   'Arquero',
    'DF':   'Defensor',
    'MF':   'Mediocampista',
    'FW':   'Delantero',
    'FB':   'Lateral',
    'LB':   'Lateral izquierdo',
    'RB':   'Lateral derecho',
    'CB':   'Defensor central',
    'DM':   'Mediocampista defensivo',
    'CM':   'Mediocampista central',
    'LM':   'Mediocampista izquierdo',
    'RM':   'Mediocampista derecho',
    'WM':   'Mediocampista amplio',
    'LW':   'Extremo izquierdo',
    'RW':   'Extremo derecho',
    'AM':   'Mediocampista ofensivo',
}


def traducir_columnas(df):
    """
    Renombra las columnas de un DataFrame de FBref al español.
    Solo traduce las columnas que existen — no falla si faltan columnas.
    """
    columnas_presentes = {k: v for k, v in COLUMNAS_ES.items() if k in df.columns}
    df = df.rename(columns=columnas_presentes)
    print(f"Columnas traducidas: {len(columnas_presentes)}")
    return df


def traducir_posiciones(df, columna='Posición'):
    """
    Traduce las abreviaturas de posición al español.
    Maneja posiciones combinadas como 'DF,FW' o 'FW,MF'.

    Parámetros:
        columna : nombre de la columna de posición (después de traducir columnas)
    """
    if columna not in df.columns:
        print(f"Columna '{columna}' no encontrada — verificá que ya tradujiste las columnas")
        return df

    def traducir_pos(valor):
        if pd.isna(valor):
            return valor
        # Manejar posiciones combinadas (ej: 'DF,FW', 'FW,MF')
        partes = str(valor).split(',')
        traducidas = [POSICIONES_ES.get(p.strip(), p.strip()) for p in partes]
        return ' / '.join(traducidas)

    df[columna] = df[columna].apply(traducir_pos)
    return df


# ── Uso ───────────────────────────────────────────────────────────────────
# df_clean = traducir_columnas(df_clean)
# df_clean = traducir_posiciones(df_clean)
# display(df_clean.head())
