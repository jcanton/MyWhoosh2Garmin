#!/usr/bin/env python3
# /// script
# requires-python = "==3.13.*"
# dependencies = [
#     "garth==0.5.2",
#     "fit_tool==0.9.16",
# ]
# ///
"""
Script name: myWhoosh2Garmin.py
Usage: "uv run myWhoosh2Garmin.py"
Description:    Checks for MyNewActivity-<myWhooshVersion>.fit
                Adds avg power and heartrade
                Removes temperature
                Creates backup for the file with a timestamp as a suffix
Credits:        Garth by matin - for authenticating and uploading with
                Garmin Connect.
                https://github.com/matin/garth
                Fit_tool by mtucker - for parsing the fit file.
                https://bitbucket.org/stagescycling/python_fit_tool.git/src
                mw2gc by embeddedc - used as an example to fix the avg's.
                https://github.com/embeddedc/mw2gc
"""
import os
import json
import math
import sys
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
#import tkinter as tk
#from tkinter import filedialog
from datetime import datetime
from getpass import getpass
from pathlib import Path

import garth
from garth.exc import GarthException, GarthHTTPError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.record_message import (
    RecordMessage,
    RecordTemperatureField
)
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.profile_type import (
    Activity,
    Event,
    EventType,
    FileType,
    LapTrigger,
    SessionTrigger,
    Sport,
    SubSport
)


SCRIPT_DIR = Path(__file__).resolve().parent
log_file_path = SCRIPT_DIR / "myWhoosh2Garmin.log"
json_file_path = SCRIPT_DIR /  "backup_path.json"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_file_path)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


TOKENS_PATH = SCRIPT_DIR / '.garth'
FILE_DIALOG_TITLE = "MyWhoosh2Garmin"
# Fix for https://github.com/JayQueue/MyWhoosh2Garmin/issues/2
MYWHOOSH_PREFIX_WINDOWS = "MyWhooshTechnologyService."
GPX_NS = "{http://www.topografix.com/GPX/1/1}"
TPX_NS = "{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}"
EARTH_RADIUS_M = 6371000.0


def get_fitfile_location() -> Path:
    """
    Get the location of the FIT file directory based on the operating system.

    Returns:
        Path: The path to the FIT file directory.

    Raises:
        RuntimeError: If the operating system is unsupported.
        SystemExit: If the target path does not exist.
    """
    if os.name == "posix":  # macOS and Linux
        target_path = (
           Path.home()
           / "Library"
           / "Containers"
           / "com.whoosh.whooshgame"
           / "Data"
           / "Library"
           / "Application Support"
           / "Epic"
           / "MyWhoosh"
           / "Content"
           / "Data"
        )
        if target_path.is_dir():
            return target_path
        else:
            logger.error(f"Target path {target_path} does not exist. "
                         "Check your MyWhoosh installation.")
            sys.exit(1)
    elif os.name == "nt":  # Windows
        try:
            base_path = Path.home() / "AppData" / "Local" / "Packages"
            for directory in base_path.iterdir():
                if (directory.is_dir() and
                        directory.name.startswith(MYWHOOSH_PREFIX_WINDOWS)):
                    target_path = (
                            directory
                            / "LocalCache"
                            / "Local"
                            / "MyWhoosh"
                            / "Content"
                            / "Data"
                )
            if target_path.is_dir():
                return target_path
            else:
                raise FileNotFoundError(f"No valid MyWhoosh directory found in {target_path}")
        except FileNotFoundError as e:
                logger.error(str(e))
        except PermissionError as e:
                logger.error(f"Permission denied: {e}")
        except Exception as e:
                logger.error(f"Unexpected error: {e}")
    else:
        logger.error("Unsupported OS")
        sys.exit(1)


def get_backup_path(json_file=json_file_path) -> Path:
    """
    This function checks if a backup path already exists in a JSON file.
    If it does, it returns the stored path. If the file does not exist,
    it prompts the user to select a directory via a file dialog, saves
    the selected path to the JSON file, and returns it.

    Args:
        json_file (str): Path to the JSON file containing the backup path.

    Returns:
        str or None: The selected backup path or None if no path was selected.
    """
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            backup_path = json.load(f).get('backup_path')
        if backup_path and os.path.isdir(backup_path):
            logger.info(f"Using backup path from JSON: {backup_path}.")
            return Path(backup_path)
        else:
            logger.error("Invalid backup path stored in JSON.")
            sys.exit(1)
    else:
        # root = tk.Tk()
        # root.withdraw()
        # backup_path = filedialog.askdirectory(title=f"Select {FILE_DIALOG_TITLE} "
        #                                       "Directory")
        backup_path = "/Users/jcanton/projects/MyWhoosh2Garmin/backups"
        if not backup_path:
            logger.info("No directory selected, exiting.")
            sys.exit(1)
        with open(json_file, 'w') as f:
            json.dump({'backup_path': backup_path}, f)
        logger.info(f"Backup path saved to {json_file}.")
    return Path(backup_path)

FITFILE_LOCATION = get_fitfile_location()
BACKUP_FITFILE_LOCATION = get_backup_path()

def get_credentials_for_garmin():
    """
    Prompt the user for Garmin credentials and authenticate using Garth.

    Returns:
        None

    Exits:
        Exits with status 1 if authentication fails.
    """
    username = input("Username: ")
    password = getpass("Password: ")
    logger.info("Authenticating...")
    try:
        garth.login(username, password)
        garth.save(TOKENS_PATH)
        print()
        logger.info("Successfully authenticated!")
    except GarthHTTPError:
        logger.info("Wrong credentials. Please check username and password.")
        sys.exit(1)


def authenticate_to_garmin():
    """
    Authenticate the user to Garmin by checking for existing tokens and
    resuming the session, or prompting for credentials if no session
    exists or the session is expired.

    Returns:
        None

    Exits:
        Exits with status 1 if authentication fails.
    """
    try:
        if TOKENS_PATH.exists():
            garth.resume(TOKENS_PATH)
            try:
                logger.info(f"Authenticated as: {garth.client.username}")
            except GarthException:
                logger.info("Session expired. Re-authenticating...")
                get_credentials_for_garmin()
        else:
            logger.info("No existing session. Please log in.")
            get_credentials_for_garmin()
    except GarthException as e:
        logger.info(f"Authentication error: {e}")
        sys.exit(1)


def calculate_avg(values: iter) -> int:
    """
    Calculate the average of a list of values, returning 0 if the list is empty.

    Args:
        values (List[float]): The list of values to average.

    Returns:
        float: The average value or 0 if the list is empty.
    """
    return sum(values) / len(values) if values else 0


def append_value(values: List[int], message: object, field_name: str) -> None:
    """
    Appends a value to the 'values' list based on a field from 'message'.

    Args:
        values (List[int]): The list to append the value to.
        message (object): The object that holds the field value.
        field_name (str): The name of the field to retrieve from the message.

    Returns:
        None
    """
    value=getattr(message, field_name, None)
    values.append(value if value else 0)


def reset_values() -> tuple[List[int], List[int], List[int], List[int]]:
    """
    Resets and returns three empty lists for cadence, power
    and heart rate values.

    Returns:
        tuple: A tuple containing three empty lists
        (cadence, power, and heart rate).
    """
    return  [], [], [], []


def cleanup_fit_file(fit_file_path: Path, new_file_path: Path) -> None:
    """
    Clean up the FIT file by processing and removing unnecessary fields.
    Also, calculate average values for cadence, power, and heart rate.

    Args:
        fit_file_path (Path): The path to the input FIT file.
        new_file_path (Path): The path to save the processed FIT file.

    Returns:
        None
    """
    builder = FitFileBuilder()
    fit_file = FitFile.from_file(str(fit_file_path))
    lap_values, cadence_values, power_values, heart_rate_values = reset_values()

    for record in fit_file.records:
        message = record.message
        if isinstance(message, FileIdMessage):
            # Override manufacturer/product but keep other fields
            message.manufacturer = 1
            message.product = 1836
        if isinstance(message, LapMessage):
            append_value(lap_values, message, "start_time")
            append_value(lap_values, message, "total_elapsed_time")
            append_value(lap_values, message, "total_distance")
            append_value(lap_values, message, "avg_speed")
            append_value(lap_values, message, "max_speed")
            append_value(lap_values, message, "avg_heart_rate")
            append_value(lap_values, message, "max_heart_rate")
            append_value(lap_values, message, "avg_cadence")
            append_value(lap_values, message, "max_cadence")
            append_value(lap_values, message, "total_calories")
        if isinstance(message, RecordMessage):
            message.remove_field(RecordTemperatureField.ID)
            append_value(cadence_values, message, "cadence")
            append_value(power_values, message, "power")
            append_value(heart_rate_values, message, "heart_rate")
        if isinstance(message, SessionMessage):
            if not message.avg_cadence:
                message.avg_cadence = calculate_avg(cadence_values)
            if not message.avg_power:
                message.avg_power = calculate_avg(power_values)
            if not message.avg_heart_rate:
                message.avg_heart_rate = calculate_avg(heart_rate_values)
            lap_values, cadence_values, power_values, heart_rate_values = reset_values()
        builder.add(message)
    builder.build().to_file(str(new_file_path))
    logger.info(f"Cleaned-up file saved as {SCRIPT_DIR}/{new_file_path.name}")


def haversine_distance(start: tuple, end: tuple) -> float:
    """
    Great-circle distance in metres between two (lat, lon) pairs in degrees.

    Args:
        start (tuple): The (latitude, longitude) of the first point.
        end (tuple): The (latitude, longitude) of the second point.

    Returns:
        float: The distance in metres.
    """
    lat1, lon1 = start
    lat2, lon2 = end
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def parse_gpx_trackpoints(gpx_file_path: Path) -> List[dict]:
    """
    Read the trackpoints out of a MyWhoosh .gpx export.

    MyWhoosh writes power as a bare <power> element inside <extensions>
    rather than the namespaced <gpxtpx:pwr>, so it is read from the GPX
    namespace. Heart rate, cadence and temperature use the Garmin
    TrackPointExtension namespace.

    Args:
        gpx_file_path (Path): The path to the .gpx file.

    Returns:
        List[dict]: One dict per trackpoint, in file order.
    """
    root = ET.parse(gpx_file_path).getroot()
    trackpoints = []

    for point in root.iter(f"{GPX_NS}trkpt"):
        time_element = point.find(f"{GPX_NS}time")
        if time_element is None:
            continue

        timestamp = datetime.fromisoformat(
            time_element.text.strip().replace("Z", "+00:00")
        )
        elevation = point.find(f"{GPX_NS}ele")
        extensions = point.find(f"{GPX_NS}extensions")
        power = None if extensions is None else extensions.find(f"{GPX_NS}power")
        track_point = (None if extensions is None
                       else extensions.find(f"{TPX_NS}TrackPointExtension"))

        def reading(tag):
            if track_point is None:
                return None
            element = track_point.find(f"{TPX_NS}{tag}")
            return None if element is None else element.text

        trackpoints.append({
            "timestamp": timestamp,
            "latitude": float(point.get("lat")),
            "longitude": float(point.get("lon")),
            "altitude": float(elevation.text) if elevation is not None else 0.0,
            "power": round(float(power.text)) if power is not None else 0,
            "heart_rate": int(reading("hr") or 0),
            "cadence": int(reading("cad") or 0),
        })

    return trackpoints


def convert_gpx_to_fit(gpx_file_path: Path, new_file_path: Path) -> None:
    """
    Build an activity .fit file from a MyWhoosh .gpx export.

    Distance and speed are not recorded per trackpoint in the .gpx, so both
    are derived from the distance between consecutive points. Temperature is
    dropped, matching cleanup_fit_file. Averages are computed here because
    they are the values Garmin Connect would otherwise show as empty.

    Args:
        gpx_file_path (Path): The path to the .gpx file to convert.
        new_file_path (Path): The path to save the built .fit file to.

    Returns:
        None

    Raises:
        ValueError: If the .gpx file holds no trackpoints.
    """
    trackpoints = parse_gpx_trackpoints(gpx_file_path)
    if not trackpoints:
        raise ValueError(f"No trackpoints found in {gpx_file_path.name}")

    builder = FitFileBuilder(auto_define=True)
    start_time = round(trackpoints[0]["timestamp"].timestamp() * 1000)
    end_time = round(trackpoints[-1]["timestamp"].timestamp() * 1000)

    file_id_message = FileIdMessage()
    file_id_message.type = FileType.ACTIVITY
    file_id_message.manufacturer = 1
    file_id_message.product = 1836
    file_id_message.time_created = start_time
    builder.add(file_id_message)

    cadence_values, power_values, heart_rate_values = [], [], []
    speed_values = []
    distance = 0.0
    previous = None

    for point in trackpoints:
        timestamp = round(point["timestamp"].timestamp() * 1000)
        speed = 0.0
        if previous is not None:
            step = haversine_distance(
                (previous["latitude"], previous["longitude"]),
                (point["latitude"], point["longitude"])
            )
            elapsed = (point["timestamp"] - previous["timestamp"]).total_seconds()
            distance += step
            speed = step / elapsed if elapsed > 0 else 0.0

        record_message = RecordMessage()
        record_message.timestamp = timestamp
        record_message.position_lat = point["latitude"]
        record_message.position_long = point["longitude"]
        record_message.altitude = point["altitude"]
        record_message.distance = distance
        record_message.speed = speed
        record_message.power = point["power"]
        record_message.heart_rate = point["heart_rate"]
        record_message.cadence = point["cadence"]
        builder.add(record_message)

        cadence_values.append(point["cadence"])
        power_values.append(point["power"])
        heart_rate_values.append(point["heart_rate"])
        speed_values.append(speed)
        previous = point

    elapsed_time = (trackpoints[-1]["timestamp"]
                    - trackpoints[0]["timestamp"]).total_seconds()
    average_speed = distance / elapsed_time if elapsed_time else 0.0

    lap_message = LapMessage()
    lap_message.message_index = 0
    lap_message.timestamp = end_time
    lap_message.start_time = start_time
    lap_message.total_elapsed_time = elapsed_time
    lap_message.total_timer_time = elapsed_time
    lap_message.total_distance = distance
    lap_message.avg_speed = average_speed
    lap_message.max_speed = max(speed_values)
    lap_message.avg_power = calculate_avg(power_values)
    lap_message.max_power = max(power_values)
    lap_message.avg_cadence = calculate_avg(cadence_values)
    lap_message.max_cadence = max(cadence_values)
    lap_message.avg_heart_rate = calculate_avg(heart_rate_values)
    lap_message.max_heart_rate = max(heart_rate_values)
    lap_message.event = Event.LAP
    lap_message.event_type = EventType.STOP
    lap_message.lap_trigger = LapTrigger.SESSION_END
    lap_message.sport = Sport.CYCLING
    builder.add(lap_message)

    session_message = SessionMessage()
    session_message.message_index = 0
    session_message.timestamp = end_time
    session_message.start_time = start_time
    session_message.total_elapsed_time = elapsed_time
    session_message.total_timer_time = elapsed_time
    session_message.total_distance = distance
    session_message.avg_speed = average_speed
    session_message.max_speed = max(speed_values)
    session_message.avg_power = calculate_avg(power_values)
    session_message.max_power = max(power_values)
    session_message.avg_cadence = calculate_avg(cadence_values)
    session_message.max_cadence = max(cadence_values)
    session_message.avg_heart_rate = calculate_avg(heart_rate_values)
    session_message.max_heart_rate = max(heart_rate_values)
    session_message.first_lap_index = 0
    session_message.num_laps = 1
    session_message.sport = Sport.CYCLING
    session_message.sub_sport = SubSport.VIRTUAL_ACTIVITY
    session_message.event = Event.SESSION
    session_message.event_type = EventType.STOP
    session_message.trigger = SessionTrigger.ACTIVITY_END
    builder.add(session_message)

    activity_message = ActivityMessage()
    activity_message.timestamp = end_time
    activity_message.total_timer_time = elapsed_time
    activity_message.num_sessions = 1
    activity_message.type = Activity.MANUAL
    activity_message.event = Event.ACTIVITY
    activity_message.event_type = EventType.STOP
    builder.add(activity_message)

    builder.build().to_file(str(new_file_path))
    logger.info(f"Converted {gpx_file_path.name} to {new_file_path.name} "
                f"({len(trackpoints)} records, {distance:.0f} m).")


def get_most_recent_gpx_file(fitfile_location: Path) -> Optional[Path]:
    """
    Returns the most recent .gpx file based
    on versioning in the filename.
    """
    gpx_files = fitfile_location.glob("MyNewActivity-*.gpx")
    gpx_files = sorted(gpx_files, key=lambda f:
                       tuple(map(int, re.findall(r'(\d+)',
                                                 f.stem.split('-')[-1]))),
                       reverse=True)
    return gpx_files[0] if gpx_files else None


def get_most_recent_fit_file(fitfile_location: Path) -> Optional[Path]:
    """
    Returns the most recent .fit file based
    on versioning in the filename.
    """
    fit_files = fitfile_location.glob("MyNewActivity-*.fit")
    fit_files = sorted(fit_files, key=lambda f:
                       tuple(map(int, re.findall(r'(\d+)',
                                                 f.stem.split('-')[-1]))),
                       reverse=True)
    return fit_files[0] if fit_files else None


def generate_new_filename(fit_file: Path) -> str:
    """Generates a new filename with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{fit_file.stem}_{timestamp}.fit"


def resolve_backup_target(source_file: Path) -> Optional[Path]:
    """
    Build the timestamped path to write into the backup folder.

    Args:
        source_file (Path): The activity file the name is derived from.

    Returns:
        Optional[Path]: The path to write to, or None if the backup
        folder has gone missing.
    """
    if not BACKUP_FITFILE_LOCATION.exists():
        logger.error(f"{BACKUP_FITFILE_LOCATION} does not exist."
                     "Did you delete it?")
        return None
    return BACKUP_FITFILE_LOCATION / generate_new_filename(source_file)


def cleanup_and_save_fit_file(fitfile_location: Path) -> Optional[Path]:
    """
    Clean up the most recent .fit file in a directory and save it
    with a timestamped filename.

    Args:
        fitfile_location (Path): The directory containing the .fit files.

    Returns:
        Optional[Path]: The path to the newly saved and cleaned .fit file,
        or None if no .fit file is found or if the path is invalid.
    """
    if not fitfile_location.is_dir():
        logger.info(f"The specified path is not a directory:"
                    f"{fitfile_location}.")
        return None

    logger.debug(f"Checking for .fit files in directory: {fitfile_location}.")
    fit_file = get_most_recent_fit_file(fitfile_location)

    if not fit_file:
        logger.info("No .fit files found.")
        return None

    logger.debug(f"Found the most recent .fit file: {fit_file.name}.")
    new_file_path = resolve_backup_target(fit_file)
    if new_file_path is None:
        return None

    logger.info(f"Cleaning up {new_file_path}.")

    try:
        cleanup_fit_file(fit_file, new_file_path)
        logger.info(f"Successfully cleaned {fit_file.name} "
                    f"and saved it as {new_file_path.name}.")
        return new_file_path
    except Exception as e:
        logger.error(f"Failed to process {fit_file.name}: {e}.")
        return None


def convert_and_save_gpx_file(fitfile_location: Path) -> Optional[Path]:
    """
    Convert the most recent .gpx file in a directory into a .fit file and
    save it with a timestamped filename.

    MyWhoosh 6.2.0 was seen writing MyNewActivity-<version>.gpx instead of
    the .fit file earlier versions produced. This is the fallback for that
    case; when a .fit file is present it is used in preference.

    Args:
        fitfile_location (Path): The directory containing the .gpx files.

    Returns:
        Optional[Path]: The path to the newly written .fit file, or None if
        no .gpx file is found or the conversion fails.
    """
    if not fitfile_location.is_dir():
        logger.info(f"The specified path is not a directory:"
                    f"{fitfile_location}.")
        return None

    gpx_file = get_most_recent_gpx_file(fitfile_location)
    if not gpx_file:
        logger.info("No .gpx files found either.")
        return None

    logger.debug(f"Found the most recent .gpx file: {gpx_file.name}.")
    new_file_path = resolve_backup_target(gpx_file)
    if new_file_path is None:
        return None

    try:
        convert_gpx_to_fit(gpx_file, new_file_path)
        return new_file_path
    except Exception as e:
        logger.error(f"Failed to convert {gpx_file.name}: {e}.")
        return None


def upload_fit_file_to_garmin(new_file_path: Optional[Path]):
    """
    Upload a .fit file to Garmin using the Garth client.

    Args:
        new_file_path (Optional[Path]): The path to the .fit file to upload.

    Returns:
        None
    """
    try:
        if new_file_path and new_file_path.is_file():
            with open(new_file_path, "rb") as f:
                uploaded = garth.client.upload(f)
                logger.debug(uploaded)
        else:
            logger.info(f"Invalid file path: {new_file_path}.")
    except GarthHTTPError:
        logger.info("Duplicate activity found on Garmin Connect.")


def main():
    """
    Main function to authenticate to Garmin, clean and save the FIT file,
    and upload it to Garmin.

    Returns:
        None
    """
    authenticate_to_garmin()
    new_file_path = cleanup_and_save_fit_file(FITFILE_LOCATION)
    if new_file_path is None:
        new_file_path = convert_and_save_gpx_file(FITFILE_LOCATION)
    if new_file_path:
        upload_fit_file_to_garmin(new_file_path)


if __name__ == "__main__":
    main()
