import streamlit as st
import pandas as pd
import pydeck as pdk

# === 1 Cargar dataset ===
df = pd.read_csv("df_streamlit.csv")

st.title(" Visualización de incidentes delictivos en CDMX")

# === 2 Limpiar coordenadas ===
df = df.dropna(subset=["latitud", "longitud"])
df = df.rename(columns={"latitud": "latitude", "longitud": "longitude"})

# === 3 Selección de alcaldía ===
alcaldias_disponibles = sorted(df["alcaldia_hecho"].dropna().astype(str).unique())
opcion = st.selectbox(
    "Selecciona una alcaldía:",
    ["TODAS"] + alcaldias_disponibles
)

# Filtrado condicional
if opcion == "TODAS":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df["alcaldia_hecho"] == opcion]


# === 3 bis: Selector de tipo de delito ===
delitos_disponibles = sorted(df["categoria_delito"].dropna().astype(str).unique())
delito_seleccionado = st.selectbox(
    "Selecciona tipo de delito:",
    ["(Todos)"] + delitos_disponibles
)

if delito_seleccionado != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["categoria_delito"] == delito_seleccionado]

# === 4 Selector de tipo de mapa ===
tipo_mapa = st.radio(
    "Selecciona el tipo de mapa:",
    ("Mapa simple (st.map)", "Mapa avanzado (Pydeck)")
)

# --- Prevenir errores si no se usa Pydeck ---
capas_seleccionadas = []

# =====================================================
# === BLOQUE 1: Mapa simple con st.map() ============
# =====================================================
if tipo_mapa == "Mapa simple (st.map)":
    st.subheader(f"Mapa básico de incidentes en {opcion}")

    # Agregamos un punto central para mantener el enfoque en CDMX
    centro_cdmx = pd.DataFrame({"latitude": [19.4326], "longitude": [-99.1332]})
    df_mapa_cdmx = pd.concat([df_filtrado[["latitude", "longitude"]], centro_cdmx])

    if df_filtrado.empty:
        st.warning(" No hay registros para esta combinación de filtros.")
    else:
        st.map(df_mapa_cdmx, use_container_width=True)

# =====================================================
# === BLOQUE 2: Mapa avanzado con Pydeck ===========
# =====================================================
else:
    st.subheader(f"Mapa avanzado de incidentes en {opcion}")

    # --- Controles interactivos ---
    st.sidebar.header(" Configuración del mapa Pydeck")

    capas_seleccionadas = st.sidebar.multiselect(
        "Selecciona capa(s) a mostrar:",
        ["Heatmap", "Puntos"],
        default=["Heatmap"]
    )

    # Estilos basados en OpenStreetMap (Carto)
    estilos_osm = {
        "Oscuro": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        "Claro": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        #"Color": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    }
    estilo_mapa = st.sidebar.radio("Selecciona estilo del mapa:", list(estilos_osm.keys()))

    zoom_valor = st.sidebar.slider("Zoom inicial", 8.0, 15.0, 10.5, 0.1)
    radio_puntos = st.sidebar.slider("Tamaño de puntos", 10, 100, 25, 5)

    # --- Vista centrada en CDMX ---
    view_state = pdk.ViewState(
        latitude=19.4326,
        longitude=-99.1332,
        zoom=zoom_valor,
        pitch=40,
        bearing=0
    )

    # --- Crear capas dinámicamente ---
    capas = []

    # Capa Heatmap
    if "Heatmap" in capas_seleccionadas and not df_filtrado.empty:
        capas.append(
            pdk.Layer(
                "HeatmapLayer",
                data=df_filtrado,
                get_position=["longitude", "latitude"],
                opacity=0.9,
                threshold=0.3,
                aggregation="MEAN",
                get_weight=1
            )
        )

    # Capa Puntos con color dinámico y validación
    if "Puntos" in capas_seleccionadas:
        if df_filtrado.empty:
            st.warning(" No hay registros para esta combinación de filtros.")
        else:
            # --- Codificar color de forma segura ---
            color_codes = (
                df_filtrado["categoria_delito"]
                .astype("category")
                .cat.codes
                .astype(int)
                .abs()
            )

            # Escalar valores entre 0–255
            color_scaled = (color_codes * 13) % 256
            df_filtrado["color_id"] = color_scaled.astype(int)

            capas.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df_filtrado.sample(1000, random_state=42)
                    if len(df_filtrado) > 1000 else df_filtrado,
                    get_position=["longitude", "latitude"],
                    get_radius=radio_puntos,
                    #get_fill_color=["color_id", "200 - color_id", 50, 50, 120],
                    get_fill_color=["color_id", "200 - color_id", 160, 120], #Color verde
                    pickable=True,
                )
            )

    #  Crear el mapa solo si hay capas
    if capas:
        deck = pdk.Deck(
            map_style=estilos_osm[estilo_mapa],
            initial_view_state=view_state,
            layers=capas,
            tooltip={
                "text": " Alcaldía: {alcaldia_hecho}\n Delito: {categoria_delito}"
            }
        )

        st.pydeck_chart(deck, use_container_width=True, height=600)
    else:
        st.info("Selecciona al menos una capa para visualizar el mapa.")
