from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from shiny import App, reactive, render, ui

from model import run_route_model, TRAIN_TYPES


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h4("Route input"),
        ui.input_file("route_file", "Upload route CSV", accept=[".csv"]),
        ui.input_checkbox("include_dwell", "Include dwell times", value=True),

        ui.hr(),
        ui.h4("Train selection"),
        ui.input_selectize(
            "trains",
            "Select trains",
            choices=list(TRAIN_TYPES.keys()),
            multiple=True,
        ),

        ui.input_action_button("run_btn", "Run calculation"),
    ),

    ui.h2("Rail Travel Time Comparison"),
    ui.output_data_frame("results_table"),
    ui.output_plot("segment_plot"),
    ui.output_plot("cumulative_plot"),
    ui.output_plot("distance_time_plot"),
)


def server(input, output, session):

    @reactive.calc
    @reactive.event(input.run_btn)
    def route_df():
        fileinfo = input.route_file()

        if fileinfo:
            path = fileinfo[0]["datapath"]
        else:
            path = Path("input_route.csv")

        return pd.read_csv(path, sep=";")


    @reactive.calc
    @reactive.event(input.run_btn)
    def result_df():
        selected_trains = input.trains()

        if not selected_trains:
            return pd.DataFrame()

        return run_route_model(
            df=route_df(),
            selected_trains=selected_trains,
            include_dwell=bool(input.include_dwell()),
        )


    @render.data_frame
    def results_table():
        df = result_df()
        return render.DataGrid(df, filters=True)


    # =========================
    # Segment travel time plot
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
    # Cumulative time plot
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
    # Distance–Time diagram
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


app = App(app_ui, server)