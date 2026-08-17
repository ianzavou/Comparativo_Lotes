from __future__ import annotations

import importlib
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

import route_analysis as route_analysis_module


_REQUIRED_ROUTE_ANALYSIS_EXPORTS = (
    "DEFAULT_DASHBOARD_SNAPSHOT",
    "DEFAULT_OUTPUT_FILE",
    "aligned_route_colors",
    "build_nearest_neighbor_paths",
    "load_dashboard_snapshot",
)
route_analysis_module = importlib.reload(route_analysis_module)
missing_route_analysis_exports = [
    name
    for name in _REQUIRED_ROUTE_ANALYSIS_EXPORTS
    if not hasattr(route_analysis_module, name)
]
if missing_route_analysis_exports:
    raise ImportError(
        "route_analysis.py não disponibiliza: "
        + ", ".join(missing_route_analysis_exports)
    )

DEFAULT_DASHBOARD_SNAPSHOT = route_analysis_module.DEFAULT_DASHBOARD_SNAPSHOT
DEFAULT_OUTPUT_FILE = route_analysis_module.DEFAULT_OUTPUT_FILE
aligned_route_colors = route_analysis_module.aligned_route_colors
build_nearest_neighbor_paths = route_analysis_module.build_nearest_neighbor_paths
load_dashboard_snapshot = route_analysis_module.load_dashboard_snapshot
PROJECT_DIR = Path(__file__).resolve().parent
COMPANY_LOGO = PROJECT_DIR / "assets" / "Logo Engelmig.jpg"


st.set_page_config(
    page_title="Comparativo de Rotas VV",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def load_snapshot(snapshot_path: str, modified_ns: int, size: int):
    del modified_ns, size
    return load_dashboard_snapshot(snapshot_path)


@st.cache_data(show_spinner=False)
def load_output_file(output_path: str, modified_ns: int, size: int) -> bytes:
    del modified_ns, size
    return Path(output_path).read_bytes()


@st.cache_data(show_spinner=False, max_entries=12)
def load_path_overlay(points: pd.DataFrame) -> pd.DataFrame:
    path_columns = ["route", "installation", "latitude", "longitude"]
    return build_nearest_neighbor_paths(points[path_columns].copy())


def format_integer(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{int(value):,}".replace(",", ".")


def format_number(value, decimals: int = 3) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_distance(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    numeric_value = float(value)
    if abs(numeric_value) < 1:
        meters = numeric_value * 1000
        decimals = 1 if 0 < abs(meters) < 10 else 0
        return f"{format_number(meters, decimals)} m"
    return f"{format_number(numeric_value, 2)} km"


def format_percent(value, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value) * 100:.{decimals}f}%".replace(".", ",")


def natural_route_key(value: str):
    value = str(value)
    return (0, int(value)) if value.isdigit() else (1, value)


def metric_delta(current_value, optimized_value):
    if current_value is None or optimized_value is None:
        return None
    if pd.isna(current_value) or pd.isna(optimized_value):
        return None
    return float(optimized_value) - float(current_value)


def lot_metric(lot_metrics: pd.DataFrame, lot: int, scenario: str):
    selected = lot_metrics.loc[
        lot_metrics["lot"].eq(lot) & lot_metrics["scenario"].eq(scenario)
    ]
    return None if selected.empty else selected.iloc[0]


def route_color_frame(frame: pd.DataFrame, colors: dict[str, list[int]]) -> pd.DataFrame:
    result = frame.copy()
    result["route"] = result["route"].astype(str)
    result["color"] = result["route"].map(colors)
    return result


def calculate_view_state(current_lot: pd.DataFrame, optimized_lot: pd.DataFrame) -> pdk.ViewState:
    combined = pd.concat([current_lot, optimized_lot], ignore_index=True)
    latitude = float(combined["latitude"].mean())
    longitude = float(combined["longitude"].mean())
    latitude_span = max(float(combined["latitude"].max() - combined["latitude"].min()), 0.0005)
    longitude_span = max(float(combined["longitude"].max() - combined["longitude"].min()), 0.0005)
    span = max(latitude_span, longitude_span * np.cos(np.radians(latitude)))
    zoom = float(np.clip(np.log2(360.0 / span) - 1.4, 7.0, 14.5))
    return pdk.ViewState(latitude=latitude, longitude=longitude, zoom=zoom, pitch=0, bearing=0)


def build_map(
    points: pd.DataFrame,
    routes: pd.DataFrame,
    view_state: pdk.ViewState,
    colors: dict[str, list[int]],
    paths: pd.DataFrame | None = None,
) -> pdk.Deck:
    map_points = route_color_frame(points, colors)
    map_points["map_label"] = "Instalação " + map_points["installation"].astype(str)
    map_points["installations"] = 1
    centroids = routes[[
        "route", "centroid_latitude", "centroid_longitude", "installations"
    ]].copy()
    centroids["route"] = centroids["route"].astype(str)
    centroids["color"] = centroids["route"].map(colors)
    centroids["map_label"] = "Centroide da UL"

    layers: list[pdk.Layer] = []
    if paths is not None and not paths.empty:
        map_paths = route_color_frame(paths, colors)
        map_paths["color"] = map_paths["color"].map(
            lambda color: [*color[:3], 235] if isinstance(color, list) else [242, 142, 43, 235]
        )
        map_paths["map_label"] = map_paths.apply(
            lambda row: (
                f"Trecho NN {int(row['segment'])}/{int(row['segments'])}: "
                f"{format_distance(row['segment_distance_km'])} "
                f"(UL: {format_distance(row['distance_km'])})"
            ),
            axis=1,
        )
        layers.extend([
            pdk.Layer(
                "PathLayer",
                data=map_paths,
                get_path="path",
                get_color=[20, 25, 35, 155],
                get_width=7,
                width_min_pixels=3,
                width_max_pixels=8,
                pickable=False,
            ),
            pdk.Layer(
                "PathLayer",
                data=map_paths,
                get_path="path",
                get_color="color",
                get_width=4,
                width_min_pixels=2,
                width_max_pixels=5,
                pickable=True,
                auto_highlight=True,
            ),
        ])

    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_points,
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius=35,
        radius_min_pixels=1.5,
        radius_max_pixels=6,
        pickable=True,
        auto_highlight=True,
        opacity=0.72,
    )
    centroid_layer = pdk.Layer(
        "ScatterplotLayer",
        data=centroids,
        get_position="[centroid_longitude, centroid_latitude]",
        get_fill_color="color",
        get_line_color=[20, 20, 20, 240],
        stroked=True,
        line_width_min_pixels=2,
        get_radius=115,
        radius_min_pixels=6,
        radius_max_pixels=13,
        pickable=True,
        opacity=0.98,
    )
    layers.extend([point_layer, centroid_layer])
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={
            "html": "<b>UL:</b> {route}<br/><b>Elemento:</b> {map_label}<br/><b>Instalações:</b> {installations}",
            "style": {"backgroundColor": "#17365D", "color": "white"},
        },
    )


def build_summary_table(current_metric, optimized_metric, method_prefix: str) -> pd.DataFrame:
    method_name = "Pares dentro da UL" if method_prefix == "pair" else "Vizinho mais próximo"
    definitions = [
        (f"{method_name} — média", f"{method_prefix}_mean_km", "km"),
        (f"{method_name} — mediana", f"{method_prefix}_median_km", "km"),
        (f"{method_name} — máxima", f"{method_prefix}_max_km", "km"),
        ("Instalação ao centroide — média", "radius_mean_km", "km"),
        ("Instalação ao centroide — mediana", "radius_median_km", "km"),
        ("Instalação ao centroide — máxima", "radius_max_km", "km"),
        ("Centroide da UL ao lote — média", "route_to_lot_centroid_mean_km", "km"),
        ("Centroide da UL ao lote — mediana", "route_to_lot_centroid_median_km", "km"),
        ("Centroide da UL ao lote — máxima", "route_to_lot_centroid_max_km", "km"),
        ("Coeficiente de variação do tamanho", "route_size_cv", "%"),
        ("Índice médio de separação", "separation_index_mean", "índice"),
    ]
    rows = []
    for label, field, unit in definitions:
        current_value = np.nan if current_metric is None else current_metric.get(field, np.nan)
        optimized_value = np.nan if optimized_metric is None else optimized_metric.get(field, np.nan)
        delta = metric_delta(current_value, optimized_value)
        if unit == "%":
            formatter = format_percent
        elif unit == "km":
            formatter = format_distance
        else:
            formatter = lambda value: format_number(value, 3)
        rows.append(
            {
                "Indicador": label,
                "Atual": formatter(current_value),
                "Roteirizada": formatter(optimized_value),
                "Variação (roteirizada - atual)": formatter(delta),
            }
        )
    return pd.DataFrame(rows)


snapshot_path = PROJECT_DIR / Path(DEFAULT_DASHBOARD_SNAPSHOT)
output_path = PROJECT_DIR / Path(DEFAULT_OUTPUT_FILE)

st.sidebar.title("Comparativo VV")
st.sidebar.caption("Atualização dos dados somente pelo Run All do notebook analise_rotas.ipynb.")

if not snapshot_path.exists():
    st.error(
        "Snapshot do dashboard não encontrado. Abra analise_rotas.ipynb, execute Run All e atualize esta página."
    )
    st.stop()

snapshot_stat = snapshot_path.stat()
with st.spinner("Carregando os resultados preparados pelo notebook..."):
    analysis = load_snapshot(
        str(snapshot_path), snapshot_stat.st_mtime_ns, snapshot_stat.st_size
    )

snapshot_generated_at = analysis.get("snapshot_generated_at")
if snapshot_generated_at is not None:
    st.sidebar.caption(
        f"Snapshot: {snapshot_generated_at:%d/%m/%Y %H:%M}"
    )

coverage = analysis["coverage"]
available_lots = coverage["lot"].astype(int).sort_values().tolist()
default_lot = next(
    (int(row.lot) for row in coverage.itertuples() if row.status == "Comparável"),
    available_lots[0],
)
selected_lot = st.sidebar.selectbox(
    "Lote",
    available_lots,
    index=available_lots.index(default_lot),
    format_func=lambda lot: f"Lote {lot}",
)
distance_method = st.sidebar.radio(
    "Leitura de distância",
    ["Todos os pares", "Vizinho mais próximo"],
    help="O seletor altera os cartões e gráficos, sem recalcular ou ocultar os demais resultados do Excel.",
)
method_prefix = "pair" if distance_method == "Todos os pares" else "nearest"

if output_path.exists():
    output_stat = output_path.stat()
    st.sidebar.download_button(
        "⬇ Baixar Comparativo_Rotas_VV.xlsx",
        data=load_output_file(
            str(output_path), output_stat.st_mtime_ns, output_stat.st_size
        ),
        file_name="Comparativo_Rotas_VV.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
else:
    st.sidebar.info("O Excel será disponibilizado após executar Run All no notebook.")

logo_column, title_column = st.columns([1.3, 4.2], vertical_alignment="center")
with logo_column:
    if COMPANY_LOGO.exists():
        st.image(str(COMPANY_LOGO), width="stretch")
with title_column:
    st.title("Estrutura das rotas: Atual × Roteirizada")
st.caption(
    "Comparação por lote e por instalações. As ULs são grupos independentes em cada cenário; seus IDs não são comparados diretamente."
)

coverage_row = coverage.loc[coverage["lot"].eq(selected_lot)].iloc[0]
lot_metrics = analysis["lot_metrics"]
current_metric = lot_metric(lot_metrics, selected_lot, "Atual")
optimized_metric = lot_metric(lot_metrics, selected_lot, "Otimizada")
stability_selected = analysis["stability"].loc[analysis["stability"]["lot"].eq(selected_lot)]
stability_row = None if stability_selected.empty else stability_selected.iloc[0]

if coverage_row["status"] != "Comparável":
    status_label = str(coverage_row["status"]).replace(
        "otimização", "roteirização"
    )
    st.warning(
        f"Lote {selected_lot}: {status_label}. Os indicadores disponíveis são exibidos, mas não há delta comparável."
    )
elif coverage_row["current_coverage_pct"] < 0.99999:
    st.warning(
        "Os cenários têm coberturas diferentes neste lote. Os indicadores espaciais usam cada cenário completo; a estabilidade usa somente instalações comuns."
    )

kpi_columns = st.columns(5)
route_value = f"{format_integer(coverage_row['current_routes'])} → {format_integer(coverage_row['optimized_routes'])}"
route_delta = (
    int(coverage_row["optimized_routes"] - coverage_row["current_routes"])
    if coverage_row["current_routes"] and coverage_row["optimized_routes"]
    else None
)
kpi_columns[0].metric("Rotas", route_value, route_delta)
kpi_columns[1].metric(
    "Instalações",
    f"{format_integer(coverage_row['current_installations'])} → {format_integer(coverage_row['optimized_installations'])}",
    format_percent(coverage_row["current_coverage_pct"]) + " comuns" if pd.notna(coverage_row["current_coverage_pct"]) else None,
    delta_color="off",
)
primary_field = f"{method_prefix}_mean_km"
current_primary = np.nan if current_metric is None else current_metric[primary_field]
optimized_primary = np.nan if optimized_metric is None else optimized_metric[primary_field]
primary_delta = metric_delta(current_primary, optimized_primary)
kpi_columns[2].metric(
    "Distância média selecionada",
    format_distance(optimized_primary) if pd.notna(optimized_primary) else format_distance(current_primary),
    format_distance(primary_delta) if primary_delta is not None else None,
    delta_color="inverse",
)
current_radius = np.nan if current_metric is None else current_metric["radius_mean_km"]
optimized_radius = np.nan if optimized_metric is None else optimized_metric["radius_mean_km"]
radius_delta = metric_delta(current_radius, optimized_radius)
kpi_columns[3].metric(
    "Raio médio das ULs",
    format_distance(optimized_radius) if pd.notna(optimized_radius) else format_distance(current_radius),
    format_distance(radius_delta) if radius_delta is not None else None,
    delta_color="inverse",
)
kpi_columns[4].metric(
    "Retenção de pares",
    format_percent(None if stability_row is None else stability_row["pair_retention"]),
    help="Dos pares que estavam juntos antes, quantos continuam juntos após a roteirização.",
)

tab_summary, tab_map, tab_distribution, tab_total_distance, tab_regrouping, tab_glossary = st.tabs(
    ["Resumo", "Mapa", "Dispersão", "Percurso total", "Reagrupamento", "Glossário"]
)

with tab_summary:
    st.subheader(f"Indicadores do lote {selected_lot}")
    st.dataframe(
        build_summary_table(current_metric, optimized_metric, method_prefix),
        hide_index=True,
        width="stretch",
    )
    comparison = analysis["lot_comparison"]
    lot_comparison = comparison.loc[comparison["lot"].eq(selected_lot)]
    if not lot_comparison.empty:
        chart_data = analysis["route_metrics"].loc[
            analysis["route_metrics"]["lot"].eq(selected_lot),
            ["scenario", "route", "installations", f"{method_prefix}_mean_km", "radius_mean_km"],
        ].copy()
        chart_data = chart_data.rename(columns={
            "scenario": "Cenário",
            f"{method_prefix}_mean_km": "Distância média km",
            "installations": "Instalações",
        })
        chart_data["Distância exibida"] = chart_data["Distância média km"].map(
            format_distance
        )
        chart_data["Cenário"] = chart_data["Cenário"].replace(
            {"Otimizada": "Roteirizada"}
        )
        chart = (
            alt.Chart(chart_data)
            .mark_circle(opacity=0.72, size=75)
            .encode(
                x=alt.X("Instalações:Q", scale=alt.Scale(zero=False)),
                y=alt.Y("Distância média km:Q", scale=alt.Scale(zero=False)),
                color=alt.Color("Cenário:N", scale=alt.Scale(domain=["Atual", "Roteirizada"], range=["#637C8E", "#F28E2B"])),
                tooltip=["Cenário:N", "route:N", "Instalações:Q", "Distância exibida:N"],
            )
            .properties(height=320, title="Tamanho da UL × distância média")
            .interactive()
        )
        st.altair_chart(chart, width="stretch")

with tab_map:
    current_lot = analysis["current"].loc[analysis["current"]["lot"].eq(selected_lot)]
    optimized_lot = analysis["optimized"].loc[analysis["optimized"]["lot"].eq(selected_lot)]
    transitions_lot = analysis["transitions"].loc[analysis["transitions"]["lot"].eq(selected_lot)]
    current_routes = analysis["route_metrics"].loc[
        analysis["route_metrics"]["lot"].eq(selected_lot)
        & analysis["route_metrics"]["scenario"].eq("Atual")
    ]
    optimized_routes = analysis["route_metrics"].loc[
        analysis["route_metrics"]["lot"].eq(selected_lot)
        & analysis["route_metrics"]["scenario"].eq("Otimizada")
    ]
    show_route_paths = st.toggle(
        "Exibir traçado por vizinho mais próximo",
        value=False,
        key="show_route_paths",
        help=(
            "Liga as instalações de cada UL em um caminho aberto: começa no ponto "
            "mais afastado do centroide e segue para o ponto não visitado mais próximo."
        ),
    )
    current_paths = None
    optimized_paths = None
    if show_route_paths:
        with st.spinner("Montando os traçados das ULs..."):
            if not current_lot.empty:
                current_paths = load_path_overlay(current_lot)
            if not optimized_lot.empty:
                optimized_paths = load_path_overlay(optimized_lot)
    if current_lot.empty and optimized_lot.empty:
        st.info("Não há coordenadas disponíveis para este lote.")
    else:
        view_state = calculate_view_state(current_lot, optimized_lot)
        current_colors, optimized_colors = aligned_route_colors(
            current_lot, optimized_lot, transitions_lot
        )
        columns = st.columns(2)
        with columns[0]:
            st.markdown("#### Atual")
            if current_lot.empty:
                st.info("Sem base atual para o lote.")
            else:
                st.pydeck_chart(
                    build_map(
                        current_lot, current_routes, view_state, current_colors,
                        current_paths,
                    ),
                    width="stretch",
                )
        with columns[1]:
            st.markdown("#### Roteirizada")
            if optimized_lot.empty:
                st.info("O lote ainda não foi incluído no arquivo roteirizado.")
            else:
                st.pydeck_chart(
                    build_map(
                        optimized_lot, optimized_routes, view_state, optimized_colors,
                        optimized_paths,
                    ),
                    width="stretch",
                )
        st.caption(
            "Os dois mapas usam o mesmo enquadramento. Nos lotes comparáveis, as cores são alinhadas pela maior sobreposição de instalações, não pelo ID da UL. Os círculos maiores são centroides. Quando ativado, o traçado é uma estimativa aberta por vizinho mais próximo, não uma rota viária real."
        )

with tab_distribution:
    route_selected = analysis["route_metrics"].loc[
        analysis["route_metrics"]["lot"].eq(selected_lot)
    ].copy()
    route_selected["Cenário"] = route_selected["scenario"].replace(
        {"Otimizada": "Roteirizada"}
    )
    selected_field = f"{method_prefix}_mean_km"
    if route_selected.empty:
        st.info("Não há ULs disponíveis neste lote.")
    else:
        chart = (
            alt.Chart(route_selected)
            .mark_boxplot(size=55, extent="min-max")
            .encode(
                x=alt.X("Cenário:N", title="Cenário", sort=["Atual", "Roteirizada"]),
                y=alt.Y(f"{selected_field}:Q", title="Distância média por UL (km)", scale=alt.Scale(zero=False)),
                color=alt.Color("Cenário:N", legend=None, scale=alt.Scale(domain=["Atual", "Roteirizada"], range=["#637C8E", "#F28E2B"])),
                tooltip=["Cenário:N", "route:N", alt.Tooltip(f"{selected_field}:Q", format=".3f")],
            )
            .properties(height=360, title=f"Distribuição entre ULs — {distance_method}")
        )
        st.altair_chart(chart, width="stretch")
        display_columns = [
            "scenario", "route", "installations", f"{method_prefix}_mean_km",
            f"{method_prefix}_median_km", f"{method_prefix}_max_km",
            "radius_mean_km", "route_to_lot_centroid_km", "separation_index",
        ]
        table = route_selected[display_columns].sort_values(
            f"{method_prefix}_mean_km", ascending=False
        ).rename(columns={
            "scenario": "Cenário",
            "route": "UL",
            "installations": "Instalações",
            f"{method_prefix}_mean_km": "Média",
            f"{method_prefix}_median_km": "Mediana",
            f"{method_prefix}_max_km": "Máxima",
            "radius_mean_km": "Raio médio",
            "route_to_lot_centroid_km": "Centroide UL-lote",
            "separation_index": "Índice de separação",
        })
        table["Cenário"] = table["Cenário"].replace(
            {"Otimizada": "Roteirizada"}
        )
        for distance_column in [
            "Média", "Mediana", "Máxima", "Raio médio", "Centroide UL-lote"
        ]:
            table[distance_column] = table[distance_column].map(format_distance)
        st.dataframe(table, hide_index=True, width="stretch")

with tab_total_distance:
    st.subheader("Distância total estimada por lote")
    st.caption(
        "Soma dos caminhos abertos estimados para todas as ULs do lote. O percurso começa na instalação mais afastada do centroide e visita sempre a instalação não visitada mais próxima; não inclui depósito, retorno ao início nem rede viária."
    )
    total_distance_methods = [
        (
            "Vizinho mais próximo — Haversine",
            "nn_path_haversine_km",
            "Usa distâncias geodésicas Haversine diretamente nas coordenadas de latitude e longitude.",
        ),
        (
            "GeoPandas — projeção métrica",
            "nn_path_geopandas_km",
            "Projeta cada lote para a zona UTM local com GeoPandas e calcula o caminho por vizinho mais próximo em metros no plano projetado.",
        ),
    ]
    method_tabs = st.tabs([method[0] for method in total_distance_methods])
    full_comparison = analysis["lot_comparison"]
    selected_comparison = full_comparison.loc[
        full_comparison["lot"].eq(selected_lot)
    ]

    for method_tab, (method_name, field, method_description) in zip(
        method_tabs, total_distance_methods
    ):
        with method_tab:
            st.caption(method_description)
            if selected_comparison.empty:
                st.info("Não há resultado preparado para o lote selecionado.")
                continue

            selected_row = selected_comparison.iloc[0]
            current_field = f"current_{field}"
            routed_field = f"optimized_{field}"
            delta_field = f"{field}_delta"
            reduction_field = f"{field}_reduction_pct"
            current_total = selected_row.get(current_field, np.nan)
            routed_total = selected_row.get(routed_field, np.nan)
            total_delta = selected_row.get(delta_field, np.nan)
            reduction_pct = selected_row.get(reduction_field, np.nan)

            total_kpis = st.columns(4)
            total_kpis[0].metric("Total atual", format_distance(current_total))
            total_kpis[1].metric(
                "Total roteirizado",
                format_distance(routed_total),
                format_distance(total_delta) if pd.notna(total_delta) else None,
                delta_color="inverse",
            )
            total_kpis[2].metric(
                "Redução percentual",
                format_percent(reduction_pct),
                help="Valor positivo indica redução; valor negativo indica aumento do percurso estimado.",
            )
            total_kpis[3].metric(
                "Rotas somadas",
                f"{format_integer(selected_row['current_routes'])} → {format_integer(selected_row['optimized_routes'])}",
                delta_color="off",
            )

            chart_rows = []
            for comparison_row in full_comparison.itertuples(index=False):
                for scenario_label, column in [
                    ("Atual", current_field),
                    ("Roteirizada", routed_field),
                ]:
                    value = getattr(comparison_row, column, np.nan)
                    if pd.notna(value):
                        chart_rows.append(
                            {
                                "Lote": int(comparison_row.lot),
                                "Cenário": scenario_label,
                                "Total km": float(value),
                                "Distância exibida": format_distance(value),
                            }
                        )
            chart_frame = pd.DataFrame(chart_rows)
            if not chart_frame.empty:
                total_chart = (
                    alt.Chart(chart_frame)
                    .mark_bar()
                    .encode(
                        x=alt.X("Lote:O", title="Lote"),
                        xOffset=alt.XOffset("Cenário:N"),
                        y=alt.Y("Total km:Q", title="Distância total estimada (km)"),
                        color=alt.Color(
                            "Cenário:N",
                            scale=alt.Scale(
                                domain=["Atual", "Roteirizada"],
                                range=["#637C8E", "#F28E2B"],
                            ),
                        ),
                        tooltip=["Lote:O", "Cenário:N", "Distância exibida:N"],
                    )
                    .properties(height=360, title=f"Comparativo entre lotes — {method_name}")
                )
                st.altair_chart(total_chart, width="stretch")

            total_table = full_comparison[
                ["lot", "status", current_field, routed_field, delta_field, reduction_field]
            ].copy()
            total_table["status"] = total_table["status"].astype(str).str.replace(
                "otimização", "roteirização", regex=False
            )
            total_table = total_table.rename(columns={
                "lot": "Lote",
                "status": "Status",
                current_field: "Total atual",
                routed_field: "Total roteirizado",
                delta_field: "Variação",
                reduction_field: "Redução %",
            })
            for distance_column in ["Total atual", "Total roteirizado", "Variação"]:
                total_table[distance_column] = total_table[distance_column].map(
                    format_distance
                )
            total_table["Redução %"] = total_table["Redução %"].map(format_percent)
            st.dataframe(total_table, hide_index=True, width="stretch")

with tab_regrouping:
    if stability_row is None:
        st.info("A análise de reagrupamento exige que o lote exista nos dois cenários.")
    else:
        group_kpis = st.columns(5)
        group_kpis[0].metric("Pares mantidos", format_integer(stability_row["retained_pairs"]))
        group_kpis[1].metric("Pares separados", format_integer(stability_row["separated_pairs"]))
        group_kpis[2].metric("Novos pares", format_integer(stability_row["newly_grouped_pairs"]))
        group_kpis[3].metric("Jaccard", format_percent(stability_row["pair_jaccard"]))
        group_kpis[4].metric("ARI", format_number(stability_row["ari"], 3))
        heatmap_data = transitions_lot.copy()
        heatmap_data["current_route"] = heatmap_data["current_route"].astype(str)
        heatmap_data["optimized_route"] = heatmap_data["optimized_route"].astype(str)
        heatmap = (
            alt.Chart(heatmap_data)
            .mark_rect()
            .encode(
                x=alt.X("optimized_route:O", title="UL roteirizada", sort=sorted(heatmap_data["optimized_route"].unique(), key=natural_route_key)),
                y=alt.Y("current_route:O", title="UL atual", sort=sorted(heatmap_data["current_route"].unique(), key=natural_route_key)),
                color=alt.Color("installations:Q", title="Instalações", scale=alt.Scale(scheme="blues")),
                tooltip=["current_route:N", "optimized_route:N", "installations:Q", alt.Tooltip("share_current_route:Q", format=".1%")],
            )
            .properties(height=560, title="Matriz de transição das instalações comuns")
        )
        st.altair_chart(heatmap, width="stretch")
        fragmentation = analysis["fragmentation"].loc[
            analysis["fragmentation"]["lot"].eq(selected_lot)
        ].sort_values("separated_pairs_pct", ascending=False)
        st.markdown("#### ULs atuais mais fragmentadas")
        st.dataframe(
            fragmentation.rename(columns={
                "current_route": "UL atual",
                "common_installations": "Instalações comuns",
                "optimized_routes_received": "ULs roteirizadas recebidas",
                "dominant_optimized_route": "UL dominante",
                "dominant_share": "Participação dominante",
                "fragmentation_index": "Índice de fragmentação",
                "separated_pairs": "Pares separados",
                "separated_pairs_pct": "Pares separados %",
            }),
            hide_index=True,
            width="stretch",
            column_config={
                "Participação dominante": st.column_config.ProgressColumn(format="percent"),
                "Pares separados %": st.column_config.ProgressColumn(format="percent"),
            },
        )

with tab_glossary:
    st.subheader("Como analisar o comparativo")
    st.markdown(
        """
        1. **Selecione um lote comparável** na barra lateral e confirme a quantidade de instalações nos dois cenários.
        2. Use **Todos os pares** para avaliar a compactação geral das ULs e **Vizinho mais próximo** para avaliar a proximidade local entre instalações.
        3. No **Resumo**, verifique se a redução de rotas ocorreu junto com redução das distâncias e do raio médio.
        4. Use **Mapa** e **Dispersão** para localizar ULs extensas, instalações isoladas e valores extremos escondidos pela média. No mapa, ative o traçado para evidenciar saltos longos dentro da UL.
        5. Em **Percurso total**, compare a soma das sequências estimadas por Haversine e por projeção métrica do GeoPandas.
        6. Em **Reagrupamento**, quantifique quanto da composição anterior foi preservada ou reorganizada.
        7. Considere melhora quando houver mais compactação e equilíbrio sem perda relevante de cobertura. Nenhum indicador deve ser analisado isoladamente.
        """
    )

    st.markdown("#### Função de cada aba")
    tabs_guide = pd.DataFrame([
        {
            "Aba": "Resumo",
            "O que apresenta": "Indicadores consolidados e relação entre tamanho da UL e distância média.",
            "Como analisar": "Procure distâncias e raios menores. A redução de rotas é positiva quando não aumenta excessivamente a dispersão ou o desequilíbrio.",
        },
        {
            "Aba": "Mapa",
            "O que apresenta": "Distribuição geográfica das instalações e centroides, com traçado opcional por vizinho mais próximo.",
            "Como analisar": "Ative o traçado e procure segmentos muito longos, que evidenciam instalações isoladas ou descontinuidades. As cores são alinhadas por sobreposição, não pelo ID da UL.",
        },
        {
            "Aba": "Dispersão",
            "O que apresenta": "Boxplot e detalhamento dos indicadores de cada UL.",
            "Como analisar": "Compare mediana, concentração da caixa e extremos. Caixas mais baixas e estreitas geralmente indicam rotas mais compactas e homogêneas.",
        },
        {
            "Aba": "Percurso total",
            "O que apresenta": "Soma dos caminhos abertos estimados para todas as ULs do lote em duas metodologias.",
            "Como analisar": "Compare atual e roteirizada nas duas visões. Redução positiva sugere menor deslocamento em linha reta, mas deve ser confirmada com dados viários ou sequência real.",
        },
        {
            "Aba": "Reagrupamento",
            "O que apresenta": "Matriz de transição, retenção de pares e fragmentação das ULs atuais.",
            "Como analisar": "Identifique quais grupos permaneceram juntos, quais foram separados e para quantas ULs roteirizadas cada UL atual foi distribuída.",
        },
        {
            "Aba": "Glossário",
            "O que apresenta": "Definições, sentido dos indicadores e roteiro recomendado de leitura.",
            "Como analisar": "Use como referência antes de interpretar os resultados ou preparar uma apresentação executiva.",
        },
    ])
    st.dataframe(
        tabs_guide,
        hide_index=True,
        width="stretch",
        column_config={
            "Aba": st.column_config.TextColumn(width="small"),
            "O que apresenta": st.column_config.TextColumn(width="medium"),
            "Como analisar": st.column_config.TextColumn(width="large"),
        },
    )

    st.markdown("#### Glossário dos indicadores")
    indicators_guide = pd.DataFrame([
        {
            "Indicador": "Todos os pares",
            "Definição": "Distâncias entre todas as combinações de duas instalações dentro da mesma UL.",
            "Leitura": "Valores menores indicam maior compactação geral. ULs maiores contribuem com mais pares para o consolidado do lote.",
        },
        {
            "Indicador": "Vizinho mais próximo",
            "Definição": "Distância de cada instalação até a instalação mais próxima da mesma UL.",
            "Leitura": "Valores menores indicam maior proximidade local e ajudam a detectar instalações isoladas.",
        },
        {
            "Indicador": "Percurso NN Haversine",
            "Definição": "Caminho aberto que parte do ponto mais afastado do centroide e visita repetidamente o ponto não visitado mais próximo, medido por Haversine.",
            "Leitura": "O total do lote é a soma dos caminhos de suas ULs. Redução positiva indica menor percurso estimado em linha reta.",
        },
        {
            "Indicador": "Percurso GeoPandas",
            "Definição": "Mesmo caminho guloso calculado após projetar os pontos do lote para a zona UTM local com GeoPandas.",
            "Leitura": "Serve como segunda visão métrica e validação de sensibilidade da estimativa Haversine.",
        },
        {
            "Indicador": "Raio da UL",
            "Definição": "Distância entre cada instalação e o centroide da sua UL.",
            "Leitura": "Média e mediana menores indicam uma UL mais compacta; a máxima evidencia o ponto mais afastado.",
        },
        {
            "Indicador": "Centroide UL–lote",
            "Definição": "Distância entre o centroide de cada UL e o centroide geral do lote.",
            "Leitura": "Mostra como as ULs se distribuem pelo lote. Uma redução não é automaticamente melhor e deve ser lida junto com o mapa.",
        },
        {
            "Indicador": "Coeficiente de variação do tamanho",
            "Definição": "Variação da quantidade de instalações entre as ULs em relação à média.",
            "Leitura": "Valores menores indicam distribuição mais equilibrada de instalações entre rotas.",
        },
        {
            "Indicador": "Índice de separação",
            "Definição": "Distância ao centroide da UL vizinha dividida pelo raio médio da própria UL.",
            "Leitura": "Valores maiores geralmente indicam grupos mais separados em relação à dispersão interna.",
        },
        {
            "Indicador": "Retenção de pares",
            "Definição": "Percentual dos pares de instalações que estavam juntos e continuam juntos após a roteirização.",
            "Leitura": "Valor alto significa maior preservação da estrutura anterior; não significa necessariamente melhor compactação.",
        },
        {
            "Indicador": "Jaccard",
            "Definição": "Similaridade entre os pares agrupados nos dois cenários.",
            "Leitura": "Varia de 0 a 1. Quanto mais próximo de 1, mais semelhantes são os agrupamentos.",
        },
        {
            "Indicador": "ARI",
            "Definição": "Índice de Rand ajustado ao acaso para comparar as duas estruturas de agrupamento.",
            "Leitura": "Próximo de 1 indica estruturas semelhantes; próximo de 0 indica semelhança equivalente ao acaso; pode ser negativo.",
        },
        {
            "Indicador": "Fragmentação",
            "Definição": "Grau em que uma UL atual foi distribuída entre diferentes ULs roteirizadas.",
            "Leitura": "Valores maiores indicam maior reorganização da UL anterior. Consulte também a participação da UL dominante.",
        },
    ])
    st.dataframe(
        indicators_guide,
        hide_index=True,
        width="stretch",
        column_config={
            "Indicador": st.column_config.TextColumn(width="medium"),
            "Definição": st.column_config.TextColumn(width="large"),
            "Leitura": st.column_config.TextColumn(width="large"),
        },
    )

    st.info(
        "Distâncias inferiores a 1 km são exibidas em metros. Os cálculos permanecem armazenados em quilômetros."
    )
    st.warning(
        "Sem sequência de visitas, depósito e rede viária, o percurso total é uma estimativa em linha reta, não a distância rodada, o tempo de viagem ou o custo operacional real."
    )

source_dates = " | ".join(
    f"{item['scenario']}: {item['modified_at']:%d/%m/%Y %H:%M}" for item in analysis["source_info"]
)
snapshot_label = (
    snapshot_generated_at.strftime("%d/%m/%Y %H:%M")
    if snapshot_generated_at is not None
    else "data não disponível"
)
st.caption(f"Snapshot do notebook: {snapshot_label} | Fontes analisadas — {source_dates}")
