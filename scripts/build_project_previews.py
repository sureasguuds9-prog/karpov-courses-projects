from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "project-previews"

NAVY = "#172A46"
BLUE = "#2F6BFF"
ORANGE = "#F59E5B"
INK = "#172033"
MUTED = "#667085"
GRID = "#E6EAF0"
LIGHT_BLUE = "#EEF4FF"
LIGHT_ORANGE = "#FFF3E8"
WHITE = "#FFFFFF"


PROJECTS = [
    {
        "file": "project-1-mobile-game-analytics.png",
        "number": "01",
        "title": "Продуктовая аналитика мобильной игры",
        "subtitle": "Когортное удержание · A/B-тест · метрики тематического события",
        "panels": [
            {
                "title": "Day-N retention",
                "labels": ["D1", "D7", "D14"],
                "values": [2.35, 5.86, 4.50],
                "colors": [BLUE, BLUE, BLUE],
                "unit": "%",
                "note": "Когорты 01–09.09.2020",
            },
            {
                "title": "ARPU",
                "labels": ["A", "B"],
                "values": [25.414, 26.751],
                "colors": [BLUE, ORANGE],
                "unit": "",
                "note": "Welch t-test: p = 0,533",
            },
            {
                "title": "Конверсия в покупку",
                "labels": ["A", "B"],
                "values": [0.954, 0.891],
                "colors": [BLUE, ORANGE],
                "unit": "%",
                "note": "χ²-тест: p = 0,035",
            },
        ],
        "decision": "Набор B не раскатывать: рост ARPU не подтверждён, конверсия снизилась значимо.",
        "methods": "Pandas · cohort analysis · Pingouin · SciPy · product metrics",
    },
    {
        "file": "project-2-payment-ab-segmentation.png",
        "number": "02",
        "title": "A/B-тест оплаты и сегментация клиентов",
        "subtitle": "Новая механика оплаты · статистика · SQL-сегментация",
        "panels": [
            {
                "title": "Конверсия в оплату",
                "labels": ["A", "B"],
                "values": [5.07, 4.62],
                "colors": [BLUE, ORANGE],
                "unit": "%",
                "note": "z-тест: p = 0,445",
            },
            {
                "title": "ARPU",
                "labels": ["A", "B"],
                "values": [47.35, 58.06],
                "colors": [BLUE, ORANGE],
                "unit": "",
                "note": "Welch t-test: p = 0,198",
            },
            {
                "title": "ARPPU",
                "labels": ["A", "B"],
                "values": [933.59, 1257.88],
                "colors": [BLUE, ORANGE],
                "unit": "",
                "note": "p = 0,005; пик платежей ≈ 1900",
            },
        ],
        "decision": "Механику не раскатывать: значимо вырос только ARPPU, основной денежный эффект не доказан.",
        "methods": "Pandas · z-test · Welch t-test · bootstrap · PostgreSQL",
    },
    {
        "file": "project-3-premium-price-ab-test.png",
        "number": "03",
        "title": "A/B-тест цены премиум-подписки",
        "subtitle": "Проверка данных · A/A-контроль · влияние цены на конверсию и выручку",
        "panels": [
            {
                "title": "Payer CR",
                "labels": ["Контроль", "Тест"],
                "values": [4.40, 3.39],
                "colors": [BLUE, ORANGE],
                "unit": "%",
                "note": "z-тест: p = 0,0059",
            },
            {
                "title": "Premium CR",
                "labels": ["Контроль", "Тест"],
                "values": [2.34, 1.56],
                "colors": [BLUE, ORANGE],
                "unit": "%",
                "note": "z-тест: p = 0,0033",
            },
            {
                "title": "ARPU",
                "labels": ["Контроль", "Тест"],
                "values": [523.21, 534.08],
                "colors": [BLUE, ORANGE],
                "unit": "",
                "note": "Welch t-test: p = 0,9070",
            },
        ],
        "decision": "Новую цену не раскатывать: конверсия снизилась, а рост ARPU статистически не подтверждён.",
        "methods": "Pandas · data quality · A/A-test · z-test · Welch t-test · CI",
    },
]


def _draw_header(fig, project: dict) -> None:
    header = fig.add_axes([0, 0.78, 1, 0.22])
    header.set_facecolor(NAVY)
    header.set_xticks([])
    header.set_yticks([])
    for spine in header.spines.values():
        spine.set_visible(False)

    header.text(
        0.055,
        0.66,
        project["number"],
        color="#9BB6FF",
        fontsize=23,
        fontweight="bold",
        va="center",
    )
    header.text(
        0.12,
        0.66,
        project["title"],
        color=WHITE,
        fontsize=27,
        fontweight="bold",
        va="center",
    )
    header.text(
        0.12,
        0.28,
        project["subtitle"],
        color="#D8E3F6",
        fontsize=14,
        va="center",
    )


def _draw_decision(fig, project: dict, label: str = "ПРОДУКТОВОЕ РЕШЕНИЕ") -> None:
    decision_ax = fig.add_axes([0.055, 0.095, 0.89, 0.12])
    decision_ax.set_axis_off()
    decision_ax.add_patch(
        FancyBboxPatch(
            (0, 0),
            1,
            1,
            boxstyle="round,pad=0.016,rounding_size=0.025",
            facecolor=LIGHT_ORANGE,
            edgecolor=ORANGE,
            linewidth=1.2,
        )
    )
    decision_ax.text(0.025, 0.68, label, color="#A64B12", fontsize=10.5, fontweight="bold")
    decision_ax.text(0.025, 0.31, project["decision"], color=INK, fontsize=13.2, fontweight="bold")


def _draw_footer(fig, project: dict) -> None:
    fig.text(0.055, 0.037, project["methods"], color=MUTED, fontsize=10.5)
    fig.text(0.945, 0.037, "Karpov.Courses · Ярослав Зинченко", color=MUTED, fontsize=10.5, ha="right")


def draw_preview(project: dict) -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=WHITE)
    _draw_header(fig, project)

    left_positions = [0.055, 0.375, 0.695]
    for left, panel in zip(left_positions, project["panels"]):
        ax = fig.add_axes([left, 0.31, 0.25, 0.37])
        ax.set_facecolor(WHITE)
        bars = ax.bar(
            panel["labels"],
            panel["values"],
            color=panel["colors"],
            width=0.56,
            edgecolor=NAVY,
            linewidth=0.7,
        )
        ax.set_title(panel["title"], loc="left", fontsize=13.5, fontweight="bold", color=INK, pad=14)
        ax.set_ylim(0, max(panel["values"]) * 1.34)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", labelsize=11, colors=INK)
        ax.tick_params(axis="y", labelsize=9, colors=MUTED)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(GRID)
        ax.spines["bottom"].set_color(GRID)
        for bar, value in zip(bars, panel["values"]):
            decimals = 3 if value < 30 and not float(value).is_integer() else 2
            value_text = f"{value:.{decimals}f}".replace(".", ",") + panel["unit"]
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(panel["values"]) * 0.045,
                value_text,
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
                color=INK,
            )
        ax.text(
            0.5,
            -0.24,
            panel["note"],
            transform=ax.transAxes,
            fontsize=9.4,
            color=MUTED,
            ha="center",
        )

    _draw_decision(fig, project)
    _draw_footer(fig, project)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / project["file"], dpi=150, facecolor=WHITE)
    plt.close(fig)


PIPELINE_PROJECT = {
    "file": "final-project-pipeline.png",
    "number": "★",
    "title": "От дашборда до алерта",
    "subtitle": "Финальный проект симулятора: дашборд → ETL → отчётность → алерты",
    "stages": [
        {
            "title": "Дашборд",
            "lesson": "урок 2",
            "cadence": "по запросу",
            "tool": "Superset",
        },
        {
            "title": "ETL",
            "lesson": "урок 7",
            "cadence": "ежедневно, batch",
            "tool": "Airflow",
        },
        {
            "title": "Отчётность",
            "lesson": "урок 8",
            "cadence": "ежедневно, 11:00",
            "tool": "Telegram",
        },
        {
            "title": "Алерты",
            "lesson": "урок 9",
            "cadence": "каждые 15 минут",
            "tool": "Telegram",
            "highlight": True,
        },
    ],
    "decision": (
        "Каждая ступень сокращает время до того, как о проблеме узнает человек: "
        "с «пока не откроют дашборд» до 15 минут на IQR-алерт."
    ),
    "methods": "Apache Superset · Airflow · ClickHouse · Telegram · IQR-детектор аномалий",
}


def draw_pipeline_preview(project: dict) -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=WHITE)
    _draw_header(fig, project)

    stages = project["stages"]
    n = len(stages)
    gap = 0.03
    total_gap = gap * (n - 1)
    box_width = (0.89 - total_gap) / n
    box_axes_y, box_axes_h = 0.40, 0.30

    stage_ax = fig.add_axes([0.055, 0.24, 0.89, 0.50])
    stage_ax.set_xlim(0, 1)
    stage_ax.set_ylim(0, 1)
    stage_ax.set_axis_off()

    left = 0.0
    centers = []
    for stage in stages:
        highlight = stage.get("highlight", False)
        face = LIGHT_ORANGE if highlight else LIGHT_BLUE
        edge = ORANGE if highlight else BLUE
        box = FancyBboxPatch(
            (left, box_axes_y),
            box_width,
            box_axes_h,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            facecolor=face,
            edgecolor=edge,
            linewidth=1.4,
            transform=stage_ax.transAxes,
        )
        stage_ax.add_patch(box)
        center = left + box_width / 2
        centers.append(center)
        stage_ax.text(
            center, box_axes_y + box_axes_h * 0.62, stage["title"],
            transform=stage_ax.transAxes, ha="center", va="center",
            fontsize=15, fontweight="bold", color=INK,
        )
        stage_ax.text(
            center, box_axes_y + box_axes_h * 0.24, f"{stage['lesson']} · {stage['tool']}",
            transform=stage_ax.transAxes, ha="center", va="center",
            fontsize=10, color=MUTED,
        )
        cadence_color = "#A64B12" if highlight else "#1F4FB8"
        stage_ax.text(
            center, box_axes_y - 0.10, stage["cadence"],
            transform=stage_ax.transAxes, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=cadence_color,
        )
        left += box_width + gap

    for a, b in zip(centers[:-1], centers[1:]):
        stage_ax.annotate(
            "",
            xy=(b - box_width / 2 - 0.006, box_axes_y + box_axes_h / 2),
            xytext=(a + box_width / 2 + 0.006, box_axes_y + box_axes_h / 2),
            xycoords=stage_ax.transAxes,
            textcoords=stage_ax.transAxes,
            arrowprops=dict(arrowstyle="-|>", color=NAVY, linewidth=1.4, shrinkA=0, shrinkB=0),
        )

    _draw_decision(fig, project, label="ИТОГ КОНВЕЙЕРА")
    _draw_footer(fig, project)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / project["file"], dpi=150, facecolor=WHITE)
    plt.close(fig)


if __name__ == "__main__":
    for item in PROJECTS:
        draw_preview(item)
    draw_pipeline_preview(PIPELINE_PROJECT)
