from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from shiny import App, reactive, render, ui

from model import run_route_model


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h4("Route input"),
        ui.input_file("route_file", "Upload route CSV", accept=[".csv"]),
        ui.input_checkbox("include_dwell", "Include dwell times", value=True),
        ui.input_action_button("run_btn", "Run calculation"),

        ui.hr(),
        ui.h4("Diesel parameters"),
        ui.input_numeric("diesel_mass", "Diesel mass [kg]", 467000),
        ui.input_numeric("diesel_a0", "Diesel initial acceleration a0 [m/s²]", 0.37),
        ui.input_numeric("diesel_b", "Diesel braking b [m/s²]", 0.70),
        ui.input_numeric("diesel_power", "Diesel power [W]", 2300000),

        ui.hr(),
        ui.h4("EMU parameters"),
        ui.input_numeric("emu_mass", "EMU mass [kg]", 342000),
        ui.input_numeric("emu_a0", "EMU initial acceleration a0 [m/s²]", 1.10),
        ui.input_numeric("emu_b", "EMU braking b [m/s²]", 0.80),
        ui.input_numeric("emu_power", "EMU power [W]", 6400000),
    ),
    ui.h2("Rail Travel Time Calculator"),
    ui.p("Upload a CSV with columns: stop;distance_mi;speed_mph;dwell"),
    ui.output_data_frame("results_table"),
    ui.output_plot("travel_plot"),
    ui.output_plot("cumulative_plot"),
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
        diesel_params = {
            "mass": float(input.diesel_mass()),
            "a0": float(input.diesel_a0()),
            "b": float(input.diesel_b()),
            "power": float(input.diesel_power()),
        }

        emu_params = {
            "mass": float(input.emu_mass()),
            "a0": float(input.emu_a0()),
            "b": float(input.emu_b()),
            "power": float(input.emu_power()),
        }

        return run_route_model(
            df=route_df(),
            diesel_params=diesel_params,
            emu_params=emu_params,
            include_dwell=bool(input.include_dwell()),
        )

    @render.data_frame
    def results_table():
        return render.DataGrid(result_df(), filters=True)

    @render.plot
    def travel_plot():
        df = result_df()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["Stop"], df["Travel time Diesel [s]"], marker="o", label="Diesel")
        ax.plot(df["Stop"], df["Travel time EMU [s]"], marker="o", label="EMU")
        ax.set_ylabel("Segment travel time [s]")
        ax.set_xlabel("Stop")
        ax.set_title("Travel time by segment")
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        return fig

    @render.plot
    def cumulative_plot():
        df = result_df()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["Stop"], df["Cumulative Diesel [s]"], marker="o", label="Diesel")
        ax.plot(df["Stop"], df["Cumulative EMU [s]"], marker="o", label="EMU")
        ax.set_ylabel("Cumulative time [s]")
        ax.set_xlabel("Stop")
        ax.set_title("Cumulative running time")
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        return fig


app = App(app_ui, server)