import argparse
from pathlib import Path
import pandas as pd
from haversine import haversine, Unit
from folium import FeatureGroup, Icon, LayerControl, Map, Marker, PolyLine, Popup


class CreepDetectorWiGLE:
  @staticmethod
  def find_creeps(wiglecsv_file, distance_threshold=0.2, distance_unit=Unit.MILES):
    # Fetch all devices
    df_devices = pd.read_csv(wiglecsv_file, header=1, encoding='latin1')
    
    # Keep a list of unique MAC values
    df_mac_addrs = df_devices['MAC'].drop_duplicates()
    
    # Prepare a DataFrame for the calculated haversines
    df_haversines = pd.DataFrame(columns=['MAC', 'haversine'])
    
    # Calculate and save the haversines
    for _, mac_addr in df_mac_addrs.items():
      min_lat = df_devices.loc[df_devices['MAC'] == mac_addr]['CurrentLatitude'].min()
      max_lat = df_devices.loc[df_devices['MAC'] == mac_addr]['CurrentLatitude'].max()
      min_lon = df_devices.loc[df_devices['MAC'] == mac_addr]['CurrentLongitude'].min()
      max_lon = df_devices.loc[df_devices['MAC'] == mac_addr]['CurrentLongitude'].max()
      hav_val = haversine((min_lat, min_lon), (max_lat, max_lon),
                    unit=distance_unit)
      df_haversines.loc[len(df_haversines.index)] = [mac_addr, hav_val]
    
    # Keep only creeps, those that were seen farther than distance threshold
    df_creeps = df_haversines.loc[df_haversines['haversine'] >= distance_threshold].sort_values(by=['haversine'],
                                                ascending=False)
    
    # Prepare creeps' history
    creeps = dict()
    for _, creep in df_creeps.iterrows():
      df_history = df_devices.loc[df_devices['MAC'] == creep['MAC']]
      # Need to confirm if CurrentLatitude/CurrentLongitude can be other than a 0.0 for no coords
      df_history = df_history[(df_history['CurrentLatitude'] != 0.0) & (df_history['CurrentLongitude'] != 0.0)]\
        .sort_values(by=['FirstSeen'])

      creeps[creep['MAC']] = df_history[["FirstSeen", "CurrentLatitude", "CurrentLongitude", "Channel", "RSSI", "SSID", "Type"]]

    return creeps

  @classmethod
  def create_map(CreepDetectorClass, wiglecsv_file, output_file=None, distance_threshold=0.2, distance_unit=Unit.MILES):
    # Let's get our creeps!
    creeps = CreepDetectorClass.find_creeps(wiglecsv_file, distance_threshold, distance_unit)
    
    # Create our GPS track
    df_wigle = pd.read_csv(wiglecsv_file, header=1, encoding='latin1')
    df_drive_points = df_wigle.drop_duplicates(subset=["FirstSeen"]) # keep 1 point per time
    gps_track = df_drive_points[['CurrentLatitude', 'CurrentLongitude']].to_records(index=False)
    
    # Save our start point
    gps_start_coords = (df_drive_points.iloc[0]['CurrentLatitude'], df_drive_points.iloc[0]['CurrentLongitude'])
    
    # Generate our map
    creeps_map = Map(location=gps_start_coords, zoom_start=15)
    PolyLine(gps_track, line_opacity=0.5, weight=4).add_to(creeps_map)
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'beige', 'gray', 'pink', 'black', 'lightgreen',
          'darkblue', 'lightblue', 'lightred', 'darkpurple', 'darkred', 'cadetblue', 'lightgray', 'darkgreen']

    # Plot the creeps
    for i, creep in enumerate(creeps):
      creep_feature = FeatureGroup(name=creep)  # devmac
      for _, marker in creeps[creep].iterrows():
        popup = Popup(f'MAC: {creep}<br>'
                f'SSID: {marker["SSID"]}<br>'
                f'Type: {marker["Type"]}<br>'
                f'First Seen: {marker["FirstSeen"]}<br>'
                f'RSSI: {marker["RSSI"]}', max_width=500)
        Marker(location=(marker["CurrentLatitude"], marker["CurrentLongitude"]), popup=popup,
             icon=Icon(color=colors[i % len(colors)], icon='user-secret',
                 prefix='fa')).add_to(creep_feature)
      creep_feature.add_to(creeps_map)

    # Add toggle controls for creeps
    LayerControl().add_to(creeps_map)

    # Save the map
    try:
      filename = Path(output_file).resolve()
    except TypeError:
      filename = Path(wiglecsv_file).with_suffix('.html').resolve()
    finally:
      creeps_map.save(str(filename))
      print(f"Done! {len(creeps)} creeps found. Map file: {filename.resolve()}")


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('input_file', help="input file (WiGLE CSV, normally ends in .csv.gz)")
  parser.add_argument('-o', '--output', dest='output_file', default=None, help="output file (default: <input_file>.html)")
  parser.add_argument('-d', '--distance', dest='dist_value', default="0.2", help="distance threshold to be considered a creep (default: 0.2)")
  parser.add_argument('-u', '--unit', dest='dist_unit', default="mi", help="km|m|mi|nmi|ft|in|rad|deg (default: mi)")
  args = parser.parse_args()
  
  CreepDetectorWiGLE.create_map(args.input_file, output_file=args.output_file, distance_threshold=float(args.dist_value), distance_unit=args.dist_unit)


if __name__ == "__main__":
  main()
