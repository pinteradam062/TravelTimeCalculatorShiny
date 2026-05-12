from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from shiny import App, reactive, render, ui

from model import run_route_model, TRAIN_TYPES


# =========================
# Route configuration
# =========================
ROUTES = {
    "Providence Line": {
        "url": "https://raw.githubusercontent.com/pinteradam062/TravelTimeCalculatorShiny/main/routes/providence.csv",

        "selected_stops": [
            "Providence",
            "Wickford Junction",
        ],
    },

    "Worcester Line": {
         "url": "https://raw.githubusercontent.com/pinteradam062/TravelTimeCalculatorShiny/main/routes/worcester.csv",
    
         "selected_stops": [
             "Framingham",
             "Worcester",
         ],
     },
}


# =========================
# UI
# =========================
app_ui = ui.page_sidebar(

    ui.sidebar(

        ui.h4("Route input"),

        ui.input_radio_buttons(
            "route_source",
            "Select route source",
            choices={
                "upload": "Upload file",
                "github": "Select from list",
            },
            selected="upload",
        ),

        ui.input_file(
            "route_file",
            "Upload route CSV",
            accept=[".csv"],
        ),

        ui.input_select(
            "github_route",
            "Predefined routes",
            choices={name: name for name in ROUTES.keys()},
        ),

        ui.input_checkbox(
            "include_dwell",
            "Include dwell times",
            value=True,
        ),

        ui.hr(),

        ui.h4("Train selection"),

        ui.input_selectize(
            "trains",
            "Select trains",
            choices=list(TRAIN_TYPES.keys()),
            multiple=True,
        ),

        ui.hr(),

        ui.accordion(
            ui.accordion_panel(
                "Dwell time overrides",
                ui.output_ui("dwell_editor"),
            ),
            open=False,
        ),

        ui.hr(),

        ui.input_action_button(
            "run_btn",
            "Run calculation",
        ),
    ),

    ui.h2("Rail Travel Time Comparison"),

    ui.output_data_frame("results_table"),

    ui.output_plot("segment_plot"),

    ui.output_plot("cumulative_plot"),

    ui.output_plot("distance_time_plot"),

    ui.output_plot("terminal_bar_plot"),
)


# =========================
# Server
# =========================
def server(input, output, session):

    # =========================
    # Load route
    # =========================
    @reactive.calc
    @reactive.event(input.run_btn)
    def route_df():

        source = input.route_source()

        # Upload
        if source == "upload":

            fileinfo = input.route_file()

            if fileinfo:

                return pd.read_csv(
                    fileinfo[0]["datapath"],
                    sep=";",
                )

        # GitHub
        if source == "github":

            selected_name = input.github_route()

            url = ROUTES[selected_name]["url"]

            return pd.read_csv(
                url,
                sep=";",
            )

        # fallback
        return pd.read_csv(
            Path("input_route.csv"),
            sep=";",
        )


    # =========================
    # Dwell editor UI
    # =========================
    @render.ui
    def dwell_editor():

        df = route_df()

        if df.empty:
            return ui.div()

        controls = []

        for idx, row in df.iterrows():

            stop_name = row["stop"]

            default_dwell = int(row["dwell"])

            controls.append(

                ui.input_radio_buttons(
                    id=f"dwell_{idx}",

                    label=stop_name,

                    choices={
                        "30": "30 sec",
                        "90": "90 sec",
                        "120": "120 sec",
                    },

                    selected=str(default_dwell),

                    inline=True,
                )
            )

        return ui.div(*controls)


    # =========================
    # Modified route with overrides
    # =========================
    @reactive.calc
    def modified_route_df():

        df = route_df().copy()

        if df.empty:
            return df

        for idx in df.index:

            input_id = f"dwell_{idx}"

            # input only exists after UI render
            if input_id in input:

                selected_dwell = input[input_id]()

                if selected_dwell is not None:

                    df.loc[idx, "Dwell"] = int(selected_dwell)

        return df


    # =========================
    # Run model
    # =========================
    @reactive.calc
    @reactive.event(input.run_btn)
    def result_df():

        selected_trains = input.trains()

        if not selected_trains:
            return pd.DataFrame()

        return run_route_model(
            df=modified_route_df(),

            selected_trains=selected_trains,

            include_dwell=bool(input.include_dwell()),
        )


    # =========================
    # Results table
    # =========================
    @render.data_frame
    def results_table():

        df = result_df()

        if df.empty:
            return render.DataGrid(df)

        # round numeric columns
        numeric_cols = df.select_dtypes(include="number").columns

        df[numeric_cols] = df[numeric_cols].round(1)

        return render.DataGrid(df)


    # =========================
    # Segment plot
    # =========================
    @render.plot
    def segment_plot():

        df = result_df()

        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 5))

        for train in input.trains():

            ax.plot(
                df["Stop"],
                df[f"Travel time {train} [s]"],
                marker="o",
                label=train,
            )

        ax.set_ylabel("Segment travel time [s]")

        ax.set_xlabel("Stop")

        ax.set_title("Travel time by segment")

        ax.legend()

        plt.xticks(rotation=45, ha="right")

        fig.tight_layout()

        return fig


    # =========================
    # Cumulative plot
    # =========================
    @render.plot
    def cumulative_plot():

        df = result_df()

        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 5))

        for train in input.trains():

            ax.plot(
                df["Stop"],
                df[f"Cumulative {train} [s]"],
                marker="o",
                label=train,
            )

        ax.set_ylabel("Cumulative time [s]")

        ax.set_xlabel("Stop")

        ax.set_title("Cumulative running time")

        ax.legend()

        plt.xticks(rotation=45, ha="right")

        fig.tight_layout()

        return fig


    # =========================
    # Distance-time plot
    # =========================
    @render.plot
    def distance_time_plot():

        df = result_df()

        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(10, 5))

        for train in input.trains():

            ax.plot(
                df[f"Cumulative {train} [s]"],
                df["Total distance [mi]"],
                marker="o",
                label=train,
            )

        ax.set_xlabel("Time [s]")

        ax.set_ylabel("Distance [mi]")

        ax.set_title("Distance–Time Diagram")

        ax.legend()

        fig.tight_layout()

        return fig


    # =========================
    # Terminal cumulative bar plot
    # =========================
    @render.plot
    def terminal_bar_plot():

        df = result_df()

        if df.empty:
            return

        selected_route = input.github_route()

        if selected_route not in ROUTES:
            return

        selected_stops = ROUTES[selected_route]["selected_stops"]

        filtered_df = df[df["Stop"].isin(selected_stops)]

        fig, ax = plt.subplots(figsize=(10, 5))

        x = range(len(filtered_df))

        width = 0.8 / len(input.trains())

        for i, train in enumerate(input.trains()):

            # sec -> min
            values = filtered_df[f"Cumulative {train} [s]"] / 60

            positions = [p + i * width for p in x]

            bars = ax.bar(
                positions,
                values,
                width=width,
                label=train,
            )

            # labels
            for bar in bars:

                height = bar.get_height()

                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_xticks(
            [
                p + width * (len(input.trains()) - 1) / 2
                for p in x
            ]
        )

        ax.set_xticklabels(filtered_df["Stop"])

        ax.set_ylabel("Cumulative running time [min]")

        ax.set_title(
            "Cumulative running time at selected stops"
        )

        ax.legend()

        fig.tight_layout()

        return fig


# =========================
# App
# =========================
app = App(app_ui, server)