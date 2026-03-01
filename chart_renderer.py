# chart_renderer.py — South Indian Vedic Chart Renderer (Plotly)
# Fixed grid: signs always in same position, house numbers shift with lagna

import plotly.graph_objects as go
from vedic_data import SIGNS, SOUTH_INDIAN_GRID

PLANET_COLORS = {
    "Sun":     "#FF8C00",
    "Moon":    "#4169E1",
    "Mars":    "#DC143C",
    "Mercury": "#228B22",
    "Jupiter": "#DAA520",
    "Venus":   "#FF69B4",
    "Saturn":  "#708090",
    "Rahu":    "#4B0082",
    "Ketu":    "#8B4513",
}

NATURE_COLORS = {
    "Benefic": "#E8F5E9",
    "Malefic": "#FFEBEE",
    "Neutral": "#FFF9C4",
    "Mixed":   "#E3F2FD",
}

def render_south_indian_chart(chart: dict, title: str = "South Indian Vedic Chart",
                               dark_mode: bool = False) -> go.Figure:
    """
    Draw a South Indian Vedic chart using Plotly.
    chart: output dict from astro_engine.calculate_chart()
    """
    bg_color  = "#1a1a2e" if dark_mode else "#FFFDE7"
    grid_color = "#ffffff" if dark_mode else "#1a1a2e"
    text_color = "#ffffff" if dark_mode else "#1a1a2e"
    sign_color = "#334" if dark_mode else "#FFF8E1"
    lagna_cell_color = "#FFD700" if dark_mode else "#FFF176"
    center_color = "#0d0d23" if dark_mode else "#F5F5DC"

    lagna_sign = chart["lagna_sign"]
    planets = chart["planets"]

    # Group planets by sign (for display in sign boxes)
    sign_planets = {}
    for planet_name, data in planets.items():
        s = data["sign"]
        sign_planets.setdefault(s, []).append(planet_name)

    # Build the 4×4 grid
    # Cells: 12 sign cells + 4 center cells (display as one merged area)
    grid_size = 4
    cell_size = 100  # arbitrary units

    shapes = []
    annotations = []

    def cell_rect(row, col, color="#FFF8E1", border_width=2, border_color="#1a1a2e"):
        return dict(
            type="rect",
            x0=col * cell_size, y0=(grid_size - 1 - row) * cell_size,
            x1=(col + 1) * cell_size, y1=(grid_size - row) * cell_size,
            fillcolor=color,
            line=dict(color=border_color, width=border_width),
            layer="below",
        )

    def center_rect():
        return dict(
            type="rect",
            x0=cell_size, y0=cell_size,
            x1=3 * cell_size, y1=3 * cell_size,
            fillcolor=center_color,
            line=dict(color=grid_color, width=3),
            layer="below",
        )

    # Grid positions for each sign
    GRID_POS = SOUTH_INDIAN_GRID  # sign_num -> (row, col)

    # Draw the 12 sign cells
    for sign_num in range(12):
        row, col = GRID_POS[sign_num]
        house_num = ((sign_num - lagna_sign) % 12) + 1
        sign_name = SIGNS[sign_num]["name"][:3]  # abbreviate
        is_lagna = (sign_num == lagna_sign)

        cell_color = lagna_cell_color if is_lagna else sign_color
        shapes.append(cell_rect(row, col, color=cell_color, border_color=grid_color))

        # Center x,y of cell
        cx = (col + 0.5) * cell_size
        cy = (grid_size - 1 - row + 0.5) * cell_size

        # House number (top-left area of cell)
        annotations.append(dict(
            x=col * cell_size + 5, y=(grid_size - row) * cell_size - 5,
            xref="x", yref="y",
            text=f"<b>{house_num}</b>",
            showarrow=False,
            font=dict(size=11, color="#888888" if not dark_mode else "#aaaaaa"),
            xanchor="left", yanchor="top",
        ))

        # Sign abbreviation (bottom-right)
        annotations.append(dict(
            x=(col + 1) * cell_size - 4, y=(grid_size - 1 - row) * cell_size + 4,
            xref="x", yref="y",
            text=f"<i>{sign_name}</i>",
            showarrow=False,
            font=dict(size=9, color="#aaaaaa" if not dark_mode else "#888888"),
            xanchor="right", yanchor="bottom",
        ))

        # Lagna marker
        if is_lagna:
            annotations.append(dict(
                x=cx, y=(grid_size - row) * cell_size - 5,
                xref="x", yref="y",
                text="<b>Lag</b>",
                showarrow=False,
                font=dict(size=10, color="#B8860B"),
                xanchor="center", yanchor="top",
            ))

        # Planets in this sign
        planet_list = sign_planets.get(sign_num, [])
        if planet_list:
            planet_text = _format_planet_list(planet_list, planets)
            annotations.append(dict(
                x=cx, y=cy,
                xref="x", yref="y",
                text=planet_text,
                showarrow=False,
                font=dict(size=11, color=text_color),
                xanchor="center", yanchor="middle",
                align="center",
            ))

    # Draw center area (cosmetic)
    shapes.append(center_rect())

    # Center text — chart title
    annotations.append(dict(
        x=2 * cell_size, y=2 * cell_size,
        xref="x", yref="y",
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(size=12, color=text_color),
        xanchor="center", yanchor="middle",
        align="center",
    ))

    fig = go.Figure()
    fig.update_layout(
        shapes=shapes,
        annotations=annotations,
        xaxis=dict(range=[0, grid_size * cell_size], showgrid=False,
                   zeroline=False, showticklabels=False),
        yaxis=dict(range=[0, grid_size * cell_size], showgrid=False,
                   zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        margin=dict(l=10, r=10, t=10, b=10),
        height=420,
        width=420,
    )
    return fig


def _format_planet_list(planet_names: list, planets: dict) -> str:
    """Format planet names for display in a chart cell."""
    lines = []
    for name in planet_names:
        data = planets.get(name, {})
        sym = data.get("symbol", name[:2])
        deg = data.get("degree", 0)
        retro = " ®" if data.get("retrograde") else ""
        lines.append(f"{sym}{retro}<br>{deg:.1f}°")
    return "<br>".join(lines)


def render_planet_table(chart: dict) -> list:
    """Return a list of dicts suitable for a Streamlit dataframe."""
    rows = []
    lagna_sign = chart["lagna_sign"]
    for name, data in chart["planets"].items():
        rows.append({
            "Planet": name,
            "Sign": data["sign_name"],
            "Degree": f"{data['degree']:.2f}°",
            "House": data["house"],
            "Nakshatra": data["nakshatra_name"],
            "Pada": data["pada"],
            "Nak Lord": data["nakshatra_lord"],
            "R": "℞" if data.get("retrograde") else "",
        })
    return rows
